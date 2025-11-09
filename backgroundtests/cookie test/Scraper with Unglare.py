"""
Independent debug script for Inmuebles24 scraper
Based on the original scraping logic but adapted for inmuebles24.com
Now with Unflare integration for Cloudflare bypass
"""
from pathlib import Path
from playwright.async_api import async_playwright
import pandas as pd
import math
import asyncio
import json
from datetime import datetime
import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

STATE_PATH = "cf_storage_state.json"

class UnflareIntegration:
    """Handles Unflare service integration for Cloudflare bypass"""
    
    def __init__(self, unflare_url="http://localhost:5002"):
        self.unflare_url = unflare_url
        self.cf_clearance = None
        self.user_agent = None
        self.cookies_dict = {}
    
    def get_unflare_cookie(self):
        """
        Get cf_clearance cookie from Unflare service
        
        Returns:
            tuple: (cf_clearance_cookie, user_agent, all_cookies) or (None, None, {}) if failed
        """
        try:
            target_url = "https://www.inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-5.html"
                         
            payload = {
                "url": target_url,
                "timeout": 60000,
            }
            
            print("Getting cf_clearance cookie from Unflare...")
            print(f"Target URL: {target_url}")
            response = requests.post(f"{self.unflare_url}/scrape", 
                                   json=payload, 
                                   timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract cf_clearance cookie and ALL cookies
                cf_clearance = None
                cookies_dict = {}
                
                for cookie in data.get('cookies', []):
                    cookies_dict[cookie['name']] = cookie['value']
                    if cookie['name'] == 'cf_clearance':
                        cf_clearance = cookie['value']
                
                user_agent = data.get('headers', {}).get('user-agent', '')
                
                print(f"Total cookies received: {len(cookies_dict)}")
                print(f"Cookie names: {list(cookies_dict.keys())}")
                
                if cf_clearance and user_agent:
                    print(f"Successfully got cf_clearance: {cf_clearance[:20]}...")
                    print(f"User agent from Unflare: {user_agent}")
                    
                    # Check if user agent indicates Chrome vs Chromium
                    if 'Chrome/' in user_agent and 'Chromium/' not in user_agent:
                        print("Unflare used Chrome (good for fingerprint matching)")
                    else:
                        print("Unflare might be using Chromium - fingerprint may differ")
                    
                    self.cf_clearance = cf_clearance
                    self.user_agent = user_agent
                    self.cookies_dict = cookies_dict
                    return cf_clearance, user_agent, cookies_dict
                else:
                    print("cf_clearance cookie not found in response")
                    print(f"Available cookies: {list(cookies_dict.keys())}")
                    return None, None, {}
            else:
                print(f"Unflare request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None, None, {}
                
        except Exception as e:
            print(f"Error getting cookie from Unflare: {e}")
            return None, None, {}

# Global Unflare instance
unflare = UnflareIntegration()

# Function to merge multiple run data dictionaries
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
        
    return merged_data

# Function to run multiple cycles and merge results
async def run_playwright_historical(url: str, property_type=None, n: int = None, headless: bool = False):
    """
    Executes capture_with_playwright for a URL, stores results in historicaldata,
    then runs n cycles, storing each result in rundata and merges into historicaldata.
    """
    run_data_list = []

    # Step 1: Initial run
    print(f"Step 1: Running initial capture for {url}")
    initial_data = await capture_with_playwright(url, property_type=property_type, headless=headless)
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
            lastPageNum = n

    # Step 2: Loop for n cycles
    for i in range(1, lastPageNum + 2):
        # Insert -pagina-{i} before .html in the URL
        paged_url = url.replace('.html', f'-pagina-{i}.html')
        print(f"Step 2: Running capture {i} for {paged_url}")
        rundata = await capture_with_playwright(paged_url, property_type=property_type, headless=headless)
        run_data_list.append(rundata)

    # Merge all runs into historicaldata
    historicaldata = merge_playwright_data(run_data_list)
    
    # Save the historical data to a csv file
    df = pd.DataFrame(historicaldata.get('property_cards', []))
    
    # Ensure directory exists
    try:
        import os
        os.makedirs(os.path.dirname("backgroundtests/csv/"), exist_ok=True)
    except Exception:
        pass
    
    # Timestamped filename to avoid overwrites
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_csv = f"backgroundtests/csv/property_cards_{ts}_{property_type}.csv"
    df.to_csv(final_csv, index=False, encoding="utf-8")
    print(f"Saved {len(df)} property cards to {final_csv}")

    print(f"All runs complete. Total runs merged: {len(run_data_list)}")
    return historicaldata

# Function to Capture Data using Playwright with Unflare integration
async def capture_with_playwright(url, property_type=None, headless=False):
    """Capture the page using Playwright with Cloudflare bypass via Unflare"""
    
    # Get fresh cookies from Unflare if not already available
    if not unflare.cf_clearance or not unflare.user_agent:
        print("No cf_clearance cookie available. Getting one from Unflare...")
        cf_clearance, user_agent, cookies_dict = unflare.get_unflare_cookie()
        if not cf_clearance:
            raise Exception("Failed to get cf_clearance cookie from Unflare")
    else:
        cookies_dict = unflare.cookies_dict
    
    async with async_playwright() as p:
        # Launch browser with stealth settings to match Unflare fingerprint
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-default-apps',
                '--user-agent=' + unflare.user_agent
            ]
        )

        # Create context with EXACT same fingerprint as Unflare
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=unflare.user_agent,
            locale='en-US',
            timezone_id='America/Mexico_City',
            geolocation={'latitude': 19.4326, 'longitude': -99.1332},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
        )

        # Add stealth scripts to further mask automation
        await context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override automation properties
            delete navigator.__proto__.webdriver;
            
            // Override chrome property to match real Chrome
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Add all cookies from Unflare, especially cf_clearance
        await context.add_cookies([
            {
                'name': name,
                'value': value,
                'domain': '.inmuebles24.com',
                'path': '/',
                'httpOnly': True,
                'secure': True
            } for name, value in cookies_dict.items()
        ])

        # Create page
        page = await context.new_page()

        # Navigate and wait for content
        print(f"Navigating to {url}")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check if we got blocked by Cloudflare
            page_content = await page.content()
            if 'cloudflare' in page_content.lower() and 'checking your browser' in page_content.lower():
                print("Detected Cloudflare challenge page, waiting longer...")
                await page.wait_for_timeout(10000)
                
                # Try to refresh with the cookies
                await page.reload(wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
        except Exception as e:
            print(f"Navigation error: {e}")
            await browser.close()
            return {'property_cards': [], 'content': '', 'error': str(e)}

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

        # Extract property cards using the same JavaScript logic
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
            tipo_inmueble: ptype || null
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
        await page.wait_for_timeout(1000)

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
        print(f"\nScraping: {human_label} -> {url}")

        data = await run_playwright_historical(
            url,
            property_type=tipo_inmueble_value,
            n=page_limit,
            headless=headless
        )
        all_runs.append(data)

    # Merge everything
    merged = merge_playwright_data(all_runs)

    # Save CSV (property_cards only)
    df = pd.DataFrame(merged.get('property_cards', []))
    
    # Ensure directory exists
    try:
        import os
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    except Exception:
        pass

    # Timestamped filename to avoid overwrites
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_csv = csv_path.replace(".csv", f"_{ts}.csv")
    df.to_csv(final_csv, index=False, encoding="utf-8")
    print(f"Saved {len(df)} property cards (all types) to {final_csv}")

    return merged, final_csv

async def debug_inmuebles24_scraper():
    """Debug the Inmuebles24 scraping logic step by step with Unflare integration"""
    
    # Define property type slugs for inmuebles24
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

    print("DEBUG: Inmuebles24 Scraper Analysis with Unflare")
    print("=" * 50)
    print("Prerequisites:")
    print("- Unflare service running on localhost:5002")
    print("- Playwright installed: pip install playwright")
    print("- Chromium installed: playwright install chromium")
    print("=" * 50)
    
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
            use_human_label_for_tipo=False
        )
        
        print(f"\nScraping completed successfully!")
        print(f"Total properties scraped: {len(merged_data.get('property_cards', []))}")
        print(f"Data saved to: {csv_file}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        print("Make sure Unflare service is running on localhost:5002")

if __name__ == "__main__":
    asyncio.run(debug_inmuebles24_scraper())