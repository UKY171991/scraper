import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from .models import Client, ScrapedData
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
import re
import concurrent.futures

def index(request):
    clients = Client.objects.all()
    return render(request, 'scraper_app/index.html', {'clients': clients})

def scrape_data(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        client_id = request.POST.get('client')
        category = request.POST.get('category', '').strip()
        city = request.POST.get('city', '').strip()
        country = request.POST.get('country', '').strip()
        
        client = None
        client_name = ""
        if client_id:
             try:
                 client = Client.objects.get(id=client_id)
                 client_name = client.name
             except Client.DoesNotExist:
                 pass

        print(f"DEBUG: Scrape request - Cat: {category}, City: {city}, Country: {country}, Client: {client_name}")

        raw_results, dup_count = perform_scraping(category, city, country)
        
        # Filter and save ONLY real leads (Must have email or phone)
        final_results = []
        saved_count = 0
        
        for r in raw_results:
            # Skip if filtered by country validation
            if r.get('is_invalid_country'):
                continue

            email = (r.get('email') or '').strip()
            phone = (r.get('phone') or '').strip()
            
            # PRIORitize scraped city over form city
            scraped_city = (r.get('city') or '').strip()
            final_city = scraped_city if scraped_city else city
            final_country = country if country else (r.get('country') or '')
            
            r['client'] = client_name
            r['category'] = category
            r['city'] = final_city
            r['country'] = final_country
            
            # Skip leads with NO contact info - as per user: "if phone or email is empty then do not need to add"
            if not email and not phone:
                continue

            # Default to NOT verified as per user request
            is_verified = False
            r['is_verified'] = is_verified
            
            # Save to database (Skip if URL already exists)
            if not ScrapedData.objects.filter(link=r.get('link')).exists():
                try:
                    ScrapedData.objects.create(
                        client=client,
                        category=category,
                        city=final_city,
                        country=final_country,
                        title=r.get('title', '').strip(),
                        link=r.get('link', '').strip(),
                        snippet=r.get('snippet', '').strip(),
                        email=email,
                        phone=phone,
                        is_elfsight=r.get('is_elfsight', False),
                        is_verified=False # Default to False
                    )
                    saved_count += 1
                except Exception as e:
                    print(f"Error saving to DB: {e}")
            
            # Add to results only if verifiably a business with contact info
            final_results.append(r)

        # Store results in session for download
        request.session['scraped_data'] = final_results
        
        return JsonResponse({
            'status': 'success', 
            'results': final_results, 
            'count': len(final_results), 
            'saved': saved_count,
            'skipped_duplicates': dup_count
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
import concurrent.futures

def perform_scraping(category, city, country):
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
    
    def add_unique(new_list):
        nonlocal total_skipped_duplicates
        # Blacklist of aggregator/social/junk/govt domains
        blacklist = [
            'reddit.com', 'tripadvisor.', 'indiatimes.com', 'justdial.com', 
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'youtube.com', 'pinterest.com', 'yelp.com', 'yellowpages.',
            'magicpin.in', 'urbanpro.com', 'zumba.com', 'timesofindia.',
            'wikipedia.org', 'quora.com', 'medium.com', 'glassdoor.',
            'mapquest.com', 'maps.google.com', 'booking.com', 'expedia.',
            'search.yahoo.com', 'search.brave.com',
            '.gov', '.nic.in', 'gov.in', 'gov.uk', 'usa.gov', 'pib.gov.in',
            '.edu', '.mil', 'india.gov.in'
        ]
        
        c = 0
        for item in new_list:
            link = item['link'].lower()
            if link.startswith('/'): continue
            
            # Skip blacklisted domains
            if any(domain in link for domain in blacklist):
                continue
            
            if link not in seen_links:
                # Check database to prevent duplicates in UI/Processing
                if ScrapedData.objects.filter(link=item['link']).exists():
                    total_skipped_duplicates += 1
                    continue

                seen_links.add(link)
                all_results.append(item)
                c += 1
        print(f"Engine batch: {c} new unique leads found.")

    # Search Engines to try
    engines = [
        ('DuckDuckGo', scrape_duckduckgo),
        ('Brave', scrape_brave),
        ('Yahoo', scrape_yahoo),
        ('Mojeek', scrape_mojeek)
    ]
    
    import random
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0"
    ]

    for name, engine_func in engines:
        # If we already have enough results, we can stop
        if len(all_results) >= 30: break 
        
        # Try multiple variations to get results for the specific city
        search_queries = [query]
        if city:
            # Fallback if specific city query fails
            search_queries.append(f"{category} {city}")
            search_queries.append(f"{category} near {city} {country}")

        for q in search_queries:
            if len(all_results) >= 20: break
            print(f"Trying {name} with query: {q}")
            try:
                current_headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Connection": "keep-alive"
                }
                batch = engine_func(q, current_headers)
                if batch:
                    for r in batch:
                        # Ensure we don't overwrite if engine already found a city
                        if not r.get('city'): r['city'] = (city or '').strip()
                        r['country'] = (country or '').strip()
                    add_unique(batch)
                
                # If we found something, no need to try other variations for this engine
                if batch and len(batch) > 0:
                    break
            except Exception as e:
                print(f"{name} error: {e}")
            time.sleep(random.uniform(0.5, 1.2))

    # Enrichment
    final_results = all_results[:40]
    if final_results:
        print(f"Total unique new found: {len(final_results)}. Enriching...")
        enrich_data(final_results)
    
    return final_results, total_skipped_duplicates

def scrape_duckduckgo(query, headers):
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.result')
            for r in items:
                title_tag = r.select_one('.result__title a')
                snippet_tag = r.select_one('.result__snippet')
                if title_tag:
                    results.append({
                        'title': title_tag.get_text(strip=True),
                        'link': title_tag['href'],
                        'snippet': snippet_tag.get_text(strip=True) if snippet_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False,
                        'is_verified': False
                    })
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
    return results

def scrape_brave(query, headers):
    results = []
    try:
        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Brave selectors often change, try multiple
            items = soup.select('.snippet') or soup.select('.result')
            for r in items:
                title_tag = r.select_one('.heading') or r.select_one('a.title') or r.select_one('a')
                if title_tag:
                    raw_title = title_tag.get_text(" ", strip=True)
                    clean_title = raw_title.split(' - ')[0].split(' | ')[0].split('...')[0]
                    link = title_tag.get('href')
                    if not link and r.select_one('a'):
                        link = r.select_one('a')['href']
                    
                    if not link or link.startswith('/'): continue

                    desc_tag = r.select_one('.snippet-content') or r.select_one('.snippet-description') or r.select_one('.result-content')
                    results.append({
                        'title': clean_title,
                        'link': link,
                        'snippet': desc_tag.get_text(strip=True) if desc_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False,
                        'is_verified': False
                    })
    except Exception as e:
        print(f"Brave error: {e}")
    return results

def scrape_yahoo(query, headers):
    results = []
    try:
        url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('div.algo')
            for r in items:
                title_tag = r.select_one('h3.title a')
                if title_tag:
                    raw_title = title_tag.get_text(" ", strip=True)
                    clean_title = raw_title.split(' - ')[0].split(' | ')[0]
                    
                    link = title_tag['href']
                    # Yahoo often wraps links: r.search.yahoo.com/RK=2/RS=.../RV=2/RE=.../RU=REAL_URL/
                    if 'RU=' in link:
                        try:
                            # Extract the REAL URL from the RU parameter
                            parts = link.split('RU=')
                            real_url = urllib.parse.unquote(parts[1].split('/')[0])
                            link = real_url
                        except: pass

                    snippet_tag = r.select_one('.compText') or r.select_one('.fc-falcon')
                    results.append({
                        'title': clean_title,
                        'link': link,
                        'snippet': snippet_tag.get_text(strip=True) if snippet_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False,
                        'is_verified': False
                    })
    except: pass
    return results

def scrape_searxng(query, headers):
    results = []
    try:
        # Public SearXNG instance
        url = f"https://searx.be/search?q={urllib.parse.quote(query)}&format=json"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for r in data.get('results', []):
                results.append({
                    'title': r.get('title', ''),
                    'link': r.get('url', ''),
                    'snippet': r.get('content', ''),
                    'email': None,
                    'phone': None,
                    'is_elfsight': False,
                    'is_verified': False
                })
    except: pass
    return results

def scrape_mojeek(query, headers):
    results = []
    try:
        url = f"https://www.mojeek.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('li.result')
            for r in items:
                title_tag = r.select_one('a.title')
                snippet_tag = r.select_one('.s')
                if title_tag:
                    results.append({
                        'title': title_tag.get_text(strip=True),
                        'link': title_tag['href'],
                        'snippet': snippet_tag.get_text(strip=True) if snippet_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False,
                        'is_verified': False
                    })
    except: pass
    return results

def enrich_data(results):
    # Sequential or low-parallel visit to avoid IP ban during visit phase
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_result = {executor.submit(visit_and_extract, r): r for r in results}
        for future in concurrent.futures.as_completed(future_to_result):
            try: future.result()
            except: pass

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
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
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
            
            # Phone Numbers (International & Local)
            phone_patterns = [
                r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", # Standard US/International
                r"\+?\d{2}[-.\s]?\d{10}", # Indian with code
                r"[6-9]\d{9}", # Indian 10-digit mobile
                r"\d{3}-\d{3}-\d{4}", # Simple dash
                # Avoid capturing random small numbers
            ]
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, text))
            
            # Check for tel: links (Remove non-numeric junk)
            tel_links = re.findall(r'tel:([^\s\'">]+)', text)
            for tl in tel_links:
                clean_tl = re.sub(r"[^\d+]", "", tl)
                if len(clean_tl) >= 10:
                    phones.append(tl)

            if phones:
                unique_phones = []
                unique_clean = set()
                for p in phones:
                    p_clean = re.sub(r"[^\d+]", "", p)
                    if len(p_clean) >= 10 and len(p_clean) <= 15:
                        if p_clean not in unique_clean:
                            unique_clean.add(p_clean)
                            unique_phones.append(p.strip())
                if unique_phones:
                    result['phone'] = unique_phones[0]
                else:
                    result['phone'] = ''
            else:
                result['phone'] = ''
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

# Dummy removal
def scrape_bing(q, h): return []
def scrape_ask(q, h): return []
def scrape_ecosia(q, h): return []
def scrape_ddg_html(q): return []

