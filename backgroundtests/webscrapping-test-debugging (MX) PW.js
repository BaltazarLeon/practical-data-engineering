// debug-inmuebles24.js
// Node.js port of your Python Inmuebles24 scraper

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

// ---------- helpers ----------
function mergePlaywrightData(runDataList) {
  const merged = {
    property_cards: [],
    screenshots: [],
    network_requests: [],
    console_logs: [],
    metrics: [],
  };

  for (const run of runDataList) {
    merged.property_cards.push(...(run.property_cards || []));
    // (screenshots/network/console/metrics kept minimal to avoid huge files)
  }
  return merged;
}

function toCsv(rows) {
  if (!rows || rows.length === 0) return "";
  const headers = Array.from(
    rows.reduce((set, r) => {
      Object.keys(r).forEach((k) => set.add(k));
      return set;
    }, new Set())
  );
  const escape = (v) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [
    headers.join(","),
    ...rows.map((r) => headers.map((h) => escape(r[h])).join(",")),
  ];
  return lines.join("\n");
}

function ts() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return (
    d.getFullYear().toString() +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    "_" +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds())
  );
}

function buildInmuebles24Url(base, slug, rentOrBuy, city) {
  return `${base}${slug}-en-${rentOrBuy}-en-${city}-mas-de-5-pesos.html`;
}

