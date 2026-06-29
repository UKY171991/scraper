import requests
from bs4 import BeautifulSoup
import urllib.parse

# Test if DuckDuckGo search is working
query = "Gym Nunavut India"
url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

print(f"Testing search: {query}")
print(f"URL: {url}")
print("="*60)

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('.result')
        print(f"Found {len(items)} results")
        
        if len(items) > 0:
            print("\nFirst 3 results:")
            for i, item in enumerate(items[:3], 1):
                title_tag = item.select_one('.result__title a') or item.select_one('.result__a')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    print(f"\n{i}. {title}")
                    print(f"   URL: {link[:80]}")
        else:
            print("\nNo results found!")
            print("HTML preview:")
            print(resp.text[:500])
    else:
        print(f"Error: HTTP {resp.status_code}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
