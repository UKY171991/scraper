import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from .models import Client, ScrapedData
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv

def index(request):
    clients = Client.objects.all()
    return render(request, 'scraper_app/index.html', {'clients': clients})

def scrape_data(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        client_id = request.POST.get('client')
        category = request.POST.get('category')
        city = request.POST.get('city', '')
        country = request.POST.get('country')
        
        client_name = "Unknown"
        if client_id:
             try:
                 client = Client.objects.get(id=client_id)
                 client_name = client.name
             except Client.DoesNotExist:
                 pass

        results = perform_scraping(category, city, country)
        
        # Add client info to results and save to DB
        saved_count = 0
        for r in results:
            r['client'] = client_name
            r['category'] = category
            r['city'] = city
            r['country'] = country
            
            # Save to database
            try:
                ScrapedData.objects.create(
                    client=client if client_id else None,
                    category=category,
                    city=city,
                    country=country,
                    title=r.get('title', ''),
                    link=r.get('link', ''),
                    snippet=r.get('snippet', ''),
                    email=r.get('email', ''),
                    phone=r.get('phone', ''),
                    is_elfsight=r.get('is_elfsight', False)
                )
                saved_count += 1
            except Exception as e:
                print(f"Error saving to DB: {e}")

        # Store results in session for download
        request.session['scraped_data'] = results
        
        return JsonResponse({'status': 'success', 'results': results, 'count': len(results), 'saved': saved_count})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
import concurrent.futures

def perform_scraping(category, city, country):
    location_part = f" in {city}" if city else ""
    # Simple, broad query for best results
    query = f"{category}{location_part} {country}"
    print(f"Scraping query: {query}")
    
    all_results = []
    seen_links = set()
    
    def add_unique(new_list):
        for item in new_list:
            # Clean link
            link = item['link']
            if link.startswith('/'): continue
            if 'search.yahoo.com' in link or 'search.brave.com' in link: continue
            
            if link not in seen_links:
                seen_links.add(link)
                all_results.append(item)

    # Search Engines to try - IN ORDER OF RELIABILITY from debug
    engines = [
        ('Brave', scrape_brave),
        ('Yahoo', scrape_yahoo),
        ('SearXNG', scrape_searxng), # Public proxy
        ('Mojeek', scrape_mojeek)
    ]
    
    import random
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0"
    ]

    for name, engine_func in engines:
        if len(all_results) >= 40: break # Good enough
        
        print(f"Trying {name}...")
        try:
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            results = engine_func(query, headers)
            if results:
                # Add city/country context to results
                for r in results:
                    r['city'] = city
                    r['country'] = country
                print(f"{name} found {len(results)} results.")
                add_unique(results)
            else:
                print(f"{name} returned zero.")
        except Exception as e:
            print(f"{name} failed: {e}")
        
        time.sleep(random.uniform(1, 2))

    # Enrichment
    results = all_results[:100]
    if results:
        print(f"Total unique found: {len(results)}. Extracting details...")
        enrich_data(results)
    
    return results

def scrape_brave(query, headers):
    results = []
    try:
        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Brave uses .snippet
            items = soup.select('.snippet')
            for r in items:
                title_tag = r.select_one('.heading') or r.select_one('a')
                if title_tag:
                    # Brave titles often have garbage, let's try to get only the real title
                    raw_title = title_tag.get_text(" ", strip=True)
                    # Simple heuristic: remove everything after common separators if they look like domains
                    clean_title = raw_title.split(' - ')[0].split(' | ')[0].split('...')[0]
                    
                    link = title_tag.get('href') or r.select_one('a')['href']
                    desc_tag = r.select_one('.snippet-content') or r.select_one('.snippet-description')
                    results.append({
                        'title': clean_title,
                        'link': link,
                        'snippet': desc_tag.get_text(strip=True) if desc_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False
                    })
    except: pass
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
                    snippet_tag = r.select_one('.compText') or r.select_one('.fc-falcon')
                    results.append({
                        'title': clean_title,
                        'link': link,
                        'snippet': snippet_tag.get_text(strip=True) if snippet_tag else "",
                        'email': None,
                        'phone': None,
                        'is_elfsight': False
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
                    'is_elfsight': False
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
                        'is_elfsight': False
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
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            text = resp.text
            # Elfsight
            if any(t in text.lower() for t in ['elfsight.com', 'elfsight-app']):
                result['is_elfsight'] = True
            
            # Emails
            import re
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
                result['email'] = best
            
            # Phone Numbers (International & Local)
            phone_patterns = [
                r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", # Standard US/International
                r"\+?\d{2}[-.\s]?\d{10}", # Indian with code
                r"[6-9]\d{9}", # Indian 10-digit mobile
                r"\d{3}-\d{3}-\d{4}", # Simple dash
                r"\d{5}\s\d{6}" # alternative format
            ]
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, text))
            
            # Check for tel: links
            tel_links = re.findall(r'tel:([\d\+\-\s]+)', text)
            if tel_links:
                phones.extend(tel_links)

            if phones:
                # Clean and take unique
                unique_phones = []
                unique_clean = set()
                for p in phones:
                    p_clean = re.sub(r"[^\d+]", "", p)
                    if len(p_clean) >= 10 and len(p_clean) <= 15:
                        if p_clean not in unique_clean:
                            unique_clean.add(p_clean)
                            unique_phones.append(p.strip())
                if unique_phones:
                    # Prefer those with codes or symbols if available
                    result['phone'] = unique_phones[0]
    except: pass
    return result

def download_csv(request):
    data = request.session.get('scraped_data', [])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scraped_data_results.csv"'
    writer = csv.writer(response)
    writer.writerow(['Sr No.', 'Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Phone', 'Is Elfsight'])
    
    for i, r in enumerate(data, 1):
        writer.writerow([
            i,
            r.get('title',''), 
            r.get('link',''), 
            r.get('snippet',''), 
            r.get('category',''), 
            r.get('city',''), 
            r.get('country',''), 
            r.get('email',''), 
            r.get('phone',''), 
            'Yes' if r.get('is_elfsight') else 'No'
        ])
    return response

def download_client_csv(request, client_id):
    try:
        client = Client.objects.get(id=client_id)
        data = ScrapedData.objects.filter(client=client).order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="scraped_data_{client.name.replace(" ", "_")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Sr No.', 'Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Phone', 'Is Elfsight'])
        
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
                'Yes' if row.is_elfsight else 'No'
            ])
        return response
    except Client.DoesNotExist:
        return HttpResponse("Client not found", status=404)

# Dummy removal
def scrape_bing(q, h): return []
def scrape_ask(q, h): return []
def scrape_ecosia(q, h): return []
def scrape_ddg_html(q): return []