// Enhanced capture function with Cloudflare bypass capabilities
async function captureWithPlaywrightEnhanced(url, { 
  propertyType = null, 
  headless = false, 
  proxy = null,
  userDataDir = null,
  captchaSolver = null 
} = {}) {
  
  // Randomize viewport to avoid fingerprint consistency
  const viewport = {
    width: 1280 + Math.floor(Math.random() * 100),
    height: 720 + Math.floor(Math.random() * 100)
  };

  // Browser launch args with enhanced stealth
  const launchArgs = [
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security",
    "--disable-extensions", 
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-features=VizDisplayCompositor",
    "--disable-ipc-flooding-protection",
    "--disable-backgrounding-occluded-windows",
    "--disable-component-update",
    "--disable-client-side-phishing-detection",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-first-run",
    "--mute-audio",
    "--hide-scrollbars",
    "--disable-component-extensions-with-background-pages",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=TranslateUI"
  ];

  // Add proxy if provided
  if (proxy) {
    launchArgs.push(`--proxy-server=${proxy}`);
  }

  // Use persistent context if userDataDir provided for session continuity
  let browser, context;
  
  if (userDataDir) {
    browser = await chromium.launchPersistentContext(userDataDir, {
      headless,
      args: launchArgs,
      viewport
    });
    context = browser; // In persistent context, browser IS the context
  } else {
    browser = await chromium.launch({
      headless,
      args: launchArgs
    });
    
    context = await browser.newContext({
      viewport,
      // Randomize user agent slightly but keep it realistic
      userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      locale: "en-US",
      timezoneId: "America/New_York", // Match with proxy location if using geo-specific proxies
      extraHTTPHeaders: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
      }
    });
  }

  const page = await context.newPage();

  // Enhanced stealth script injection
  await page.addInitScript(() => {
    // Remove webdriver traces
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    
    // Fix languages
    Object.defineProperty(navigator, "languages", { 
      get: () => ["en-US", "en"] 
    });
    
    // Add chrome object
    Object.defineProperty(window, "chrome", { 
      get: () => ({ 
        runtime: {},
        csi: function() {},
        loadTimes: function() {
          return {
            commitLoadTime: Date.now() / 1000 - Math.random(),
            connectionInfo: 'http/1.1',
            finishDocumentLoadTime: Date.now() / 1000 - Math.random(),
            finishLoadTime: Date.now() / 1000 - Math.random(),
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000 - Math.random(),
            navigationType: 'Other',
            npnNegotiatedProtocol: 'unknown',
            requestTime: Date.now() / 1000 - Math.random(),
            startLoadTime: Date.now() / 1000 - Math.random(),
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: false
          };
        }
      })
    });
    
    // Mock plugins
    Object.defineProperty(navigator, "plugins", {
      get: () => [
        {
          0: {
            type: "application/x-google-chrome-pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
          description: "Portable Document Format", 
          filename: "internal-pdf-viewer",
          length: 1,
          name: "Chrome PDF Plugin",
        },
        {
          0: {
            type: "application/x-nacl",
            suffixes: "",
            description: "Native Client Executable",
          },
          1: {
            type: "application/x-pnacl",
            suffixes: "",
            description: "Portable Native Client Executable",
          },
          description: "Native Client",
          filename: "internal-nacl-plugin", 
          length: 2,
          name: "Native Client",
        }
      ],
    });

    // Fix permissions
    const originalQuery = window.navigator.permissions?.query;
    if (originalQuery) {
      window.navigator.permissions.query = (parameters) =>
        parameters.name === "notifications"
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters);
    }

    // Mock WebGL
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === 37445) {
        return 'Intel Inc.';
      }
      if (parameter === 37446) {
        return 'Intel(R) Iris(TM) Graphics 6100';
      }
      return getParameter(parameter);
    };

    // Override toString methods
    WebGLRenderingContext.prototype.getParameter.toString = () => 'function getParameter() { [native code] }';
    
    // Mock hardware concurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
      get: () => 4
    });

    // Mock device memory
    Object.defineProperty(navigator, 'deviceMemory', {
      get: () => 8
    });

    // Add connection info
    Object.defineProperty(navigator, 'connection', {
      get: () => ({
        effectiveType: '4g',
        rtt: 50,
        downlink: 10
      })
    });
  });

  // Network and console monitoring
  const network_requests = [];
  const console_logs = [];
  
  page.on("request", (req) =>
    network_requests.push({
      url: req.url(),
      method: req.method(),
      type: req.resourceType(),
      timestamp: Date.now()
    })
  );
  
  page.on("console", (msg) =>
    console_logs.push({
      type: msg.type(),
      text: msg.text(),
      timestamp: Date.now()
    })
  );

  try {
    console.log(`🌐 Navigating to ${url}`);
    
    // Navigate with longer timeout for Cloudflare challenges
    await page.goto(url, { 
      waitUntil: "domcontentloaded", 
      timeout: 60000 
    });
    
    // Wait for Cloudflare challenges to complete
    await page.waitForTimeout(5000);
    
    // Check for Cloudflare CAPTCHA challenges
    const captchaDetected = await detectCaptcha(page);
    
    if (captchaDetected.found) {
      console.log(`🚨 CAPTCHA detected: ${captchaDetected.type}`);
      
      if (captchaSolver && captchaDetected.type !== 'unknown') {
        console.log('🤖 Attempting to solve CAPTCHA...');
        const solved = await solveCaptcha(page, captchaDetected.type, captchaSolver);
        
        if (solved) {
          console.log('✅ CAPTCHA solved successfully');
          await page.waitForTimeout(3000); // Wait for page to reload after solving
        } else {
          console.log('❌ CAPTCHA solving failed');
          throw new Error('CAPTCHA could not be solved');
        }
      } else {
        throw new Error(`CAPTCHA detected but no solver provided. Type: ${captchaDetected.type}`);
      }
    }

    // Additional wait for dynamic content
    await page.waitForTimeout(2000);

    // Extract property cards with enhanced error handling
    const property_cards = await page.evaluate((ptype) => {
      const container = document.querySelector("div.postingsList-module__postings-container");
      if (!container) {
        console.log('Property container not found');
        return [];
      }

      const toNumber = (s) => {
        if (!s) return null;
        const cleaned = s.replace(/,/g, "");
        const m = cleaned.match(/\d+(?:\.\d+)?/);
        return m ? parseFloat(m[0]) : null;
      };

      const firstNumber = (s) => {
        if (!s) return null;
        const m = s.replace(/,/g, "").match(/\d+(?:\.\d+)?/);
        return m ? parseFloat(m[0]) : null;
      };

      return Array.from(container.children).map((card, index) => {
        try {
          const sub = card.querySelector("[data-id][data-to-posting]");
          const data_id = sub ? sub.getAttribute("data-id") : null;
          const url = sub ? sub.getAttribute("data-to-posting") || null : null;

          const priceEl = card.querySelector('div.postingPrices-module__price[data-qa="POSTING_CARD_PRICE"]');
          let precio = null, moneda = null;
          if (priceEl) {
            const raw = priceEl.innerText.trim();
            moneda = /USD/i.test(raw) ? "USD" : "MN";
            precio = toNumber(raw);
          }

          const locEl = card.querySelector(
            'h2.postingLocations-module__location-text[data-qa="POSTING_CARD_LOCATION"]'
          );
          let zona = null;
          if (locEl) {
            const parts = locEl.innerText.split(",");
            if (parts.length > 1) zona = parts[1].trim();
          }

          const addrEl = card.querySelector("div.postingLocations-module__location-address");
          let direccion = null, codigo_postal = null;
          if (addrEl) {
            const t = addrEl.innerText.trim();
            direccion = t;
            const cp = t.match(/\b\d{5}\b/);
            if (cp) codigo_postal = cp[0];
          }

          let tamano_lote = null, recamaras = null, banos = null, estacionamientos = null;
          const featuresEl = card.querySelector('h3[data-qa="POSTING_CARD_FEATURES"]');
          if (featuresEl) {
            featuresEl.querySelectorAll("span").forEach((span) => {
              const txt = (span.innerText || "").trim().toLowerCase();
              if (/(m²|m2) lote$/.test(txt)) tamano_lote = firstNumber(txt);
              if (/rec\.$/.test(txt)) recamaras = firstNumber(txt);
              if (/baños?$/.test(txt)) banos = firstNumber(txt);
              if (/estac\.$/.test(txt)) estacionamientos = firstNumber(txt);
            });
          }

          const descEl = card.querySelector("h3.postingCard-module__posting-description a");
          const descripcion = descEl ? descEl.innerText.trim() : null;

          const sellerImg = card.querySelector(
            "div.postingPublisher-module__container-logo-publisher img"
          );
          const url_vendedor = sellerImg ? sellerImg.getAttribute("src") : null;

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
            tipo_inmueble: ptype || null,
            scrape_index: index
          };
        } catch (error) {
          console.log(`Error processing card ${index}:`, error.message);
          return null;
        }
      }).filter(card => card !== null);
    }, propertyType);

    // Enhanced page metrics
    const metrics = await page.evaluate(() => ({
      totalElements: document.getElementsByTagName("*").length,
      totalImages: document.images.length,
      totalLinks: document.links.length,
      totalScripts: document.scripts.length,
      bodyText: document.body.innerText.substring(0, 1000),
      loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart,
      domReady: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
      pageHeight: document.body.scrollHeight,
      viewportHeight: window.innerHeight
    }));

    const content = await page.content();
    
    // Save cookies for session persistence
    const cookies = await context.cookies();

    return {
      title: await page.title(),
      url: page.url(),
      content,
      screenshots: {},
      prices: {},
      network_requests,
      console_logs,
      property_cards,
      metrics,
      cookies, // Include cookies for session management
      captcha_encountered: captchaDetected.found,
      success: true
    };

  } catch (error) {
    console.error(`❌ Error during capture: ${error.message}`);
    return {
      success: false,
      error: error.message,
      url,
      property_cards: [],
      metrics: {}
    };
  } finally {
    if (userDataDir) {
      // For persistent context, just close the context
      await context.close();
    } else {
      // For regular browser, close the browser
      await browser.close();
    }
  }
}

