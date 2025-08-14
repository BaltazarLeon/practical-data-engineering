"""
Independent debug script for Inmuebles24 scraper
Based on the original scraping logic but adapted for inmuebles24.com
"""
from pathlib import Path
from playwright.async_api import async_playwright
from playwright.async_api import async_playwright
import pandas as pd
import math
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

STATE_PATH = "cf_storage_state.json"

# Function to merge multiple run data dictionaries
# This is useful for combining results from multiple runs of the scraper
# into a single comprehensive dataset.
# Each run data dictionary should have the same structure.
def merge_playwright_data(run_data_list: list):
    """
    Merges a list of run data dictionaries by type (prices, property_cards, etc.).
    Returns a single merged dictionary.
    """
    merged_data = {
        'property_cards': [],
        'screenshots': [],
        'network_requests': [],
        'console_logs': [],
        'metrics': []
    }

    for run_data in run_data_list:
        # Merge property cards
        merged_data['property_cards'].extend(run_data.get('property_cards', []))
        
        #Commented out screenshot merging for now, as it causing issues with multiple property types
        """
        # Merge screenshots (optional: just keep all, or only the first)
        merged_data['screenshots'].append(run_data['screenshots'].get('full'))
        # Merge network requests and console logs
        merged_data['network_requests'].extend(run_data.get('network_requests', []))
        merged_data['console_logs'].extend(run_data.get('console_logs', []))
        # Merge metrics
        merged_data['metrics'].append(run_data.get('metrics'))
        """
    return merged_data

# Function to run multiple cycles and merge results
async def run_playwright_historical(url: str,property_type=None ,n: int = None, headless: bool = False):
    """
    Executes capture_with_playwright for a URL, stores results in historicaldata,
    then runs n cycles, storing each result in rundata and merges into historicaldata.
    """
    run_data_list = []

    # Step 1: Initial run
    print(f"Step 1: Running initial capture for {url}")
    initial_data = await capture_with_playwright(url,property_type=property_type, headless=headless)
    run_data_list.append(initial_data)


    # After capturing initial_data
    html_content = initial_data['content']

    # Extract the title text using regex
    match = re.search(r'<h1[^>]*class="postingsTitle-module__title"[^>]*>([\d,.]+)', html_content)
    if match:
        num_str = match.group(1).replace(',', '')
        total_listings = int(num_str)
        lastPageNum = math.ceil(total_listings / 30)
        print(f"Extracted total listings: {total_listings}")
        print(f"Calculated lastPageNum: {lastPageNum}")
    else:
        lastPageNum = 1
        print("Could not extract total listings, defaulting lastPageNum to 1")

    if n is None:
        print("No page limit (n) specified, scraping all pages.")
    else:
        print(f"Page limit (n) specified: {n}")
        if lastPageNum > n:
            lastPageNum = n  # Limit to 3 for testing purposes
    # Step 2: Loop for n cycles
    for i in range(6, lastPageNum + 2):
        # Insert -pagina-{i} before .html in the URL
        paged_url = url.replace('.html', f'-pagina-{i}.html')
        print(f"Step 2: Running capture {i} for {paged_url}")
        rundata = await capture_with_playwright(paged_url,property_type=property_type, headless=headless)
        run_data_list.append(rundata)

    # Merge all runs into historicaldata
    historicaldata = merge_playwright_data(run_data_list)
    # Save the historical data to a csv file
    df = pd.DataFrame(historicaldata.get('property_cards', []))
    # Ensure directory exists (optional)
    try:
        import os
        os.makedirs(os.path.dirname("backgroundtests/csv/"), exist_ok=True)
    except Exception:
        pass
    # Timestamped filename to avoid overwrites

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_csv = f"backgroundtests/csv/property_cards_{ts}_{property_type}.csv"
    df.to_csv(final_csv, index=False, encoding="utf-8")
    print(f"✅ Saved {len(df)} property cards to {final_csv}")


    print(f"All runs complete. Total runs merged: {len(run_data_list)}")
    return historicaldata

# You need to have merge_playwright_data defined as in previous examples.


#Original Function to capture data using Playwright, no CLoudflare bypass


