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
import re

def perform_scraping(category, city, country):
    location_part = f" in {city}" if city else ""
    query = f"{category}{location_part} {country}"
    print(f"Scraping query: {query}")
    
    # Try Bing first
    results = scrape_bing(query)
    
    if len(results) < 5:
        print("Bing returned few results, trying DuckDuckGo Lite...")
        ddg_results = scrape_ddg_lite(query)
        # Merge ensuring no duplicates by link
        existing_links = {r['link'] for r in results}
        for r in ddg_results:
            if r['link'] not in existing_links:
                results.append(r)
                if len(results) >= 150:
                    break
                    
    # Visit sites to extract data
    print(f"Visiting {len(results)} links to extract emails and footprints...")
    enriched_results = []
    
    # Use ThreadPoolExecutor to speed up page visits
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_result = {executor.submit(visit_and_extract, r): r for r in results[:150]}
        for future in concurrent.futures.as_completed(future_to_result):
            res = future.result()
            if res:
                enriched_results.append(res)
                
    return enriched_results

def visit_and_extract(result):
    url = result['link']
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            text = response.text
            
            # 1. Check for Elfsight footprint
            # Common markers: 'elfsight-app', 'static.elfsight.com', 'platform.elfsight.com'
            is_elfsight = False
            if 'elfsight.com' in text or 'elfsight-app' in text:
                is_elfsight = True
            
            # 2. Extract Emails
            # Simple regex for emails
            emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
            
            # Filter and prioritize
            valid_emails = []
            generic_emails = []
            
            for email in emails:
                email_lower = email.lower()
                # Basic validation to filter out obvious junk (e.g. image files caught by regex, or extremely long strings)
                if len(email) > 50 or ('.png' in email_lower) or ('.jpg' in email_lower):
                    continue
                    
                if any(x in email_lower for x in ['info@', 'contact@', 'support@', 'admin@', 'hello@', 'sales@']):
                    generic_emails.append(email)
                else:
                    valid_emails.append(email)
            
            # Preference: Specific > Generic
            final_email = None
            if valid_emails:
                final_email = valid_emails[0] # Take first specific one
            elif generic_emails:
                final_email = generic_emails[0] # Fallback to generic
                
            result['email'] = final_email
            result['is_elfsight'] = is_elfsight
            
            return result
    except Exception as e:
        # print(f"Failed to visit {url}: {e}")
        pass
        
    # Return result even if visit failed (metadata still valid), just without extra info
    # Or skip? Let's return original.
    return result

def scrape_bing(query):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    try:
        # Loop for pagination
        for page in range(0, 100, 10): # Bing uses 'first=1', 'first=11' etc.
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&first={page*10 + 1}"
            print(f"Scraping Bing URL: {url}")
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Bing failed with status {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Bing selectors
            items = soup.select('li.b_algo')
            if not items:
                print("No items found on Bing page.")
                break
                
            for r in items:
                title_tag = r.select_one('h2 a')
                snippet_tag = r.select_one('.b_caption p')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'email': None,
                        'is_elfsight': False
                    })
            
            if len(results) >= 150: # Collect a bit more initially before filtering/enriching
                break
            
            time.sleep(1) # Polite delay
             
    except Exception as e:
        print(f"Error scraping Bing: {e}")
        
    return results

def scrape_ddg_lite(query):
    results = []
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {'q': query}
    
    try:
         session = requests.Session()
         response = session.post(url, data=data, headers=headers)
         
         if response.status_code == 200:
             soup = BeautifulSoup(response.text, 'html.parser')
             rows = soup.select('table:nth-of-type(2) tr')
             
             for r in rows:
                 link_tag = r.select_one('a.result-link')
                 snippet_tag = r.select_one('td.result-snippet')
                 
                 if link_tag:
                     title = link_tag.get_text(strip=True)
                     link = link_tag['href']
                     snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                     
                     results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'email': None,
                        'is_elfsight': False
                     })
    except Exception as e:
        print(f"Error scraping DDG Lite: {e}")
        
    return results


def download_csv(request):
    data = request.session.get('scraped_data', [])
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scraped_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Link', 'Description', 'Category', 'City', 'Country', 'Email', 'Is Elfsight'])
    
    for row in data:
        writer.writerow([
            row.get('title', ''), 
            row.get('link', ''), 
            row.get('snippet', ''), 
            row.get('category', ''), 
            row.get('city', ''), 
            row.get('country', ''),
            row.get('email', ''),
            'Yes' if row.get('is_elfsight') else 'No'
        ])
        
    return response