// Helper function to detect various CAPTCHA types
async function detectCaptcha(page) {
  try {
    // Check for Cloudflare challenge patterns
    const cfChallenge = await page.$('div.cf-browser-verification, div.cf-challenge, div.cf-wrapper');
    if (cfChallenge) {
      return { found: true, type: 'cloudflare', element: cfChallenge };
    }

    // Check for hCaptcha
    const hCaptcha = await page.$('iframe[src*="hcaptcha"], div[class*="hcaptcha"]');
    if (hCaptcha) {
      return { found: true, type: 'hcaptcha', element: hCaptcha };
    }

    // Check for reCAPTCHA
    const recaptcha = await page.$('iframe[src*="recaptcha"], div[class*="recaptcha"], div.g-recaptcha');
    if (recaptcha) {
      return { found: true, type: 'recaptcha', element: recaptcha };
    }

    // Check for Turnstile
    const turnstile = await page.$('iframe[src*="turnstile"], div[class*="turnstile"]');
    if (turnstile) {
      return { found: true, type: 'turnstile', element: turnstile };
    }

    // Generic CAPTCHA iframe detection
    const captchaIframe = await page.$('iframe[src*="captcha"]');
    if (captchaIframe) {
      return { found: true, type: 'unknown', element: captchaIframe };
    }

    return { found: false, type: null, element: null };
  } catch (error) {
    console.log('Error detecting CAPTCHA:', error.message);
    return { found: false, type: null, element: null };
  }
}

