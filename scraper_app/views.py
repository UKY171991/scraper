from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
import requests
from bs4 import BeautifulSoup
import urllib.parse

def index(request):
    return render(request, 'scraper_app/index.html')

def scrape_data(request):
    if request.method == 'POST':
        category = request.POST.get('category')
        city = request.POST.get('city')
        country = request.POST.get('country')
        
        results = perform_scraping(category, city, country)
        
        # Store results in session for download
        request.session['scraped_data'] = results
        
        return render(request, 'scraper_app/results.html', {'results': results, 'category': category, 'city': city, 'country': country})
    return render(request, 'scraper_app/index.html')

def perform_scraping(category, city, country):
    query = f"{category} in {city} {country}"
    url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:  
        print(f"Scraping URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        results = []
        # DuckDuckGo HTML structure (may vary, try generic fallback if empty)
        for result in soup.select('.result'):
            title_tag = result.select_one('.result__a')
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                snippet_tag = result.select_one('.result__snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No description"
                
                results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'category': category,
                    'city': city,
                    'country': country
                })
        
        if not results:
             print("No results found with default selectors. Dumping HTML for debugging (truncated).")
             print(soup.prettify()[:500])

        return results
    except Exception as e:
        print(f"Error scraping: {e}")
        return []


def download_csv(request):
    data = request.session.get('scraped_data', [])
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scraped_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Link', 'Description', 'Category', 'City', 'Country'])
    
    for row in data:
        writer.writerow([row['title'], row['link'], row['snippet'], row['category'], row['city'], row['country']])
        
    return response
