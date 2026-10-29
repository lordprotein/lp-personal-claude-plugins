"""Pure functions: decay with distance, noise estimate, preliminary scores from geodata.

No network, so they can be tested separately. Parameters come from ../config/adjustments.json.
"""
import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "..", "config", "adjustments.json")

_DEFAULT_DECAY = {
    "metro": {"full": 400, "zero": 1200},
    "rail": {"full": 500, "zero": 1500},
    "park": {"full": 150, "zero": 600},
    "large_park": {"full": 300, "zero": 1500},
    "powerline": {"full": 30, "zero": 200},
    "landfill": {"full": 500, "zero": 5000},
    "industrial": {"full": 100, "zero": 1000},
    "school": {"full": 300, "zero": 1500},
    "kindergarten": {"full": 300, "zero": 1000},
    "grocery": {"full": 200, "zero": 800},
    "clinic": {"full": 500, "zero": 2000},
}

_cache = {}


def load_config(path=None):
    path = path or CONFIG_PATH
    if path in _cache:
        return _cache[path]
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    _cache[path] = cfg
    return cfg


def decay_params(name, cfg=None):
    cfg = cfg if cfg is not None else load_config()
    d = (cfg.get("decay_m") or {}).get(name) or _DEFAULT_DECAY.get(name)
    if not d:
        raise KeyError(name)
    return d["full"], d["zero"]


def decay(distance, full, zero):
    """1.0 up to full, linearly down to 0 at zero, None → 0."""
    if distance is None:
        return 0.0
    if distance <= full:
        return 1.0
    if distance >= zero:
        return 0.0
    return (zero - distance) / float(zero - full)


def decay_named(name, distance, cfg=None):
    full, zero = decay_params(name, cfg)
    return decay(distance, full, zero)


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


# --- Noise -------------------------------------------------------------

# Level (dBA) at 10 m from the source, a reference for the daytime equivalent level.
SOURCE_DB_AT_10M = {
    "motorway": 78,
    "trunk": 75,
    "primary": 72,
    "secondary": 68,
    "tertiary": 64,
    "tram": 70,
    "rail": 75,
    "light_rail": 70,
}
MIN_DB = 35.0


def estimate_road_db(highway_class, distance_m, lanes=None):
    """Line source: -3 dB per doubling of distance from 10 m."""
    base = SOURCE_DB_AT_10M.get(highway_class)
    if base is None or distance_m is None:
        return None
    base = float(base)
    try:
        n = int(str(lanes).split(";")[0]) if lanes else None
    except ValueError:
        n = None
    if n and n >= 6:
        base += 2
    elif n and n <= 2 and highway_class in ("primary", "secondary"):
        base -= 1
    d = max(float(distance_m), 10.0)
    db = base - 3.0 * math.log2(d / 10.0)
    return round(max(MIN_DB, db), 1)


def combine_db(levels):
    """Logarithmic sum of levels."""
    vals = [x for x in levels if x is not None]
    if not vals:
        return None
    return round(10 * math.log10(sum(10 ** (x / 10.0) for x in vals)), 1)


def aircraft_db(distance_m):
    """Rough: an aerodrome closer than 5 km gives background noise, otherwise None."""
    if distance_m is None or distance_m >= 5000:
        return None
    if distance_m < 2000:
        return 65.0
    if distance_m < 3500:
        return 60.0
    return 55.0


def noise_discount_pct(db, kind="road", cfg=None):
    """Price discount by NDI: % per dB above the threshold. Returns [lo, hi]."""
    cfg = cfg if cfg is not None else load_config()
    n = cfg.get("noise") or {}
    thr = n.get("threshold_db", 55)
    ndi = (n.get("ndi_pct_per_db") or {}).get(kind, [0.4, 0.9])
    if not isinstance(ndi, list):
        ndi = [ndi, ndi]
    if db is None or db <= thr:
        return [0.0, 0.0]
    over = db - thr
    return [round(over * ndi[0], 1), round(over * ndi[1], 1)]


# --- Preliminary scores ----------------------------------------------

def _clip(x, lo=0.0, hi=10.0):
    return round(max(lo, min(hi, x)), 1)


