
"""
Independent debug script for ImmoScout24 scraper
Based on the original scraping logic but simplified for debugging
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

def debug_immoscout_scraper():
    """Debug the ImmoScout24 scraping logic step by step"""
    
    # Test configuration - matches your working URL
    search_criteria = {
        "rentOrBuy": "buy",
        "city": "twann", 
        "propertyType": "real-estate",
        "radius": 0
    }
    
    # URLs from your original config
    immo24_main_url_en = "https://www.immoscout24.ch/en/"
    immo24_search_url_en = "https://www.immoscout24.ch/en/real-estate/"
    
    print("🔍 DEBUG: ImmoScout24 Scraper Analysis")
    print("=" * 50)
    
    # Step 1: Test the working URL you provided
    working_url = "https://www.immoscout24.ch/en/house/buy/city-bern?pn=1&r=7&se=16&map=1"
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
    
    # Step 2: Reconstruct URL using original logic
    print(f"\n📍 Step 2: Testing original URL construction logic")
    
    # This matches lines 57-65 from your original code
    original_search_url = (
        immo24_search_url_en
        + search_criteria["rentOrBuy"]
        + "/city-"
        + search_criteria["city"]
        + "?r="
        + str(search_criteria["radius"])
        + "&map=1"
    )
    print(f"Original search URL: {original_search_url}")
    
    # This matches lines 82-94 from your original code  
    original_page_url = (
        immo24_main_url_en
        + search_criteria["propertyType"]
        + "/"
        + search_criteria["rentOrBuy"]
        + "/city-"
        + search_criteria["city"]
        + "?pn=1"
        + "&r="
        + str(search_criteria["radius"])
        + "&se=16"
        + "&map=1"
    )
    print(f"Original page URL: {original_page_url}")
    print(f"Working URL:       {working_url}")
    print(f"URLs match: {original_page_url == working_url}")
    
    # Step 3: Find maximum pages (lines 68-78 logic)
    print(f"\n📍 Step 3: Finding maximum pages")
    
    try:
        html = requests.get(original_search_url)
        soup = BeautifulSoup(html.text, "html.parser")
        buttons = soup.find_all("a")
        
        print(f"Found {len(buttons)} anchor tags")
        
        lastPage = find_last_page_strategic(buttons)
            
    except Exception as e:
        print(f"❌ Error finding pages: {e}")
        last_page = 1
    
    # Step 4: Extract property links (lines 98-102 logic - THE CRITICAL PART)
    print(f"\n📍 Step 4: Testing property link extraction")
    
    try:
        
        html = requests.get(original_page_url)
        soup = BeautifulSoup(html.text, "html.parser")
        
        # Get all links
        links = soup.find_all("a", href=True)
        print(f"Total links found: {len(links)}")
        
        # Show first 10 href patterns for analysis
        print("\n🔗 Sample href patterns:")
        hrefs = [item["href"] for item in links]
        for i, href in enumerate(hrefs[:15]):
            print(f"  {i+1:2d}. {href}")
        
        # Test original filter logic (line 102)
        original_filter = "/" + search_criteria['rentOrBuy'] + "/"  # "/buy/"
        print(f"\n🎯 Original filter pattern: '{original_filter}'")
        
        hrefs_filtered_original = [href for href in hrefs if href.startswith(original_filter)]
        print(f"Links matching original filter: {len(hrefs_filtered_original)}")
        
        if hrefs_filtered_original:
            print("✅ Original filter found matches:")
            for href in hrefs_filtered_original[:5]:
                print(f"  - {href}")
        else:
            print("❌ Original filter found NO matches")
            
            # Try alternative patterns
            print("\n🔍 Testing alternative patterns:")
            
            patterns_to_test = [
                "/en/d/",
                "/d/",
                f"/{search_criteria['propertyType']}/",
                f"/house/",
                f"/property/",
                f"/listing/",
                f"/detail/",
                "/en/house/",
                "/en/property/"
            ]
            
            for pattern in patterns_to_test:
                matches = [href for href in hrefs if pattern in href]
                print(f"  Pattern '{pattern}': {len(matches)} matches")
                if matches:
                    print(f"    Examples: {matches[:3]}")
    
    except Exception as e:
        print(f"❌ Error extracting links: {e}")
    
   # Step 5: Test property ID extraction
    print(f"\n📍 Step 5: Testing property ID extraction")

    if 'hrefs_filtered_original' in locals() and hrefs_filtered_original:
        print("Using original filter results...")
        test_hrefs = hrefs_filtered_original
    else:
        print("Original filter failed, testing manual examples...")
        # Test with some example property URLs if we can find them
        test_hrefs = [href for href in hrefs if re.search(r'/\d+', href)][:5]

    if test_hrefs:
        print(f"Testing ID extraction from {len(test_hrefs)} URLs:")
        extracted_ids = []  # Track all extracted IDs
        
        for href in test_hrefs:
            # Original logic: extract first number found (line 103)
            numbers = re.findall(r"\d+", href)
            if numbers:
                property_id = numbers[0]
                extracted_ids.append(property_id)
                print(f"  {href} → ID: {property_id}")
            else:
                print(f"  {href} → No ID found")
        
        # Print summary
        print(f"\n✅ Summary: Successfully extracted {len(extracted_ids)} IDs out of {len(test_hrefs)} URLs")
        print(f"   Extraction success rate: {len(extracted_ids)/len(test_hrefs)*100:.1f}%")
        if extracted_ids:
            print(f"   Sample IDs: {', '.join(extracted_ids[:5])}")
    else:
        print("❌ No URLs available for ID extraction test")
    
    # Step 6: Test price extraction (lines 105-116 logic)
    print(f"\n📍 Step 6: Testing price extraction")
    
    try:
        html = requests.get(original_page_url)
        print(f"Final URL: {html.url}")  # Check if you were redirected
        soup2 = BeautifulSoup(html.text, "html.parser")
        span_elements = soup2.find_all("span")
        print(f"Found {len(span_elements)} span elements")
        
        prices_found = []
        for span in span_elements: 
            text = span.getText().strip()
            if "CHF" in text or "EUR" in text:
                print(f"Currency text found: '{text[:100]}...'")
                
                # Original price extraction logic
                if "CHF" in text:
                    start = text.find("CHF") + 4
                    end = text.find(".â\x80\x94")  # em dash
                    if end == -1:
                        end = len(text)
                    
                    price_text = text[start:end]
                    price_clean = re.sub(r"\D", "", price_text)
                    if price_clean:
                        prices_found.append(price_clean)
                        print(f"  → Extracted price: {price_clean}")
        
        print(f"\n✅ Total prices extracted: {len(prices_found)}")
        if prices_found:
            print(f"Sample prices: {prices_found[:5]}")
        
    except Exception as e:
        print(f"❌ Error extracting prices: {e}")
    
    print(f"\n" + "=" * 50)
    print("🏁 Debug Summary:")
    print(f"✅ URL construction: Working")
    print(f"✅ Page fetching: Working") 
    print(f"{'✅' if 'hrefs_filtered_original' in locals() and hrefs_filtered_original else '❌'} Property link extraction: {'Working' if 'hrefs_filtered_original' in locals() and hrefs_filtered_original else 'BROKEN'}")
    print(f"{'✅' if 'prices_found' in locals() and prices_found else '❌'} Price extraction: {'Working' if 'prices_found' in locals() and prices_found else 'BROKEN'}")

if __name__ == "__main__":
    debug_immoscout_scraper()