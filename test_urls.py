import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

def get_url_list():
    category = "gym"
    city = "Ahmadabad"
    country = "India"
    query = f"{category} in {city} {country}"
    
    print(f"--- COMPLETE URL LIST TEST ---")
    print(f"Searching for: {query}\n")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    
    all_urls = set()
    
    # 3. SearXNG
    try:
        url = f"https://searx.be/search?q={urllib.parse.quote(query)}&format=json"
        resp = requests.get(url, headers={"User-Agent": random.choice(user_agents)}, timeout=10)
        data = resp.json()
        for r in data.get('results', []):
            all_urls.add(r.get('url'))
    except: pass

    # 4. Mojeek
    try:
        url = f"https://www.mojeek.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers={"User-Agent": random.choice(user_agents)}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = [a['href'] for a in soup.select('a.title') if a.has_attr('href')]
        for link in links:
            all_urls.add(link)
    except: pass

    print(f"Total Unique URLs found: {len(all_urls)}")
    print("-" * 50)
    for i, url in enumerate(sorted(all_urls), 1):
        print(f"{i}. {url}")
    print("-" * 50)

if __name__ == "__main__":
    get_url_list()