// Placeholder CAPTCHA solver - integrate with 2Captcha, CapMonster, etc.
async function solveCaptcha(page, captchaType, solver) {
  // This is a placeholder - you would integrate with actual CAPTCHA solving services
  console.log(`Attempting to solve ${captchaType} CAPTCHA with solver: ${solver}`);
  
  if (captchaType === 'cloudflare') {
    // For simple Cloudflare "verify you are human" challenges
    try {
      const verifyButton = await page.$('input[type="button"][value*="Verify"], button:has-text("Verify")');
      if (verifyButton) {
        await verifyButton.click();
        await page.waitForTimeout(3000);
        return true;
      }
    } catch (error) {
      console.log('Error solving Cloudflare challenge:', error.message);
    }
  }
  
  // For hCaptcha/reCAPTCHA, you would integrate with services like:
  // - 2Captcha API
  // - CapMonster
  // - AntiCaptcha
  // Example integration would go here
  
  return false;
}

// Usage example with proxy rotation and session persistence
async function scrapeWithProxyRotation(urls, proxies) {
  const results = [];
  const sessionDir = './browser-sessions';
  
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    const proxy = proxies[i % proxies.length]; // Rotate proxies
    
    try {
      const result = await captureWithPlaywrightEnhanced(url, {
        propertyType: 'casa',
        headless: false, // Use headed mode for better stealth
        proxy: proxy,
        userDataDir: `${sessionDir}/session-${i % 3}`, // Reuse 3 different sessions
        captchaSolver: '2captcha' // Your CAPTCHA solver
      });
      
      results.push(result);
      
      // Add delay between requests to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
      
    } catch (error) {
      console.error(`Failed to scrape ${url}:`, error.message);
      results.push({ url, success: false, error: error.message });
    }
  }
  
  return results;
}

module.exports = {
  captureWithPlaywrightEnhanced,
  scrapeWithProxyRotation,
  detectCaptcha,
  solveCaptcha
};

