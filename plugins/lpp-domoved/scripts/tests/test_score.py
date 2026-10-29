import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import score  # noqa: E402

IDS = ["noise", "building", "legal", "transport", "ecology", "green",
       "kids", "amenities", "safety", "value_liquidity", "future"]


def make(scores=None, conf="high", flags=None, obj_type="secondary", **extra):
    scores = scores or {}
    criteria = {cid: {"score": scores.get(cid, 8), "confidence": conf} for cid in IDS}
    data = {"meta": {"input": "test"}, "object": {"type": obj_type},
            "criteria": criteria, "red_flags": flags or []}
    data.update(extra)
    return data


class ScoreTest(unittest.TestCase):
    def test_profiles_sum_to_one(self):
        cfg = score.load_config()
        for name, p in cfg["profiles"].items():
            self.assertAlmostEqual(sum(p["weights"].values()), 1.0, places=6, msg=name)
            self.assertEqual(set(p["weights"]), set(IDS), msg=name)

    def test_uniform_scores(self):
        res, _ = score.compute(make())
        self.assertEqual(res["total"], 8.0)
        self.assertEqual(res["verdict_code"], "buy_after_checks")
        self.assertEqual(res["confidence"], "high")
        self.assertEqual(res["coverage"], 1.0)

    def test_stop_flag_caps(self):
        flags = [{"id": "emergency", "title": "Аварийный дом", "severity": "stop"}]
        res, _ = score.compute(make({cid: 10 for cid in IDS}, flags=flags))
        self.assertEqual(res["total"], 5.4)
        self.assertTrue(res["capped"])
        self.assertEqual(res["verdict_code"], "avoid")

    def test_major_penalty_limited(self):
        flags = [{"title": "f%d" % i, "severity": "major"} for i in range(6)]
        res, _ = score.compute(make(flags=flags))
        self.assertEqual(res["penalty"], 1.0)
        self.assertEqual(res["total"], 7.0)
        self.assertEqual(res["penalty_per_flag"], 0.3)
        self.assertEqual(res["penalty_max"], 1.0)

    def test_missing_criteria_not_averaged(self):
        data = make({"safety": None})
        data["criteria"]["safety"]["confidence"] = "none"
        res, _ = score.compute(data)
        self.assertIn("safety", res["missing"])
        self.assertEqual(res["total"], 8.0)
        self.assertLess(res["coverage"], 1.0)

    def test_low_confidence_has_less_influence(self):
        hi = make({"noise": 2})
        lo = make({"noise": 2})
        lo["criteria"]["noise"]["confidence"] = "low"
        self.assertLess(score.compute(hi)[0]["total"], score.compute(lo)[0]["total"])

    def test_profile_changes_result(self):
        data = make({"noise": 2, "future": 10, "value_liquidity": 10})
        quiet = score.compute(data, "quiet")[0]["total"]
        invest = score.compute(data, "investment")[0]["total"]
        self.assertLess(quiet, invest)

    def test_low_coverage_marks_verdict(self):
        data = make()
        for cid in ["noise", "building", "legal", "transport", "ecology"]:
            data["criteria"][cid] = {"score": None, "confidence": "none"}
        res, _ = score.compute(data)
        self.assertEqual(res["confidence"], "low")
        self.assertIn("мало данных", res["verdict_title"])

    def test_auto_mortgage_flag(self):
        data = make(valuation={"mortgage_eligible": False})
        res, flags = score.compute(data)
        self.assertIn("not_mortgage_eligible", [f.get("id") for f in flags])
        self.assertEqual(res["penalty"], 0.3)

    def test_private_house_title(self):
        res, _ = score.compute(make(obj_type="private_house"))
        self.assertEqual(res["per_criterion"]["building"]["title"], "Дом и участок")

    def test_clamp_and_unknown_profile(self):
        res, _ = score.compute(make({"noise": 14}))
        self.assertEqual(res["per_criterion"]["noise"]["score"], 10.0)
        self.assertIn("warnings", res)
        with self.assertRaises(ValueError):
            score.compute(make(), "nope")


if __name__ == "__main__":
    unittest.main()
