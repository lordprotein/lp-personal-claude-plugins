#!/usr/bin/env python3
"""Listing → listing.json without an LLM.

Takes the compact extract of extract_listing.js (--json) or listing text
pasted by the user (--text). Uses regexes to pull price, areas, floor,
year, house type, ceilings, bathroom, renovation, address, coordinates, flags from the description.
Whatever is not recognized goes to meta.data_gaps: the agent fills it in.

Usage:
  normalize_listing.py --json extract.json [--url URL] [--out listing.json]
  normalize_listing.py --text listing.txt  [--url URL] [--out listing.json]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_input  # noqa: E402

NUM = r"(\d+(?:[.,]\d+)?)"
HOUSE_TYPES = [
    ("монолитно-кирпич", "monolith_brick"), ("кирпично-монолит", "monolith_brick"),
    ("монолит", "monolith"), ("панел", "panel"), ("кирпич", "brick"),
    ("блоч", "block"), ("деревян", "wood"), ("сталин", "brick"),
]
FLAG_RULES = [
    (r"перепланировк", "перепланировка"),
    (r"\bдол[яи]\b|продаж[аи] дол", "продаётся доля"),
    (r"апартамент", "апартаменты"),
    (r"наследств", "наследство"),
    (r"материнск|маткапитал|мат\.\s*капитал", "упоминается материнский капитал"),
    (r"срочн|быстрая продажа", "срочная или быстрая продажа"),
    (r"обременени|залог|в ипотеке", "обременение (залог или ипотека продавца)"),
    (r"только наличн|наличный расч", "только наличные"),
    (r"доверенност", "продажа по доверенности"),
    (r"окна (?:выходят )?во двор|окна во двор", "окна во двор"),
    (r"окна (?:выходят )?на (?:дорог|улиц|проспект|шоссе)", "окна на дорогу"),
    (r"газов(?:ая|ой) плит|\bгаз\b", "газ в доме"),
    (r"деревянн\w* перекрыт", "деревянные перекрытия"),
    (r"менее (?:3|тр[её]х) лет|меньше (?:3|тр[её]х) лет", "собственник менее 3 лет"),
    (r"альтернатив", "альтернативная сделка"),
]
NEEDS_REPAIR = re.compile(r"требует ремонта|без ремонта|под ремонт", re.I)
GOOD_REPAIR = re.compile(r"ремонт\w*[^.\n]{0,60}(?:хорош|отличн|свеж|евро|дизайн)", re.I)


def _f(x):
    return float(x.replace(",", ".").replace(" ", "").replace(" ", ""))


def _num(x):
    v = _f(x)
    return int(v) if v.is_integer() else v


def _search(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m


def parse_price(text):
    m = _search(r"(\d{1,3}(?:[   ]\d{3}){1,3})\s*(?:₽|руб)", text)
    if m:
        return int(re.sub(r"\D", "", m.group(1)))
    m = _search(r"(\d+(?:[.,]\d+)?)\s*млн\.?\s*(?:₽|руб)", text)
    if m:
        return int(round(_f(m.group(1)) * 1000000))
    return None


def parse_fields(text, params=None):
    params = params or {}
    joined = text + "\n" + "\n".join("%s: %s" % (k, v) for k, v in params.items())
    t = joined.replace(" ", " ")
    o = {}

    def grab(key, *patterns, conv=_num):
        for p in patterns:
            m = _search(p, t)
            if m:
                try:
                    o[key] = conv(m.group(1))
                    return
                except (ValueError, IndexError):
                    continue

    grab("area_total", r"общая площадь[:\s]*" + NUM, r"квартира,\s*" + NUM + r"\s*м²", r"\b" + NUM + r"\s*м²,\s*\d+/\d+\s*эт")
    grab("area_kitchen", r"(?:площадь кухни|кухня)[:\s]*" + NUM + r"\s*м")
    grab("area_living", r"жилая площадь[:\s]*" + NUM)
    grab("rooms", r"количество комнат[:\s]*(\d+)", r"(\d+)-к(?:\.|омн)")
    if _search(r"студи", t) and "rooms" not in o:
        o["rooms"] = "студия"
    m = _search(r"этаж[:\s]*(\d+)\s*из\s*(\d+)", t) or _search(r"(\d+)\s*/\s*(\d+)\s*эт", t)
    if m:
        o["floor"], o["floors_total"] = int(m.group(1)), int(m.group(2))
    else:
        grab("floors_total", r"этажей в доме[:\s]*(\d+)")
    grab("year_built", r"год (?:постройки|сдачи)[:\s]*(\d{4})", r"(?:построен|сдан)\w*\s+в\s+(\d{4})", conv=int)
    grab("ceiling_m", r"(?:высота потолков|потолки)[:\s]*" + NUM)
    m = _search(r"тип дома[:\s]*([а-яё -]+)", t)
    src = m.group(1) if m else t
    for needle, code in HOUSE_TYPES:
        if needle in src.lower():
            o["house_type"] = code
            break
    m = _search(r"санузел[:\s]*([а-яё, ]+)", t)
    if m:
        o["bathroom"] = m.group(1).strip().split("\n")[0][:40]
    m = _search(r"ремонт[:\s]*([а-яё ]+)", t)
    if m and len(m.group(1).strip()) > 2:
        o["condition"] = m.group(1).strip()[:60]
    grab("area_land_sotok", r"площадь участка[:\s]*" + NUM + r"\s*сот", r"участ\w*\s*" + NUM + r"\s*сот")
    return o


def detect_type(url, text):
    hint = None
    if url:
        try:
            hint = parse_input.parse_url(url).get("object_type_hint")
        except Exception:  # noqa: BLE001
            hint = None
    low = text.lower()
    if hint:
        return hint
    if re.search(r"\bдом\b.*\bучаст|ижс|коттедж|таунхаус", low):
        return "private_house"
    if re.search(r"новостройк|сдача в \d|дду|переуступк|эскроу", low):
        return "new_build"
    return "secondary"


NEGATED = re.compile(r"без\s+обременени\w*|не\s+найден\w*\s+(?:ограничени\w*\s+и\s+)?обременени\w*|"
                     r"обременени\w*\s+(?:нет|отсутству\w*)|нет\s+обременени\w*|без\s+залог\w*")


def _strip_negated(low):
    """Remove phrases like «без обременений», «не найдены ограничения и обременения»."""
    return NEGATED.sub(" ", low)


MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7,
          "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}


def days_since(published, today=None):
    """«12 октября в 17:54» or «12 октября 2025» → number of days since publication."""
    import datetime as _dt
    today = today or _dt.date.today()
    m = re.search(r"(\d{1,2})\s+(%s)(?:\s+(\d{4}))?" % "|".join(MONTHS), (published or "").lower())
    if not m:
        if re.search(r"сегодня", (published or "").lower()):
            return 0
        if re.search(r"вчера", (published or "").lower()):
            return 1
        return None
    day, month = int(m.group(1)), MONTHS[m.group(2)]
    year = int(m.group(3)) if m.group(3) else today.year
    try:
        d = _dt.date(year, month, day)
    except ValueError:
        return None
    if d > today and not m.group(3):
        d = _dt.date(year - 1, month, day)
    return (today - d).days


def flags(text):
    low = _strip_negated(text.lower())
    out = []
    for pat, label in FLAG_RULES:
        if re.search(pat, low) and label not in out:
            out.append(label)
    return out


def red_flags(text, url):
    rf = []
    low = _strip_negated(text.lower())
    if re.search(r"обременени\w*[:\s]*(?:есть|ипотек|залог)|есть обременения", low):
        rf.append({"id": "seller_mortgage_encumbrance", "title": "Квартира в залоге (ипотека продавца)",
                   "severity": "minor", "criterion": "legal",
                   "detail": "Сделку проводить через банк продавца: погашение долга, снятие обременения, безопасные расчёты.",
                   "source_url": url})
    if NEEDS_REPAIR.search(text) and GOOD_REPAIR.search(text):
        rf.append({"id": "listing_condition_contradiction", "title": "Противоречие в описании ремонта",
                   "severity": "minor", "criterion": "building",
                   "detail": "Где-то указано, что нужен ремонт, а где-то что ремонт хороший. Проверить на просмотре и учесть в торге.",
                   "source_url": url})
    return rf


EXPECTED = ["price", "area_total", "rooms", "floor", "floors_total", "year_built", "house_type", "address"]


def normalize(extract=None, text=None, url=None):
    extract = extract or {}
    url = url or extract.get("url")
    params = extract.get("params") or {}
    parts = [extract.get("title") or "", text or "", extract.get("description") or "",
             extract.get("rosreestr") or ""]
    full = "\n".join(p for p in parts if p)
    obj = parse_fields(full, params)
    price = extract.get("price") if isinstance(extract.get("price"), (int, float)) else None
    obj["price"] = price or parse_price(full)
    addr = extract.get("address")
    if not addr:
        m = _search(r"(?:адрес|расположение)[:\s]*([^\n]{8,160})", full)
        addr = m.group(1).strip() if m else None
    if addr:
        obj["address"] = addr
    for k in ("lat", "lon"):
        v = extract.get(k)
        try:
            if v is not None:
                obj[k] = float(v)
        except (TypeError, ValueError):
            pass
    if extract.get("title"):
        obj["title"] = extract["title"]
    if url:
        obj["listing_url"] = url
    if extract.get("published"):
        obj["listing_published"] = extract["published"]
        dom = days_since(extract["published"])
        if dom is not None:
            obj["days_on_market"] = dom
    obj["type"] = detect_type(url, full)
    obj["description_flags"] = flags(full)
    m = _search(r"смена собственника[:\s]*([0-9]{1,2}\s+[а-я]+\s+\d{4}|\d{2}\.\d{2}\.\d{4})", full)
    if m:
        obj["description_flags"].append("последняя смена собственника: %s" % m.group(1))
    m = _search(r"(\d+)\s+собственник", full)
    if m:
        obj["description_flags"].append("собственников по данным площадки: %s" % m.group(1))
    if extract.get("house_rating"):
        obj["description_flags"].append("рейтинг дома на площадке: %s" % extract["house_rating"])
    obj = {k: v for k, v in obj.items() if v not in (None, "", [])}
    site = extract.get("site")
    if not site and url:
        try:
            site = parse_input.parse_url(url).get("source")
        except Exception:  # noqa: BLE001
            site = None
    gaps = [k for k in EXPECTED if k not in obj]
    sources = [{"title": "Объявление" + (" (%s)" % site if site else ""), "url": url}] if url else []
    return {
        "status": "ok" if not gaps else "partial",
        "object": obj,
        "red_flags": red_flags(full, url),
        "sources": sources,
        "meta": {"source": site or "other_url", "data_gaps": ["не распознано: " + ", ".join(gaps)] if gaps else []},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Listing extract or text → listing.json")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--json", help="JSON from extract_listing.js")
    g.add_argument("--text", help="text file with the listing ('-' for stdin)")
    ap.add_argument("--url")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        if a.json:
            with open(a.json, encoding="utf-8") as f:
                raw = f.read().strip()
            data = json.loads(raw)
            if isinstance(data, str):  # javascript_tool returned a JSON string
                data = json.loads(data)
            res = normalize(extract=data, url=a.url)
        else:
            txt = sys.stdin.read() if a.text == "-" else open(a.text, encoding="utf-8").read()
            res = normalize(text=txt, url=a.url)
    except (OSError, ValueError) as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1
    out = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
        print("listing: %s, status %s, gaps: %s" % (a.out, res["status"], "; ".join(res["meta"]["data_gaps"]) or "none"))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
