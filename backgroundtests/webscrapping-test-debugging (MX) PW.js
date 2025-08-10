// debug-inmuebles24.js
// Node.js port of your Python Inmuebles24 scraper


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

const { chromium } = require('playwright-extra');
const stealth = require('puppeteer-extra-plugin-stealth')();
const RecaptchaPlugin = require('@extra/recaptcha');
const fs = require('fs');
const path = require('path');

// Configure stealth plugin BEFORE launching browser
chromium.use(stealth);

// Optional: Add CAPTCHA solving capability
// chromium.use(
//   RecaptchaPlugin({
//     provider: {
//       id: '2captcha',
//       token: 'YOUR_2CAPTCHA_API_KEY' // Replace with your actual API key
//     },
//     visualFeedback: true
//   })
// );

// ---------- Enhanced core capture with advanced stealth ----------
async function captureWithPlaywright(url, { 
  propertyType = null, 
  headless = false,
  proxy = null,
  sessionDir = './session-profiles',
  maxRetries = 3 
} = {}) {
  
  let browser;
  let context;
  let attempt = 0;
  
  while (attempt < maxRetries) {
    try {
      // Prepare launch arguments with enhanced stealth
      const launchArgs = [
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--start-maximized",
        // Additional stealth arguments
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-features=BlockInsecurePrivateNetworkRequests"
      ];
      
      // Add proxy if provided
      if (proxy) {
        launchArgs.push(`--proxy-server=${proxy}`);
      }
      
      // Create or load persistent session
      const sessionPath = path.join(sessionDir, `session-${Date.now()}`);
      
      // Check if we have saved cookies
      const cookiesPath = path.join(sessionDir, 'cookies.json');
      const hasSavedCookies = fs.existsSync(cookiesPath);
      
      // Launch browser with enhanced configuration
      if (hasSavedCookies && !browser) {
        // Use persistent context to maintain session
        browser = await chromium.launchPersistentContext(sessionPath, {
          headless,
          args: launchArgs,
          viewport: {
            width: 1366 + Math.floor(Math.random() * 100),
            height: 768 + Math.floor(Math.random() * 100)
          },
          userAgent: getRandomUserAgent(),
          locale: "en-US",
          timezoneId: "America/New_York",
          extraHTTPHeaders: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
          }
        });
        context = browser;
      } else {
        browser = await chromium.launch({
          headless,
          args: launchArgs
        });
        
        context = await browser.newContext({
          viewport: {
            width: 1366 + Math.floor(Math.random() * 100),
            height: 768 + Math.floor(Math.random() * 100)
          },
          userAgent: getRandomUserAgent(),
          locale: "en-US",
          timezoneId: "America/New_York",
          extraHTTPHeaders: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
          }
        });
        
        // Load saved cookies if available
        if (hasSavedCookies) {
          const savedCookies = JSON.parse(fs.readFileSync(cookiesPath, 'utf-8'));
          await context.addCookies(savedCookies);
        }
      }

      const page = await context.newPage();

      // Enhanced fingerprint removal
      await page.addInitScript(() => {
        // Remove webdriver property
        Object.defineProperty(navigator, "webdriver", { 
          get: () => undefined 
        });
        
        // Set realistic languages
        Object.defineProperty(navigator, "languages", { 
          get: () => ["en-US", "en"] 
        });
        
        // Add complete chrome object
        Object.defineProperty(window, "chrome", {
          get: () => ({
            runtime: {
              connect: () => {},
              sendMessage: () => {}
            },
            loadTimes: () => {},
            csi: () => {}
          })
        });
        
        // Enhanced plugins array
        Object.defineProperty(navigator, "plugins", {
          get: () => {
            return Object.create(PluginArray.prototype, {
              length: { value: 3 },
              0: {
                value: {
                  name: "Chrome PDF Plugin",
                  description: "Portable Document Format",
                  filename: "internal-pdf-viewer",
                  length: 1,
                  0: {
                    type: "application/x-google-chrome-pdf",
                    suffixes: "pdf",
                    description: "Portable Document Format"
                  }
                }
              },
              1: {
                value: {
                  name: "Chrome PDF Viewer",
                  description: "Portable Document Format",
                  filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                  length: 1,
                  0: {
                    type: "application/pdf",
                    suffixes: "pdf",
                    description: ""
                  }
                }
              },
              2: {
                value: {
                  name: "Native Client",
                  description: "",
                  filename: "internal-nacl-plugin",
                  length: 2,
                  0: {
                    type: "application/x-nacl",
                    suffixes: "",
                    description: "Native Client Executable"
                  },
                  1: {
                    type: "application/x-pnacl",
                    suffixes: "",
                    description: "Portable Native Client Executable"
                  }
                }
              }
            });
          }
        });
        
        // Fix permissions
        const originalQuery = window.navigator.permissions?.query;
        if (originalQuery) {
          window.navigator.permissions.query = (parameters) =>
            parameters.name === "notifications"
              ? Promise.resolve({ state: Notification.permission })
              : originalQuery(parameters);
        }
        
        // Add WebGL vendor and renderer
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
          if (parameter === 37445) {
            return 'Intel Inc.';
          }
          if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
          }
          return getParameter.apply(this, arguments);
        };
        
        // Fix hardwareConcurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
          get: () => 8
        });
        
        // Fix screen resolution
        Object.defineProperty(screen, 'width', { get: () => 1920 });
        Object.defineProperty(screen, 'height', { get: () => 1080 });
        Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
        Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
      });

      // Set up network and console monitoring
      const network_requests = [];
      const console_logs = [];
      
      page.on("request", (req) =>
        network_requests.push({
          url: req.url(),
          method: req.method(),
          type: req.resourceType(),
        })
      );
      
      page.on("console", (msg) =>
        console_logs.push({
          type: msg.type(),
          text: msg.text(),
        })
      );

      console.log(`🌐 Navigating to ${url} (Attempt ${attempt + 1}/${maxRetries})`);
      
      // Navigate with human-like timing
      await page.goto(url, { 
        waitUntil: "domcontentloaded", 
        timeout: 30000 
      });
      
      // Initial wait
      await page.waitForTimeout(3000 + Math.random() * 2000);

      // First verify if the page loaded correctly
      const pageLoadedCorrectly = await verifyPageLoaded(page);

      if (!pageLoadedCorrectly) {
        // Only check for challenges if expected content is missing
        const challengeDetected = await detectCloudflareChallenge(page);
        
        if (challengeDetected) {
          console.log("⚠️ Cloudflare challenge detected");
          
          const challengeHandled = await handleCloudflareChallenge(page);
          
          if (!challengeHandled) {
            throw new Error("Failed to bypass Cloudflare challenge");
          }
          
          // Wait for page to stabilize after challenge
          await page.waitForTimeout(3000 + Math.random() * 2000);
          
          // Verify the page loaded after challenge
          const pageLoadedAfterChallenge = await verifyPageLoaded(page);
          if (!pageLoadedAfterChallenge) {
            throw new Error("Page did not load correctly after challenge");
          }
        } else {
          console.log("⚠️ Page didn't load expected content, but no challenge detected");
          // Might be a different issue - 404, different page structure, etc.
        }
      } else {
        console.log("✅ Page loaded successfully without challenges");
      
        // Wait for page to stabilize after challenge
        await page.waitForTimeout(3000 + Math.random() * 2000);
      }

      // Extract property cards (your original logic)
      const property_cards = await page.evaluate((ptype) => {
        const container = document.querySelector("div.postingsList-module__postings-container");
        if (!container) return [];

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

        return Array.from(container.children).map((card) => {
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
          };
        });
      }, propertyType);

      // Page metrics
      const metrics = await page.evaluate(() => ({
        totalElements: document.getElementsByTagName("*").length,
        totalImages: document.images.length,
        totalLinks: document.links.length,
        totalScripts: document.scripts.length,
        bodyText: document.body.innerText.substring(0, 1000),
      }));

      const content = await page.content();
      
      // Save successful session cookies
      const cookies = await context.cookies();
      if (!fs.existsSync(sessionDir)) {
        fs.mkdirSync(sessionDir, { recursive: true });
      }
      fs.writeFileSync(cookiesPath, JSON.stringify(cookies, null, 2));
      
      console.log("✅ Successfully scraped page and saved session");

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
        success: true
      };
      
    } catch (error) {
      console.error(`❌ Attempt ${attempt + 1} failed:`, error.message);
      attempt++;
      
      if (attempt >= maxRetries) {
        throw error;
      }
      
      // Wait before retry with exponential backoff
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
    } finally {
      if (browser && attempt >= maxRetries - 1) {
        await browser.close();
      }
    }
  }
}

