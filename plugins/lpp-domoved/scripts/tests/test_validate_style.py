import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import validate  # noqa: E402

IDS = validate.CRITERIA


def base():
    crit = {c: {"score": 7, "confidence": "low", "evidence": [{"text": "x", "source_url": "https://e.ru/" + c}]} for c in IDS}
    return {"criteria": crit, "checklists": {"viewing": ["v"]}, "object": {"type": "secondary"}}


class StyleTest(unittest.TestCase):
    def test_clean_has_no_style_warnings(self):
        a = base()
        a["criteria"]["noise"]["pros"] = [{"text": "Окна во двор", "url": "https://e.ru/1"}, "Тихий двор"]
        a["valuation"] = {"comment_points": ["Справедливая цена около 10,57 млн ₽", "199 342 ₽/м², переплата 14,5%"]}
        self.assertEqual(validate.check_style(a), [])

    def test_medium_without_links(self):
        a = base()
        a["criteria"]["green"] = {"score": 6, "confidence": "medium", "evidence": [{"text": "парк"}]}
        w = validate.check_style(a)
        self.assertTrue(any("green" in x and "not a single link" in x for x in w))

    def test_pros_without_urls_on_key_criteria(self):
        a = base()
        a["criteria"]["legal"]["pros"] = ["один собственник", "нет долгов", {"text": "ЕГРН", "url": "https://e.ru"}]
        w = validate.check_style(a)
        self.assertTrue(any(x.startswith("legal: 2 of 3") for x in w))
        a["criteria"]["kids"]["pros"] = ["школа рядом", "сад рядом"]  # not a key criterion
        self.assertFalse(any(x.startswith("kids:") for x in validate.check_style(a)))

    def test_jargon_and_numbers(self):
        a = base()
        a["valuation"] = {"comment": "все аналоги в пределах net 15%", "comment_points": ["цена 10.57 млн", "199,342 ₽/м²"]}
        a["criteria"]["transport"]["cons"] = ["далеко rail_station"]
        w = "\n".join(validate.check_style(a))
        self.assertIn("«net»", w)
        self.assertIn("10.57 млн", w)
        self.assertIn("199,342 ₽", w)
        self.assertIn("rail_station", w)

    def test_check_includes_style(self):
        a = base()
        a["criteria"]["noise"]["summary"] = "по geo_brief тихо"
        errors, warns, _ = validate.check(a)
        self.assertEqual(errors, [])
        self.assertTrue(any("geo_brief" in x for x in warns))


    def test_style_only_cli(self):
        import json
        import tempfile
        frag = {"criteria": {"value_liquidity": {"score": 3, "confidence": "medium", "summary": "переплата 14.5%"}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(frag, f, ensure_ascii=False)
        self.assertEqual(validate.main(["--style-only", f.name]), 0)
        os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
