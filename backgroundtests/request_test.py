#!/usr/bin/env python3
"""
Independent script to compare ImmoScout24 content between requests and browser
This will help identify why you're seeing different content
"""

import requests
from bs4 import BeautifulSoup
import re
import hashlib
import json
from datetime import datetime

def get_page_fingerprint(html_content):
    """Create a fingerprint of the page to compare versions"""
    return hashlib.md5(html_content.encode()).hexdigest()[:8]

def extract_all_prices(soup):
    """Extract ALL price patterns from the page"""
    prices = {
        'span_with_chf': [],
        'class_with_price': [],
        'data_attributes': [],
        'json_ld': [],
        'any_number_pattern': []
    }
    
    # Method 1: Any span containing CHF
    for span in soup.find_all('span'):
        text = span.get_text(strip=True)
        if 'CHF' in text:
            prices['span_with_chf'].append({
                'text': text[:100],  # First 100 chars
                'class': span.get('class', []),
                'parent_class': span.parent.get('class', []) if span.parent else []
            })
    
    # Method 2: Elements with price-related classes
    price_class_patterns = ['price', 'Price', 'cost', 'Cost', 'amount', 'Amount']
    for pattern in price_class_patterns:
        for elem in soup.find_all(class_=re.compile(pattern)):
            text = elem.get_text(strip=True)
            if text:
                prices['class_with_price'].append({
                    'text': text[:100],
                    'tag': elem.name,
                    'class': elem.get('class', [])
                })
    
    # Method 3: Data attributes
    for elem in soup.find_all(attrs={"data-price": True}):
        prices['data_attributes'].append({
            'data-price': elem.get('data-price'),
            'tag': elem.name,
            'text': elem.get_text(strip=True)[:50]
        })
    
    # Method 4: JSON-LD structured data
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            prices['json_ld'].append(data)
        except:
            pass
    
    # Method 5: Any text with price-like patterns
    price_pattern = re.compile(r'(?:CHF|Fr\.|€|EUR)\s*[\d,\']+(?:\.\d{2})?')
    for text in soup.stripped_strings:
        matches = price_pattern.findall(text)
        if matches:
            prices['any_number_pattern'].extend(matches)
    
    return prices

def analyze_page_structure(soup):
    """Analyze the page structure to understand what we're getting"""
    analysis = {
        'title': soup.title.string if soup.title else 'No title',
        'meta_description': None,
        'total_links': len(soup.find_all('a')),
        'total_spans': len(soup.find_all('span')),
        'total_divs': len(soup.find_all('div')),
        'total_scripts': len(soup.find_all('script')),
        'has_results': False,
        'property_cards': [],
        'navigation_elements': []
    }
    
    # Get meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        analysis['meta_description'] = meta_desc.get('content', '')[:100]
    
    # Look for property cards (common patterns)
    card_patterns = ['listing', 'Listing', 'property', 'Property', 'result', 'Result', 'card', 'Card']
    for pattern in card_patterns:
        cards = soup.find_all(class_=re.compile(pattern))
        if cards:
            analysis['property_cards'].append({
                'pattern': pattern,
                'count': len(cards),
                'sample_classes': [c.get('class', []) for c in cards[:3]]
            })
    
    # Check for navigation elements
    nav_patterns = ['nav', 'Nav', 'menu', 'Menu', 'header', 'Header']
    for pattern in nav_patterns:
        navs = soup.find_all(class_=re.compile(pattern))
        if navs:
            analysis['navigation_elements'].append({
                'pattern': pattern,
                'count': len(navs)
            })
    
    # Check if this looks like a results page
    results_indicators = ['results', 'Results', 'properties', 'Properties', 'found', 'Found']
    for indicator in results_indicators:
        if indicator in str(soup):
            analysis['has_results'] = True
            break
    
    return analysis

