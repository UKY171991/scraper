from duckduckgo_search import DDGS

def test_scraping():
    category = "law firm"
    country = "India"
    query = f"{category} {country}"
    
    print(f"Testing DDGS scraping for: {query}")
    
    try:
        results = []
        with DDGS() as ddgs:
             # Use text search with a simple loop
             gen = ddgs.text(query, max_results=10)
             if gen:
                 for r in gen:
                     results.append(r)
        
        print(f"Found {len(results)} results")
        if results:
            print(f"First result: {results[0]['title']}")
            print(f"Link: {results[0]['href']}")
            print(f"Snippet: {results[0]['body']}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_scraping()
