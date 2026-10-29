#!/usr/bin/env python3
"""Assemble a single analysis JSON from agent fragments.

Each agent writes its own fragment (listing.json, house.json, district.json,
future.json, market.json), osm_nearby.py writes geo.json. The script merges them
into analysis.json by these rules:
- dicts merge recursively, lists are concatenated without duplicates;
- each criterion has one owner; if a criterion comes from two agents,
  the score with higher confidence stays and the other goes to warnings;
- sources are deduplicated by url.

Usage:
  assemble.py --dir WORK_DIR --input "<link>" [--profile balance] [--mode full] [--out analysis.json]
"""
import argparse
import datetime
import glob
import json
import os
import sys

CONF_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}
FRAGMENT_ORDER = ["listing", "house", "district", "market", "future"]


def _key(item):
    if isinstance(item, dict):
        return item.get("url") or item.get("source_url") or item.get("id") or item.get("title") or json.dumps(item, sort_keys=True, ensure_ascii=False)
    return json.dumps(item, ensure_ascii=False)


def merge_lists(a, b):
    seen = {_key(x) for x in a}
    out = list(a)
    for item in b:
        k = _key(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def deep_merge(base, extra):
    for k, v in extra.items():
        if v is None:
            continue
        if k not in base or base[k] in (None, "", [], {}):
            base[k] = v
        elif isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        elif isinstance(base[k], list) and isinstance(v, list):
            base[k] = merge_lists(base[k], v)
        # scalars: the first non-empty value wins (fragment order is fixed)
    return base


def merge_criteria(target, incoming, origin, warnings):
    for cid, crit in (incoming or {}).items():
        if not isinstance(crit, dict):
            continue
        crit = dict(crit)
        crit.setdefault("_from", origin)
        if cid not in target:
            target[cid] = crit
            continue
        old = target[cid]
        if CONF_RANK.get(crit.get("confidence"), 0) > CONF_RANK.get(old.get("confidence"), 0):
            target[cid] = crit
            loser = old
        else:
            loser = crit
        warnings.append("Criterion %s came twice (%s and %s), kept the score with higher confidence"
                        % (cid, old.get("_from"), crit.get("_from")))
        # do not lose evidence and check items
        for field in ("evidence", "check_in_person", "pros", "cons"):
            if loser.get(field):
                target[cid][field] = merge_lists(target[cid].get(field) or [], loser[field])


# Map facts added to evidence automatically (1 to 3 per criterion)
GEO_EVIDENCE = {
    "transport": ["metro", "rail_station", "stop_bus_tram"],
    "kids": ["school", "kindergarten"],
    "green": ["park", "forest", "water"],
    "amenities": ["grocery", "clinic", "pharmacy"],
    "ecology": ["industrial", "landfill", "power_plant", "powerline", "substation"],
    "noise": ["major_road", "railway_line", "minor_road"],
}
GEO_LABELS = {
    "metro": "Метро", "rail_station": "Ж/д станция", "stop_bus_tram": "Остановка",
    "school": "Школа", "kindergarten": "Детский сад", "park": "Парк", "forest": "Лес",
    "water": "Водоём", "grocery": "Продукты", "clinic": "Поликлиника", "pharmacy": "Аптека",
    "industrial": "Промзона", "landfill": "Полигон или свалка", "power_plant": "Электростанция",
    "powerline": "ЛЭП", "substation": "Подстанция", "major_road": "Магистраль",
    "railway_line": "Железная дорога", "minor_road": "Улица",
}
# negative objects are shown only when close
GEO_MAX_DIST = {"industrial": 2000, "landfill": 5000, "power_plant": 2000, "powerline": 300,
                "substation": 150, "major_road": 500, "railway_line": 800, "minor_road": 300}
OSM_TITLE = "Карта OpenStreetMap"


def fmt_dist(m):
    if m is None:
        return ""
    if m < 1000:
        return "%d м" % int(round(m))
    return ("%.1f км" % (m / 1000.0)).replace(".", ",")


def osm_url(item):
    if item.get("url"):
        return item["url"]
    ref = item.get("osm")
    if ref and "/" in ref:
        return "https://www.openstreetmap.org/" + ref
    return None


def geo_fact(cat, item):
    label = GEO_LABELS.get(cat, cat)
    name = (item.get("name") or "").strip()
    dist = fmt_dist(item.get("distance_m"))
    if name and name.lower() != label.lower():
        text = "%s «%s», %s" % (label, name, dist)
    else:
        text = "%s, %s" % (label, dist)
    return {"text": text, "source_url": osm_url(item), "source_title": OSM_TITLE}


def add_geo_evidence(analysis, geo, limit=3):
    cats = (geo or {}).get("categories") or {}
    # links for old files without the url field
    for items in cats.values():
        for it in items or []:
            if isinstance(it, dict) and not it.get("url") and osm_url(it):
                it["url"] = osm_url(it)
    for cid, cat_list in GEO_EVIDENCE.items():
        crit = analysis["criteria"].get(cid)
        if not isinstance(crit, dict):
            continue
        ev = crit.setdefault("evidence", [])
        have = {e.get("source_url") for e in ev if isinstance(e, dict)}
        added = 0
        for cat in cat_list:
            if added >= limit:
                break
            items = cats.get(cat) or []
            if not items:
                continue
            it = items[0]
            maxd = GEO_MAX_DIST.get(cat)
            if maxd is not None and (it.get("distance_m") or 0) > maxd:
                continue
            fact = geo_fact(cat, it)
            if not fact["source_url"] or fact["source_url"] in have:
                continue
            ev.append(fact)
            have.add(fact["source_url"])
            added += 1


def yandex_maps_url(lat, lon):
    return "https://yandex.ru/maps/?pt=%s,%s&z=17&l=map" % (lon, lat)


def load_fragments(work_dir):
    frags = {}
    for path in glob.glob(os.path.join(work_dir, "*.json")):
        name = os.path.splitext(os.path.basename(path))[0]
        # only agent fragments and geodata; service files (brief, rates, OSM cache, extract) are not merged
        if name not in FRAGMENT_ORDER and name not in ("geo", "reviews_site", "local", "market_future"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                frags[name] = json.load(f)
        except (OSError, ValueError) as exc:
            print("Skipping %s: %s" % (path, exc), file=sys.stderr)
    return frags


def assemble(frags, input_text, profile="balance", mode="full", theme="light"):
    analysis = {
        "meta": {"input": input_text, "profile": profile, "mode": mode, "theme": theme,
                 "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 "data_gaps": []},
        "object": {},
        "criteria": {},
        "red_flags": [],
        "sources": [],
    }
    warnings = []
    names = [n for n in FRAGMENT_ORDER if n in frags] + sorted(n for n in frags if n not in FRAGMENT_ORDER and n not in ("geo", "reviews_site"))
    for name in names:
        frag = dict(frags[name])
        merge_criteria(analysis["criteria"], frag.pop("criteria", None), name, warnings)
        deep_merge(analysis, frag)
    if "geo" in frags:
        analysis["geo"] = frags["geo"]
        center = frags["geo"].get("center") or {}
        analysis["object"].setdefault("lat", center.get("lat"))
        analysis["object"].setdefault("lon", center.get("lon"))
    for crit in analysis["criteria"].values():
        crit.pop("_from", None)
    if "geo" in frags:
        add_geo_evidence(analysis, analysis["geo"])
    rs = frags.get("reviews_site")
    if isinstance(rs, dict) and not rs.get("blocked") and rs.get("url"):
        site = {k: rs.get(k) for k in ("url", "site", "rating", "count")}
        analysis.setdefault("reviews", {})["site"] = site
        analysis["sources"] = merge_lists(analysis["sources"], [{"title": "Отзывы о доме на сайте объявления", "url": rs["url"]}])
    lat, lon = analysis["object"].get("lat"), analysis["object"].get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        analysis["sources"] = merge_lists(analysis["sources"], [{"title": "Объект на Яндекс Картах", "url": yandex_maps_url(lat, lon)}])
    if not analysis["object"].get("type"):
        analysis["object"]["type"] = "secondary"
        analysis["meta"]["data_gaps"].append("Тип объекта не определён, принят как вторичка")
    if warnings:
        analysis["meta"]["assemble_warnings"] = warnings
    return analysis


def main(argv=None):
    p = argparse.ArgumentParser(description="Assemble analysis.json from agent fragments")
    p.add_argument("--dir", required=True, help="work folder with *.json fragments")
    p.add_argument("--input", required=True, help="original link or address")
    p.add_argument("--profile", default="balance")
    p.add_argument("--mode", default="full", choices=["full", "quick"])
    p.add_argument("--theme", default="light", choices=["light", "dark"], help="report and PDF theme")
    p.add_argument("--out", help="output path (default WORK_DIR/analysis.json)")
    args = p.parse_args(argv)
    if not os.path.isdir(args.dir):
        print("No folder %s" % args.dir, file=sys.stderr)
        return 1
    frags = load_fragments(args.dir)
    if not frags:
        print("No fragments in %s" % args.dir, file=sys.stderr)
        return 1
    analysis = assemble(frags, args.input, args.profile, args.mode, args.theme)
    out = args.out or os.path.join(args.dir, "analysis.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(json.dumps({"out": out, "fragments": sorted(frags),
                      "criteria": sorted(analysis["criteria"]),
                      "warnings": analysis["meta"].get("assemble_warnings", [])},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
