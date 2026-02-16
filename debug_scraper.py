import requests
from bs4 import BeautifulSoup
import urllib.parse

def test_all_engines():
    category = "gym"
    country = "India"
    location_part = ""
    query = f"{category}{location_part} {country} reviews business"
    print(f"Testing scraping for: {query}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    # 7. Brave Search
    print("\n--- Testing Brave Search ---")
    try:
        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('.snippet')
        print(f"Brave found: {len(results)}")
        if results:
            title = results[0].select_one('.heading') or results[0].select_one('a')
            print(f"Sample: {title.get_text(strip=True) if title else 'No title'}")
    except Exception as e:
        print(f"Brave Error: {e}")
    
    # 1. Yahoo
    print("\n--- Testing Yahoo ---")
    try:
        url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('div.algo')
        print(f"Yahoo found: {len(results)}")
        if results:
            print(f"Sample: {results[0].select_one('h3').get_text(strip=True)}")
    except Exception as e:
        print(f"Yahoo Error: {e}")

    # 2. Bing
    print("\n--- Testing Bing ---")
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('li.b_algo')
        print(f"Bing found: {len(results)}")
        if results:
            print(f"Sample: {results[0].select_one('h2').get_text(strip=True)}")
    except Exception as e:
        print(f"Bing Error: {e}")

    # 3. DuckDuckGo HTML
    print("\n--- Testing DDG HTML ---")
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={'q': query}, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('.result')
        print(f"DDG found: {len(results)}")
        if results:
            print(f"Sample: {results[0].select_one('.result__a').get_text(strip=True)}")
    except Exception as e:
        print(f"DDG Error: {e}")
        
    # 4. Ask.com
    print("\n--- Testing Ask.com ---")
    try:
        url = f"https://www.ask.com/web?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('.PartialSearchResults-item')
        print(f"Ask found: {len(results)}")
        if results:
            print(f"Sample: {results[0].select_one('a').get_text(strip=True)}")
    except Exception as e:
        print(f"Ask Error: {e}")

    # 6. Ecosia
    print("\n--- Testing Ecosia ---")
    try:
        url = f"https://www.ecosia.org/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.select('a.result-title')
        print(f"Ecosia found: {len(results)}")
        if results:
            print(f"Sample: {results[0].get_text(strip=True)}")
    except Exception as e:
        print(f"Ecosia Error: {e}")

if __name__ == "__main__":
    test_all_engines()
