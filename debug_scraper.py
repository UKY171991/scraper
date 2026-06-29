import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

def test_scraping():
    category = "Law Firm"
    city = "Toronto"
    country = "Canada"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    # Test 1: Google Reviews ONLY
    print("\n=== Test 1: Google Reviews ONLY ===")
    query = f"{category} {city} {country} google reviews"
    print(f"Query: {query}")
    
    time.sleep(2)  # Wait before request
    
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.result')
            print(f"Total results found: {len(items)}")
            
            filtered_count = 0
            for i, r in enumerate(items[:10], 1):
                title_tag = r.select_one('.result__title a') or r.select_one('.result__a')
                snippet_tag = r.select_one('.result__snippet')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # Check for Google Reviews indicators
                    is_google_maps = 'google.com/maps' in link.lower() or 'goo.gl/maps' in link.lower()
                    has_review_keywords = any(keyword in title.lower() or keyword in snippet.lower() 
                                             for keyword in ['review', 'rating', 'star', '★', 'google'])
                    
                    if is_google_maps or has_review_keywords:
                        filtered_count += 1
                        print(f"\n{filtered_count}. {title}")
                        print(f"   Link: {link[:80]}...")
                        if is_google_maps:
                            print("   ✓ GOOGLE MAPS LINK")
                        if has_review_keywords:
                            print("   ✓ HAS REVIEW KEYWORDS")
            
            print(f"\nFiltered results with Google Reviews: {filtered_count}/{len(items)}")
        else:
            print(f"Rate limited or blocked. Try again in a few seconds.")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Elfsight Businesses
    print("\n\n=== Test 2: Elfsight Businesses ===")
    query = f"{category} {city} {country} elfsight"
    print(f"Query: {query}")
    
    time.sleep(3)  # Wait before request
    
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.result')
            print(f"Found: {len(items)} results")
            
            for i, r in enumerate(items[:5], 1):
                title_tag = r.select_one('.result__title a') or r.select_one('.result__a')
                snippet_tag = r.select_one('.result__snippet')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    has_elfsight = 'elfsight' in link.lower() or 'elfsight' in title.lower() or 'elfsight' in snippet.lower()
                    
                    print(f"\n{i}. {title}")
                    print(f"   Link: {link[:80]}...")
                    if has_elfsight:
                        print("   ✓ ELFSIGHT DETECTED")
        else:
            print(f"Rate limited or blocked. Try again in a few seconds.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scraping()
