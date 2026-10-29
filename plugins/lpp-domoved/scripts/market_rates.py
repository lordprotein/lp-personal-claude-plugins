#!/usr/bin/env python3
"""Market rates for the investment block: OFZ (ОФЗ) yield and the Bank of Russia (ЦБ) key rate.

Sources are official and open:
  - OFZ: MOEX ISS zero-coupon yield curve (zcyc.json), terms 1, 3, 5 years;
  - key rate: cbr.ru (page hd_base/KeyRate or the DailyInfo web service).
If the Bank of Russia is unavailable, key_rate_pct = null and notes contain a hint to find the rate with one search.
The result is cached for one day (kind rates).
ofz_source stays in Russian: it may be cited as a source in the report.

Usage: market_rates.py [--fresh]
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache  # noqa: E402

UA = "domoved/0.1 (claude-code plugin)"
TIMEOUT = 15
CBR_TIMEOUT = 8
MOEX_URL = "https://iss.moex.com/iss/engines/stock/zcyc.json?iss.only=yearyields&iss.meta=off"
CBR_PAGE = "https://www.cbr.ru/hd_base/KeyRate/"
CBR_SOAP = "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
CACHE_KEY = "rates"


def http(url, data=None, headers=None, timeout=TIMEOUT):
    """GET/POST with an honest User-Agent. If urllib fails on TLS (old LibreSSL), try curl."""
    hdrs = {"User-Agent": UA}
    hdrs.update(headers or {})
    try:
        req = urllib.request.Request(url, data=data, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as first:  # noqa: BLE001
        if not shutil.which("curl"):
            raise
        cmd = ["curl", "-s", "-f", "-m", str(timeout), "-A", UA]
        for k, v in hdrs.items():
            if k != "User-Agent":
                cmd += ["-H", "%s: %s" % (k, v)]
        if data is not None:
            cmd += ["--data-binary", "@-"]
        p = subprocess.run(cmd + [url], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout + 5)
        if p.returncode != 0:
            raise RuntimeError("%s; curl exit %s" % (first, p.returncode))
        return p.stdout.decode("utf-8", "replace")


def parse_moex(payload):
    data = payload["yearyields"]
    cols = data["columns"]
    i_date, i_per, i_val = cols.index("tradedate"), cols.index("period"), cols.index("value")
    out, date = {}, None
    for row in data["data"]:
        per = float(row[i_per])
        for want in (1, 3, 5):
            if abs(per - want) < 1e-6:
                out[str(want)] = round(float(row[i_val]), 2)
                date = row[i_date]
    if not out:
        raise ValueError("MOEX response has no 1/3/5 year terms")
    return out, date


def parse_cbr_page(html):
    """First table row on hd_base/KeyRate: date and rate, e.g. 24.10.2026 | 14,00."""
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*</td>\s*<td[^>]*>\s*([\d]+,[\d]+)", html)
    if not m:
        raise ValueError("key rate not found on the Bank of Russia page")
    d = datetime.datetime.strptime(m.group(1), "%d.%m.%Y").date().isoformat()
    return float(m.group(2).replace(",", ".")), d


def parse_cbr_soap(xml):
    rows = re.findall(r"<DT>([\d-]+)T[^<]*</DT>\s*<Rate>([\d.]+)</Rate>", xml)
    if not rows:
        raise ValueError("empty DailyInfo KeyRate response")
    rows.sort()
    d, r = rows[-1]
    return float(r), d


def fetch_key_rate(today):
    try:
        return parse_cbr_page(http(CBR_PAGE, timeout=CBR_TIMEOUT)) + (CBR_PAGE,)
    except Exception as e1:  # noqa: BLE001
        if "timed out" in str(e1) or "exit 28" in str(e1):
            # the Bank of Russia server does not respond: do not try the second address on the same host
            raise RuntimeError("cbr.ru does not respond")
        start = (today - datetime.timedelta(days=120)).isoformat()
        body = ('<?xml version="1.0" encoding="utf-8"?><soap12:Envelope '
                'xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body>'
                '<KeyRate xmlns="http://web.cbr.ru/"><fromDate>%s</fromDate><ToDate>%s</ToDate>'
                '</KeyRate></soap12:Body></soap12:Envelope>' % (start, today.isoformat())).encode("utf-8")
        try:
            xml = http(CBR_SOAP, data=body, headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                       timeout=CBR_TIMEOUT)
            return parse_cbr_soap(xml) + (CBR_SOAP + " (KeyRate)",)
        except Exception as e2:  # noqa: BLE001
            raise RuntimeError("page: %s; DailyInfo: %s" % (e1, e2))


def collect(today=None):
    today = today or datetime.date.today()
    res = {"date": today.isoformat(), "ofz_yield_pct": None, "ofz_source": None,
           "key_rate_pct": None, "key_rate_date": None, "key_rate_source": None, "notes": []}
    try:
        ofz, d = parse_moex(json.loads(http(MOEX_URL)))
        res["ofz_yield_pct"], res["ofz_source"] = ofz, "MOEX ISS, кривая бескупонной доходности, %s" % d
    except Exception as e:  # noqa: BLE001
        res["notes"].append("MOEX unavailable (%s): find the OFZ yield with one search" % str(e)[:120])
    try:
        rate, d, src = fetch_key_rate(today)
        res["key_rate_pct"], res["key_rate_date"], res["key_rate_source"] = rate, d, src
    except Exception as e:  # noqa: BLE001
        res["notes"].append("Bank of Russia unavailable (%s): find the key rate with one search" % str(e)[:120])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="OFZ yield (MOEX) and the Bank of Russia key rate, cached for one day")
    ap.add_argument("--fresh", action="store_true", help="skip the cache")
    a = ap.parse_args(argv)
    cp = None if a.fresh else cache.get("rates", CACHE_KEY)
    if cp:
        with open(cp, encoding="utf-8") as f:
            res = json.load(f)
        res.setdefault("notes", []).append("from cache")
    else:
        res = collect()
        # cache only a complete response, so Bank of Russia unavailability does not stick for a day
        if res["ofz_yield_pct"] and res["key_rate_pct"] is not None:
            cache.put("rates", CACHE_KEY, data=json.dumps(res, ensure_ascii=False))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if (res["ofz_yield_pct"] or res["key_rate_pct"] is not None) else 1


if __name__ == "__main__":
    sys.exit(main())
