from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import csv
import requests
from bs4 import BeautifulSoup
import urllib.parse

import time
from .models import Client

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
        
        # Add client info to results
        for r in results:
            r['client'] = client_name

        # Store results in session for download
        request.session['scraped_data'] = results
        
        return JsonResponse({'status': 'success', 'results': results, 'count': len(results)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

from duckduckgo_search import DDGS

def perform_scraping(category, city, country):
    location_part = f" in {city}" if city else ""
    query = f"{category}{location_part} {country}"
    
    print(f"Scraping query: {query}")
    results = []
    
    try:
        with DDGS() as ddgs:
            # increasing max_results to ensure we get enough
            # DDGS .text() returns an iterator
            ddgs_gen = ddgs.text(query, max_results=150)
            
            for r in ddgs_gen:
                results.append({
                    'title': r.get('title'),
                    'link': r.get('href'),
                    'snippet': r.get('body'),
                    'category': category,
                    'city': city,
                    'country': country
                })
                
                if len(results) >= 150:
                    break
                    
        return results
    except Exception as e:
        print(f"Error scraping with DDGS: {e}")
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