// ---------- Helper Functions ----------

// ---------- Improved Cloudflare Challenge Detection ----------
async function detectCloudflareChallenge(page) {
  try {
    // First, check if we're on the actual site by looking for expected content
    const isLikelyRealSite = await page.evaluate(() => {
      // Check for signs this is the actual website content
      // Adjust these selectors based on what you expect on the real site
      const hasPropertyCards = !!document.querySelector("div.postingsList-module__postings-container");
      const hasNavigation = !!document.querySelector("nav, header");
      const hasSubstantialContent = document.body?.innerText?.length > 500;
      
      return hasPropertyCards || (hasNavigation && hasSubstantialContent);
    });
    
    // If we found real site content, it's definitely not a challenge
    if (isLikelyRealSite) {
      console.log("✅ Real site content detected, no challenge present");
      return false;
    }
    
    // Now check for challenge indicators with stricter criteria
    const indicators = await page.evaluate(() => {
      const title = document.title.toLowerCase();
      const bodyText = document.body?.innerText?.toLowerCase() || '';
      
      // More specific challenge detection
      const challengeIndicators = {
        // Title must contain very specific challenge phrases
        hasChallengeTitle: (
          title.includes('just a moment') || 
          title.includes('checking your browser') ||
          title.includes('attention required') ||
          title === 'please wait...' ||
          title.includes('ddos protection')
        ),
        
        // Body must contain multiple challenge-related phrases
        hasChallengeText: (
          (bodyText.includes('checking your browser') || 
           bodyText.includes('verify you are human') ||
           bodyText.includes('please complete the security check')) &&
          bodyText.length < 2000 // Challenge pages typically have little text
        ),
        
        // Look for actual CAPTCHA elements (not just any iframe)
        hasCaptcha: !!(
          document.querySelector('iframe[src*="challenges.cloudflare.com"]') ||
          document.querySelector('iframe[src*="hcaptcha.com/captcha"]') ||
          document.querySelector('iframe[src*="recaptcha/api2"]') ||
          document.querySelector('div.cf-turnstile') ||
          document.querySelector('div#cf-captcha-container')
        ),
        
        // Check for Cloudflare challenge-specific elements
        hasCloudflareChallenge: !!(
          document.querySelector('form#challenge-form') ||
          document.querySelector('div.cf-browser-verification') ||
          document.querySelector('div.cf-im-under-attack') ||
          (document.querySelector('script')?.innerHTML?.includes('_cf_chl_opt') ?? false)
        ),
        
        // Check meta tags specific to Cloudflare challenges
        hasChallengeMetaTags: !!(
          document.querySelector('meta[name="cf-2fa-verify"]') ||
          document.querySelector('meta[data-cf-settings]')
        )
      };
      
      return {
        ...challengeIndicators,
        // Count how many indicators are true
        indicatorCount: Object.values(challengeIndicators).filter(v => v).length
      };
    });
    
    // Require at least 2 indicators to consider it a challenge
    // This prevents false positives from single matching conditions
    const isChallenge = indicators.indicatorCount >= 2;
    
    if (isChallenge) {
      console.log(`⚠️ Challenge detected (${indicators.indicatorCount} indicators found):`, 
        Object.entries(indicators)
          .filter(([k, v]) => v === true)
          .map(([k]) => k)
          .join(', ')
      );
    }
    
    return isChallenge;
    
  } catch (error) {
    console.error("Error detecting Cloudflare challenge:", error);
    // On error, assume no challenge to avoid blocking legitimate pages
    return false;
  }
}

