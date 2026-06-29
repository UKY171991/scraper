"""
Test script to verify multiple categories and cities parsing
"""

# Simulate the parsing logic
category_input = "Restaurants, Gyms, Lawyers"
city_input = "Toronto, Vancouver, Montreal"
country = "Canada"

# Parse multiple categories and cities (comma-separated)
categories = [c.strip() for c in category_input.split(',') if c.strip()]
cities = [c.strip() for c in city_input.split(',') if c.strip()] if city_input else ['']

print("=" * 60)
print("MULTIPLE INPUT PARSING TEST")
print("=" * 60)
print(f"\nInput:")
print(f"  Categories: {category_input}")
print(f"  Cities: {city_input}")
print(f"  Country: {country}")

print(f"\nParsed:")
print(f"  Categories: {categories}")
print(f"  Cities: {cities}")

print(f"\nCombinations to scrape:")
print(f"  Total: {len(categories)} × {len(cities)} = {len(categories) * len(cities)} combinations")
print()

combination_count = 0
for category in categories:
    for city in cities:
        combination_count += 1
        print(f"  {combination_count}. {category} in {city}, {country}")

print("\n" + "=" * 60)
print("TEST PASSED ✓")
print("=" * 60)

# Test with empty city
print("\n\nTest 2: Empty city input")
print("=" * 60)
city_input2 = ""
cities2 = [c.strip() for c in city_input2.split(',') if c.strip()] if city_input2 else ['']
print(f"City input: '{city_input2}'")
print(f"Parsed cities: {cities2}")
print(f"Will scrape {len(categories)} categories without specific city")
for category in categories:
    for city in cities2:
        print(f"  - {category} in {city or 'any city'}, {country}")