// ---------- pagination & historical ----------
async function runPlaywrightHistorical(url, { propertyType = null, n = null, headless = false } = {}) {
  const runs = [];

  console.log(`Step 1: Running initial capture for ${url}`);
  const initial = await captureWithPlaywright(url, { propertyType, headless });
  runs.push(initial);

  // Extract total listings → page count
  let lastPageNum = 1;
  try {
    const html = initial.content || "";
    const m = html.match(/<h1[^>]*class="postingsTitle-module__title"[^>]*>([\d,.]+)/i);
    if (m) {
      const numStr = m[1].replace(/,/g, "");
      const total = parseInt(numStr, 10);
      lastPageNum = Math.ceil(total / 30) || 1;
      console.log(`Extracted total listings: ${total}`);
      console.log(`Calculated lastPageNum: ${lastPageNum}`);
    } else {
      console.log("Could not extract total listings, defaulting lastPageNum to 1");
    }
  } catch {
    console.log("Title parse failed, defaulting lastPageNum to 1");
  }

  if (n != null && lastPageNum > n) {
    console.log(`Page limit specified: ${n} (capping from ${lastPageNum})`);
    lastPageNum = n;
  } else if (n == null) {
    console.log("No page limit (n) specified, scraping all pages.");
  }

  for (let i = 2; i <= lastPageNum; i++) {
    const pagedUrl = url.replace(".html", `-pagina-${i}.html`);
    console.log(`Step 2: Running capture ${i} for ${pagedUrl}`);
    const r = await captureWithPlaywright(pagedUrl, { propertyType, headless });
    runs.push(r);
  }

  const merged = mergePlaywrightData(runs);

  // Save CSV for this batch
  const dir = path.join("backgroundtests", "csv");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `property_cards_${ts()}_${(propertyType || "type").replace(/\s+/g, "_")}.csv`);
  const csv = toCsv(merged.property_cards || []);
  fs.writeFileSync(file, csv, "utf8");
  console.log(`✅ Saved ${merged.property_cards.length} property cards to ${file}`);

  console.log(`All runs complete. Total runs merged: ${runs.length}`);
  return merged;
}

// ---------- multi-type orchestrator ----------
async function scrapeAllPropertyTypes({
  baseUrl,
  searchCriteria,
  propertyTypeSlugs,
  headless = false,
  pageLimit = 3,
  csvPath = "backgroundtests/csv/property_cards_all.csv",
  useHumanLabelForTipo = true,
}) {
  const allRuns = [];

  for (const [humanLabel, slug] of Object.entries(propertyTypeSlugs)) {
    const url = buildInmuebles24Url(
      baseUrl,
      slug,
      searchCriteria.rentOrBuy,
      searchCriteria.city
    );
    const tipoValue = useHumanLabelForTipo ? humanLabel : slug;
    console.log(`\n🎭 Scraping: ${humanLabel} -> ${url}`);

    const data = await runPlaywrightHistorical(url, {
      propertyType: tipoValue,
      n: pageLimit,
      headless,
    });
    allRuns.push(data);
  }

  const merged = mergePlaywrightData(allRuns);

  // Write single merged CSV
  const dir = path.dirname(csvPath);
  fs.mkdirSync(dir, { recursive: true });
  const finalCsv = csvPath.replace(/\.csv$/i, `_${ts()}.csv`);
  fs.writeFileSync(finalCsv, toCsv(merged.property_cards || []), "utf8");
  console.log(`✅ Saved ${merged.property_cards.length} property cards (all types) to ${finalCsv}`);

  return { merged, finalCsv };
}

// ---------- debug runner ----------
async function debugInmuebles24Scraper() {
  console.log("🔍 DEBUG: Inmuebles24 Scraper Analysis");
  console.log("==================================================");

  const propertyTypeSlugs = {
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
    "Villa": "villa",
  };

  const baseUrl = "https://www.inmuebles24.com/";
  const searchCriteria = { rentOrBuy: "venta", city: "ciudad-de-mexico" };

  try {
    await scrapeAllPropertyTypes({
      baseUrl,
      searchCriteria,
      propertyTypeSlugs,
      headless: false,          // set true for CI / servers
      pageLimit: null,          // null = try all pages (based on listing count / 30)
      csvPath: "backgroundtests/csv/property_cards_all.csv",
      useHumanLabelForTipo: false,
    });
  } catch (err) {
    console.error("❌ Error in debug run:", err);
  }
}

if (require.main === module) {
  debugInmuebles24Scraper();
}
