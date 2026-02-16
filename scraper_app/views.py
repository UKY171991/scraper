import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from .models import Client

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
                    
    return results[:150]

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
                        'snippet': snippet
                    })
            
            # Use 'category', 'city', 'country' keys to be consistent? 
            # The caller expects these but they are constant for the query.
            # We add them at the end or in the loop.
            
            if len(results) >= 100:
                break
            
            time.sleep(1) # Polite delay
            
        # Add metadata
        for r in results:
             # Basic extraction, we don't have these separated easily so we just pass the query params back
             pass
             
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
         # DDG Lite scraping is harder to paginate with simple POSTs without keeping state,
         # but let's try getting the first page at least or following 'next' links if possible.
         # For now, just one page or robust checking.
         
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
                        'snippet': snippet
                     })
    except Exception as e:
        print(f"Error scraping DDG Lite: {e}")
        
    return results


def download_csv(request):
    data = request.session.get('scraped_data', [])
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scraped_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Link', 'Description', 'Category', 'City', 'Country'])
    
    for row in data:
        writer.writerow([row['title'], row['link'], row['snippet'], row['category'], row['city'], row['country']])
        
    return response
