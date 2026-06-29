import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from .models import Client, ScrapedData, BlacklistedDomain, SearchEngine
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
import re

def index(request):
    clients = Client.objects.all()
    return render(request, 'scraper_app/index.html', {'clients': clients})

def scrape_data(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        client_id = request.POST.get('client')
        category_input = request.POST.get('category', '').strip()
        city_input = request.POST.get('city', '').strip()
        country = request.POST.get('country', '').strip()
        url = request.POST.get('url', '').strip()
        
        client = None
        client_name = ""
        if client_id:
             try:
                 client = Client.objects.get(id=client_id)
                 client_name = client.name
             except Client.DoesNotExist:
                 pass

        # Parse multiple categories and cities (comma-separated)
        categories = [c.strip() for c in category_input.split(',') if c.strip()]
        cities = [c.strip() for c in city_input.split(',') if c.strip()] if city_input else ['']
        
        print(f"DEBUG: Scrape request - Categories: {categories}, Cities: {cities}, Country: '{country}', URL: '{url}', Client: {client_name}")

        raw_results = []
        total_dup_count = 0
        total_saved = 0
        all_skipped_items = []
        
        # Check if URL is provided - if so, scrape directly from URL
        if url:
            # For URL scraping, use first category and city
            category = categories[0] if categories else ''
            city = cities[0] if cities else ''
            print(f"DEBUG: URL scraping mode - passing category='{category}', city='{city}', country='{country}'")
            raw_results, dup_count, saved_count = scrape_from_url(url, category, city, country, client, client_name)
            total_dup_count = dup_count
            total_saved = saved_count
            print(f"DEBUG: scrape_from_url returned {len(raw_results)} results, saved {saved_count}")
            if raw_results:
                print(f"DEBUG: First result - category: '{raw_results[0].get('category')}', city: '{raw_results[0].get('city')}', country: '{raw_results[0].get('country')}'")
        else:
            # Regular search-based scraping - iterate through all combinations
            total_combinations = len(categories) * len(cities)
            current_combination = 0
            
            # Store progress in session for polling
            request.session['scraping_progress'] = {
                'current': 0,
                'total': total_combinations,
                'current_category': '',
                'current_city': '',
                'saved': 0,
                'skipped': 0
            }
            request.session.save()
            
            for category in categories:
                for city in cities:
                    current_combination += 1
                    
                    # Update progress in session
                    request.session['scraping_progress'] = {
                        'current': current_combination,
                        'total': total_combinations,
                        'current_category': category,
                        'current_city': city or 'All cities',
                        'saved': total_saved,
                        'skipped': len(all_skipped_items),
                        'status': f'Searching for {category} in {city or "all cities"}...'
                    }
                    request.session.save()
                    
                    print(f"\n{'='*60}")
                    print(f"PROGRESS: Scraping combination {current_combination}/{total_combinations}")
                    print(f"Category: '{category}', City: '{city}', Country: '{country}'")
                    print(f"{'='*60}")
                    
                    batch_results, dup_count, saved_count, skipped_items, found_urls = perform_scraping(category, city, country, client, client_name)
                    raw_results.extend(batch_results)
                    total_dup_count += dup_count
                    total_saved += saved_count
                    all_skipped_items.extend(skipped_items)
                    print(f"✓ Got {len(batch_results)} results, saved {saved_count} to database for {category} in {city or 'any city'}")
                    
                    # Small delay between combinations to avoid rate limiting
                    # Only add delay if we have more combinations to process
                    if current_combination < total_combinations:
                        time.sleep(0.5)
            
            # Clear progress from session
            if 'scraping_progress' in request.session:
                del request.session['scraping_progress']
                request.session.save()
        
        # For display purposes, prepare final results
        final_results = []
        for r in raw_results:
            # Skip if filtered by country validation
            if r.get('is_invalid_country'):
                continue

            email = (r.get('email') or '').strip()
            phone = (r.get('phone') or '').strip()
            
            # Skip leads with NO contact info
            if not email and not phone:
                continue
            
            # Always use form data for display
            if url:
                # URL scraping - use form values
                final_city = city
                final_country = country
                final_category = category
            else:
                # Search scraping - use form values from the loop
                final_city = r.get('city', '')  # This was set from form in the loop
                final_country = r.get('country', '')  # This was set from form in the loop
                final_category = r.get('category', '')  # This was set from form in the loop
            
            r['client'] = client_name
            r['category'] = final_category
            r['city'] = final_city
            r['country'] = final_country
            r['is_verified'] = False
            
            final_results.append(r)

        # Store results in session for download
        request.session['scraped_data'] = final_results
        
        return JsonResponse({
            'status': 'success', 
            'results': final_results, 
            'count': len(final_results), 
            'saved': total_saved,
            'skipped_duplicates': total_dup_count,
            'skipped_items': all_skipped_items[:50]  # Limit to 50 items for display
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def get_scraping_progress(request):
    """Return current scraping progress from session"""
    progress = request.session.get('scraping_progress', {})
    return JsonResponse(progress)

import concurrent.futures

def scrape_from_url(url, category, city, country, client=None, client_name=""):
    """
    Scrape data directly from a provided URL and save/update to database
    Returns result list, duplicate count, and saved count
    """
    print(f"Scraping from URL: {url} - Category: {category}, City: {city}, Country: {country}")
    
    result = {
        'title': '',
        'link': url,
        'snippet': '',
        'email': None,
        'phone': None,
        'is_elfsight': False,
        'is_verified': False,
        'city': city or '',  # Use provided city
        'country': country or '',  # Use provided country
        'category': category or ''  # Add category
    }
    
    saved_count = 0
    
    # Visit and extract data from the URL
    try:
        visit_and_extract(result)
        
        # Always use form data - never use extracted values
        result['city'] = city
        result['country'] = country
        result['category'] = category
        
        # Extract title from URL if not found
        if not result['title']:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            result['title'] = domain.replace('www.', '').replace('.com', '').replace('.', ' ').title()
        
        # Set snippet if empty
        if not result['snippet']:
            result['snippet'] = f"Direct scrape from {url}"
        
        print(f"Extracted - Email: {result.get('email')}, Phone: {result.get('phone')}, Using Form Data - Category: {category}, City: {city}, Country: {country}")
        
        # Save or update to database if has contact info
        email = (result.get('email') or '').strip()
        phone = (result.get('phone') or '').strip()
        
        if email or phone:
            try:
                obj, created = ScrapedData.objects.update_or_create(
                    link=url,
                    defaults={
                        'client': client,
                        'category': category,  # Always use form category
                        'city': city,  # Always use form city
                        'country': country,  # Always use form country
                        'title': result.get('title', '').strip(),
                        'snippet': result.get('snippet', '').strip(),
                        'email': email,
                        'phone': phone,
                        'is_elfsight': result.get('is_elfsight', False),
                        'is_verified': False
                    }
                )
                saved_count = 1
                action = "CREATED" if created else "UPDATED"
                print(f"✓ {action} URL scrape in database (Cat: {category}, City: {city}, Country: {country})")
            except Exception as e:
                print(f"Error saving URL scrape to DB: {e}")
        
    except Exception as e:
        print(f"Error scraping URL {url}: {e}")
        result['snippet'] = f"Error: {str(e)}"
    
    return [result], 0, saved_count  # Return single result, 0 duplicates, saved count

def perform_scraping(category, city, country, client=None, client_name=""):
    """
    Perform scraping and save results incrementally to database
    Returns count of saved results and skip details
    """
    # Natural query construction (e.g. "Gym Toronto Canada")
    # Avoid "in" which can sometimes limit engine results
    query_parts = [category]
    if city: query_parts.append(city)
    if country: query_parts.append(country)
    
    query = " ".join(query_parts).strip()
    print(f"Scraping query: {query}")
    
    all_results = []
    seen_links = set()
    total_skipped_duplicates = 0
    saved_count = 0
    skipped_items = []  # Track skipped items with reasons
    all_found_urls = []  # Track ALL URLs found from search engines
    
    def add_unique_and_save(new_list):
        nonlocal total_skipped_duplicates, saved_count, skipped_items, all_found_urls
        
        # Get active blacklisted domains from database
        db_blacklist = list(BlacklistedDomain.objects.filter(is_active=True).values_list('domain', flat=True))
        
        # Fallback hardcoded blacklist (in case database is empty)
        fallback_blacklist = [
            # Review & Listing Sites
            'birdeye.com', 'trustpilot.com', 'yelp.com', 'yellowpages.',
            'tripadvisor.', 'bbb.org', 'foursquare.com', 'zomato.com',
            'clutch.co', 'goodfirms.co', 'yably.ca', 'bestratedintoronto.com',
            'threebestrated.', 'threebest.', '3bestrated.',
            
            # Forums & Discussion Sites
            'reddit.com', 'quora.com', 'stackoverflow.com', 'stackexchange.com',
            'answers.yahoo.com', 'thestudentroom.co.uk', 'studentroom.co.uk',
            'lawstudents.', 'studentdoctor.', 'studentforums.',
            'forum.', 'forums.', 'community.', 'discuss.',
            
            # Legal Directories
            'lawyers.com', 'avvo.com', 'findlaw.com', 'martindale.com',
            'superlawyers.com', 'nolo.com', 'bestlawfirms.com', 'lexpert.ca',
            
            # Social Media
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'pinterest.com', 'youtube.com', 'tumblr.com', 'medium.com',
            
            # Maps & Directories
            'google.com/maps', 'maps.google.com', 'mapquest.com',
            'justdial.com', 'indiamart.com', 'sulekha.com', 'indiatimes.com',
            'magicpin.in', 'urbanpro.com', 'timesofindia.',
            
            # Job Sites
            'glassdoor.', 'indeed.com',
            
            # Travel & Booking
            'booking.com', 'expedia.', 'hotels.com', 'airbnb.com',
            'opentable.com', 'urbanspoon.com',
            
            # Home Services
            'homeadvisor.com', 'angi.com', 'thumbtack.com', 'houzz.com',
            'porch.com', 'bark.com',
            
            # Other
            'wikipedia.org', 'zumba.com',
            
            # Search Engines
            'search.yahoo.com', 'search.brave.com',
            
            # Government & Education
            '.gov', '.nic.in', 'gov.in', 'gov.uk', 'usa.gov', 'pib.gov.in',
            '.edu', '.mil', 'india.gov.in'
        ]
        
        # Use database blacklist if available, otherwise use fallback
        blacklist = db_blacklist if db_blacklist else fallback_blacklist
        
        print(f"  Using {len(blacklist)} blacklisted domains ({len(db_blacklist)} from database, {len(fallback_blacklist)} fallback)")
        
        c = 0
        skipped_listing_sites = 0
        for item in new_list:
            link = item['link'].lower()
            title = item.get('title', '').lower()
            
            # Log ALL found URLs
            all_found_urls.append({
                'url': item['link'],
                'title': item.get('title', ''),
                'source': 'search_engine'
            })
            
            if link.startswith('/'): continue
            
            # Skip non-English titles
            non_english_chars = sum(1 for c in title if ord(c) > 127)
            if non_english_chars > len(title) * 0.3:
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Non-English content'
                })
                print(f"  Skipped non-English: {item['title'][:60]}...")
                continue
            
            # Skip businesses without Google Reviews
            has_reviews = item.get('has_reviews', False)
            if not has_reviews:
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'No Google Reviews found'
                })
                print(f"  Skipped (no reviews): {item['title'][:60]}...")
                continue
            
            # Skip blacklisted domains (listing sites)
            is_listing_site = any(domain in link for domain in blacklist)
            if is_listing_site:
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Listing/Review site (blacklisted)'
                })
                print(f"  Skipped listing site: {item['link'][:60]}...")
                continue
            
            # Skip forum posts, discussion threads, and non-business URLs
            forum_keywords = [
                'forum', 'thread', 'topic', 'discussion', 'post', 'comment',
                'reddit.com', 'quora.com', 'stackoverflow', 'answers.yahoo',
                '/forum/', '/thread/', '/topic/', '/discussion/', '/post/',
                'lawstudents', 'studentroom', 'thestudentroom',
                'wiki', 'wikipedia', 'fandom', 'wikia'
            ]
            
            is_forum = any(keyword in link for keyword in forum_keywords)
            if is_forum:
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Forum/Discussion thread (not a business)'
                })
                print(f"  Skipped forum/discussion: {item['link'][:60]}...")
                continue
            
            # Skip URLs with forum-like patterns in title
            title_forum_keywords = ['forum', 'discussion', 'thread', 'post', 'comment', 'question', 'answer']
            if any(keyword in title for keyword in title_forum_keywords):
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Forum/Discussion content'
                })
                print(f"  Skipped forum content: {item['title'][:60]}...")
                continue
            
            # Only accept URLs that look like business websites
            # Must have a proper domain (not just subpages of forums/portals)
            from urllib.parse import urlparse
            parsed = urlparse(item['link'])
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Skip if URL path contains forum-like segments
            bad_path_segments = ['/forum/', '/thread/', '/topic/', '/discussion/', '/post/', '/questions/', '/answers/']
            if any(segment in path for segment in bad_path_segments):
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Forum URL path'
                })
                print(f"  Skipped forum URL: {item['link'][:60]}...")
                continue
            
            # Skip "Top X" / "Best of" ranking pages
            ranking_keywords = [
                'top 10', 'top 5', 'top 20', 'top 30', 'top 50', 'top 100',
                'top ten', 'top five', 'top twenty',
                'best 10', 'best 5', 'best 20', 'best of', 'best in',
                'top rated', 'highest rated', 'top-rated',
                '10 best', '5 best', '20 best', '30 best',
                'rankings', 'ranked', 'list of', 'directory of',
                'best lawyers', 'best doctors', 'best clinics', 'best firms',
                'best restaurants', 'best gyms', 'best services',
                'top lawyers', 'top doctors', 'top clinics', 'top firms'
            ]
            
            is_ranking_page = any(keyword in title for keyword in ranking_keywords)
            if is_ranking_page:
                skipped_listing_sites += 1
                skipped_items.append({
                    'url': item['link'][:80],
                    'reason': 'Ranking page (Top 10/Best of)'
                })
                print(f"  Skipped ranking page: {item['title'][:60]}...")
                continue
            
            if link not in seen_links:
                seen_links.add(link)
                
                # Visit and extract data immediately
                visit_and_extract(item)
                
                # Save or update in database immediately if has contact info
                email = (item.get('email') or '').strip()
                phone = (item.get('phone') or '').strip()
                
                # Skip if no contact info
                if not email and not phone:
                    skipped_items.append({
                        'url': item['link'][:80],
                        'reason': 'No contact info (email/phone)'
                    })
                    print(f"  Skipped (no contact): {item['title'][:50]}...")
                    continue
                
                # Skip if invalid country
                if item.get('is_invalid_country'):
                    skipped_items.append({
                        'url': item['link'][:80],
                        'reason': 'Wrong country'
                    })
                    print(f"  Skipped (wrong country): {item['title'][:50]}...")
                    continue
                
                # Always use form data - never use extracted/hardcoded values
                final_city = city  # Always use form city
                final_country = country  # Always use form country
                final_category = category  # Always use form category
                
                # Update or create in database
                try:
                    obj, created = ScrapedData.objects.update_or_create(
                        link=item.get('link', '').strip(),
                        defaults={
                            'client': client,
                            'category': final_category,
                            'city': final_city,
                            'country': final_country,
                            'title': item.get('title', '').strip(),
                            'snippet': item.get('snippet', '').strip(),
                            'email': email,
                            'phone': phone,
                            'is_elfsight': item.get('is_elfsight', False),
                            'is_verified': False
                        }
                    )
                    saved_count += 1
                    action = "CREATED" if created else "UPDATED"
                    print(f"  ✓ {action}: {item['title'][:50]}... (Cat: {final_category}, City: {final_city}, Country: {final_country})")
                except Exception as e:
                    print(f"  Error saving to DB: {e}")
                
                all_results.append(item)
                c += 1
        print(f"Engine batch: {c} new unique business URLs found and saved (skipped {skipped_listing_sites} listing/ranking sites).")

    # Get active search engines from database
    db_engines = SearchEngine.objects.filter(is_active=True).order_by('priority')
    
    if not db_engines.exists():
        print("WARNING: No active search engines found in database. Using default Google and Bing.")
        # Fallback to hardcoded engines
        engines = [
            ('Google Search', scrape_google_reviews_only),
            ('Bing Search', scrape_elfsight_businesses)
        ]
    else:
        print(f"Using {db_engines.count()} active search engine(s) from database:")
        for eng in db_engines:
            print(f"  - {eng.name} (Priority: {eng.priority}, Add Reviews: {eng.add_reviews_keyword})")
        
        # Build engines list from database
        engines = []
        for db_engine in db_engines:
            if 'google' in db_engine.name.lower():
                engines.append((db_engine.name, scrape_google_reviews_only))
            elif 'bing' in db_engine.name.lower():
                engines.append((db_engine.name, scrape_elfsight_businesses))
            else:
                # Generic search engine
                engines.append((db_engine.name, scrape_google_reviews_only))
    
    import random
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    ]

    for name, engine_func in engines:
        # If we already have enough results, we can stop
        if len(all_results) >= 100:  # Increased from 30 to 100
            print(f"Already have {len(all_results)} results, stopping search")
            break 
        
        # Get delay setting from database
        try:
            db_engine = SearchEngine.objects.get(name=name, is_active=True)
            delay = db_engine.delay_between_requests
            max_results = db_engine.max_results
            print(f"\n--- Using {name}: delay={delay}s, max_results={max_results} ---")
        except SearchEngine.DoesNotExist:
            delay = 2.0  # Default delay
            max_results = 50  # Increased default
            print(f"\n--- Using {name}: default settings (delay=2s, max=50) ---")
        
        # Try multiple variations to get results for the specific city
        search_queries = [query]
        if city:
            # Fallback if specific city query fails
            search_queries.append(f"{category} {city}")
            search_queries.append(f"{category} near {city} {country}")
            search_queries.append(f"{category} in {city} {country}")
            search_queries.append(f"best {category} {city}")

        for q in search_queries:
            if len(all_results) >= max_results: break
            print(f"\n--- Trying {name} with query: {q} ---")
            try:
                current_headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0"
                }
                
                # Add random delay BEFORE request to avoid rate limiting
                delay_time = delay + random.uniform(0, 1.0)
                print(f"--- Waiting {delay_time:.1f}s before request (anti-blocking) ---")
                time.sleep(delay_time)
                
                batch = engine_func(q, current_headers)
                print(f"--- {name} returned {len(batch) if batch else 0} raw results ---")
                if batch:
                    for r in batch:
                        # Always use form data - set it on every result
                        r['city'] = city
                        r['country'] = country
                        r['category'] = category
                    add_unique_and_save(batch)
                
                # If we found something, no need to try other variations for this engine
                if batch and len(batch) > 0:
                    print(f"--- Found results, moving to next engine ---")
                    break
                else:
                    print(f"--- No results from this query, trying next variation ---")
            except Exception as e:
                print(f"{name} error: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"SCRAPING SUMMARY for '{query}':")
    print(f"  Total URLs found from search: {len(all_found_urls)}")
    print(f"  Total unique results found: {len(all_results)}")
    print(f"  Total saved to database: {saved_count}")
    print(f"  Total skipped: {len(skipped_items)}")
    print(f"{'='*60}\n")
    
    # Log all found URLs for debugging
    if all_found_urls:
        print(f"\nAll URLs found from search engines:")
        for i, url_info in enumerate(all_found_urls[:20], 1):  # Show first 20
            print(f"  {i}. {url_info['title'][:60]}")
            print(f"     {url_info['url'][:80]}")
        if len(all_found_urls) > 20:
            print(f"  ... and {len(all_found_urls) - 20} more URLs")
    
    return all_results, total_skipped_duplicates, saved_count, skipped_items, all_found_urls

def scrape_google_reviews_only(query, headers):
    """
    Search ONLY for businesses that have Google Reviews
    Filters to include only businesses with review indicators
    """
    results = []
    try:
        # Search specifically for businesses with Google reviews
        # Add "business" keyword to avoid forums and discussions
        search_query = f"{query} business google reviews -forum -discussion -thread"
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=en&lr=lang_en"
        
        print(f"  Searching Google (English only): {search_query}")
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Google search results are in divs with class 'g'
            items = soup.select('div.g')
            
            print(f"  Found {len(items)} raw results from Google")
            
            for r in items:
                # Try to find title and link
                title_tag = r.select_one('h3')
                link_tag = r.select_one('a')
                
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    link = link_tag.get('href', '')
                    
                    if not link or link.startswith('/') or 'google.com' in link:
                        continue
                    
                    # Skip non-English titles (check for Chinese, Japanese, Korean, Arabic, etc.)
                    # English text should be mostly ASCII or common Latin characters
                    non_english_chars = sum(1 for c in title if ord(c) > 127)
                    if non_english_chars > len(title) * 0.3:  # If more than 30% non-ASCII, skip
                        print(f"  Skipped non-English: {title[:50]}")
                        continue
                    
                    # Get snippet
                    snippet_tag = r.select_one('.VwiC3b, .s, .st')
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # ONLY include if it has Google Maps/Reviews indicators
                    is_google_maps = 'google.com/maps' in link.lower() or 'goo.gl/maps' in link.lower()
                    has_review_keywords = any(keyword in title.lower() or keyword in snippet.lower() 
                                             for keyword in ['review', 'reviews', 'rating', 'ratings', 'star', '★', 'google'])
                    
                    # Skip if no review indicators
                    if not (is_google_maps or has_review_keywords):
                        print(f"  Skipped (no reviews): {title[:50]}")
                        continue
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'email': None,
                        'phone': None,
                        'is_elfsight': False,
                        'is_verified': False,
                        'has_reviews': True,
                        'is_google_maps': is_google_maps
                    })
                    
    except Exception as e:
        print(f"Google search error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"  Returning {len(results)} results with Google Reviews")
    return results

def scrape_elfsight_businesses(query, headers):
    """
    Secondary search for businesses with reviews using Bing
    """
    results = []
    try:
        # Search for businesses with reviews, exclude forums
        search_query = f"{query} business reviews -forum -discussion"
        url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}&setlang=en"
        
        print(f"  Searching Bing (English only): {search_query}")
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.b_algo')
            
            print(f"  Found {len(items)} raw results from Bing")
            
            for r in items:
                title_tag = r.select_one('h2 a')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    
                    if not link or link.startswith('/'):
                        continue
                    
                    # Skip non-English titles
                    non_english_chars = sum(1 for c in title if ord(c) > 127)
                    if non_english_chars > len(title) * 0.3:  # If more than 30% non-ASCII, skip
                        print(f"  Skipped non-English: {title[:50]}")
                        continue
                    
                    snippet_tag = r.select_one('.b_caption p')
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # ONLY include if it has review indicators
                    has_review_keywords = any(keyword in title.lower() or keyword in snippet.lower() 
                                             for keyword in ['review', 'reviews', 'rating', 'ratings', 'star', '★'])
                    
                    # Skip if no review indicators
                    if not has_review_keywords:
                        print(f"  Skipped (no reviews): {title[:50]}")
                        continue
                    
                    # Check if Elfsight is mentioned (will be verified during page visit)
                    has_elfsight = 'elfsight' in link.lower() or 'elfsight' in title.lower() or 'elfsight' in snippet.lower()
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'email': None,
                        'phone': None,
                        'is_elfsight': has_elfsight,
                        'is_verified': False,
                        'has_reviews': True
                    })
                    
    except Exception as e:
        print(f"Bing search error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"  Returning {len(results)} results with reviews from Bing")
    return results

def visit_and_extract(result):
    url = result['link']
    result['city'] = (result.get('city') or '').strip()
    target_country = (result.get('country') or '').strip()
    
    # Country map for fuzzy matching
    country_variations = {
        'Canada': ['canada', 'ca'],
        'USA': ['usa', 'united states', 'u.s.a', 'america', ' u.s '],
        'India': ['india', ' bhart ', ' in '],
        'UK': ['united kingdom', ' u.k', 'great britain', 'england', 'london']
    }
    
    # Quick Check in Link (Link often contains .ca, .in, .uk)
    link_lower = url.lower()
    if target_country == 'Canada' and ('.ca/' in link_lower or link_lower.endswith('.ca')):
        pass # Good sign
    elif target_country == 'India' and ('.in/' in link_lower or link_lower.endswith('.in')):
        pass # Good sign
    elif target_country == 'UK' and ('.uk/' in link_lower or link_lower.endswith('.uk')):
        pass # Good sign

    # Dynamic Snippet Check: Look for "City, Country" pattern
    if not result['city'] and target_country:
        meta_text = ((result.get('title') or '') + " " + (result.get('snippet') or '')).lower()
        pattern = rf"([a-z\s]+),\s*{re.escape(target_country.lower())}"
        match = re.search(pattern, meta_text)
        if match:
            extracted = match.group(1).strip().title()
            if len(extracted.split()) <= 2:
                result['city'] = extracted

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if resp.status_code == 200:
            text = resp.text
            text_lower = text.lower()
            soup = BeautifulSoup(text, 'html.parser')
            
            # Country verification: Does this site actually belong to the target country?
            if target_country:
                candidates = country_variations.get(target_country, [target_country.lower()])
                # Does the page content mention the country or its variations?
                found_target = any(c in text_lower for c in candidates)
                
                # If country name is missing, but the city matches our search, consider it FOUND
                # (e.g. searching Toronto and found Toronto, even if 'Canada' isn't explicitly on footer)
                if not found_target and result['city']:
                    if result['city'].lower() in text_lower:
                        found_target = True

                # Check for mention of WRONG countries
                wrong_countries = []
                for k, v in country_variations.items():
                    if k != target_country:
                        if any(f" {var} " in f" {text_lower} " for var in v):
                            wrong_countries.append(k)
                
                # If target is NOT found AND a wrong country IS found, this is definitely random data
                if not found_target and len(wrong_countries) > 0:
                    result['is_invalid_country'] = True
                else:
                    result['is_invalid_country'] = False
            else:
                result['is_invalid_country'] = False

            # 1. Elfsight detection
            if any(t in text.lower() for t in ['elfsight.com', 'elfsight-app']):
                result['is_elfsight'] = True
            
            # 2. Dynamic City Scraping (JSON-LD) - The most reliable way
            if not result['city']:
                try:
                    import json
                    scripts = soup.find_all('script', type='application/ld+json')
                    for script in scripts:
                        try:
                            data = json.loads(script.string)
                            # Handle both single object and list of objects
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                addr = item.get('address')
                                if isinstance(addr, dict):
                                    city = addr.get('addressLocality')
                                    if city:
                                        result['city'] = str(city).strip()
                                        break
                                elif isinstance(item.get('location'), dict):
                                    loc_addr = item['location'].get('address')
                                    if isinstance(loc_addr, dict):
                                        city = loc_addr.get('addressLocality')
                                        if city:
                                            result['city'] = str(city).strip()
                                            break
                            if result['city']: break
                        except: continue
                except: pass

            # 3. Dynamic City Scraping (Microdata / Schema.org)
            if not result['city']:
                city_tag = soup.find(attrs={"itemprop": "addressLocality"})
                if city_tag:
                    result['city'] = city_tag.get_text(strip=True)

            # 4. Dynamic City Scraping (Common HTML classes)
            if not result['city']:
                for cls in ['city', 'locality', 'address-city', 'contact-city']:
                    tag = soup.find(class_=re.compile(cls, re.I))
                    if tag:
                        val = tag.get_text(strip=True)
                        if len(val) < 30 and len(val) > 2:
                            result['city'] = val
                            break

            # 5. Last Resort: Meta tags
            if not result['city']:
                meta_city = soup.find('meta', attrs={'name': re.compile('city|location', re.I)})
                if meta_city:
                    result['city'] = meta_city.get('content', '').strip()

            # Emails
            result['email'] = '' # Initialize as empty
            emails = re.findall(r"[a-zA-Z0-9.\-_%+#]+@[a-zA-Z0-9.\-_%+#]+\.[a-zA-Z]{2,4}", text)
            if emails:
                best = None
                for e in set(emails):
                    el = e.lower()
                    if any(g in el for g in ['info@', 'contact@', 'support@']):
                        if not best: best = e
                    elif not any(x in el for x in ['.png', '.jpg', '.gif']):
                        best = e
                        break
                if best:
                    result['email'] = best
            
            # Phone Numbers - Try structured data first (most reliable)
            result['phone'] = ''
            
            # 1. Try JSON-LD structured data
            try:
                import json
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            # Check for telephone field
                            phone = item.get('telephone') or item.get('phone')
                            if phone:
                                result['phone'] = str(phone).strip()
                                break
                            # Check in contactPoint
                            contact = item.get('contactPoint')
                            if isinstance(contact, dict):
                                phone = contact.get('telephone')
                                if phone:
                                    result['phone'] = str(phone).strip()
                                    break
                        if result['phone']:
                            break
                    except:
                        continue
            except:
                pass
            
            # 2. Try microdata/schema.org
            if not result['phone']:
                phone_tag = soup.find(attrs={"itemprop": "telephone"})
                if phone_tag:
                    result['phone'] = phone_tag.get_text(strip=True)
            
            # 3. Try common HTML patterns
            if not result['phone']:
                # Look for tel: links first (most reliable)
                tel_links = soup.find_all('a', href=re.compile(r'^tel:', re.I))
                if tel_links:
                    href = tel_links[0].get('href', '')
                    phone = href.replace('tel:', '').strip()
                    if phone:
                        result['phone'] = phone
            
            # 4. If still no phone, search in text with improved patterns
            # 4. If still no phone, search in text with improved patterns
            if not result['phone']:
                phones = []
                
                # Search with improved patterns
                phone_patterns = [
                    # International format with country code
                    r'\+\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
                    # US/Canada format: (123) 456-7890 or 123-456-7890
                    r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                    # Indian format: +91 98765 43210 or 9876543210
                    r'\+?91[-.\s]?[6-9]\d{9}',
                    r'[6-9]\d{9}',
                    # UK format: +44 20 1234 5678
                    r'\+?44[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
                    # General international
                    r'\+\d{10,15}'
                ]
                
                for pattern in phone_patterns:
                    found = re.findall(pattern, text)
                    phones.extend(found)
                
                # Clean and deduplicate phones
                if phones:
                    unique_phones = []
                    unique_clean = set()
                    
                    for p in phones:
                        # Clean the phone number
                        p_clean = re.sub(r"[^\d+]", "", p)
                        
                        # Validate length (10-15 digits)
                        if len(p_clean) >= 10 and len(p_clean) <= 15:
                            # Check if we haven't seen this number
                            if p_clean not in unique_clean:
                                unique_clean.add(p_clean)
                                # Keep original formatting
                                unique_phones.append(p.strip())
                    
                    # Prioritize numbers with '+' (international format), then longer numbers
                    if unique_phones:
                        unique_phones.sort(key=lambda x: (
                            not x.startswith('+'),
                            -len(re.sub(r"[^\d]", "", x))
                        ))
                        result['phone'] = unique_phones[0]
    except: 
        if 'phone' not in result: result['phone'] = ''
    return result

def download_csv(request):
    data = request.session.get('scraped_data', [])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scraped_data_results.csv"'
    writer = csv.writer(response)
    writer.writerow(['Sr No.', 'Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Phone', 'Is Elfsight', 'Verified'])
    
    for i, r in enumerate(data, 1):
        writer.writerow([
            i,
            (r.get('title') or ''), 
            (r.get('link') or ''), 
            (r.get('snippet') or ''), 
            (r.get('category') or ''), 
            (r.get('city') or ''), 
            (r.get('country') or ''), 
            (r.get('email') or ''), 
            (r.get('phone') or ''), 
            'Yes' if r.get('is_elfsight') else 'No',
            'Verified' if (r.get('email') or r.get('phone')) else 'Not Verified'
        ])
    return response

def download_client_csv(request, client_id):
    try:
        client = Client.objects.get(id=client_id)
        data = ScrapedData.objects.filter(client=client).order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="scraped_data_{client.name.replace(" ", "_")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Sr No.', 'Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Phone', 'Is Elfsight', 'Verified'])
        
        for i, row in enumerate(data, 1):
            writer.writerow([
                i,
                row.title, 
                row.link, 
                row.snippet, 
                row.category, 
                row.city, 
                row.country,
                row.email,
                row.phone,
                'Yes' if row.is_elfsight else 'No',
                'Verified' if (row.email or row.phone) else 'Not Verified'
            ])
        return response
    except Client.DoesNotExist:
        return HttpResponse("Client not found", status=404)

def download_verified_client_csv(request, client_id):
    try:
        client = Client.objects.get(id=client_id)
        # Filter ONLY verified data
        data = ScrapedData.objects.filter(client=client, is_verified=True).order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="verified_data_{client.name.replace(" ", "_")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Sr No.', 'Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Phone', 'Is Elfsight', 'Verified'])
        
        for i, row in enumerate(data, 1):
            writer.writerow([
                i,
                row.title, 
                row.link, 
                row.snippet, 
                row.category, 
                row.city, 
                row.country,
                row.email,
                row.phone,
                'Yes' if row.is_elfsight else 'No',
                'Verified' # Since we filtered by is_verified=True
            ])
        return response
    except Client.DoesNotExist:
        return HttpResponse("Client not found", status=404)

# Removed unused scrapers - now only using Google Reviews

