import requests
from bs4 import BeautifulSoup
import re
import json

def test_phone_extraction(url):
    print(f"Testing phone extraction from: {url}\n")
    
    try:
        print("Fetching URL...")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=10)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            text = resp.text
            soup = BeautifulSoup(text, 'html.parser')
            
            print("=" * 60)
            print("METHOD 1: JSON-LD Structured Data")
            print("=" * 60)
            try:
                scripts = soup.find_all('script', type='application/ld+json')
                for i, script in enumerate(scripts, 1):
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            phone = item.get('telephone') or item.get('phone')
                            if phone:
                                print(f"Found in JSON-LD #{i}: {phone}")
                            contact = item.get('contactPoint')
                            if isinstance(contact, dict):
                                phone = contact.get('telephone')
                                if phone:
                                    print(f"Found in contactPoint #{i}: {phone}")
                    except Exception as e:
                        print(f"Error parsing JSON-LD #{i}: {e}")
            except Exception as e:
                print(f"No JSON-LD found: {e}")
            
            print("\n" + "=" * 60)
            print("METHOD 2: Microdata/Schema.org")
            print("=" * 60)
            phone_tag = soup.find(attrs={"itemprop": "telephone"})
            if phone_tag:
                print(f"Found: {phone_tag.get_text(strip=True)}")
            else:
                print("Not found")
            
            print("\n" + "=" * 60)
            print("METHOD 3: Tel: Links")
            print("=" * 60)
            tel_links = soup.find_all('a', href=re.compile(r'^tel:', re.I))
            if tel_links:
                for i, link in enumerate(tel_links[:5], 1):
                    href = link.get('href', '')
                    text_content = link.get_text(strip=True)
                    print(f"{i}. href: {href} | text: {text_content}")
            else:
                print("No tel: links found")
            
            print("\n" + "=" * 60)
            print("METHOD 4: Regex Pattern Matching")
            print("=" * 60)
            
            patterns = {
                'International': r'\+\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
                'US/Canada': r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                'Indian +91': r'\+?91[-.\s]?[6-9]\d{9}',
                'Indian 10-digit': r'[6-9]\d{9}',
                'UK': r'\+?44[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
            }
            
            for name, pattern in patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    print(f"\n{name} pattern:")
                    for match in matches[:5]:
                        print(f"  - {match}")
            
            print("\n" + "=" * 60)
            print("FINAL RECOMMENDATION")
            print("=" * 60)
            
            # Try all methods in order
            final_phone = None
            
            # 1. JSON-LD
            try:
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            phone = item.get('telephone') or item.get('phone')
                            if phone:
                                final_phone = str(phone).strip()
                                break
                            contact = item.get('contactPoint')
                            if isinstance(contact, dict):
                                phone = contact.get('telephone')
                                if phone:
                                    final_phone = str(phone).strip()
                                    break
                        if final_phone:
                            break
                    except:
                        continue
            except:
                pass
            
            # 2. Microdata
            if not final_phone:
                phone_tag = soup.find(attrs={"itemprop": "telephone"})
                if phone_tag:
                    final_phone = phone_tag.get_text(strip=True)
            
            # 3. Tel links
            if not final_phone:
                tel_links = soup.find_all('a', href=re.compile(r'^tel:', re.I))
                if tel_links:
                    href = tel_links[0].get('href', '')
                    final_phone = href.replace('tel:', '').strip()
            
            # 4. Regex
            if not final_phone:
                for pattern in patterns.values():
                    matches = re.findall(pattern, text)
                    if matches:
                        final_phone = matches[0]
                        break
            
            if final_phone:
                print(f"✓ Best phone number found: {final_phone}")
            else:
                print("✗ No phone number found")
        else:
            print(f"Failed to fetch URL. Status: {resp.status_code}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test with the URL from the screenshot
    test_phone_extraction("https://bombaybeatsstudios.com/")
