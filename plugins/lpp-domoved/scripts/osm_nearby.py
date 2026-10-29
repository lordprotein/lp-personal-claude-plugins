#!/usr/bin/env python3
"""Objects near a point from OpenStreetMap (Overpass API, no keys).

Computes distances to metro, stations, schools, kindergartens, parks, major roads, railways,
industrial zones, power lines etc., estimates external noise and gives preliminary scores.

  python3 osm_nearby.py --lat 55.6215 --lon 37.5064 [--radius 1500] [--out geo.json]
"""
import argparse
import datetime
import json
import math
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_scoring as gs  # noqa: E402
import cache  # noqa: E402
import geo_brief  # noqa: E402

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
UA = "domoved/0.1 (claude-code plugin)"
TIMEOUT = 60
MAX_PER_CAT = 10

KEEP_TAGS = ("name", "name:ru", "highway", "railway", "station", "lanes", "maxspeed", "voltage",
             "amenity", "leisure", "landuse", "natural", "shop", "power", "aeroway", "service",
             "operator", "ref", "colour", "network", "healthcare:speciality", "school", "grades",
             "opening_hours", "industrial", "man_made", "iata", "icao")

MAJOR_ROADS = ("motorway", "trunk", "primary", "secondary")


def build_query(lat, lon, radius):
    r = int(radius)
    a = "around:%d,%f,%f" % (r, lat, lon)
    a500 = "around:500,%f,%f" % (lat, lon)
    a5k = "around:5000,%f,%f" % (lat, lon)
    a15k = "around:15000,%f,%f" % (lat, lon)
    # Geometry of lines and polygons: roads in a smaller radius, railways and polygons in the common radius.
    g_road = "around:%d,%f,%f" % (min(r, 800), lat, lon)
    g_line = "around:%d,%f,%f" % (min(r, 1200), lat, lon)
    g_pl = "around:%d,%f,%f" % (min(r, 600), lat, lon)
    s, w, n, e = bbox(lat, lon, max(r, 1500) + 200)
    head = "[out:json][timeout:90];\n"
    q_poi = head + """(
  nwr[railway=station](%(a)s);
  nwr[railway=halt](%(a)s);
  node[railway=subway_entrance](%(a)s);
  node[highway=bus_stop](%(a)s);
  node[railway=tram_stop](%(a)s);
  node[public_transport=platform][trolleybus=yes](%(a)s);
  nwr[amenity=school](%(a)s);
  nwr[amenity=kindergarten](%(a)s);
  nwr[amenity~"^(university|college)$"](%(a)s);
  nwr[leisure=playground](%(a500)s);
  nwr[shop~"^(supermarket|convenience|greengrocer)$"](%(a)s);
  nwr[shop=mall](%(a)s);
  nwr[amenity=pharmacy](%(a)s);
  nwr[amenity~"^(clinic|doctors)$"](%(a)s);
  nwr[healthcare=centre](%(a)s);
  nwr[amenity=hospital](%(a)s);
  nwr[leisure~"^(sports_centre|fitness_centre|stadium|swimming_pool)$"](%(a)s);
  nwr[amenity~"^(bar|pub|nightclub)$"](%(a)s);
  nwr[amenity=fuel](%(a)s);
  nwr[amenity=prison](%(a)s);
  nwr["healthcare:speciality"~"psychiatry|narcology"](%(a)s);
  nwr[power=substation](%(a)s);
  nwr[power=plant](%(a5k)s);
  nwr[landuse=landfill](%(a5k)s);
  nwr[amenity~"^(waste_transfer_station|recycling_centre)$"](%(a)s);
  nwr[man_made=wastewater_plant](%(a)s);
);
out center tags;
"""
    q_geom = head + """(
  way[highway~"^(motorway|trunk|primary|secondary|tertiary)$"](%(g_road)s);
  way[railway~"^(rail|light_rail)$"](%(g_line)s);
  way[railway=tram](%(g_road)s);
  way[power=line](%(g_pl)s);
  nwr[leisure~"^(park|garden)$"](%(a)s);
  nwr[landuse=forest](%(a)s);
  nwr[natural=wood](%(a)s);
  nwr[natural=water](%(a)s);
  way[waterway=river](%(a)s);
  nwr[landuse=industrial](%(a)s);
  nwr[man_made=works](%(a)s);
  nwr[landuse=cemetery](%(a)s);
  nwr[landuse=construction](%(a500)s);
);
out tags geom(%(s)f,%(w)f,%(n)f,%(e)f);
"""
    q_air = head + """(
  nwr[aeroway=aerodrome](%(a15k)s);
);
out center tags;
"""
    p = dict(a=a, a500=a500, a5k=a5k, a15k=a15k, g_road=g_road, g_line=g_line, g_pl=g_pl,
             s=s, w=w, n=n, e=e)
    return [("poi", q_poi % p), ("geom", q_geom % p), ("aerodrome", q_air % p)]


