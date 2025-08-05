#!/usr/bin/env python3
"""
Playwright script to compare ImmoScout24 content with real browser rendering
This will show you exactly what a real browser sees, including JavaScript-rendered content
"""

import asyncio
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup

async def capture_with_playwright(url, headless=False):
    """Capture the page using Playwright (real browser rendering)"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with realistic viewport and user agent
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            locale='en-US'
        )
        
        # Create page
        page = await context.new_page()
        
        # Navigate and wait for content
        print(f"🌐 Navigating to {url}")
        await page.goto(url, wait_until='networkidle')
        
        # Wait a bit more for any lazy-loaded content
        await page.wait_for_timeout(3000)
        
        # Capture various data
        results = {
            'title': await page.title(),
            'url': page.url,
            'content': await page.content(),
            'screenshots': {},
            'prices': {},
            'network_requests': [],
            'console_logs': []
        }
        
        # Capture screenshots
        results['screenshots']['full'] = await page.screenshot(full_page=True)
        
        # Extract prices using multiple methods
        # Method 1: Get all visible text containing CHF
        price_texts = await page.evaluate('''() => {
            const prices = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let node;
            while (node = walker.nextNode()) {
                if (node.nodeValue && node.nodeValue.includes('CHF')) {
                    const text = node.nodeValue.trim();
                    if (text.length > 0 && text.length < 200) {
                        prices.push({
                            text: text,
                            parentClass: node.parentElement ? node.parentElement.className : '',
                            parentTag: node.parentElement ? node.parentElement.tagName : ''
                        });
                    }
                }
            }
            return prices;
        }''')
        results['prices']['visible_text'] = price_texts
        
        # Method 2: Get all elements with price classes
        price_elements = await page.evaluate('''() => {
            const elements = document.querySelectorAll('[class*="price"], [class*="Price"], [class*="cost"], [class*="Cost"]');
            return Array.from(elements).map(el => ({
                text: el.innerText || el.textContent,
                class: el.className,
                tag: el.tagName
            })).filter(el => el.text && el.text.includes('CHF'));
        }''')
        results['prices']['price_classes'] = price_elements
        
        # Method 3: Get specific price spans
        specific_prices = await page.evaluate('''() => {
            const spans = document.querySelectorAll('span');
            const prices = [];
            spans.forEach(span => {
                const text = span.innerText || span.textContent || '';
                if (text.includes('CHF') && text.match(/CHF\\s*[\\d,\\']+/)) {
                    prices.push({
                        text: text.trim(),
                        class: span.className,
                        fullMatch: text.match(/CHF\\s*[\\d,\\']+\\.?–?/g)
                    });
                }
            });
            return prices;
        }''')
        results['prices']['span_prices'] = specific_prices
        
        # Method 4: Check for JSON-LD structured data
        json_ld_data = await page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            const data = [];
            scripts.forEach(script => {
                try {
                    data.push(JSON.parse(script.textContent));
                } catch (e) {}
            });
            return data;
        }''')
        results['prices']['structured_data'] = json_ld_data
        
        # Get property cards/listings
        property_cards = await page.evaluate('''() => {
            // Try multiple selectors for property cards
            const selectors = [
                '[class*="listing"]',
                '[class*="Listing"]',
                '[class*="property"]',
                '[class*="Property"]',
                '[class*="result"]',
                '[class*="Result"]',
                'article',
                '[data-test*="property"]'
            ];
            
            const cards = [];
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    elements.forEach(el => {
                        // Look for price within each card
                        const priceEl = el.querySelector('[class*="price"], [class*="Price"]');
                        const titleEl = el.querySelector('h2, h3, h4, [class*="title"], [class*="Title"]');
                        
                        if (priceEl || titleEl) {
                            cards.push({
                                selector: selector,
                                price: priceEl ? priceEl.innerText : 'No price',
                                title: titleEl ? titleEl.innerText : 'No title',
                                classes: el.className
                            });
                        }
                    });
                    if (cards.length > 0) break;
                }
            }
            return cards;
        }''')
        results['property_cards'] = property_cards
        
        # Capture network activity
        page.on('request', lambda request: results['network_requests'].append({
            'url': request.url,
            'method': request.method,
            'type': request.resource_type
        }))
        
        # Capture console logs
        page.on('console', lambda msg: results['console_logs'].append({
            'type': msg.type,
            'text': msg.text
        }))
        
        # Scroll to load any lazy content
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(2000)
        
        # Get final page metrics
        metrics = await page.evaluate('''() => ({
            totalElements: document.getElementsByTagName('*').length,
            totalImages: document.images.length,
            totalLinks: document.links.length,
            totalScripts: document.scripts.length,
            bodyText: document.body.innerText.substring(0, 1000)
        })''')
        results['metrics'] = metrics
        
        await browser.close()
        
        return results

async def compare_with_requests(url):
    """Get the same page with requests for comparison"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract prices
    prices = []
    for span in soup.find_all('span'):
        text = span.get_text(strip=True)
        if 'CHF' in text and re.search(r'CHF\s*[\d,\']+', text):
            prices.append(text)
    
    return {
        'status': response.status_code,
        'content_length': len(response.text),
        'title': soup.title.string if soup.title else 'No title',
        'prices': prices[:10]  # First 10 prices
    }

