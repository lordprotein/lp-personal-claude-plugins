#!/usr/bin/env python3
"""Geocoding via Nominatim (OpenStreetMap), no keys.

  python3 geocode.py --address "Москва, Профсоюзная 140к2"
  python3 geocode.py --reverse 55.6215 37.5064
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://nominatim.openstreetmap.org"
UA = "domoved/0.1 (claude-code plugin)"
TIMEOUT = 20


def _get(path, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru"})
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            time.sleep(1.5)
    raise RuntimeError("Nominatim unavailable: %s" % last)


def _norm(rec):
    a = rec.get("address") or {}
    city = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or a.get("state")
    district = a.get("city_district") or a.get("suburb") or a.get("district") or a.get("county")
    return {
        "lat": float(rec["lat"]),
        "lon": float(rec["lon"]),
        "display_name": rec.get("display_name"),
        "city": city,
        "district": district,
        "suburb": a.get("suburb"),
        "road": a.get("road"),
        "house_number": a.get("house_number"),
        "postcode": a.get("postcode"),
        "osm_type": rec.get("osm_type"),
        "osm_id": rec.get("osm_id"),
        "category": rec.get("class") or rec.get("category"),
        "type": rec.get("type"),
    }


def geocode(address, limit=5):
    data = _get("/search", {
        "q": address, "format": "jsonv2", "addressdetails": 1,
        "limit": limit, "countrycodes": "ru", "accept-language": "ru",
    })
    if not data:
        return None
    cands = [_norm(r) for r in data]
    best = dict(cands[0])
    best["candidates"] = cands[1:]
    best["query"] = address
    return best


def reverse(lat, lon):
    data = _get("/reverse", {
        "lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1,
        "zoom": 18, "accept-language": "ru",
    })
    if not data or "error" in data:
        return None
    res = _norm(data)
    res["candidates"] = []
    res["query"] = "%s,%s" % (lat, lon)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="Address → coordinates or coordinates → address (Nominatim, OSM).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--address", help="free-form address, preferably with the city")
    g.add_argument("--reverse", nargs=2, type=float, metavar=("LAT", "LON"))
    a = ap.parse_args(argv)
    try:
        res = geocode(a.address) if a.address else reverse(*a.reverse)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3
    if not res:
        print("Nothing found", file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