def bbox(lat, lon, radius_m):
    dlat = radius_m / 110540.0
    dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


_USE_CURL = False  # after the first urllib SSL error go straight through curl


class _Busy(Exception):
    pass


def _post_urllib(ep, body):
    req = urllib.request.Request(ep, data=body, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (429, 502, 503, 504):
            raise _Busy("HTTP %s" % e.code)
        raise RuntimeError("HTTP %s" % e.code)


def _post_curl(ep, body):
    """Fallback transport: the old LibreSSL in the system Python fails TLS with some servers."""
    if not shutil.which("curl"):
        raise RuntimeError("curl not found")
    p = subprocess.run(
        ["curl", "-s", "-m", str(TIMEOUT), "-A", UA, "-w", "\n%{http_code}", "--data-binary", "@-", ep],
        input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT + 10)
    out = p.stdout.decode("utf-8", "replace")
    text, _, code = out.rpartition("\n")
    if p.returncode != 0:
        raise RuntimeError("curl exit %s" % p.returncode)
    if code in ("429", "502", "503", "504"):
        raise _Busy("HTTP " + code)
    if code != "200":
        raise RuntimeError("HTTP " + code)
    return text


def fetch(query, budget_s=240):
    """Tries servers with retries and a growing pause. Returns (json, endpoint, errors)."""
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    global _USE_CURL
    errors = []
    use_curl = _USE_CURL
    start = time.time()
    delay = 2
    for rnd in range(3):
        for ep in ENDPOINTS:
            if time.time() - start > budget_s:
                break
            try:
                txt = _post_curl(ep, body) if use_curl else _post_urllib(ep, body)
                data = json.loads(txt)
                if data.get("remark") and "error" in data.get("remark", "").lower() and not data.get("elements"):
                    raise _Busy(data["remark"][:120])
                return data, ep, errors
            except _Busy as e:
                errors.append("%s: %s" % (ep, e))
            except (urllib.error.URLError, ssl.SSLError) as e:
                # SSL or network error in urllib: retry the same server through curl
                errors.append("%s: %s" % (ep, e))
                if not use_curl and shutil.which("curl"):
                    use_curl = _USE_CURL = True
                    try:
                        data = json.loads(_post_curl(ep, body))
                        return data, ep, errors
                    except (_Busy, RuntimeError, ValueError, subprocess.SubprocessError) as e2:
                        errors.append("%s (curl): %s" % (ep, e2))
            except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as e:
                errors.append("%s: %s" % (ep, e))
        if time.time() - start > budget_s:
            break
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("Overpass unavailable: " + "; ".join(errors[-6:]))


# --- Geometry -------------------------------------------------------------

def _xy(lat, lon, lat0, lon0):
    return ((lon - lon0) * 111320.0 * math.cos(math.radians(lat0)), (lat - lat0) * 110540.0)


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _inside(pts):
    """Whether point (0,0) is inside polygon pts (list of (x,y))."""
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > 0) != (y2 > 0):
            xi = x1 + (0 - y1) * (x2 - x1) / (y2 - y1)
            if xi > 0:
                inside = not inside
    return inside


def _lines(el):
    """List of polylines [(lat, lon), ...] of an element with geometry."""
    out = []
    if el.get("geometry"):
        out.append([(p["lat"], p["lon"]) for p in el["geometry"] if p])
    for m in el.get("members") or []:
        if m.get("geometry") and m.get("role", "outer") in ("outer", ""):
            out.append([(p["lat"], p["lon"]) for p in m["geometry"] if p])
    return [l for l in out if l]


