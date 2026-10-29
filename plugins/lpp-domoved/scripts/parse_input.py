#!/usr/bin/env python3
"""Parse the input: links to listings and maps, or an address.

Example:
  python3 parse_input.py "https://www.cian.ru/sale/flat/312345678/"
  python3 parse_input.py "https://yandex.ru/maps/?ll=37.617635,55.755814&z=17" "Москва, Тверская 7"
"""
import argparse
import json
import re
import sys
from urllib.parse import urlparse, parse_qs, unquote

URL_RE = re.compile(r"https?://[^\s<>\"']+|(?:www\.)?(?:[a-z0-9-]+\.)+(?:ru|com|рф|app\.goo\.gl|gl)/[^\s<>\"']*", re.I)


COORD_RE = re.compile(r"\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*")


def _valid(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if 41.0 <= lat <= 82.0 and -180.0 <= lon <= 180.0:
        return round(lat, 7), round(lon, 7)
    return None


def _pair(text, lon_first):
    """'a,b' → (lat, lon), taking the order into account."""
    if not text:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*[,~ ]\s*(-?\d+(?:\.\d+)?)", unquote(text))
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    return _valid(b, a) if lon_first else _valid(a, b)


def _first(qs, *keys):
    for k in keys:
        v = qs.get(k)
        if v:
            return v[0]
    return None


def _item(text):
    return {
        "input": text,
        "source": None,
        "listing_id": None,
        "lat": None,
        "lon": None,
        "object_type_hint": None,
        "needs_fetch": False,
        "needs_geocode": False,
        "short_link": False,
    }


def _type_hint(path):
    p = path.lower()
    if any(k in p for k in ("suburban", "doma_dachi", "dom/", "/house", "kottedzh", "/cottage", "uchastok", "sale__house", "sale__cottage", "townhouse")):
        return "private_house"
    if any(k in p for k in ("zhk", "newbuilding", "novostroy", "novostroyki", "/complex", "new_flat", "sale__newbuilding")):
        return "new_build"
    if any(k in p for k in ("flat", "kvartiry", "sale__flat", "/offer/")):
        return "secondary"
    return None


def parse_url(raw):
    it = _item(raw)
    url = raw if re.match(r"https?://", raw, re.I) else "https://" + raw
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = u.path or ""
    qs = parse_qs(u.query)
    frag = u.fragment or ""

    if host.endswith("cian.ru"):
        it["source"] = "cian"
        m = re.search(r"/(?:sale|rent)/(?:flat|suburban|commercial)/(\d+)", path)
        if m:
            it["listing_id"] = m.group(1)
        elif re.search(r"/zhk-|newobject|/kupit-kvartiru-zhiloy-kompleks", path):
            m2 = re.search(r"(\d{3,})", path)
            it["listing_id"] = m2.group(1) if m2 else None
        it["object_type_hint"] = _type_hint(path)
        if re.search(r"zhk-|newobject|novostroyk|zhiloy-kompleks", path, re.I) or host.startswith("zhk-"):
            it["object_type_hint"] = "new_build"
        if "/suburban/" in path:
            it["object_type_hint"] = "private_house"
        it["needs_fetch"] = True
    elif host.endswith("domclick.ru"):
        it["source"] = "domclick"
        m = re.search(r"/card/([a-z_]+?)__(\d+)", path)
        if m:
            kind, it["listing_id"] = m.group(1), m.group(2)
            if "newbuilding" in kind or "new_flat" in kind:
                it["object_type_hint"] = "new_build"
            elif any(k in kind for k in ("house", "cottage", "townhouse", "lot")):
                it["object_type_hint"] = "private_house"
            elif "flat" in kind:
                it["object_type_hint"] = "secondary"
        else:
            it["object_type_hint"] = _type_hint(path)
        it["needs_fetch"] = True
    elif host.endswith("avito.ru"):
        it["source"] = "avito"
        m = re.search(r"_(\d{6,})(?:$|[/?#])", path + "/")
        if m:
            it["listing_id"] = m.group(1)
        it["object_type_hint"] = _type_hint(path)
        if "novostroyka" in path.lower() or "novostroyki" in path.lower():
            it["object_type_hint"] = "new_build"
        it["needs_fetch"] = True
    elif host.startswith("realty.yandex.") or host.startswith("realty.ya."):
        it["source"] = "yandex_realty"
        m = re.search(r"/offer/(\d+)", path)
        if m:
            it["listing_id"] = m.group(1)
            it["object_type_hint"] = None
        if re.search(r"/novostrojka|/newbuilding|-\d+/?$", path) and "/offer/" not in path:
            it["object_type_hint"] = "new_build"
        it["needs_fetch"] = True
    elif (host.startswith("yandex.") or host.startswith("maps.yandex.")) and ("/maps" in path or host.startswith("maps.")):
        it["source"] = "yandex_maps"
        if "/maps/-/" in path:
            it["short_link"] = True
        # Priority: the point (pt / whatshere) is more precise than the map center (ll). Yandex puts longitude first.
        wh = _first(qs, "whatshere[point]")
        pt = _first(qs, "pt")
        ll = _first(qs, "ll")
        coords = _pair(wh, True) or _pair(pt, True) or _pair(ll, True)
        m = re.search(r"/maps/org/[^/]+/(\d+)", path)
        if m:
            it["listing_id"] = m.group(1)
        if coords:
            it["lat"], it["lon"] = coords
    elif host.endswith("2gis.ru") or host.endswith("2gis.com"):
        it["source"] = "2gis"
        m = re.search(r"/geo/(\d+)(?:/(-?\d+(?:\.\d+)?)%2C(-?\d+(?:\.\d+)?)|/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?))?", path, re.I)
        coords = None
        if m:
            it["listing_id"] = m.group(1)
            lon = m.group(2) or m.group(4)
            lat = m.group(3) or m.group(5)
            if lon and lat:
                coords = _valid(lat, lon)
        if not coords:
            mm = _first(qs, "m")
            coords = _pair(mm.split("/")[0] if mm else None, True)
        if coords:
            it["lat"], it["lon"] = coords
    elif host in ("maps.app.goo.gl", "goo.gl") or (("google." in host) and ("/maps" in path or host.startswith("maps."))):
        it["source"] = "google_maps"
        if host in ("maps.app.goo.gl", "goo.gl"):
            it["short_link"] = True
        coords = None
        m = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", path)
        if m:
            coords = _valid(m.group(1), m.group(2))
        if not coords:
            m = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", path)
            if m:
                coords = _valid(m.group(1), m.group(2))
        if not coords:
            coords = _pair(_first(qs, "q", "query", "ll", "destination"), False)
        if coords:
            it["lat"], it["lon"] = coords
    elif host.endswith("openstreetmap.org"):
        it["source"] = "osm"
        coords = None
        if qs.get("mlat") and qs.get("mlon"):
            coords = _valid(qs["mlat"][0], qs["mlon"][0])
        if not coords:
            m = re.search(r"map=\d+/(-?\d+(?:\.\d+)?)/(-?\d+(?:\.\d+)?)", frag)
            if m:
                coords = _valid(m.group(1), m.group(2))
        if coords:
            it["lat"], it["lon"] = coords
    else:
        it["source"] = "other_url"
        it["needs_fetch"] = True

    if it["source"] in ("yandex_maps", "2gis", "google_maps", "osm") and it["lat"] is None:
        # Short link or organization link without coordinates: needs WebFetch or a browser.
        it["needs_fetch"] = True
        it["needs_geocode"] = not it["short_link"]
    return it


def split_inputs(args):
    """Links are pulled out of the text, the rest (if it looks like an address) is used as the address."""
    items = []
    for text in args:
        text = text.strip()
        if not text:
            continue
        urls = URL_RE.findall(text)
        rest = URL_RE.sub(" ", text)
        for u in urls:
            items.append(u.rstrip(".,;)"))
        # command flags (--profile family, --quick) are not an address
        rest = re.sub(r"--profile\s+\S+", " ", rest)
        rest = re.sub(r"(?<!\S)--?[A-Za-z][\w-]*", " ", rest)
        rest = re.sub(r"\s+", " ", rest).strip(" ,;")
        if rest and (re.search(r"[A-Za-zА-Яа-яЁё]{3,}", rest) or COORD_RE.fullmatch(rest)):
            items.append(rest)
    return items


def parse(texts):
    out = []
    for t in split_inputs(texts):
        if URL_RE.fullmatch(t) or re.match(r"https?://", t, re.I):
            out.append(parse_url(t))
        else:
            it = _item(t)
            coords = _pair(t, False) if COORD_RE.fullmatch(t) else None
            if coords:
                it["source"] = "coordinates"
                it["lat"], it["lon"] = coords
            else:
                it["source"] = "address"
                it["needs_geocode"] = True
            out.append(it)
    return {"items": out}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Detects the link type (ЦИАН, Домклик, Авито, Яндекс Недвижимость, Яндекс/2ГИС/Google/OSM maps) or an address and extracts the id and coordinates.")
    ap.add_argument("text", nargs="+", help="links and/or an address; several allowed")
    a = ap.parse_args(argv)
    res = parse(a.text)
    if not res["items"]:
        print("Found neither links nor an address", file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