async def main():
    """Run the comparison"""
    print("🎭 ImmoScout24 Playwright vs Requests Comparison")
    print("="*70)
    
    url = "https://www.immoscout24.ch/en/real-estate/buy/city-twann?pn=1&r=0&se=16&map=1"
    
    # First, get with requests
    print("\n📦 Getting with Requests...")
    requests_data = await compare_with_requests(url)
    print(f"✅ Requests: {len(requests_data['prices'])} prices found")      
    print("Sample prices:", requests_data['prices'][:3])
    
    # Then, get with Playwright
    print("\n🎭 Getting with Playwright (real browser)...")
    playwright_data = await capture_with_playwright(url, headless=False)
    
    # Save screenshot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"immoscout_screenshot_{timestamp}.png"
    with open(screenshot_path, 'wb') as f:
        f.write(playwright_data['screenshots']['full'])
    print(f"📸 Screenshot saved: {screenshot_path}")
    
    # Compare results
    print("\n" + "="*70)
    print("📊 COMPARISON RESULTS")
    print("="*70)
    
    print(f"\n📄 Page Titles:")
    print(f"  Requests:   {requests_data['title']}")
    print(f"  Playwright: {playwright_data['title']}")
    
    print(f"\n💰 Prices Found:")        
    print(f"\n  Requests ({len(requests_data['prices'])} total):")
    for i, price in enumerate(requests_data['prices'][:5], 1):
        print(f"    {i}. {price}")
    
    print(f"\n  Playwright - Visible Text ({len(playwright_data['prices']['visible_text'])} total):")
    for i, price in enumerate(playwright_data['prices']['visible_text'][:5], 1):
        print(f"    {i}. {price['text']}")
    
    print(f"\n  Playwright - Span Prices ({len(playwright_data['prices']['span_prices'])} total):")
    for i, price in enumerate(playwright_data['prices']['span_prices'][:5], 1):
        print(f"    {i}. {price['text']}")
    
    print(f"\n🏠 Property Cards Found: {len(playwright_data['property_cards'])}")
    for i, card in enumerate(playwright_data['property_cards'][:3], 1):
        print(f"  {i}. {card['title'][:50]}... - {card['price']}")
    
    print(f"\n📊 Page Metrics (Playwright):")
    metrics = playwright_data['metrics']
    print(f"  Total elements: {metrics['totalElements']}")
    print(f"  Total images: {metrics['totalImages']}")
    print(f"  Total links: {metrics['totalLinks']}")
    print(f"  Total scripts: {metrics['totalScripts']}")
    
    # Save detailed comparison
    comparison_file = f"immoscout_detailed_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump({
            'url': url,
            'timestamp': timestamp,
            'requests_prices': requests_data['prices'],
            'playwright_prices': {
                'visible_text': [p['text'] for p in playwright_data['prices']['visible_text']],
                'span_prices': [p['text'] for p in playwright_data['prices']['span_prices']],
                'property_cards': playwright_data['property_cards'][:10]
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed comparison saved: {comparison_file}")
    
    # Final analysis
    print("\n" + "="*70)
    print("🎯 ANALYSIS")
    print("="*70)
    
    # Extract unique prices from each method
    requests_prices = set(re.findall(r'CHF\s*[\d,\']+', ' '.join(requests_data['prices'])))
    playwright_prices = set()
    for price_data in playwright_data['prices']['span_prices']:
        if price_data.get('fullMatch'):
            playwright_prices.update(price_data['fullMatch'])
    
    print(f"\n🔍 Unique price values:")
    print(f"  Requests:   {sorted(requests_prices)[:5]}")
    print(f"  Playwright: {sorted(playwright_prices)[:5]}")
    
    if requests_prices == playwright_prices:
        print("\n✅ SAME PRICES: Both methods return identical prices")
        print("   → The issue is NOT JavaScript rendering")
        print("   → Prices are different due to personalization/location/session")
    else:
        print("\n❌ DIFFERENT PRICES: Playwright sees different prices")
        print("   → JavaScript is modifying prices after page load")
        print("   → Or different content is served to real browsers")

# Install playwright browsers if needed
# Run: playwright install chromium

if __name__ == "__main__":
    print("\n⚠️  Make sure you have Playwright installed:")
    print("   pip install playwright")
    print("   playwright install chromium")
    print()
    
    asyncio.run(main())