def geom_distance(el, lat0, lon0, area=False):
    """Distance (m) from the point to the geometry, 0 if the point is inside a polygon. Also returns the nearest point."""
    best, best_pt = None, None
    lines = _lines(el)
    for line in lines:
        pts = [_xy(a, b, lat0, lon0) for a, b in line]
        if area and len(pts) >= 3 and _inside(pts):
            return 0.0, (lat0, lon0)
        if len(pts) == 1:
            d = math.hypot(*pts[0])
            cand = line[0]
            if best is None or d < best:
                best, best_pt = d, cand
            continue
        for i in range(len(pts) - 1):
            d = _seg_dist(0, 0, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            if best is None or d < best:
                best, best_pt = d, line[i]
    return best, best_pt


# --- Classification -------------------------------------------------------

def categorize(t):
    """Tags → list of categories (an element can fall into several)."""
    cats = []
    rw, hw, am, le, lu, nat = (t.get(k) for k in ("railway", "highway", "amenity", "leisure", "landuse", "natural"))
    if rw == "station" and t.get("station") == "subway":
        cats.append("metro")
    elif rw == "subway_entrance":
        cats.append("metro")
    elif rw in ("station", "halt"):
        cats.append("rail_station")
    if hw == "bus_stop" or rw == "tram_stop" or (t.get("public_transport") == "platform" and t.get("trolleybus") == "yes"):
        cats.append("stop_bus_tram")
    if am == "school":
        cats.append("school")
    if am == "kindergarten":
        cats.append("kindergarten")
    if am in ("university", "college"):
        cats.append("university")
    if le == "playground":
        cats.append("playground")
    if le in ("park", "garden"):
        cats.append("park")
    if lu == "forest" or nat == "wood":
        cats.append("forest")
    if nat == "water" or t.get("waterway") == "river":
        cats.append("water")
    if t.get("shop") in ("supermarket", "convenience", "greengrocer"):
        cats.append("grocery")
    if t.get("shop") == "mall":
        cats.append("mall")
    if am == "pharmacy":
        cats.append("pharmacy")
    if am in ("clinic", "doctors") or t.get("healthcare") == "centre":
        cats.append("clinic")
    if am == "hospital":
        cats.append("hospital")
    if le in ("sports_centre", "fitness_centre", "stadium", "swimming_pool"):
        cats.append("sport")
    if am in ("bar", "pub", "nightclub"):
        cats.append("nightlife")
    if hw in MAJOR_ROADS:
        cats.append("major_road")
    elif hw == "tertiary":
        cats.append("minor_road")
    if rw in ("rail", "light_rail"):
        cats.append("railway_line")
    if rw == "tram":
        cats.append("tram_line")
    if lu == "industrial" or t.get("man_made") == "works":
        cats.append("industrial")
    if t.get("power") == "line":
        cats.append("powerline")
    if t.get("power") == "substation":
        cats.append("substation")
    if t.get("power") == "plant":
        cats.append("power_plant")
    if lu == "landfill":
        cats.append("landfill")
    if am in ("waste_transfer_station", "recycling_centre") or t.get("man_made") == "wastewater_plant":
        cats.append("waste")
    if lu == "cemetery":
        cats.append("cemetery")
    if t.get("aeroway") == "aerodrome":
        cats.append("aerodrome")
    if am == "prison":
        cats.append("prison")
    if "psychiatry" in (t.get("healthcare:speciality") or "") or "narcology" in (t.get("healthcare:speciality") or ""):
        cats.append("psychiatric")
    if lu == "construction":
        cats.append("construction")
    if am == "fuel":
        cats.append("fuel")
    return cats


AREA_CATS = {"park", "forest", "water", "industrial", "cemetery", "construction", "landfill"}
ALL_CATS = ["metro", "rail_station", "stop_bus_tram", "school", "kindergarten", "university", "playground",
            "park", "forest", "water", "grocery", "mall", "pharmacy", "clinic", "hospital", "sport", "nightlife",
            "major_road", "minor_road", "railway_line", "tram_line", "industrial", "powerline", "substation",
            "power_plant", "landfill", "waste", "cemetery", "aerodrome", "prison", "psychiatric", "construction",
            "fuel"]


# Human-readable road names in Russian: they are shown in the report.
ROAD_RU = {"motorway": "Автомагистраль", "motorway_link": "Съезд с автомагистрали", "trunk": "Магистраль",
           "trunk_link": "Съезд с магистрали", "primary": "Главная дорога", "primary_link": "Съезд",
           "secondary": "Дорога районного значения", "secondary_link": "Съезд", "tertiary": "Улица",
           "tertiary_link": "Съезд"}


def _name(t, cat):
    n = t.get("name:ru") or t.get("name")
    if n:
        return n
    if cat in ("major_road", "minor_road"):
        return ("%s %s" % (ROAD_RU.get(t.get("highway"), "Дорога"), t.get("ref") or "")).strip()
    if cat == "powerline":
        return "ЛЭП %s" % (t.get("voltage") or "")
    return None


def process(data, lat0, lon0, radius):
    raw = {c: [] for c in ALL_CATS}
    for el in data.get("elements", []):
        t = el.get("tags") or {}
        cats = categorize(t)
        if not cats:
            continue
        for cat in cats:
            if el.get("geometry") or el.get("members"):
                d, pt = geom_distance(el, lat0, lon0, area=cat in AREA_CATS)
            else:
                if el.get("type") == "node":
                    pt = (el.get("lat"), el.get("lon"))
                else:
                    c = el.get("center") or {}
                    pt = (c.get("lat"), c.get("lon"))
                if pt[0] is None:
                    continue
                d = gs.haversine_m(lat0, lon0, pt[0], pt[1])
            if d is None:
                continue
            tags = {k: t[k] for k in KEEP_TAGS if k in t}
            raw[cat].append({
                "name": _name(t, cat),
                "distance_m": int(round(d)),
                "lat": round(pt[0], 6) if pt and pt[0] is not None else None,
                "lon": round(pt[1], 6) if pt and pt[1] is not None else None,
                "osm": "%s/%s" % (el.get("type"), el.get("id")),
                "url": "https://www.openstreetmap.org/%s/%s" % (el.get("type"), el.get("id")),
                "tags": tags,
            })
    # unnamed metro entrances: take the name of the nearest station (Russian label, shown in the report)
    stations = [x for x in raw["metro"] if x["tags"].get("railway") == "station" and x["name"]]
    for x in raw["metro"]:
        if not x["name"] and stations and x["lat"] is not None:
            st = min(stations, key=lambda s_: gs.haversine_m(x["lat"], x["lon"], s_["lat"], s_["lon"]))
            x["name"] = "%s (вход)" % st["name"]
    categories, counts, nearest = {}, {}, {}
    for cat, items in raw.items():
        items.sort(key=lambda x: x["distance_m"])
        # duplicates: the same road/object split into several pieces → keep the nearest piece
        seen, uniq = set(), []
        for it in items:
            key = (it["name"], it["tags"].get("highway") or it["tags"].get("railway")) if it["name"] else it["osm"]
            if cat == "metro" and it["name"]:
                key = it["name"].replace(" (вход)", "")
            elif cat in ("stop_bus_tram", "grocery", "pharmacy", "school", "kindergarten"):
                key = it["osm"]
            if key in seen:
                continue
            seen.add(key)
            uniq.append(it)
        categories[cat] = uniq[:MAX_PER_CAT]
        counts[cat] = {
            "500": sum(1 for x in uniq if x["distance_m"] <= 500),
            "1000": sum(1 for x in uniq if x["distance_m"] <= 1000),
            "1500": sum(1 for x in uniq if x["distance_m"] <= max(1500, radius)),
        }
        nearest[cat] = uniq[0]["distance_m"] if uniq else None
    return categories, counts, nearest


def noise_estimate(categories, nearest, cfg=None):
    sources = []
    for it in categories.get("major_road", []) + categories.get("minor_road", []):
        cls = it["tags"].get("highway")
        db = gs.estimate_road_db(cls, it["distance_m"], it["tags"].get("lanes"))
        if db is not None and db > 40:
            sources.append({"kind": "road_" + cls, "name": it["name"], "distance_m": it["distance_m"], "est_db": db})
    for it in categories.get("railway_line", []):
        cls = it["tags"].get("railway", "rail")
        db = gs.estimate_road_db(cls, it["distance_m"])
        if db is not None and it["tags"].get("service"):
            db = max(gs.MIN_DB, db - 8)
        if db is not None and db > 40:
            sources.append({"kind": "rail", "name": it["name"], "distance_m": it["distance_m"], "est_db": db})
    for it in categories.get("tram_line", [])[:2]:
        db = gs.estimate_road_db("tram", it["distance_m"])
        if db is not None and db > 40:
            sources.append({"kind": "tram", "name": it["name"], "distance_m": it["distance_m"], "est_db": db})
    air = categories.get("aerodrome", [])
    if air:
        db = gs.aircraft_db(air[0]["distance_m"])
        if db:
            sources.append({"kind": "aircraft", "name": air[0]["name"], "distance_m": air[0]["distance_m"], "est_db": db})
    # For the sum take only the loudest source per road/line.
    sources.sort(key=lambda s: -s["est_db"])
    seen, top = set(), []
    for s in sources:
        k = (s["kind"], s["name"])
        if k in seen:
            continue
        seen.add(k)
        top.append(s)
    top = top[:8]
    # Sum over the 3 loudest: distant sources are usually shielded by buildings.
    combined = gs.combine_db([s["est_db"] for s in top[:3]]) if top else None
    db_max = top[0]["est_db"] if top else None
    kind = "aircraft" if top and top[0]["kind"] == "aircraft" else ("rail" if top and top[0]["kind"] == "rail" else "road")
    return {
        "sources": top,
        "est_db_max": db_max,
        "est_db_combined": combined,
        "method": ("approximate: daytime level at the facade facing the source; line source, "
                   "-3 dB per doubling of distance from 10 m, ignoring shielding by buildings and noise barriers. "
                   "Courtyard-facing windows are usually 10-20 dB quieter."),
        "price_discount_pct": gs.noise_discount_pct(combined, kind, cfg),
    }


def suggested(categories, counts, nearest, noise, cfg=None):
    n = nearest
    nl = n.get("nightlife")
    scores, notes = {}, {}
    scores["noise_external"] = gs.score_noise_external(noise.get("est_db_combined"), nl)
    notes["noise_external"] = "external noise estimate %s dB%s" % (
        noise.get("est_db_combined"), ", bar/club at %d m" % nl if nl is not None and nl < 150 else "")
    scores["transport"] = gs.score_transport(n.get("metro"), n.get("rail_station"),
                                             counts.get("stop_bus_tram", {}).get("500", 0), cfg)
    notes["transport"] = "metro %s m, railway station %s m, stops within 500 m: %s" % (
        n.get("metro"), n.get("rail_station"), counts.get("stop_bus_tram", {}).get("500", 0))
    scores["green"] = gs.score_green(n.get("park"), n.get("forest"), n.get("water"),
                                     counts.get("park", {}).get("1000", 0), cfg)
    notes["green"] = "park %s m, forest %s m, water %s m" % (n.get("park"), n.get("forest"), n.get("water"))
    scores["kids"] = gs.score_kids(n.get("school"), n.get("kindergarten"),
                                   counts.get("school", {}).get("1000", 0),
                                   counts.get("kindergarten", {}).get("1000", 0), cfg)
    notes["kids"] = "school %s m (%s within 1 km), kindergarten %s m (%s within 1 km); school quality and catchment not considered" % (
        n.get("school"), counts.get("school", {}).get("1000", 0),
        n.get("kindergarten"), counts.get("kindergarten", {}).get("1000", 0))
    scores["amenities"] = gs.score_amenities(n, cfg)
    notes["amenities"] = "grocery %s m, pharmacy %s m, clinic %s m, mall %s m, sport %s m" % (
        n.get("grocery"), n.get("pharmacy"), n.get("clinic"), n.get("mall"), n.get("sport"))
    eco, pens = gs.score_ecology(n, cfg)
    scores["ecology"] = eco
    notes["ecology"] = ("penalties: " + ", ".join("%s -%s" % p for p in pens)) if pens else "no major pollution sources nearby found in OSM"
    return scores, notes


PARTIAL_NOTE = "Major roads, railways and power lines failed to load: road noise not counted, noise_external and ecology scores are incomplete."
PARTIAL_TTL_DAYS = 1


def _cache_key(lat, lon, radius):
    return "%s_r%d" % (cache.key_coords(lat, lon, step=50), int(radius))


def analyze(lat, lon, radius=1500, raw_path=None, use_cache=True, fresh=False):
    elements, eps, errs = [], [], []
    from_cache = False
    partial = False
    cached = None
    if raw_path and os.path.exists(raw_path) and not fresh:
        with open(raw_path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("center") == [lat, lon] and cached.get("radius") == radius:
            eps = ["cache: " + raw_path]
        else:
            cached = None
    if cached is None and use_cache and not fresh:
        ck = _cache_key(lat, lon, radius)
        cp = cache.get("osm", ck)
        if cp:
            with open(cp, encoding="utf-8") as f:
                cached = json.load(f)
            # an incomplete response stays in the cache for at most one day
            if cached.get("partial") and not cache.get("osm", ck, max_age_days=PARTIAL_TTL_DAYS):
                cached = None
            else:
                eps = ["cache: " + cp]
    if cached is not None:
        elements = cached["elements"]
        partial = bool(cached.get("partial"))
        from_cache = True
    for part, q in ([] if from_cache else build_query(lat, lon, radius)):
        try:
            data, ep, e = fetch(q)
            elements.extend(data.get("elements", []))
            eps.append("%s: %s" % (part, ep))
            errs.extend(e)
        except RuntimeError as e:
            if part == "poi":
                raise
            if part == "geom":
                partial = True
            errs.append("part '%s' not received: %s" % (part, e))
    if not from_cache:
        payload = {"center": [lat, lon], "radius": radius, "elements": elements, "partial": partial}
        if raw_path:
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        if use_cache:
            cache.put("osm", _cache_key(lat, lon, radius), data=json.dumps(payload, ensure_ascii=False))
    data = {"elements": elements}
    ep = "; ".join(eps)
    cfg = gs.load_config()
    categories, counts, nearest = process(data, lat, lon, radius)
    noise = noise_estimate(categories, nearest, cfg)
    scores, notes = suggested(categories, counts, nearest, noise, cfg)
    out_notes = [
        "OpenStreetMap data: completeness depends on the city, an object missing in OSM may still exist.",
        "suggested_scores are preliminary, agents refine them with reviews and official data.",
    ]
    if partial:
        out_notes.insert(0, PARTIAL_NOTE)
    if nearest.get("construction") is not None:
        out_notes.append("Construction site nearby (%d m): check what is being built and whether it will block the view." % nearest["construction"])
    if nearest.get("nightlife") is not None and nearest["nightlife"] < 50:
        out_notes.append("Bar or club closer than 50 m: night noise is possible.")
    return {
        "center": {"lat": lat, "lon": lon},
        "radius_m": radius,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endpoint": ep,
        "categories": categories,
        "counts": counts,
        "nearest": nearest,
        "noise_estimate": noise,
        "suggested_scores": scores,
        "score_notes": notes,
        "notes": out_notes,
        "errors": errs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Objects near a point from OSM (Overpass): distances, noise, preliminary scores.")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=int, default=1500, help="search radius, m (default 1500)")
    ap.add_argument("--out", help="save JSON to a file (and still print it)")
    ap.add_argument("--raw", help="raw Overpass response cache: read it if present, otherwise save it")
    ap.add_argument("--fresh", action="store_true", help="skip the cache, fetch again")
    ap.add_argument("--no-cache", action="store_true", help="do not read or write the shared cache")
    a = ap.parse_args(argv)
    if not (-90 <= a.lat <= 90 and -180 <= a.lon <= 180):
        print("Invalid coordinates", file=sys.stderr)
        return 2
    try:
        res = analyze(a.lat, a.lon, a.radius, a.raw, use_cache=not a.no_cache, fresh=a.fresh)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3
    txt = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        brief_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "geo_brief.json")
        with open(brief_path, "w", encoding="utf-8") as f:
            f.write(geo_brief.dumps(geo_brief.build(res)))
        print("geo: %s\ngeo_brief: %s" % (a.out, brief_path))
        return 0
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