def test_different_methods(url):
    """Test the URL with different request methods"""
    results = {}
    
    # Method 1: Basic request
    print("\n🔍 Method 1: Basic requests.get()")
    try:
        r1 = requests.get(url)
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        results['basic'] = {
            'status': r1.status_code,
            'url': r1.url,
            'fingerprint': get_page_fingerprint(r1.text),
            'content_length': len(r1.text),
            'prices': extract_all_prices(soup1),
            'structure': analyze_page_structure(soup1)
        }
        print(f"✅ Status: {r1.status_code}, Size: {len(r1.text):,} bytes")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['basic'] = {'error': str(e)}
    
    # Method 2: With browser headers
    print("\n🔍 Method 2: With browser User-Agent")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        r2 = requests.get(url, headers=headers)
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        results['with_headers'] = {
            'status': r2.status_code,
            'url': r2.url,
            'fingerprint': get_page_fingerprint(r2.text),
            'content_length': len(r2.text),
            'prices': extract_all_prices(soup2),
            'structure': analyze_page_structure(soup2)
        }
        print(f"✅ Status: {r2.status_code}, Size: {len(r2.text):,} bytes")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['with_headers'] = {'error': str(e)}
    
    # Method 3: With session (cookies)
    print("\n🔍 Method 3: With session (maintains cookies)")
    session = requests.Session()
    session.headers.update(headers)
    try:
        # First visit the main page
        session.get('https://www.immoscout24.ch/en/')
        # Then visit our target URL
        r3 = session.get(url)
        soup3 = BeautifulSoup(r3.text, 'html.parser')
        results['with_session'] = {
            'status': r3.status_code,
            'url': r3.url,
            'fingerprint': get_page_fingerprint(r3.text),
            'content_length': len(r3.text),
            'cookies': len(session.cookies),
            'prices': extract_all_prices(soup3),
            'structure': analyze_page_structure(soup3)
        }
        print(f"✅ Status: {r3.status_code}, Size: {len(r3.text):,} bytes, Cookies: {len(session.cookies)}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        results['with_session'] = {'error': str(e)}
    
    return results

def compare_results(results):
    """Compare the results from different methods"""
    print("\n" + "="*70)
    print("📊 COMPARISON RESULTS")
    print("="*70)
    
    # Compare fingerprints
    print("\n🔐 Page Fingerprints (to detect different content):")
    for method, data in results.items():
        if 'fingerprint' in data:
            print(f"  {method:15}: {data['fingerprint']}")
    
    # Compare content sizes
    print("\n📏 Content Sizes:")
    for method, data in results.items():
        if 'content_length' in data:
            print(f"  {method:15}: {data['content_length']:,} bytes")
    
    # Compare prices found
    print("\n💰 Prices Found:")
    for method, data in results.items():
        if 'prices' in data:
            total_prices = sum(len(prices) for prices in data['prices'].values() if isinstance(prices, list))
            print(f"\n  {method}:")
            print(f"    Total price mentions: {total_prices}")
            
            # Show sample prices from each extraction method
            for price_type, price_list in data['prices'].items():
                if price_list and isinstance(price_list, list):
                    print(f"    {price_type}: {len(price_list)} found")
                    if price_type == 'span_with_chf' and price_list:
                        for i, p in enumerate(price_list[:3]):
                            print(f"      → {p['text']}")
    
    # Compare page structure
    print("\n🏗️ Page Structure Analysis:")
    for method, data in results.items():
        if 'structure' in data:
            struct = data['structure']
            print(f"\n  {method}:")
            print(f"    Title: {struct['title']}")
            print(f"    Has results page indicators: {struct['has_results']}")
            print(f"    Total links/spans/divs: {struct['total_links']}/{struct['total_spans']}/{struct['total_divs']}")
            if struct['property_cards']:
                print(f"    Property cards found: {struct['property_cards']}")

def save_comparison_html(results, timestamp):
    """Save the raw HTML from each method for manual comparison"""
    filename = f"immoscout_comparison_{timestamp}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>ImmoScout24 Content Comparison - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .method {{ border: 1px solid #ccc; padding: 10px; margin: 10px 0; }}
        .prices {{ background: #f0f0f0; padding: 5px; margin: 5px 0; }}
        pre {{ overflow-x: auto; background: #f5f5f5; padding: 10px; }}
    </style>
</head>
<body>
    <h1>ImmoScout24 Content Comparison</h1>
    <p>Generated: {timestamp}</p>
""")
        
        for method, data in results.items():
            if 'prices' in data:
                f.write(f"<div class='method'><h2>Method: {method}</h2>")
                f.write(f"<p>Fingerprint: {data.get('fingerprint', 'N/A')}</p>")
                f.write(f"<p>Content Length: {data.get('content_length', 'N/A'):,} bytes</p>")
                
                # Show prices
                f.write("<div class='prices'><h3>Prices Found:</h3>")
                for price_type, price_list in data['prices'].items():
                    if price_list and isinstance(price_list, list):
                        f.write(f"<h4>{price_type} ({len(price_list)} found):</h4><ul>")
                        for p in price_list[:10]:  # First 10
                            if isinstance(p, dict) and 'text' in p:
                                f.write(f"<li>{p['text']}</li>")
                            else:
                                f.write(f"<li>{p}</li>")
                        f.write("</ul>")
                f.write("</div></div>")
        
        f.write("</body></html>")
    
    print(f"\n💾 Comparison saved to: {filename}")

def main():
    """Run the comparison"""
    print("🔍 ImmoScout24 Content Comparison Tool")
    print("="*70)
    
    # The URL from your example
    url = "https://www.immoscout24.ch/en/real-estate/buy/city-twann?pn=1&r=0&se=16&map=1"
    print(f"Testing URL: {url}")
    
    # Run tests
    results = test_different_methods(url)
    
    # Compare results
    compare_results(results)
    
    # Save for manual inspection
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_comparison_html(results, timestamp)
    
    print("\n" + "="*70)
    print("🎯 RECOMMENDATIONS:")
    print("="*70)
    print("""
1. If fingerprints are different → You're getting different content
2. If all fingerprints are same → Content is consistent, issue is in parsing
3. Check the HTML file for manual comparison of prices
4. If you see different prices in browser, try:
   - Using Selenium for JavaScript rendering
   - Checking if prices are loaded via XHR/API calls
   - Using browser DevTools to monitor network requests
    """)

if __name__ == "__main__":
    main()