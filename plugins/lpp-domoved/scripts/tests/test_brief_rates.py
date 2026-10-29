import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import geo_brief  # noqa: E402
import market_rates  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


class GeoBriefTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "osm_sample.json"), encoding="utf-8") as f:
            self.geo = json.load(f)

    def test_size_and_keys(self):
        b = geo_brief.build(self.geo)
        self.assertLessEqual(len(geo_brief.dumps(b).encode("utf-8")), 2048)
        for k in ("center", "nearest", "top3", "noise_estimate", "suggested_scores", "partial", "errors_count"):
            self.assertIn(k, b)
        self.assertTrue(all(v is not None for v in b["nearest"].values()))
        self.assertTrue(all(len(v) <= 3 for v in b["top3"].values()))
        if "major_road" in b["top3"]:
            self.assertEqual(len(b["top3"]["major_road"][0]), 3)

    def test_partial_flag(self):
        g = dict(self.geo)
        g["notes"] = ["Major roads, railways and power lines failed to load: road noise not counted"]
        self.assertTrue(geo_brief.build(g)["partial"])
        g2 = dict(self.geo, notes=[], errors=["part 'geom' not received: timeout"])
        self.assertTrue(geo_brief.build(g2)["partial"])

    def test_oversized_is_trimmed(self):
        g = json.loads(json.dumps(self.geo))
        for c in geo_brief.TOP_CATS:
            g.setdefault("categories", {})[c] = [{"name": "Очень длинное название объекта номер %d для теста" % i,
                                                  "distance_m": i, "tags": {"highway": "primary"}} for i in range(5)]
        g["score_notes"] = {k: "x" * 300 for k in ("a", "b", "c")}
        self.assertLessEqual(len(geo_brief.dumps(geo_brief.build(g)).encode("utf-8")), 2048)


class MarketRatesTest(unittest.TestCase):
    def test_parse_moex(self):
        with open(os.path.join(FIX, "moex_zcyc.json"), encoding="utf-8") as f:
            ofz, d = market_rates.parse_moex(json.load(f))
        self.assertEqual(ofz, {"1": 14.04, "3": 15.46, "5": 16.07})
        self.assertEqual(d, "2026-10-29")

    def test_parse_cbr_page(self):
        html = "<table><tr><th>Дата</th><th>Ставка</th></tr><tr><td>24.10.2026</td><td>14,00</td></tr>" \
               "<tr><td>23.10.2026</td><td>15,00</td></tr></table>"
        self.assertEqual(market_rates.parse_cbr_page(html), (14.0, "2026-10-24"))

    def test_parse_cbr_soap(self):
        xml = "<KR><DT>2026-10-20T00:00:00+03:00</DT><Rate>15.00</Rate></KR>" \
              "<KR><DT>2026-10-24T00:00:00+03:00</DT><Rate>14.00</Rate></KR>"
        self.assertEqual(market_rates.parse_cbr_soap(xml), (14.0, "2026-10-24"))

    def test_collect_handles_failures(self):
        orig = market_rates.http
        market_rates.http = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("timed out"))
        try:
            res = market_rates.collect()
        finally:
            market_rates.http = orig
        self.assertIsNone(res["key_rate_pct"])
        self.assertIsNone(res["ofz_yield_pct"])
        self.assertTrue(any("Bank of Russia unavailable" in n for n in res["notes"]))


if __name__ == "__main__":
    unittest.main()
