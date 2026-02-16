from requests_html import HTMLSession

def test_scraping():
    category = "law firm"
    country = "India"
    query = f"{category} {country}"
    
    print(f"Testing requests-html Google scraping for: {query}")
    
    try:
        session = HTMLSession()
        resp = session.get(f"https://www.google.com/search?q={query}")
        print(f"Status Code: {resp.status_code}")
        
        # Google search result selector often changes, but 'div.tF2Cxc' or 'div.g' is common
        results = resp.html.find('div.g') # Generic container
        
        print(f"Found {len(results)} results")
        
        for r in results:
            title_elm = r.find('h3', first=True)
            link_elm = r.find('a', first=True)
            if title_elm and link_elm:
                print(f"Title: {title_elm.text}")
                print(f"Link: {list(link_elm.absolute_links)[0]}")
                break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scraping()
