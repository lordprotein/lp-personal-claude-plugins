/* Domoved: compact listing extract from the page (Avito, CIAN, Domclick, Yandex Realty).
   Runs as a single javascript_tool call on an already open page. Only reads the DOM.
   Returns a JSON string up to ~2 KB: it is saved to extract.json and passed to normalize_listing.py.
   Russian strings below match Russian page text: do not translate them. */
(() => {
  const clip = (s, n) => (s || "").replace(/\s+/g, " ").trim().slice(0, n);
  const num = (s) => { const d = String(s || "").replace(/[^\d]/g, ""); return d ? Number(d) : null; };
  const host = location.hostname.replace(/^www\./, "");
  const site = /avito/.test(host) ? "avito" : /cian/.test(host) ? "cian" : /domclick/.test(host) ? "domclick"
    : /realty\.yandex|realty\.ya/.test(host) ? "yandex_realty" : "other_url";
  const q = (sel) => document.querySelector(sel);
  const txt = (sel) => { const el = q(sel); return el ? el.textContent : ""; };
  const body = document.body ? document.body.innerText : "";
  const out = { url: location.href.split("?")[0], site, title: clip(txt("h1") || document.title, 120) };

  // JSON-LD: price, address, coordinates, description
  let ld = {};
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
    try {
      const j = JSON.parse(s.textContent);
      (Array.isArray(j) ? j : [j]).forEach((o) => {
        if (!o || typeof o !== "object") return;
        if (o.offers && o.offers.price && !ld.price) ld.price = o.offers.price;
        if (o.geo && o.geo.latitude && !ld.lat) { ld.lat = o.geo.latitude; ld.lon = o.geo.longitude; }
        if (o.address && !ld.address) ld.address = typeof o.address === "string" ? o.address : [o.address.addressLocality, o.address.streetAddress].filter(Boolean).join(", ");
        if (o.description && !ld.description) ld.description = o.description;
      });
    } catch (e) { /* skip unrelated JSON-LD */ }
  });

  // Price
  const priceEl = q('[itemprop="price"]') || q('[data-marker="item-view/item-price"]') || q('[data-testid="price-amount"]')
    || q('[data-e2e-id="price"]') || q('[class*="price-value"]');
  out.price = num(priceEl && (priceEl.getAttribute("content") || priceEl.textContent)) || num(ld.price);
  if (!out.price) { const m = body.match(/(\d{1,3}(?:[  ]\d{3}){2,3})\s*₽/); if (m) out.price = num(m[1]); }
  const ppm = body.match(/(\d{2,3}(?:\s\d{3}))\s*₽\s*за\s*м²/);
  out.price_per_m2 = ppm ? num(ppm[1]) : null;

  // "key: value" parameters
  const params = {};
  const addPair = (k, v) => { k = clip(k, 40).replace(/:$/, ""); v = clip(v, 60); if (k && v && k !== v && Object.keys(params).length < 30) params[k] = v; };
  document.querySelectorAll('[data-marker="item-view/item-params"] li, [data-marker*="item-params"] li').forEach((li) => {
    const t = li.innerText || ""; const i = t.indexOf(":"); if (i > 0) addPair(t.slice(0, i), t.slice(i + 1));
  });
  // CIAN, Domclick, Yandex: label/value pairs
  document.querySelectorAll('[data-name="OfferSummaryInfoItem"], [data-name="ObjectFactoidsItem"], [data-testid*="object-info"] li, [class*="OfferCardDetail"] li').forEach((el) => {
    const parts = (el.innerText || "").split("\n").map((s) => s.trim()).filter(Boolean);
    if (parts.length >= 2) addPair(parts[0], parts.slice(1).join(" "));
  });
  if (Object.keys(params).length < 4) {
    // fallback: "Key: value" lines from the page text
    const keys = ["Количество комнат", "Общая площадь", "Площадь кухни", "Жилая площадь", "Этаж", "Этажей в доме", "Высота потолков",
      "Санузел", "Ремонт", "Тип дома", "Год постройки", "Балкон или лоджия", "Парковка", "Тип комнат", "Способ продажи", "Площадь участка"];
    keys.forEach((k) => { const m = body.match(new RegExp(k + "[:\\s]+([^\\n]{1,50})")); if (m) addPair(k, m[1]); });
  }
  out.params = params;

  // Address and coordinates
  const addrEl = q('[itemprop="address"]') || q('[data-marker="item-view/item-address"]') || q('[data-name="AddressContainer"]') || q('[data-testid="address"]');
  out.address = clip((addrEl && addrEl.textContent) || ld.address, 160) || null;
  if (!out.address) { const m = body.match(/Расположение\s*\n([^\n]{8,160})/); if (m) out.address = clip(m[1], 160); }
  const mapEl = q("[data-map-lat]");
  out.lat = mapEl ? Number(mapEl.getAttribute("data-map-lat")) : (ld.lat ? Number(ld.lat) : null);
  out.lon = mapEl ? Number(mapEl.getAttribute("data-map-lon")) : (ld.lon ? Number(ld.lon) : null);
  if (!out.lat) {
    const html = document.documentElement.innerHTML;
    const m = html.match(/"coordinates"\s*:\s*\{\s*"lat"\s*:\s*([\d.]+)\s*,\s*"lng"\s*:\s*([\d.]+)/) || html.match(/"lat(?:itude)?"\s*:\s*(5\d\.\d+|[4-7]\d\.\d+)\s*,\s*"lo?ng?(?:itude)?"\s*:\s*(\d{2,3}\.\d+)/);
    if (m) { out.lat = Number(m[1]); out.lon = Number(m[2]); }
  }

  // Publication date, views, price history
  const meta = body.match(/№\s*\d+\s*·\s*([^·\n]+)·\s*(\d[\d ]*)\s*просмотр/);
  out.published = meta ? clip(meta[1], 40) : null;
  out.views = meta ? num(meta[2]) : null;
  const hist = document.documentElement.innerHTML.match(/priceHistory[^{]{0,20}\{[^}]*recordsCount\\?"?:\s*(\d+)/);
  out.price_history_count = hist ? Number(hist[1]) : null;

  // Description, Rosreestr (Росреестр) check, house rating
  const descEl = q('[data-marker="item-view/item-description"]') || q('[itemprop="description"]') || q('[data-name="Description"]') || q('[data-testid="description"]');
  out.description = clip((descEl && descEl.innerText) || ld.description, 1500) || null;
  const rr = body.match(/Проверка\s+в\s+Росреестре([\s\S]{0,400}?)(?:Расположение|Описание|$)/);
  out.rosreestr = rr ? clip(rr[1], 300) : null;
  const rating = body.match(/О доме\s*\n?\s*(\d[,.]\d)\s*·\s*(\d+)\s*отзыв/);
  out.house_rating = rating ? rating[1] + " (" + rating[2] + " отзывов)" : null;

  let s = JSON.stringify(out);
  if (s.length > 2400) { out.description = clip(out.description, 700); s = JSON.stringify(out); }
  return s;
})()