def score_noise_external(est_db_combined, nightlife_nearest_m=None):
    """<=45 → 10, 55 → 7, 65 → 4, >=75 → 1 (piecewise linear)."""
    if est_db_combined is None:
        s = 9.0
    else:
        pts = [(45, 10.0), (55, 7.0), (65, 4.0), (75, 1.0)]
        db = est_db_combined
        if db <= pts[0][0]:
            s = pts[0][1]
        elif db >= pts[-1][0]:
            s = pts[-1][1]
        else:
            s = 1.0
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if x0 <= db <= x1:
                    s = y0 + (y1 - y0) * (db - x0) / (x1 - x0)
                    break
    if nightlife_nearest_m is not None:
        if nightlife_nearest_m < 50:
            s -= 2.0
        elif nightlife_nearest_m < 150:
            s -= 1.0
    return _clip(s)


def score_transport(nearest_metro=None, nearest_rail=None, stops_500=0, cfg=None):
    m = decay_named("metro", nearest_metro, cfg)
    r = decay_named("rail", nearest_rail, cfg)
    rail_part = max(m, 0.8 * r)
    stops = min(stops_500 or 0, 8) / 8.0
    s = 2.0 + 6.0 * rail_part + 2.0 * stops
    return _clip(s)


def score_green(nearest_park=None, nearest_forest=None, nearest_water=None, parks_1000=0, cfg=None):
    p = decay_named("park", nearest_park, cfg)
    big = max(decay_named("large_park", nearest_park, cfg), decay_named("large_park", nearest_forest, cfg))
    w = decay(nearest_water, 300, 1500)
    s = 2.0 + 3.5 * p + 3.0 * big + 1.0 * w + 0.5 * min(parks_1000 or 0, 4) / 4.0 * 1.0
    return _clip(s)


def score_kids(nearest_school=None, nearest_kg=None, schools_1000=0, kg_1000=0, cfg=None):
    sc = decay_named("school", nearest_school, cfg)
    kg = decay_named("kindergarten", nearest_kg, cfg)
    choice = min(schools_1000 or 0, 4) / 4.0 * 0.5 + min(kg_1000 or 0, 4) / 4.0 * 0.5
    s = 1.0 + 4.0 * sc + 3.0 * kg + 2.0 * choice
    return _clip(s)


def score_amenities(nearest=None, cfg=None):
    """nearest: dict category → distance."""
    nearest = nearest or {}
    g = decay_named("grocery", nearest.get("grocery"), cfg)
    ph = decay(nearest.get("pharmacy"), 300, 1000)
    cl = decay_named("clinic", nearest.get("clinic"), cfg)
    mall = decay(nearest.get("mall"), 800, 3000)
    sp = decay(nearest.get("sport"), 500, 2000)
    s = 1.0 + 3.0 * g + 1.5 * ph + 2.0 * cl + 1.5 * mall + 1.0 * sp
    return _clip(s)


def ecology_penalties(nearest=None, cfg=None):
    """Returns a list of (reason, penalty)."""
    nearest = nearest or {}
    out = []

    def add(label, pen):
        if pen >= 0.1:
            out.append((label, round(pen, 1)))

    add("industrial zone", 2.5 * decay_named("industrial", nearest.get("industrial"), cfg))
    add("power line", 2.5 * decay_named("powerline", nearest.get("powerline"), cfg))
    add("landfill/waste dump", 4.0 * decay_named("landfill", nearest.get("landfill"), cfg))
    add("waste processing facility", 2.5 * decay(nearest.get("waste"), 300, 2000))
    add("power plant", 2.0 * decay(nearest.get("power_plant"), 300, 1500))
    add("cemetery", 1.0 * decay(nearest.get("cemetery"), 100, 500))
    add("fuel station", 0.7 * decay(nearest.get("fuel"), 50, 150))
    add("substation", 0.7 * decay(nearest.get("substation"), 30, 100))
    road = nearest.get("major_road")
    if road is not None and road < 50:
        add("major road closer than 50 m", 1.5)
    elif road is not None and road < 150:
        add("major road closer than 150 m", 0.7)
    return out


def score_ecology(nearest=None, cfg=None):
    pens = ecology_penalties(nearest, cfg)
    s = 8.0 - sum(p for _, p in pens)
    green_bonus = max(decay_named("large_park", (nearest or {}).get("forest"), cfg),
                      decay_named("large_park", (nearest or {}).get("park"), cfg))
    s += 1.5 * green_bonus
    return _clip(s), pens
