import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import assemble  # noqa: E402


class AssembleTest(unittest.TestCase):
    def test_merge_and_ownership(self):
        frags = {
            "listing": {"object": {"type": "secondary", "price": 10000000, "address": "ул. Тестовая, 1"},
                        "sources": [{"title": "ЦИАН", "url": "https://cian.ru/1"}]},
            "house": {"criteria": {"noise": {"score": 5, "confidence": "medium", "evidence": [{"text": "a"}]}},
                      "red_flags": [{"id": "x", "title": "X", "severity": "minor"}],
                      "sources": [{"title": "ЦИАН", "url": "https://cian.ru/1"}, {"title": "РЖКХ", "url": "https://r/1"}]},
            "district": {"criteria": {"noise": {"score": 7, "confidence": "high", "evidence": [{"text": "b"}]},
                                      "green": {"score": 9, "confidence": "high"}},
                         "object": {"price": 1}},
            "geo": {"center": {"lat": 55.7, "lon": 37.6}},
        }
        a = assemble.assemble(frags, "https://cian.ru/1")
        self.assertEqual(a["object"]["price"], 10000000)  # the first value wins
        self.assertEqual(a["criteria"]["noise"]["score"], 7)  # higher confidence
        self.assertEqual(len(a["criteria"]["noise"]["evidence"]), 2)
        self.assertEqual(len(a["sources"]), 3)
        self.assertTrue(any("yandex.ru/maps/?pt=37.6,55.7" in x["url"] for x in a["sources"]))
        self.assertEqual(a["object"]["lat"], 55.7)
        self.assertTrue(a["meta"]["assemble_warnings"])
        self.assertNotIn("_from", a["criteria"]["noise"])

    def test_default_type(self):
        a = assemble.assemble({"house": {}}, "addr")
        self.assertEqual(a["object"]["type"], "secondary")
        self.assertTrue(a["meta"]["data_gaps"])


class GeoEvidenceTest(unittest.TestCase):
    def _geo(self):
        return {"center": {"lat": 60.05, "lon": 30.42}, "categories": {
            "metro": [{"name": "Девяткино", "distance_m": 1303, "osm": "node/1"}],
            "school": [{"name": "Школа № 2", "distance_m": 268, "osm": "way/2", "url": "https://www.openstreetmap.org/way/2"}],
            "park": [{"name": None, "distance_m": 549, "osm": "way/3"}],
            "landfill": [{"name": None, "distance_m": 9000, "osm": "way/4"}],
            "minor_road": [{"name": "улица Шувалова", "distance_m": 268, "osm": "way/5"}],
        }}

    def test_adds_osm_facts_with_links(self):
        frags = {"district": {"criteria": {c: {"score": 6, "confidence": "medium", "evidence": []}
                                           for c in ("transport", "kids", "green", "ecology")}},
                 "house": {"criteria": {"noise": {"score": 6, "confidence": "low"}}},
                 "geo": self._geo()}
        a = assemble.assemble(frags, "x", theme="dark")
        self.assertEqual(a["meta"]["theme"], "dark")
        t = a["criteria"]["transport"]["evidence"][0]
        self.assertEqual(t["text"], "Метро «Девяткино», 1,3 км")
        self.assertEqual(t["source_url"], "https://www.openstreetmap.org/node/1")
        self.assertEqual(t["source_title"], "Карта OpenStreetMap")
        self.assertEqual(a["criteria"]["green"]["evidence"][0]["text"], "Парк, 549 м")
        self.assertEqual(a["criteria"]["ecology"]["evidence"], [])  # landfill is far away
        self.assertIn("Шувалова", a["criteria"]["noise"]["evidence"][0]["text"])
        self.assertNotIn("amenities", a["criteria"])  # criteria are not invented
        # re-assembling does not duplicate
        assemble.add_geo_evidence(a, a["geo"])
        self.assertEqual(len(a["criteria"]["transport"]["evidence"]), 1)

    def test_reviews_site_fragment(self):
        frags = {"house": {}, "reviews_site": {"url": "https://www.avito.ru/catalog/houses/x/1/reviews",
                                               "site": "avito", "rating": 4.6, "count": 23, "reviews": [{"text": "t"}]}}
        a = assemble.assemble(frags, "x")
        self.assertEqual(a["reviews"]["site"]["count"], 23)
        self.assertNotIn("reviews", a["reviews"]["site"])
        frags["reviews_site"]["blocked"] = True
        self.assertNotIn("reviews", assemble.assemble(frags, "x"))

    def test_fmt_dist(self):
        self.assertEqual(assemble.fmt_dist(999), "999 м")
        self.assertEqual(assemble.fmt_dist(1250), "1,2 км")


if __name__ == "__main__":
    unittest.main()
