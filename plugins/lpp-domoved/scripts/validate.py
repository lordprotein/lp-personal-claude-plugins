#!/usr/bin/env python3
"""Check analysis.json without reading it whole into the chat: prints only the problems.

Levels: ERROR (exit 1) and WARN. If there are no problems: OK and a short summary.
Usage:
  validate.py analysis.json              full check
  validate.py --style-only <file.json>   only links and text readability (for agent fragments)
"""
import json
import re
import sys

CRITERIA = ["noise", "building", "legal", "transport", "ecology", "green", "kids",
            "amenities", "safety", "value_liquidity", "future"]


def _is_http(u):
    return isinstance(u, str) and (u.startswith("http://") or u.startswith("https://"))


SCRIPT_SOURCES = ("osm_nearby", "openstreetmap", "osm", "geo.json", "market_rates", "moex", "listing")


def _is_script_source(e):
    """Data from the plugin scripts (OSM, MOEX, listing): no link, but the source is known."""
    title = str(e.get("source_title") or "").lower()
    return any(s in title for s in SCRIPT_SOURCES)


def _urls(obj):
    """All strings under *url* keys in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and "url" in k.lower():
                yield k, v
            else:
                for x in _urls(v):
                    yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in _urls(v):
                yield x


# criteria whose pros and cons must be backed by links
LINKED_CRITERIA = ("noise", "building", "legal", "value_liquidity")
JARGON = re.compile(r"\b(net|gross|mortgage_eligible|priced_in|suggested_scores|geo_brief|noise_external|"
                    r"rail_station|stop_bus_tram|university|playground|major_road|minor_road|railway_line|"
                    r"powerline|kindergarten|nightlife|landfill|est_db\w*)\b", re.I)
# 10.57 млн, 199,342 ₽ (comma as thousands separator), 1,234,567
BAD_NUM = re.compile(r"\d+\.\d+\s*(млн|млрд|тыс|%|₽|м²|км)|\b\d{1,3},\d{3}(?!\d)\s*(₽|руб|м²)|\d{1,3},\d{3},\d{3}")


def _point_text(p):
    if isinstance(p, dict):
        return p.get("text") or ""
    return p if isinstance(p, str) else ""


def _point_url(p):
    return isinstance(p, dict) and _is_http(p.get("url"))


def _texts(a):
    """Texts the buyer reads: (location, text)."""
    for cid, c in (a.get("criteria") or {}).items():
        if not isinstance(c, dict):
            continue
        if isinstance(c.get("summary"), str):
            yield cid + ".summary", c["summary"]
        for k in ("pros", "cons", "check_in_person"):
            for i, p in enumerate(c.get(k) or []):
                yield "%s.%s[%d]" % (cid, k, i), _point_text(p)
    for blk, keys in (("valuation", ("comment", "comment_points")), ("investment", ("comment", "comment_points", "buy_vs_rent")),
                      ("reviews", ("house_summary", "district_summary", "house_points", "district_points"))):
        b = a.get(blk) or {}
        for k in keys:
            v = b.get(k)
            for i, t in enumerate(v if isinstance(v, list) else [v]):
                if isinstance(t, str):
                    yield "%s.%s" % (blk, k) + ("[%d]" % i if isinstance(v, list) else ""), t
    for i, f in enumerate(a.get("red_flags") or []):
        if isinstance(f, dict):
            yield "red_flags[%d]" % i, "%s %s" % (f.get("title") or "", f.get("detail") or "")


def check_style(a):
    """Warnings about links and text readability."""
    warns = []
    crit = a.get("criteria") or {}
    for cid, c in crit.items():
        if not isinstance(c, dict) or c.get("score") is None:
            continue
        links = sum(1 for e in (c.get("evidence") or []) if isinstance(e, dict) and _is_http(e.get("source_url")))
        links += sum(1 for k in ("pros", "cons") for p in (c.get(k) or []) if _point_url(p))
        if c.get("confidence") in ("medium", "high") and links == 0:
            warns.append("%s: confidence %s, but there is not a single link" % (cid, c.get("confidence")))
        if cid in LINKED_CRITERIA:
            pts = [p for k in ("pros", "cons") for p in (c.get(k) or [])]
            if pts:
                no_url = sum(1 for p in pts if not _point_url(p))
                if no_url * 2 > len(pts):
                    warns.append("%s: %d of %d pros and cons have no link" % (cid, no_url, len(pts)))
    seen = set()
    for where, text in _texts(a):
        if not text:
            continue
        m = JARGON.search(text)
        if m and (where, "j") not in seen:
            seen.add((where, "j"))
            warns.append("%s: internal term «%s» in buyer-facing text" % (where, m.group(0)))
        n = BAD_NUM.search(text)
        if n and (where, "n") not in seen:
            seen.add((where, "n"))
            warns.append("%s: number not in Russian format «%s» (expected like 10,57 млн; 199 342 ₽)" % (where, n.group(0)))
    return warns


def check(a):
    errors, warns = [], []
    crit = a.get("criteria") or {}
    with_data = 0
    for cid in CRITERIA:
        c = crit.get(cid)
        if c is None:
            errors.append("criterion %s is missing" % cid)
            continue
        score = c.get("score")
        conf = c.get("confidence")
        if score is None:
            if conf not in (None, "none"):
                warns.append("%s: score is empty, but confidence=%s" % (cid, conf))
            continue
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 10:
            errors.append("%s: score outside 0..10 (%r)" % (cid, score))
            continue
        with_data += 1
        ev = c.get("evidence") or []
        has_src = any(_is_http(e.get("source_url")) or _is_script_source(e) for e in ev if isinstance(e, dict))
        if not ev:
            warns.append("%s: score without evidence" % cid)
        elif not has_src:
            warns.append("%s: evidence has neither a link nor a script source" % cid)
        if conf == "high" and not has_src:
            errors.append("%s: confidence high without source_url" % cid)
    for key, url in _urls(a):
        if url and not _is_http(url):
            errors.append("link is not http(s) in %s: %s" % (key, url[:80]))
    cl = a.get("checklists") or {}
    if not any(cl.get(k) for k in ("documents", "questions_to_seller", "viewing")):
        errors.append("checklists are missing (documents, questions_to_seller, viewing)")
    obj = a.get("object") or {}
    for k in ("price", "area_total"):
        v = obj.get(k)
        if isinstance(v, (int, float)) and v <= 0:
            errors.append("object.%s is not positive: %s" % (k, v))
    val = a.get("valuation") or {}
    if isinstance(val.get("asking_price"), (int, float)) and val["asking_price"] <= 0:
        errors.append("valuation.asking_price is not positive")
    flags = {f.get("id") for f in (a.get("red_flags") or []) if isinstance(f, dict)}
    if val.get("mortgage_eligible") is True and "not_mortgage_eligible" in flags:
        errors.append("contradiction: mortgage_eligible=true with flag not_mortgage_eligible")
    if (obj.get("type") is None):
        warns.append("object.type is not set")
    warns.extend(check_style(a))
    summary = "sources: %d, criteria with data: %d of %d" % (len(a.get("sources") or []), with_data, len(CRITERIA))
    return errors, warns, summary


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    style_only = "--style-only" in argv
    argv = [x for x in argv if x != "--style-only"]
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    try:
        with open(argv[0], encoding="utf-8") as f:
            a = json.load(f)
    except (OSError, ValueError) as e:
        print("ERROR: cannot read %s: %s" % (argv[0], e))
        return 1
    if style_only:
        warns = check_style(a)
        for w in warns:
            print("WARN: " + w)
        print("OK: style and links are fine" if not warns else "Fix the warnings above")
        return 0
    errors, warns, summary = check(a)
    for e in errors:
        print("ERROR: " + e)
    for w in warns:
        print("WARN: " + w)
    if not errors and not warns:
        print("OK: " + summary)
    else:
        print(("OK with warnings: " if not errors else "Errors found: ") + summary)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
