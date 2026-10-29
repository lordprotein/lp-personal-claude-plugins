/* Domoved: finds a link to reviews of the house or residential complex (ЖК) on a listing page.
   A single expression for javascript_tool. Only reads the DOM.
   Returns a JSON string: {href, text} (absolute href, without the service ?context=) or {href: null}.
   Russian strings below match Russian page text: do not translate them. */
(() => {
  const links = Array.from(document.querySelectorAll("a[href]"));
  const clean = (h) => { try { const u = new URL(h, location.href); u.searchParams.delete("context"); return u.toString(); } catch (e) { return null; } };
  const score = (a) => {
    const t = (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim();
    const h = a.getAttribute("href") || "";
    if (/\/reviews|otzyv|#reviews|review/i.test(h) && /отзыв/i.test(t)) return 3;
    if (/отзыв/i.test(t) && /(дом|ЖК|жк|\d[,.]\d)/i.test(t)) return 2;
    if (/\/reviews|otzyv/i.test(h)) return 2;
    if (/^О доме(\s|$)|Узнать больше о доме|О ЖК|О жилом комплексе/i.test(t)) return 1;
    return 0;
  };
  let best = null, bestScore = 0;
  for (const a of links) {
    const s = score(a);
    if (s > bestScore) { best = a; bestScore = s; }
  }
  if (!best) return JSON.stringify({ href: null });
  let href = clean(best.getAttribute("href"));
  // from the Avito "О доме" (about the house) page, reviews live at …/reviews
  if (bestScore === 1 && href && /avito\.ru\/catalog\/houses\//.test(href) && !/\/reviews/.test(href)) {
    const u = new URL(href); u.pathname = u.pathname.replace(/\/$/, "") + "/reviews"; href = u.toString();
  }
  return JSON.stringify({ href, text: (best.innerText || "").replace(/\s+/g, " ").trim().slice(0, 60) });
})()
