import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import geo_scoring as gs  # noqa: E402
import osm_nearby as on  # noqa: E402


class TestDecay(unittest.TestCase):
    def test_linear(self):
        self.assertEqual(gs.decay(100, 400, 1200), 1.0)
        self.assertEqual(gs.decay(400, 400, 1200), 1.0)
        self.assertAlmostEqual(gs.decay(800, 400, 1200), 0.5)
        self.assertEqual(gs.decay(1200, 400, 1200), 0.0)
        self.assertEqual(gs.decay(None, 400, 1200), 0.0)

    def test_named_uses_config(self):
        full, zero = gs.decay_params("metro")
        self.assertLess(full, zero)
        self.assertEqual(gs.decay_named("metro", 50), 1.0)


class TestNoise(unittest.TestCase):
    def test_road_halving(self):
        self.assertEqual(gs.estimate_road_db("primary", 10), 72.0)
        self.assertEqual(gs.estimate_road_db("primary", 20), 69.0)
        self.assertEqual(gs.estimate_road_db("primary", 5), 72.0)  # does not grow closer than 10 m
        self.assertEqual(gs.estimate_road_db("motorway", 10 * 2 ** 20), gs.MIN_DB)
        self.assertIsNone(gs.estimate_road_db("residential", 10))

    def test_lanes(self):
        self.assertGreater(gs.estimate_road_db("trunk", 50, "8"), gs.estimate_road_db("trunk", 50))

    def test_combine(self):
        self.assertAlmostEqual(gs.combine_db([60, 60]), 63.0, places=0)
        self.assertEqual(gs.combine_db([70]), 70.0)
        self.assertIsNone(gs.combine_db([]))

    def test_aircraft(self):
        self.assertIsNone(gs.aircraft_db(8000))
        self.assertEqual(gs.aircraft_db(1000), 65.0)

    def test_discount(self):
        self.assertEqual(gs.noise_discount_pct(50), [0.0, 0.0])
        lo, hi = gs.noise_discount_pct(65)
        self.assertAlmostEqual(lo, 4.0)
        self.assertAlmostEqual(hi, 9.0)


class TestScores(unittest.TestCase):
    def test_noise_score_points(self):
        self.assertEqual(gs.score_noise_external(40), 10.0)
        self.assertEqual(gs.score_noise_external(55), 7.0)
        self.assertEqual(gs.score_noise_external(65), 4.0)
        self.assertEqual(gs.score_noise_external(80), 1.0)
        self.assertEqual(gs.score_noise_external(55, nightlife_nearest_m=30), 5.0)

    def test_transport(self):
        near = gs.score_transport(200, None, 8)
        far = gs.score_transport(3000, None, 1)
        self.assertEqual(near, 10.0)
        self.assertLess(far, 4)
        # a commuter train nearby also counts, but less than the metro
        self.assertLess(gs.score_transport(None, 200, 0), gs.score_transport(200, None, 0))

    def test_green(self):
        self.assertGreater(gs.score_green(100, 200, 300, 4), 9)
        self.assertLess(gs.score_green(None, None, None, 0), 3)

    def test_kids(self):
        self.assertGreater(gs.score_kids(200, 200, 4, 4), 9)
        self.assertLess(gs.score_kids(None, None, 0, 0), 2)

    def test_amenities(self):
        good = gs.score_amenities({"grocery": 100, "pharmacy": 100, "clinic": 300, "mall": 500, "sport": 300})
        self.assertEqual(good, 10.0)
        self.assertEqual(gs.score_amenities({}), 1.0)

    def test_ecology(self):
        clean, pens = gs.score_ecology({})
        self.assertEqual(clean, 8.0)
        self.assertEqual(pens, [])
        dirty, pens = gs.score_ecology({"industrial": 50, "powerline": 20, "landfill": 400, "major_road": 30})
        self.assertLess(dirty, 1.0)
        self.assertTrue(any("power line" in p[0] for p in pens))


class TestGeometry(unittest.TestCase):
    def test_inside_polygon(self):
        el = {"geometry": [{"lat": 55.0, "lon": 37.0}, {"lat": 55.0, "lon": 37.01},
                           {"lat": 55.01, "lon": 37.01}, {"lat": 55.01, "lon": 37.0}, {"lat": 55.0, "lon": 37.0}]}
        d, _ = on.geom_distance(el, 55.005, 37.005, area=True)
        self.assertEqual(d, 0.0)
        d2, _ = on.geom_distance(el, 55.005, 37.005, area=False)
        self.assertGreater(d2, 300)

    def test_line_distance(self):
        # horizontal line at latitude 55.0; point ~111 m to the north
        el = {"geometry": [{"lat": 55.0, "lon": 37.0}, {"lat": 55.0, "lon": 37.02}]}
        d, _ = on.geom_distance(el, 55.001, 37.01)
        self.assertAlmostEqual(d, 110.5, delta=2)

    def test_categorize(self):
        self.assertEqual(on.categorize({"railway": "station", "station": "subway"}), ["metro"])
        self.assertEqual(on.categorize({"railway": "station", "train": "yes"}), ["rail_station"])
        self.assertIn("major_road", on.categorize({"highway": "primary"}))
        self.assertEqual(on.categorize({"power": "minor_line"}), [])
        self.assertEqual(on.categorize({"landuse": "forest"}), ["forest"])


class TestFixture(unittest.TestCase):
    """Format check on a saved real osm_nearby output."""

    def test_fixture_shape(self):
        p = os.path.join(HERE, "fixtures", "osm_sample.json")
        if not os.path.exists(p):
            self.skipTest("no fixture")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        for k in ("center", "radius_m", "categories", "counts", "nearest", "noise_estimate",
                  "suggested_scores", "score_notes", "notes", "errors"):
            self.assertIn(k, d)
        for k in ("noise_external", "transport", "green", "kids", "amenities", "ecology"):
            self.assertTrue(0 <= d["suggested_scores"][k] <= 10)
        self.assertIsNotNone(d["nearest"]["metro"])


if __name__ == "__main__":
    unittest.main()