// ---------- Enhanced Challenge Handler with Better Logging ----------
async function handleCloudflareChallenge(page) {
  try {
    console.log("🔧 Attempting to handle Cloudflare challenge...");
    
    // Take a screenshot for debugging
    if (process.env.DEBUG) {
      await page.screenshot({ 
        path: `challenge-${Date.now()}.png`,
        fullPage: true 
      });
      console.log("📸 Saved screenshot of challenge page");
    }
    
    // Check what type of challenge we're dealing with
    const challengeType = await page.evaluate(() => {
      if (document.querySelector('div.cf-turnstile')) return 'turnstile';
      if (document.querySelector('iframe[src*="hcaptcha"]')) return 'hcaptcha';
      if (document.querySelector('iframe[src*="recaptcha"]')) return 'recaptcha';
      if (document.querySelector('form#challenge-form')) return 'javascript';
      if (document.querySelector('input[type="button"][value*="Verify"]')) return 'button';
      return 'unknown';
    });
    
    console.log(`🎯 Challenge type detected: ${challengeType}`);
    
    switch (challengeType) {
      case 'button':
        // Simple button click challenge
        const verifyButton = await page.$('input[type="button"][value*="Verify"]') ||
                           await page.$('button:has-text("Verify")');
        if (verifyButton) {
          console.log("📍 Clicking verify button...");
          await verifyButton.click();
          await page.waitForTimeout(5000);
          return true;
        }
        break;
        
      case 'turnstile':
        // Cloudflare Turnstile (usually auto-solves)
        console.log("⏳ Waiting for Turnstile to auto-solve...");
        await page.waitForTimeout(8000);
        
        // Check if there's a submit button after Turnstile
        const submitButton = await page.$('button[type="submit"]');
        if (submitButton) {
          await submitButton.click();
        }
        return true;
        
      case 'javascript':
        // JavaScript challenge (usually auto-solves)
        console.log("⏳ Waiting for JavaScript challenge to complete...");
        
        // Wait for either navigation or challenge to disappear
        await Promise.race([
          page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
          page.waitForFunction(
            () => !document.querySelector('form#challenge-form'),
            { timeout: 15000 }
          ).catch(() => {})
        ]);
        
        return true;
        
      case 'hcaptcha':
      case 'recaptcha':
        console.log(`⚠️ ${challengeType} detected - manual solving or 2Captcha integration required`);
        
        // If you have a solver configured
        if (page.solveRecaptchas) {
          await page.solveRecaptchas();
          await page.waitForTimeout(3000);
          return true;
        }
        
        // Otherwise, wait and hope it's optional or has an alternative
        console.log("⏳ Waiting to see if CAPTCHA is optional...");
        await page.waitForTimeout(5000);
        
        // Check if we can proceed without solving
        const canProceed = await page.evaluate(() => {
          return !document.querySelector('iframe[src*="captcha"]');
        });
        
        return canProceed;
        
      default:
        console.log("⏳ Unknown challenge type, waiting for auto-resolution...");
        await page.waitForTimeout(10000);
    }
    
    // Final check - are we still on a challenge page?
    const stillChallenged = await detectCloudflareChallenge(page);
    
    if (!stillChallenged) {
      console.log("✅ Challenge appears to be resolved");
      return true;
    } else {
      console.log("❌ Challenge still present after handling attempt");
      return false;
    }
    
  } catch (error) {
    console.error("Error handling Cloudflare challenge:", error);
    return false;
  }
}