# Function to capture data using Playwright, with Cloudflare bypass
# Function to Capture Data using Playwright I think I need to separate this more into models
async def capture_with_playwright(url, property_type=None, headless=False):
    #Capture the page using Playwright (real browser rendering)
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
        await page.goto(url)
        await page.wait_for_timeout(3000)  # let initial content load a bit

        # Wait a bit more for any lazy-loaded content
        await page.wait_for_timeout(1000)
        
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
        
        # NOTE: pass `property_type` into evaluate and assign to tipo_inmueble
        property_cards = await page.evaluate('''(ptype) => {
        const container = document.querySelector('div.postingsList-module__postings-container');
        if (!container) return [];

            // numbers: drop commas (thousands), keep dot as decimal if present
        const toNumber = (s) => {
            if (!s) return null;
            const cleaned = s.replace(/,/g, '');
            const m = cleaned.match(/\\d+(?:\\.\\d+)?/);
            return m ? parseFloat(m[0]) : null;
        };

        // get FIRST number only (handles "2 a 4", "50 – 100", etc.)
        const firstNumber = (s) => {
            if (!s) return null;
            const m = s.replace(/,/g, '').match(/\\d+(?:\\.\\d+)?/);
            return m ? parseFloat(m[0]) : null;
        };

        return Array.from(container.children).map((card) => {
            // Core link & ID
            const sub = card.querySelector('[data-id][data-to-posting]');
            const data_id = sub ? sub.getAttribute('data-id') : null;
            const url     = sub ? sub.getAttribute('data-to-posting') || null : null;

            // Precio + Moneda (same selector)
            const priceEl = card.querySelector('div.postingPrices-module__price[data-qa="POSTING_CARD_PRICE"]');
            let precio = null, moneda = null;
            if (priceEl) {
            const raw = priceEl.innerText.trim();
            moneda = /USD/i.test(raw) ? 'USD' : 'MN';
            precio = toNumber(raw); // commas removed -> numeric value
            }

            // Zona: text AFTER the comma from location h2
            const locEl = card.querySelector('h2.postingLocations-module__location-text[data-qa="POSTING_CARD_LOCATION"]');
            let zona = null;
            if (locEl) {
            const parts = locEl.innerText.split(',');
            if (parts.length > 1) zona = parts[1].trim();
            }

            // Dirección + Código postal (5 digits inside address div)
            const addrEl = card.querySelector('div.postingLocations-module__location-address');
            let direccion = null, codigo_postal = null;
            if (addrEl) {
            const t = addrEl.innerText.trim();
            direccion = t;
            const cp = t.match(/\\b\\d{5}\\b/);
            if (cp) codigo_postal = cp[0];
            }

            // Features: tamaño lote, recámaras, baños, estacionamientos
            let tamano_lote = null, recamaras = null, banos = null, estacionamientos = null;
            const featuresEl = card.querySelector('h3[data-qa="POSTING_CARD_FEATURES"]');
            if (featuresEl) {
            featuresEl.querySelectorAll('span').forEach(span => {
                const txt = (span.innerText || '').trim().toLowerCase();

                // tamaño lote: must end with "m² lote"
                if (/(m²|m2) lote$/.test(txt)) {
                tamano_lote = firstNumber(txt);
                }

                // recámaras: must end with "rec."
                if (/rec\\.$/.test(txt)) {
                recamaras = firstNumber(txt);
                }

                // baños: must end with "baños" or "baño"
                if (/baños?$/.test(txt)) {
                banos = firstNumber(txt);
                }

                // estacionamientos: must end with "estac."
                if (/estac\\.$/.test(txt)) {
                estacionamientos = firstNumber(txt);
                }
            });
            }

            // Descripción
            const descEl = card.querySelector('h3.postingCard-module__posting-description a');
            const descripcion = descEl ? descEl.innerText.trim() : null;

            // URL vendedor (logo src)
            const sellerImg = card.querySelector('div.postingPublisher-module__container-logo-publisher img');
            const url_vendedor = sellerImg ? sellerImg.getAttribute('src') : null;

            // Tipo de inmueble (manual later)
            const tipo_inmueble = null;

            return {
            data_id,
            url,
            precio,
            moneda,
            zona,
            direccion,
            codigo_postal,
            tamano_lote,
            recamaras,
            banos,
            estacionamientos,
            descripcion,
            url_vendedor,
            tipo_inmueble: ptype || null   // <- here
            };
        });
        }''', property_type)

        results['property_cards'] = property_cards


        # Capture screenshots
        results['screenshots']['full'] = await page.screenshot(full_page=True)
        
  
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
        #await page.wait_for_timeout(1000)
        
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


def build_inmuebles24_url(base, slug, rent_or_buy, city):
    return (
        base
        + slug
        + "-en-"
        + rent_or_buy
        + "-en-"
        + city
        + "-mas-de-5-pesos.html"
    )

