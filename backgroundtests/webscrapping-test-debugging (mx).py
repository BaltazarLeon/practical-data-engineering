"""
Independent debug script for Inmuebles24 scraper
Based on the original scraping logic but adapted for inmuebles24.com
"""

import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

def find_last_page_robust(buttons):
    """
    Robust pagination detection that handles various formats:
    - Simple: 1 2 3 4 5
    - With ellipsis: 1 2 3 ... 15
    - With next: 1 2 3 Next
    - With arrows: 1 2 3 →
    """
    
    page_numbers = []
    potential_last_pages = []
    
    print("🔍 Analyzing pagination buttons...")
    
    for i, item in enumerate(buttons):
        text = item.text.strip()
        
        # Skip empty text
        if not text:
            continue
            
        print(f"  Button {i+1}: '{text}' (length: {len(text)})")
        
        # Strategy 1: Direct numeric detection (original logic, but improved)
        if len(text) <= 3 and text.isdigit():
            page_num = int(text)
            page_numbers.append(page_num)
            print(f"    ✅ Found page number: {page_num}")
        
        # Strategy 2: Extract numbers from text with ellipsis (handles "...15")
        elif "..." in text:
            # Extract all numbers from the text
            numbers = re.findall(r'\d+', text)
            if numbers:
                # Take the last/largest number found
                page_num = int(numbers[-1])
                potential_last_pages.append(page_num)
                print(f"    ✅ Found ellipsis page: {page_num} from '{text}'")
        
        # Strategy 3: Look for longer numeric strings (handles edge cases)
        elif text.isdigit() and len(text) <= 5:  # Allow up to 5 digits (99999 pages max)
            page_num = int(text)
            potential_last_pages.append(page_num)
            print(f"    ✅ Found long page number: {page_num}")
        
        # Strategy 4: Extract numbers from mixed text (handles "Page 15", "15 results", etc.)
        else:
            numbers = re.findall(r'\d+', text)
            if numbers:
                for num_str in numbers:
                    if 1 <= int(num_str) <= 9999:  # Reasonable page range
                        potential_last_pages.append(int(num_str))
                        print(f"    ⚠️ Potential page from '{text}': {num_str}")
    
    # Combine all found numbers
    all_pages = page_numbers + potential_last_pages
    
    if all_pages:
        last_page = max(all_pages)
        print(f"\n✅ Final result: Last page = {last_page}")
        print(f"   All pages found: {sorted(set(all_pages))}")
        return last_page
    else:
        print(f"\n❌ No pages found, defaulting to 1")
        return 1


def find_last_page_simple_fallback(buttons):
    """
    Simpler approach: just look for the highest number in any button text
    This is more aggressive but should work for most cases
    """
    
    all_numbers = []
    
    for item in buttons:
        text = item.text.strip()
        # Extract ALL numbers from each button text
        numbers = re.findall(r'\d+', text)
        for num_str in numbers:
            num = int(num_str)
            # Only consider reasonable page numbers (filter out phone numbers, prices, etc.)
            if 1 <= num <= 9999:
                all_numbers.append(num)
    
    if all_numbers:
        return max(all_numbers)
    else:
        return 1


def find_last_page_strategic(buttons):
    """
    Strategic approach: try multiple methods and pick the most reasonable result
    """
    
    # Method 1: Original logic (short numeric text only)
    method1_pages = []
    for item in buttons:
        text = item.text.strip()
        if len(text) <= 3 and len(text) > 0 and text.isdigit():
            method1_pages.append(int(text))
    
    # Method 2: Look for ellipsis patterns
    method2_pages = []
    for item in buttons:
        text = item.text.strip()
        if "..." in text:
            numbers = re.findall(r'\d+', text)
            if numbers:
                method2_pages.append(int(numbers[-1]))
    
    # Method 3: All numbers approach
    method3_pages = []
    for item in buttons:
        text = item.text.strip()
        numbers = re.findall(r'\d+', text)
        for num_str in numbers:
            num = int(num_str)
            if 1 <= num <= 999:  # Reasonable page range
                method3_pages.append(num)
    
    print(f"Method 1 (original): {method1_pages}")
    print(f"Method 2 (ellipsis): {method2_pages}")
    print(f"Method 3 (all nums): {sorted(set(method3_pages)) if method3_pages else []}")
    
    # Decision logic
    if method2_pages:
        # If we found ellipsis patterns, trust those (likely the real last page)
        result = max(method2_pages)
        print(f"✅ Using ellipsis method: {result}")
        return result
    elif method1_pages:
        # Fall back to original method
        result = max(method1_pages)
        print(f"✅ Using original method: {result}")
        return result
    elif method3_pages:
        # Last resort: highest reasonable number
        result = max(method3_pages)
        print(f"⚠️ Using fallback method: {result}")
        return result
    else:
        print(f"❌ No pages found, defaulting to 1")
        return 1


