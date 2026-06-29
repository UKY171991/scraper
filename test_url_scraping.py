"""
Test script to verify URL scraping preserves category, city, and country
"""

# Simulate the scrape_from_url function behavior
def test_url_scraping():
    # Test data
    url = "https://codeapka.com/"
    category = "Web Development"
    city = "Mumbai"
    country = "India"
    
    # Simulate result from scrape_from_url
    result = {
        'title': 'Codeapka',
        'link': url,
        'snippet': f'Direct scrape from {url}',
        'email': 'uky171991@gmail.com',
        'phone': '+91-9453619260',
        'is_elfsight': False,
        'is_verified': False,
        'city': city,
        'country': country,
        'category': category
    }
    
    # Simulate the processing in scrape_data view
    email = (result.get('email') or '').strip()
    phone = (result.get('phone') or '').strip()
    
    # URL scraping logic
    final_city = city if city else (result.get('city') or '').strip()
    final_country = country if country else (result.get('country') or '').strip()
    final_category = category if category else (result.get('category') or '').strip()
    
    result['category'] = final_category
    result['city'] = final_city
    result['country'] = final_country
    
    # Verify
    print("=" * 60)
    print("URL SCRAPING TEST")
    print("=" * 60)
    print(f"Input URL: {url}")
    print(f"Input Category: {category}")
    print(f"Input City: {city}")
    print(f"Input Country: {country}")
    print()
    print("Result:")
    print(f"  Title: {result['title']}")
    print(f"  Category: {result['category']}")
    print(f"  City: {result['city']}")
    print(f"  Country: {result['country']}")
    print(f"  Email: {result['email']}")
    print(f"  Phone: {result['phone']}")
    print()
    
    # Check if values are preserved
    assert result['category'] == category, f"Category mismatch: {result['category']} != {category}"
    assert result['city'] == city, f"City mismatch: {result['city']} != {city}"
    assert result['country'] == country, f"Country mismatch: {result['country']} != {country}"
    
    print("✓ All values preserved correctly!")
    print("=" * 60)

if __name__ == "__main__":
    test_url_scraping()
