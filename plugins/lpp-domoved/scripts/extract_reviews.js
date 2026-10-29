/* Domoved: reviews of the house or residential complex (ЖК) from a reviews page (Avito /catalog/houses/.../reviews, CIAN, Domclick).
   Runs as a single javascript_tool call on an already open page. Only reads the DOM.
   Returns a JSON string up to ~4 KB: {url, site, rating, count, reviews:[{date, rating, text, pros, cons}], blocked}.
   blocked = true if a verification or access restriction page is open: do not pass it and do not bypass it.
   Site selectors have some slack; on live Avito markup only the text fallback has been verified.
   Russian strings and regexes below match Russian page text: do not translate them. */
(() => {
  const clip = (s, n) => (s || "").replace(/\s+/g, " ").trim().slice(0, n);
  const host = location.hostname.replace(/^www\./, "");
  const site = /avito/.test(host) ? "avito" : /cian/.test(host) ? "cian" : /domclick/.test(host) ? "domclick" : "other";
  const body = document.body ? document.body.innerText : "";
  const out = { url: location.href.split("#")[0], site, rating: null, count: null, reviews: [], blocked: false };

  // Verification or access restriction page
  const blockRe = /Доступ ограничен|Пройти проверку|проблема с IP|Подтвердите, что вы не робот|captcha|showcaptcha|Я не робот/i;
  if (blockRe.test(document.title) || blockRe.test(body.slice(0, 3000)) ||
      document.querySelector('iframe[src*="captcha"], [class*="captcha" i], form[action*="captcha"]')) {
    out.blocked = true;
    return JSON.stringify(out);
  }

  const num = (s) => { const m = String(s || "").replace(",", ".").match(/\d+(?:\.\d+)?/); return m ? Number(m[0]) : null; };

  // Overall rating and review count: «4,6 · 23 отзыва», «4.6 из 5», «23 отзыва»
  const head = body.slice(0, 4000);
  const r1 = head.match(/(\d[,.]\d)\s*(?:·|из 5|\n)\s*(\d+)\s*отзыв/);
  if (r1) { out.rating = num(r1[1]); out.count = Number(r1[2]); }
  if (out.count == null) { const c = head.match(/(\d+)\s*отзыв/); if (c) out.count = Number(c[1]); }
  if (out.rating == null) {
    const ld = document.querySelector('script[type="application/ld+json"]');
    try { const j = ld && JSON.parse(ld.textContent); const ag = j && (j.aggregateRating || (j[0] && j[0].aggregateRating));
      if (ag) { out.rating = num(ag.ratingValue); out.count = out.count || num(ag.reviewCount || ag.ratingCount); } } catch (e) { /* skip */ }
  }

  // Avito: house reviews page (data-marker labels verified on a live page 29.10.2026)
  const avito = document.querySelectorAll('[data-marker="model-review"]');
  if (avito.length) {
    const mt = (root, m) => { const e = root.querySelector('[data-marker="' + m + '"]'); return e ? (e.innerText || "").trim() : ""; };
    out.rating = num(mt(document, "rating-summary/rating")) || out.rating;
    const cnt = body.match(/на основе\s+(\d+)\s+отзыв\S*\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/);
    if (cnt) { out.count = Number(cnt[1]); out.distribution = { "5": +cnt[2], "4": +cnt[3], "3": +cnt[4], "2": +cnt[5], "1": +cnt[6] }; }
    const sum = mt(document, "rating-summary/reviews-summary").replace(/Главное из отзывов|и другие мнения/g, "");
    if (sum.trim()) out.summary = clip(sum, 400);
    avito.forEach((r) => {
      if (out.reviews.length >= 15) return;
      const rv = { date: clip(mt(r, "model-review/header/subtitle"), 30) || null, status: null, text: "", pros: null, cons: null };
      const lines = (r.innerText || "").split("\n").map((s) => s.trim()).filter(Boolean);
      const st = lines.find((l) => /в этом доме|живу|снимаю|куплен|собственник|арендую/i.test(l));
      let title = null; const free = [];
      if (st) {
        rv.status = clip(st, 60);
        const nx = lines[lines.indexOf(st) + 1];  // the main text follows the status right away, without a label
        if (nx && !/^(Преимущества|Достоинства|Недостатки|Минусы|Комментарий)$/i.test(nx)) free.push(nx);
      }
      r.querySelectorAll('[data-marker^="model-review/text-section/"]').forEach((e) => {
        const m = e.getAttribute("data-marker"); const t = (e.innerText || "").trim();
        if (m.endsWith("/title")) { title = t; return; }
        if (/Преимущества|Достоинства|Плюсы/i.test(title || "")) rv.pros = clip(t, 160);
        else if (/Недостатки|Минусы/i.test(title || "")) rv.cons = clip(t, 160);
        else free.push(t);
        title = null;
      });
      rv.text = clip(free.join(" "), 280);
      if (rv.text || rv.pros || rv.cons) out.reviews.push(rv);
    });
    const pageBtns = Array.from(document.querySelectorAll("button")).filter((b) => /^\d+$/.test((b.innerText || "").trim()));
    out.pages = pageBtns.length ? Math.max.apply(null, pageBtns.map((b) => +b.innerText.trim())) : 1;
    // next pages open at <reviews page>?reviewsPage=N (the buttons navigate there themselves)
    out.next_page_url = out.pages > 1 ? location.href.split("?")[0] + "?reviewsPage=" : null;
    return JSON.stringify(out);
  }

  const dateRe =/(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(?:\s+\d{4})?|\d{2}\.\d{2}\.\d{4}|(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\s+\d{4})/i;
  const split = (t) => {
    // «Достоинства: … Недостатки: … Комментарий: …» (pros, cons, comment)
    const g = (re) => { const m = t.match(re); return m ? clip(m[1], 120) : ""; };
    return {
      pros: g(/(?:Достоинства|Плюсы)[:\s]+([\s\S]*?)(?:Недостатки|Минусы|Комментарий|$)/i),
      cons: g(/(?:Недостатки|Минусы)[:\s]+([\s\S]*?)(?:Комментарий|Достоинства|Плюсы|$)/i),
    };
  };
  const push = (el) => {
    if (out.reviews.length >= 15) return;
    const t = (el.innerText || "").trim();
    if (t.length < 25) return;
    const d = t.match(dateRe);
    const stars = el.querySelectorAll('[data-marker*="star"][class*="filled" i], [class*="star" i][class*="active" i], [class*="star" i][class*="full" i]').length;
    const rr = t.match(/(?:^|\s)([1-5])(?:[,.]0)?\s*(?:из 5|★)/);
    const pc = split(t);
    out.reviews.push({
      date: d ? clip(d[1], 30) : null,
      rating: stars ? Math.min(stars, 5) : (rr ? Number(rr[1]) : null),
      text: clip(t.replace(dateRe, ""), 280),
      pros: pc.pros || null,
      cons: pc.cons || null,
    });
  };

  // 1) Site markup (with slack for class name changes)
  const selectors = [
    '[data-marker*="review"]:not([data-marker*="reviews-"])',
    '[data-marker="review"]',
    '[data-name*="Review"]',
    '[data-testid*="review" i]',
    '[itemprop="review"]',
    'article[class*="review" i]',
    'div[class*="review-item" i], div[class*="ReviewItem"], div[class*="review-card" i]',
  ];
  const seen = new Set();
  for (const sel of selectors) {
    let nodes = [];
    try { nodes = Array.from(document.querySelectorAll(sel)); } catch (e) { continue; }
    // take outer elements, excluding ones nested in each other
    nodes = nodes.filter((n) => !nodes.some((o) => o !== n && o.contains(n)));
    for (const n of nodes) {
      const key = (n.innerText || "").slice(0, 80);
      if (seen.has(key)) continue;
      seen.add(key);
      push(n);
    }
    if (out.reviews.length >= 3) break;
  }

  // 2) Text fallback: chunks of text starting with a date
  if (out.reviews.length < 2) {
    out.reviews = [];
    const parts = body.split(/\n(?=[^\n]{0,40}(?:\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)|\d{2}\.\d{2}\.\d{4}))/i);
    for (const p of parts.slice(1)) {
      if (out.reviews.length >= 15) break;
      const t = p.trim();
      if (t.length < 40 || !/[а-яё]{4,}/i.test(t)) continue;
      const d = t.match(dateRe);
      const rr = t.match(/(?:^|\s)([1-5])(?:[,.]0)?\s*(?:из 5|★)/);
      const pc = split(t);
      out.reviews.push({ date: d ? clip(d[1], 30) : null, rating: rr ? Number(rr[1]) : null,
        text: clip(t.replace(dateRe, ""), 280), pros: pc.pros || null, cons: pc.cons || null });
    }
  }

  let s = JSON.stringify(out);
  while (s.length > 4000 && out.reviews.length) {
    const last = out.reviews[out.reviews.length - 1];
    if (last.text.length > 140) { out.reviews.forEach((r) => { r.text = clip(r.text, 140); r.pros = r.pros && clip(r.pros, 60); r.cons = r.cons && clip(r.cons, 60); }); }
    else out.reviews.pop();
    s = JSON.stringify(out);
  }
  return s;
})()