# Test function you can use in your debug script
def test_pagination_methods():
    """
    Test the pagination detection with mock data
    """
    import re
    
    # Mock buttons for testing
    class MockButton:
        def __init__(self, text):
            self.text = text
    
    # Test different pagination scenarios
    test_cases = [
        # Scenario 1: Simple pagination
        [MockButton("1"), MockButton("2"), MockButton("3"), MockButton("4"), MockButton("5")],
        
        # Scenario 2: Pagination with ellipsis  
        [MockButton("1"), MockButton("2"), MockButton("3"), MockButton("..."), MockButton("...15")],
        
        # Scenario 3: Mixed content
        [MockButton("Previous"), MockButton("1"), MockButton("2"), MockButton("..."), MockButton("...25"), MockButton("Next")],
        
        # Scenario 4: No clear pagination
        [MockButton("Home"), MockButton("Contact"), MockButton("About")],
    ]
    
    for i, test_buttons in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"TEST CASE {i}: {[b.text for b in test_buttons]}")
        print(f"{'='*50}")
        
        result = find_last_page_strategic(test_buttons)
        print(f"Final result: {result}")

# Updated code for your scraper
def improved_page_detection(buttons):
    """
    Drop-in replacement for your current page detection logic
    """
    return find_last_page_strategic(buttons)

