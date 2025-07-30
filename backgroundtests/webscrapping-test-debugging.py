        #!/usr/bin/env python3
"""
Independent debug script for ImmoScout24 scraper
Based on the original scraping logic but simplified for debugging
"""

import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

def debug_immoscout_scraper():
    """Debug the ImmoScout24 scraping logic step by step"""
    
    # Test configuration - matches your working URL
    search_criteria = {
        "rentOrBuy": "buy",
        "city": "bern", 
        "propertyType": "house",
        "radius": 7
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
        buttons = soup.findAll("a")
        
        print(f"Found {len(buttons)} anchor tags")
        
        # Extract potential page numbers (original logic lines 71-74)
        page_numbers = []
        for item in buttons:
            text = item.text.strip()
            if len(text) <= 3 and len(text) != 0:
                page_numbers.append(text)
        
        print(f"Potential page numbers found: {page_numbers}")
        
        # Try to find actual page numbers
        numeric_pages = []
        for p in page_numbers:
            try:
                num = int(p)
                numeric_pages.append(num)
            except ValueError:
                continue
                
        if numeric_pages:
            last_page = max(numeric_pages)
            print(f"✅ Last page detected: {last_page}")
        else:
            last_page = 1
            print(f"⚠️ No pages found, defaulting to: {last_page}")
            
    except Exception as e:
        print(f"❌ Error finding pages: {e}")
        last_page = 1
    
    # Step 4: Extract property links (lines 98-102 logic - THE CRITICAL PART)
    print(f"\n📍 Step 4: Testing property link extraction")
    
    try:
        # Use the working URL for this test
        html = requests.get(working_url)
        soup = BeautifulSoup(html.text, "html.parser")
        
        # Get all links
        links = soup.findAll("a", href=True)
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
        for href in test_hrefs:
            # Original logic: extract first number found (line 103)
            numbers = re.findall(r"\d+", href)
            if numbers:
                property_id = numbers[0]
                print(f"  {href} → ID: {property_id}")
            else:
                print(f"  {href} → No ID found")
    else:
        print("❌ No URLs available for ID extraction test")
    
    # Step 6: Test price extraction (lines 105-116 logic)
    print(f"\n📍 Step 6: Testing price extraction")
    
    try:
        span_elements = soup.findAll("span")
        print(f"Found {len(span_elements)} span elements")
        
        prices_found = []
        for span in span_elements[:50]:  # Test first 50 spans
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