async def scrape_all_property_types(
    base_url: str,
    search_criteria: dict,
    property_type_slugs: dict,
    headless: bool = False,
    page_limit: int = 3,
    csv_path: str = "backgroundtests/csv/property_cards_all.csv",
    use_human_label_for_tipo: bool = True
):
    """
    Loops all property_type_slugs, scrapes each type, merges all runs,
    and writes a single CSV.
    """
    all_runs = []

    for human_label, slug in property_type_slugs.items():
        url = build_inmuebles24_url(
            base_url,
            slug,
            search_criteria["rentOrBuy"],
            search_criteria["city"]
        )
        tipo_inmueble_value = human_label if use_human_label_for_tipo else slug
        print(f"\n🎭 Scraping: {human_label} -> {url}")

        data = await run_playwright_historical(
            url,
            property_type=tipo_inmueble_value,  # <- goes into tipo_inmueble field
            n=page_limit,
            headless=headless
        )
        all_runs.append(data)

    # Merge everything
    merged = merge_playwright_data(all_runs)

    # Save CSV (property_cards only)
    df = pd.DataFrame(merged.get('property_cards', []))
    # ensure directory exists (optional)
    try:
        import os
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    except Exception:
        pass

    # timestamped filename to avoid overwrites
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_csv = csv_path.replace(".csv", f"_{ts}.csv")
    df.to_csv(final_csv, index=False, encoding="utf-8")
    print(f"✅ Saved {len(df)} property cards (all types) to {final_csv}")

    return merged, final_csv



async def debug_inmuebles24_scraper():
    """Debug the Inmuebles24 scraping logic step by step"""
    
    # Test configuration - adapted for inmuebles24
    
    # Define property type slugs for inmuebles24
    # These slugs are used to construct URLs for different property types

    """
    property_type_slugs = {
        "Departamento": "departamentos",
        "Casa": "casas",
        "Terreno / Lote": "terrenos",
    }
    
        # Original property_type_slugs for reference
    # Uncomment if needed for comparison
    """
    property_type_slugs = {
        "Departamento": "departamentos",
        "Casa": "casas",
        "Terreno / Lote": "terrenos",
        "Casa en condominio": "casa-en-condominio",
        "Local comercial": "locales-comerciales",
        "Bodega comercial": "bodegas-comerciales",
        "Casa uso de suelo": "casa-uso-de-suelo",
        "Departamento compartido": "departamento-compartido",
        "Desarrollo horizontal": "desarrollo-horizontal",
        "Desarrollo horizontal/vertical": "desarrollo-horizontal-vertical",
        "Desarrollo vertical": "desarrollo-vertical",
        "Dúplex": "duplex",
        "Edificio": "edificio",
        "Huerta": "huerta",
        "Inmueble productivo urbano": "inmueble-productivo-urbano",
        "Local en centro comercial": "local-en-centro-comercial",
        "Nave industrial": "nave-industrial",
        "Oficina": "oficinas",
        "Quinta": "quinta",
        "Rancho": "rancho",
        "Terreno comercial": "terreno-comercial",
        "Terreno industrial": "terreno-industrial",
        "Villa": "villa"
    }
    


    # Base URL for inmuebles24
    inmuebles24_main_url = "https://www.inmuebles24.com/"
    
    
    print("🔍 DEBUG: Inmuebles24 Scraper Analysis")
    print("=" * 50)
    
    # Step 1: Test the working URL to know if the page is working
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
    
    # Inmuebles24 URL pattern seems to be (FOR THE FIRST PAGE):
    # /{property-type}-en-{rentOrBuy}-en-{city}-mas-de-5-pesos.html
    

    """
    # Step 3: Find maximum pages (adapted for inmuebles24)
    print(f"\n📍 Step 3: Finding maximum pages")
    
    try:
        html = requests.get(working_url)
        soup = BeautifulSoup(html.text, "html.parser")
        # Capture screenshots
        results['screenshots']['full'] = await page.screenshot(full_page=True)
        
        
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
    """
    # Step 4: Extract property links (adapted for inmuebles24)
    print(f"\n📍 Step 4: Testing property link extraction")
    
    try:
        
        
        merged_data, csv_file = await scrape_all_property_types(
        base_url="https://www.inmuebles24.com/",
        search_criteria={
            "rentOrBuy": "venta",
            "city": "ciudad-de-mexico"
        },  
        page_limit=None,
        property_type_slugs=property_type_slugs,
        headless=False,
        csv_path="backgroundtests/csv/property_cards_all.csv",
        use_human_label_for_tipo=False  # puts "Departamento", "Casa", etc. into tipo_inmueble
    )


        """
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
        """
    except Exception as e:
        print(f"❌ Error extracting links: {e}")
    """
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
    """
if __name__ == "__main__":
    asyncio.run(debug_inmuebles24_scraper())
    