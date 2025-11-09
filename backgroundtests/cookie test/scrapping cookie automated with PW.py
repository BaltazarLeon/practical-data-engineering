import asyncio
import time
import json
import requests
from playwright.async_api import async_playwright

class Inmuebles24PlaywrightScraper:
    def __init__(self):
        """
        Initialize the Playwright scraper for Inmuebles24
        """
        self.base_url = "https://inmuebles24.com"
        self.all_properties = []
        self.cf_clearance = None
        self.user_agent = None
    
    def get_unflare_cookie(self, unflare_url="http://localhost:5002"):
        """
        Get cf_clearance cookie from Unflare service
        
        Args:
            unflare_url (str): URL of your Unflare service
            
        Returns:
            tuple: (cf_clearance_cookie, user_agent, all_cookies) or (None, None, {}) if failed
        """
        try:
            target_url = "https://www.inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-5.html"
                         
            payload = {
                "url": target_url,
                "timeout": 60000,
            }
            
            print("🔐 Getting cf_clearance cookie from Unflare...")
            print(f"🎯 Target URL: {target_url}")
            response = requests.post(f"{unflare_url}/scrape", 
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
                
                print(f"🍪 Total cookies received: {len(cookies_dict)}")
                print(f"🔑 Cookie names: {list(cookies_dict.keys())}")
                
                if cf_clearance and user_agent:
                    print(f"✅ Successfully got cf_clearance: {cf_clearance[:20]}...")
                    print(f"🔧 User agent from Unflare: {user_agent}")
                    
                    # Check if user agent indicates Chrome vs Chromium
                    if 'Chrome/' in user_agent and 'Chromium/' not in user_agent:
                        print("✅ Unflare used Chrome (good for fingerprint matching)")
                    else:
                        print("⚠️  Unflare might be using Chromium - fingerprint may differ")
                    
                    self.cf_clearance = cf_clearance
                    self.user_agent = user_agent
                    return cf_clearance, user_agent, cookies_dict
                else:
                    print("❌ cf_clearance cookie not found in response")
                    print(f"📋 Available cookies: {list(cookies_dict.keys())}")
                    return None, None, {}
            else:
                print(f"❌ Unflare request failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return None, None, {}
                
        except Exception as e:
            print(f"❌ Error getting cookie from Unflare: {e}")
            return None, None, {}
    
    async def capture_with_playwright(self, url, property_type=None, headless=False):
        """
        Capture the page using Playwright with Cloudflare bypass
        
        Args:
            url (str): URL to scrape
            property_type (str): Type of property being scraped
            headless (bool): Whether to run browser in headless mode
            
        Returns:
            dict: Results containing property cards and other data
        """
        if not self.cf_clearance or not self.user_agent:
            print("❌ No cf_clearance cookie available. Getting one from Unflare...")
            cf_clearance, user_agent, cookies_dict = self.get_unflare_cookie()
            if not cf_clearance:
                raise Exception("Failed to get cf_clearance cookie from Unflare")
        else:
            cookies_dict = {'cf_clearance': self.cf_clearance}
        
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
                    '--user-agent=' + self.user_agent  # Force same user agent
                ]
            )
            
            # Create context with EXACT same fingerprint as Unflare
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.user_agent,  # Use EXACT user agent from Unflare
                locale='en-US',
                timezone_id='America/Mexico_City',  # Match Mexico location
                geolocation={'latitude': 19.4326, 'longitude': -99.1332},  # Mexico City coords
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
            print(f"🌐 Navigating to {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)  # let initial content load
                
                # Check if we got blocked by Cloudflare
                page_content = await page.content()
                if 'cloudflare' in page_content.lower() and 'checking your browser' in page_content.lower():
                    print("⚠️  Detected Cloudflare challenge page, waiting longer...")
                    await page.wait_for_timeout(10000)
                    
                    # Try to refresh with the cookies
                    await page.reload(wait_until='domcontentloaded')
                    await page.wait_for_timeout(3000)
                
            except Exception as e:
                print(f"❌ Navigation error: {e}")
                await browser.close()
                return {'property_cards': [], 'total_found': 0, 'error': str(e)}
            
            # Wait a bit more for any lazy-loaded content
            await page.wait_for_timeout(2000)
            
            # Capture various data
            results = {
                'title': await page.title(),
                'url': page.url,
                'property_cards': [],
                'total_found': 0
            }
            
            # Check if page loaded correctly
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Extract property cards using your JavaScript
            try:
                property_cards =  await page.evaluate( 
                    ''' (ptype) => {
                    const container = document.querySelector('div.postingsList-module__postings-container');
                    if (!container) {
                        console.log('Container not found');
                        return [];
                    }

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

                    const cards = Array.from(container.children);
                    console.log(`Found ${cards.length} cards in container`);

                    return cards.map((card, index) => {
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
                            card_index: index,
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
                results['total_found'] = len(property_cards)
                
            except Exception as e:
                print(f"❌ Error executing JavaScript: {e}")
                results['property_cards'] = []
                results['total_found'] = 0
                results['js_error'] = str(e)
            
            # Scroll to load any lazy content
            try:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1000)
            except:
                pass
            
            await browser.close()
            
            return results
    
    async def scrape_page(self, page_num, property_type="departamentos", headless=True):
        """
        Scrape a specific page and extract property data
        
        Args:
            page_num (int): Page number to scrape
            property_type (str): Type of property (departamentos, casas, etc.)
            headless (bool): Whether to run browser in headless mode
            
        Returns:
            list: List of property dictionaries
        """
        url = f"https://www.inmuebles24.com/{property_type}-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-{page_num}.html"
        
        try:
            print(f"\n🏠 Scraping page {page_num} for {property_type}...")
            results = await self.capture_with_playwright(url, property_type, headless)
            
            property_cards = results.get('property_cards', [])
            total_found = results.get('total_found', 0)
            
            if 'error' in results:
                print(f"❌ Page load error: {results['error']}")
                return []
            
            if 'js_error' in results:
                print(f"⚠️  JavaScript execution error: {results['js_error']}")
            
            print(f"✅ Found {total_found} properties on page {page_num}")
            
            # Print each property card
            if property_cards:
                print(f"\n📋 PROPERTY CARDS from Page {page_num}:")
                print("=" * 80)
                for i, prop in enumerate(property_cards, 1):
                    print(f"\n🏡 Property {i}:")
                    print(f"   ID: {prop.get('data_id')}")
                    print(f"   Precio: {prop.get('precio')} {prop.get('moneda', '')}")
                    print(f"   Zona: {prop.get('zona')}")
                    print(f"   Dirección: {prop.get('direccion')}")
                    print(f"   Código Postal: {prop.get('codigo_postal')}")
                    print(f"   Recámaras: {prop.get('recamaras')}")
                    print(f"   Baños: {prop.get('banos')}")
                    print(f"   Estacionamientos: {prop.get('estacionamientos')}")
                    print(f"   Tamaño Lote: {prop.get('tamano_lote')} m²")
                    print(f"   Descripción: {prop.get('descripcion', '')[:100] if prop.get('descripcion') else 'N/A'}...")
                    print(f"   URL: {prop.get('url')}")
                    print(f"   Tipo: {prop.get('tipo_inmueble')}")
                    print("-" * 40)
                
                # Also print as clean JSON for easy copying
                print(f"\n📄 JSON DATA for Page {page_num}:")
                print(json.dumps(property_cards, indent=2, ensure_ascii=False))
            else:
                print(f"❌ No properties found on page {page_num}")
                print("   This could be due to:")
                print("   - Cloudflare blocking the request")
                print("   - Page structure changes")
                print("   - Invalid page number")
                print("   - Network issues")
            
            return property_cards
            
        except Exception as e:
            print(f"❌ Error scraping page {page_num}: {e}")
            return []
    
    async def scrape_multiple_pages(self, start_page=5, end_page=10, property_type="departamentos", delay=3, headless=True):
        """
        Scrape multiple pages and collect all property data
        
        Args:
            start_page (int): Starting page number
            end_page (int): Ending page number (inclusive)
            property_type (str): Type of property
            delay (int): Delay between requests in seconds
            headless (bool): Whether to run browser in headless mode
        """
        print(f"🚀 Starting to scrape pages {start_page} to {end_page} for {property_type}")
        print(f"⏱️  Delay between pages: {delay} seconds")
        print(f"👁️  Headless mode: {headless}")
        
        # Get cookies once at the beginning
        print("\n🔐 Getting fresh cookies from Unflare...")
        cf_clearance, user_agent, cookies_dict = self.get_unflare_cookie()
        if not cf_clearance:
            print("❌ Failed to get cf_clearance cookie. Cannot proceed.")
            return []
        
        all_properties = []
        
        for page_num in range(start_page, end_page + 1):
            properties = await self.scrape_page(page_num, property_type, headless)
            all_properties.extend(properties)
            
            # Add delay between requests to be respectful
            if page_num < end_page:
                print(f"⏳ Waiting {delay} seconds before next page...")
                await asyncio.sleep(delay)
        
        print(f"\n🎉 Scraping completed!")
        print(f"📊 Total properties found: {len(all_properties)}")
        
        # Print summary
        if all_properties:
            print(f"\n📈 SUMMARY:")
            print(f"   Total properties: {len(all_properties)}")
            print(f"   Pages scraped: {start_page} to {end_page}")
            print(f"   Property type: {property_type}")
            
            # Save to file for backup
            filename = f"inmuebles24_{property_type}_pages_{start_page}_to_{end_page}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_properties, f, indent=2, ensure_ascii=False)
            print(f"💾 Data saved to: {filename}")
        
        self.all_properties = all_properties
        return all_properties

# Async main function
async def main():
    """
    Main function to run the Playwright scraper with Unflare integration
    """
    scraper = Inmuebles24PlaywrightScraper()
    
    # Test single page first
    print("🧪 Testing single page extraction...")
    await scraper.scrape_page(6, "departamentos", headless=False)  # Set headless=False to see browser
    
    # Uncomment below to scrape multiple pages
    # print("\n🚀 Starting multi-page scraping...")
    # await scraper.scrape_multiple_pages(
    #     start_page=5, 
    #     end_page=8, 
    #     property_type="departamentos",
    #     delay=3,
    #     headless=True
    # )

def run_scraper():
    """
    Wrapper function to run the async scraper
    """
    print("🎭 Starting Inmuebles24 Playwright + Unflare Scraper")
    print("=" * 60)
    print("🔧 Prerequisites:")
    print("   - Unflare service running on localhost:5002")
    print("   - Playwright installed: pip install playwright")
    print("   - Chromium installed: playwright install chromium")
    print("=" * 60)
    asyncio.run(main())

if __name__ == "__main__":
    run_scraper()