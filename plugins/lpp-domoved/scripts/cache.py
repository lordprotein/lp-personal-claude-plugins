#!/usr/bin/env python3
"""Domoved file cache (the .cache folder in data_home).

Kinds and default lifetime (days): osm 30, rates 1, house 30, district 30.
Repeated checks and comparisons of objects in the same house or district reuse ready data.

CLI:
  cache.py key --house "<address>"
  cache.py key --coords LAT LON [--step 300]
  cache.py get <kind> <key> [--max-age-days N]   path and exit 0, otherwise exit 1
  cache.py put <kind> <key> <file>
"""
import argparse
import hashlib
import math
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

TTL_DAYS = {"osm": 30, "rates": 1, "house": 30, "district": 30}


def normalize_address(addr):
    s = (addr or "").lower().replace("ё", "е")
    s = re.sub(r"\b\d{6}\b", " ", s)              # postal code
    s = re.sub(r"\bроссия\b|\bрф\b", " ", s)
    s = re.sub(r"[^\w]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def key_house(addr):
    norm = normalize_address(addr)
    if not norm:
        raise ValueError("empty address")
    return "h_" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def key_coords(lat, lon, step=300):
    """Grid cell of roughly step meters."""
    dlat = step / 111320.0
    dlon = step / (111320.0 * max(math.cos(math.radians(lat)), 0.01))
    return "c%d_%d_%d" % (int(step), int(math.floor(lat / dlat)), int(math.floor(lon / dlon)))


def _path(kind, key, root=None):
    if kind not in TTL_DAYS:
        raise ValueError("unknown cache kind: %s" % kind)
    if not re.match(r"^[\w.-]+$", key):
        raise ValueError("invalid key: %s" % key)
    folder = os.path.join(root or paths.cache_dir(), kind)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, key + ".json")


def get(kind, key, max_age_days=None, root=None, now=None):
    p = _path(kind, key, root)
    if not os.path.exists(p):
        return None
    age_days = ((now or time.time()) - os.path.getmtime(p)) / 86400.0
    limit = TTL_DAYS[kind] if max_age_days is None else max_age_days
    if age_days > limit:
        return None
    return p


def put(kind, key, src=None, data=None, root=None):
    """Copies file src or writes string data. Returns the path in the cache."""
    p = _path(kind, key, root)
    if src is not None:
        shutil.copyfile(src, p)
    else:
        with open(p, "w", encoding="utf-8") as f:
            f.write(data or "")
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description="Domoved cache")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("key", help="print the key")
    g = k.add_mutually_exclusive_group(required=True)
    g.add_argument("--house", help="house address")
    g.add_argument("--coords", nargs=2, type=float, metavar=("LAT", "LON"))
    k.add_argument("--step", type=int, default=300, help="grid step for --coords, m")
    gg = sub.add_parser("get", help="path to a fresh cache file")
    gg.add_argument("kind", choices=sorted(TTL_DAYS))
    gg.add_argument("key")
    gg.add_argument("--max-age-days", type=float)
    pp = sub.add_parser("put", help="put a file into the cache")
    pp.add_argument("kind", choices=sorted(TTL_DAYS))
    pp.add_argument("key")
    pp.add_argument("file")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "key":
            print(key_house(a.house) if a.house else key_coords(a.coords[0], a.coords[1], a.step))
            return 0
        if a.cmd == "get":
            p = get(a.kind, a.key, a.max_age_days)
            if not p:
                return 1
            print(p)
            return 0
        print(put(a.kind, a.key, src=a.file))
        return 0
    except (ValueError, OSError) as e:
        print("Error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