// ---------- Optional: Add a verification function ----------
async function verifyPageLoaded(page, expectedSelectors = []) {
  try {
    // Default selectors for the real estate site
    const selectors = expectedSelectors.length > 0 ? expectedSelectors : [
      'div.postingsList-module__postings-container',
      '[data-qa="POSTING_CARD_PRICE"]',
      'h2.postingLocations-module__location-text'
    ];
    
    // Check if at least one expected element exists
    for (const selector of selectors) {
      const element = await page.$(selector);
      if (element) {
        console.log(`✅ Found expected element: ${selector}`);
        return true;
      }
    }
    
    console.log("⚠️ No expected elements found on page");
    return false;
    
  } catch (error) {
    console.error("Error verifying page:", error);
    return false;
  }
}


// Generate random user agents
function getRandomUserAgent() {
  const userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
  ];
  
  return userAgents[Math.floor(Math.random() * userAgents.length)];
}

// ---------- Pagination Handler ----------
async function scrapeMultiplePages(baseUrl, maxPages = 5, options = {}) {
  const allResults = [];
  const proxies = options.proxies || [null]; // Array of proxies to rotate
  let currentProxyIndex = 0;
  
  for (let page = 1; page <= maxPages; page++) {
    console.log(`\n📄 Scraping page ${page} of ${maxPages}`);
    
    // Construct page URL (adjust based on site's pagination format)
    const pageUrl = page === 1 ? baseUrl : `${baseUrl}?page=${page}`;
    
    // Rotate proxy for each page
    const currentProxy = proxies[currentProxyIndex % proxies.length];
    currentProxyIndex++;
    
    try {
      // Add human-like delay between pages
      if (page > 1) {
        const delay = 3000 + Math.random() * 5000;
        console.log(`⏱️ Waiting ${Math.round(delay/1000)}s before next page...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
      
      const result = await captureWithPlaywright(pageUrl, {
        ...options,
        proxy: currentProxy
      });
      
      if (result.success && result.property_cards.length > 0) {
        allResults.push({
          page,
          url: pageUrl,
          cards: result.property_cards,
          timestamp: new Date().toISOString()
        });
        
        console.log(`✅ Page ${page}: Found ${result.property_cards.length} properties`);
      } else {
        console.log(`⚠️ Page ${page}: No properties found or scraping failed`);
        
        // If we hit a challenge/block, switch proxy
        if (currentProxyIndex < proxies.length) {
          console.log("🔄 Switching to next proxy...");
          currentProxyIndex++;
        }
      }
      
    } catch (error) {
      console.error(`❌ Failed to scrape page ${page}:`, error.message);
      
      // On error, try next proxy if available
      if (currentProxyIndex < proxies.length) {
        console.log("🔄 Switching to next proxy after error...");
        currentProxyIndex++;
      }
    }
  }
  
  return allResults;
}
module.exports = {
  captureWithPlaywright,
  scrapeMultiplePages,
  detectCloudflareChallenge,
  handleCloudflareChallenge
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
