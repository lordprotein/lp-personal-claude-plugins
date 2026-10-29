import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import geo_brief  # noqa: E402
import osm_nearby  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "osm_sample.json")


class OsmUrlTest(unittest.TestCase):
    def test_items_have_osm_url_and_russian_road_names(self):
        data = {"elements": [
            {"type": "node", "id": 101, "lat": 60.0585, "lon": 30.4300,
             "tags": {"railway": "station", "station": "subway", "name": "Девяткино"}},
            {"type": "way", "id": 202, "geometry": [{"lat": 60.0590, "lon": 30.4240}, {"lat": 60.0590, "lon": 30.4260}],
             "tags": {"highway": "primary"}},
        ]}
        res = osm_nearby.process(data, 60.058457, 30.42443, 1500)
        cats = res[0] if isinstance(res, tuple) else res.get("categories", res)
        metro = cats["metro"][0]
        self.assertEqual(metro["url"], "https://www.openstreetmap.org/node/101")
        roads = cats.get("major_road") or []
        self.assertTrue(roads)
        self.assertEqual(roads[0]["url"], "https://www.openstreetmap.org/way/202")
        self.assertEqual(roads[0]["name"], "Главная дорога")

    def test_brief_has_no_urls_and_fits(self):
        with open(FIX, encoding="utf-8") as f:
            geo = json.load(f)
        for items in geo["categories"].values():
            for it in items:
                it["url"] = "https://www.openstreetmap.org/" + it.get("osm", "node/1")
        b = json.dumps(geo_brief.build(geo), ensure_ascii=False)
        self.assertNotIn("openstreetmap.org", b)
        self.assertLessEqual(len(b.encode("utf-8")), 2048)


if __name__ == "__main__":
    unittest.main()