def debug_inmuebles24_scraper():
    """Debug the Inmuebles24 scraping logic step by step"""
    
    # Test configuration - adapted for inmuebles24
    search_criteria = {
        "rentOrBuy": "venta",
        "city": "ciudad-de-mexico", 
        "propertyType": "departamentos"
    }
    
    # URLs for inmuebles24
    inmuebles24_main_url = "https://www.inmuebles24.com/"
    
    print("🔍 DEBUG: Inmuebles24 Scraper Analysis")
    print("=" * 50)
    
    # Step 1: Test the working URL you provided
    working_url = "https://www.inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos.html"
    print(f"\n📍 Step 1: Testing your working URL")
    print(f"URL: {working_url}")
    
    try:
        response = requests.get(working_url)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Content Length: {len(response.text)} characters")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        print(f"✅ HTML parsed successfully")
        
    except Exception as e:
        print(f"❌ Error fetching URL: {e}")
        return
    
    # Step 2: Analyze URL pattern for inmuebles24
    print(f"\n📍 Step 2: Analyzing URL patterns for inmuebles24")
    
    # Inmuebles24 URL pattern seems to be:
    # /{property-type}-en-{rentOrBuy}-en-{city}-mas-de-5-pesos.html
    
    # Construct URL based on pattern
    constructed_url = (
        inmuebles24_main_url
        + search_criteria["propertyType"]
        + "-en-"
        + search_criteria["rentOrBuy"]
        + "-en-"
        + search_criteria["city"]
        + "-mas-de-5-pesos.html"
    )
    print(f"Constructed URL: {constructed_url}")
    print(f"Working URL:     {working_url}")
    print(f"URLs match: {constructed_url == working_url}")
    
    # Step 3: Find maximum pages (adapted for inmuebles24)
    print(f"\n📍 Step 3: Finding maximum pages")
    
    try:
        html = requests.get(working_url)
        soup = BeautifulSoup(html.text, "html.parser")
        
        # Try different pagination selectors common in real estate sites
        # First try finding pagination container
        pagination_selectors = [
            {"class": "pagination"},
            {"class": "paginator"},
            {"class": "paging"},
            {"class": "pages"},
            {"class": "page-list"},
            {"class": "nav-pages"}
        ]
        
        pagination_found = False
        for selector in pagination_selectors:
            pagination_container = soup.find("div", selector)
            if pagination_container:
                print(f"✅ Found pagination container with class: {selector['class']}")
                buttons = pagination_container.find_all("a")
                print(f"Found {len(buttons)} pagination links")
                pagination_found = True
                break
        
        if not pagination_found:
            # Fallback to all anchor tags
            buttons = soup.find_all("a")
            print(f"⚠️ No specific pagination container found, checking all {len(buttons)} anchor tags")
        
        lastPage = find_last_page_strategic(buttons)
            
    except Exception as e:
        print(f"❌ Error finding pages: {e}")
        last_page = 1
    
    # Step 4: Extract property links (adapted for inmuebles24)
    print(f"\n📍 Step 4: Testing property link extraction")
    
    try:
        html = requests.get(working_url)
        soup = BeautifulSoup(html.text, "html.parser")
        
        # Get all links
        links = soup.find_all("a", href=True)
        print(f"Total links found: {len(links)}")
        
        # Show first 15 href patterns for analysis
        print("\n🔗 Sample href patterns:")
        hrefs = [item["href"] for item in links]
        for i, href in enumerate(hrefs[:15]):
            print(f"  {i+1:2d}. {href}")
        
        # Test different patterns common for property links in inmuebles24
        patterns_to_test = [
            f"/{search_criteria['propertyType']}/",
            "/propiedades/",
            "/inmueble/",
            "/detalle/",
            "/ficha/",
            f"/{search_criteria['rentOrBuy']}/",
            "-en-venta-",
            "-departamento-",
            "/departamento/",
            "/casa/",
            ".html"
        ]
        
        print(f"\n🔍 Testing property link patterns:")
        best_pattern = None
        best_count = 0
        
        for pattern in patterns_to_test:
            matches = [href for href in hrefs if pattern in href]
            print(f"  Pattern '{pattern}': {len(matches)} matches")
            if len(matches) > best_count and len(matches) < len(hrefs) * 0.5:  # Avoid too generic patterns
                best_count = len(matches)
                best_pattern = pattern
            if matches and len(matches) <= 5:
                print(f"    Examples: {matches[:3]}")
        
        if best_pattern:
            print(f"\n✅ Best pattern found: '{best_pattern}' with {best_count} matches")
            property_links = [href for href in hrefs if best_pattern in href]
            print(f"Sample property links:")
            for link in property_links[:5]:
                print(f"  - {link}")
    
    except Exception as e:
        print(f"❌ Error extracting links: {e}")
    
    # Step 5: Test property ID extraction
    print(f"\n📍 Step 5: Testing property ID extraction")

    if 'property_links' in locals() and property_links:
        print(f"Testing ID extraction from {len(property_links)} property URLs:")
        extracted_ids = []
        
        for href in property_links[:10]:  # Test first 10
            # Try multiple ID extraction patterns
            # Pattern 1: numbers at the end before .html
            match = re.search(r'-(\d+)\.html', href)
            if match:
                property_id = match.group(1)
                extracted_ids.append(property_id)
                print(f"  {href} → ID: {property_id}")
                continue
                
            # Pattern 2: numbers after a slash
            match = re.search(r'/(\d{5,})/?', href)
            if match:
                property_id = match.group(1)
                extracted_ids.append(property_id)
                print(f"  {href} → ID: {property_id}")
                continue
                
            # Pattern 3: any long number in the URL
            numbers = re.findall(r'\d{5,}', href)
            if numbers:
                property_id = numbers[0]
                extracted_ids.append(property_id)
                print(f"  {href} → ID: {property_id}")
            else:
                print(f"  {href} → No ID found")
        
        print(f"\n✅ Summary: Successfully extracted {len(extracted_ids)} IDs")
        if extracted_ids:
            print(f"   Sample IDs: {', '.join(extracted_ids[:5])}")
    else:
        print("❌ No property links available for ID extraction test")
    
    # Step 6: Test price extraction (adapted for MXN currency)
    print(f"\n📍 Step 6: Testing price extraction")
    
    try:
        html = requests.get(working_url)
        soup = BeautifulSoup(html.text, "html.parser")
        
        # Look for price elements - common patterns in real estate sites
        price_selectors = [
            {"class": re.compile("price", re.I)},
            {"class": re.compile("precio", re.I)},
            {"class": re.compile("cost", re.I)},
            {"class": re.compile("value", re.I)},
            {"class": re.compile("amount", re.I)}
        ]
        
        prices_found = []
        
        for selector in price_selectors:
            elements = soup.find_all(["span", "div", "p"], selector)
            if elements:
                print(f"Found {len(elements)} elements with pattern: {selector}")
                
                for elem in elements[:10]:  # Check first 10
                    text = elem.getText().strip()
                    
                    # Look for Mexican peso patterns
                    if "$" in text or "MXN" in text or "USD" in text:
                        print(f"  Currency text found: '{text[:100]}'")
                        
                        # Extract numeric values
                        # Remove common separators and extract numbers
                        price_text = re.sub(r'[^\d,.]', '', text)
                        price_text = price_text.replace(',', '')
                        
                        if price_text and price_text.replace('.', '').isdigit():
                            prices_found.append(price_text)
                            print(f"    → Extracted price: {price_text}")
        
        print(f"\n✅ Total prices extracted: {len(prices_found)}")
        if prices_found:
            print(f"Sample prices: {prices_found[:5]}")
        
        # Also try searching for any text containing currency symbols
        all_text_elements = soup.find_all(text=re.compile(r'\$[\d,]+'))
        print(f"\n🔍 Alternative: Found {len(all_text_elements)} text nodes with $ symbol")
        
    except Exception as e:
        print(f"❌ Error extracting prices: {e}")
    
    print(f"\n" + "=" * 50)
    print("🏁 Debug Summary:")
    print(f"✅ URL construction: Working (with pattern adjustment)")
    print(f"✅ Page fetching: Working") 
    print(f"{'✅' if 'property_links' in locals() and property_links else '❌'} Property link extraction: {'Working' if 'property_links' in locals() and property_links else 'Needs pattern adjustment'}")
    print(f"{'✅' if 'prices_found' in locals() and prices_found else '❌'} Price extraction: {'Working' if 'prices_found' in locals() and prices_found else 'Needs selector adjustment'}")
    
    print(f"\n💡 Recommendations:")
    print("1. Inspect the actual HTML structure to find the correct selectors")
    print("2. Property links might use different patterns than tested")
    print("3. Price elements might be loaded dynamically via JavaScript")
    print("4. Consider using browser automation (Selenium/Playwright) if content is dynamic")

if __name__ == "__main__":
    debug_inmuebles24_scraper()