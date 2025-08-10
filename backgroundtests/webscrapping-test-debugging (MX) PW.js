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

// ---------- core capture (with light stealth) ----------
async function captureWithPlaywright(url, { propertyType = null, headless = false } = {}) {
  const browser = await chromium.launch({
    headless,
    args: [
      "--disable-blink-features=AutomationControlled",
      "--disable-web-security",
      "--disable-extensions",
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--disable-background-timer-throttling",
      "--disable-renderer-backgrounding",
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    locale: "en-US",
    timezoneId: "America/New_York",
    extraHTTPHeaders: {
      "Accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
      "DNT": "1",
      "Upgrade-Insecure-Requests": "1",
      "Cache-Control": "max-age=0",
    },
  });

  const page = await context.newPage();

  // Remove webdriver/automation fingerprints
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    // languages
    Object.defineProperty(navigator, "languages", { get: () => ["en-US", "en"] });
    // chrome object
    Object.defineProperty(window, "chrome", { get: () => ({ runtime: {} }) });
    // plugins
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
      ],
    });
    // permissions
    const originalQuery = window.navigator.permissions?.query;
    if (originalQuery) {
      window.navigator.permissions.query = (parameters) =>
        parameters.name === "notifications"
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters);
    }
  });

  // network + console capture (kept, but not written to disk)
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

  try {
    console.log(`🌐 Navigating to ${url}`);
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(3000);

    // Extract property cards
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
        let precio = null,
          moneda = null;
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
        let direccion = null,
          codigo_postal = null;
        if (addrEl) {
          const t = addrEl.innerText.trim();
          direccion = t;
          const cp = t.match(/\b\d{5}\b/);
          if (cp) codigo_postal = cp[0];
        }

        let tamano_lote = null,
          recamaras = null,
          banos = null,
          estacionamientos = null;
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

    // page metrics (simple)
    const metrics = await page.evaluate(() => ({
      totalElements: document.getElementsByTagName("*").length,
      totalImages: document.images.length,
      totalLinks: document.links.length,
      totalScripts: document.scripts.length,
      bodyText: document.body.innerText.substring(0, 1000),
    }));

    const content = await page.content();

    // screenshot if you want it
    // const screenshot = await page.screenshot({ fullPage: true });

    return {
      title: await page.title(),
      url: page.url(),
      content,
      screenshots: {}, // { full: screenshot }  // disabled to keep files small
      prices: {},
      network_requests,
      console_logs,
      property_cards,
      metrics,
    };
  } finally {
    await browser.close();
  }
}

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
