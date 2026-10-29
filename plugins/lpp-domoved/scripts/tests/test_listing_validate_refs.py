import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import normalize_listing as nl  # noqa: E402
import refs  # noqa: E402
import validate  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
URL = "https://www.avito.ru/murino/kvartiry/2-k._kvartira_53_m_223_et._8368369095"


class NormalizeListingTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "avito_murino.txt"), encoding="utf-8") as f:
            self.text = f.read()

    def test_text_murino(self):
        r = nl.normalize(text=self.text, url=URL)
        o = r["object"]
        self.assertEqual(o["price"], 12100000)
        self.assertEqual((o["area_total"], o["area_kitchen"], o["rooms"]), (53, 12, 2))
        self.assertEqual((o["floor"], o["floors_total"], o["year_built"]), (2, 23, 2016))
        self.assertEqual(o["house_type"], "monolith")
        self.assertEqual(o["ceiling_m"], 2.8)
        self.assertEqual(o["type"], "secondary")
        self.assertIn("Петровский б-р, 11к1", o["address"])
        self.assertIn("обременение (залог или ипотека продавца)", o["description_flags"])
        self.assertIn("последняя смена собственника: 29 октября 2018", o["description_flags"])
        ids = {f["id"] for f in r["red_flags"]}
        self.assertEqual(ids, {"seller_mortgage_encumbrance", "listing_condition_contradiction"})
        self.assertEqual(r["meta"]["source"], "avito")
        self.assertEqual(r["status"], "ok")

    def test_extract_json(self):
        ex = {"url": URL, "site": "avito", "title": "2-к. квартира, 53 м², 2/23 эт.", "price": 12100000,
              "params": {"Общая площадь": "53 м²", "Этаж": "2 из 23", "Тип дома": "монолитный", "Год постройки": "2016"},
              "address": "Мурино, Петровский б-р, 11к1", "lat": "60.058457", "lon": 30.42443,
              "description": "Срочно! Окна во двор.", "rosreestr": "1 собственник Есть обременения: ипотека"}
        r = nl.normalize(extract=ex)
        o = r["object"]
        self.assertEqual((o["lat"], o["lon"]), (60.058457, 30.42443))
        self.assertEqual(o["floors_total"], 23)
        self.assertIn("окна во двор", o["description_flags"])
        self.assertIn("срочная или быстрая продажа", o["description_flags"])

    def test_gaps_and_types(self):
        r = nl.normalize(text="Продаётся дом 120 м² на участке 8 соток, ИЖС, газ. 9,5 млн руб")
        self.assertEqual(r["object"]["type"], "private_house")
        self.assertEqual(r["object"]["price"], 9500000)
        self.assertEqual(r["object"]["area_land_sotok"], 8)
        self.assertEqual(r["status"], "partial")
        self.assertTrue(r["meta"]["data_gaps"])
        self.assertEqual(nl.normalize(text="Панельный дом, 5/9 эт.")["object"]["house_type"], "panel")


class ValidateTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "sample_scored.json"), encoding="utf-8") as f:
            self.a = json.load(f)

    def test_sample_ok(self):
        errors, _, summary = validate.check(self.a)
        self.assertEqual(errors, [])
        self.assertIn("criteria with data", summary)

    def test_detects_problems(self):
        a = copy.deepcopy(self.a)
        del a["criteria"]["noise"]
        a["criteria"]["green"]["score"] = 12
        a["criteria"]["legal"] = {"score": 7, "confidence": "high", "evidence": [{"text": "x"}]}
        a["sources"].append({"title": "bad", "url": "javascript:alert(1)"})
        a["checklists"] = {}
        a["valuation"]["mortgage_eligible"] = True
        a["red_flags"].append({"id": "not_mortgage_eligible", "title": "t", "severity": "major"})
        errors, warns, _ = validate.check(a)
        text = "\n".join(errors)
        for needle in ("criterion noise is missing", "green: score outside", "legal: confidence high", "not http(s)",
                       "checklists are missing", "contradiction"):
            self.assertIn(needle, text)


class RefsTest(unittest.TestCase):
    def test_list_and_section(self):
        path = refs.resolve("criteria")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        titles = [t for _, _, t in refs.headings(text.splitlines())]
        self.assertTrue(any("noise" in t for t in titles))
        sec = refs.section(text, "noise")
        self.assertTrue(sec.startswith("#"))
        self.assertNotIn("building:", sec.splitlines()[-1])
        self.assertIsNone(refs.section(text, "нет такого раздела"))
        with self.assertRaises(FileNotFoundError):
            refs.resolve("nope")


class ExtractJsTest(unittest.TestCase):
    def test_single_expression(self):
        p = os.path.join(os.path.dirname(__file__), "..", "extract_listing.js")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        body = src[src.index("(() =>"):].strip()
        self.assertTrue(body.endswith("})()"))
        for forbidden in ("fetch(", "XMLHttpRequest", ".click(", "submit(", "localStorage.setItem"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()


class NegationAndDaysTest(unittest.TestCase):
    def test_no_encumbrance_when_negated(self):
        import normalize_listing as nl
        txt = "Квартира без обременений. Проверка в Росреестре: Не найдены ограничения и обременения"
        self.assertNotIn("обременение (залог или ипотека продавца)", nl.flags(txt))
        self.assertEqual(nl.red_flags(txt, "u"), [])
        self.assertIn("обременение (залог или ипотека продавца)", nl.flags("Есть обременения: ипотека"))

    def test_days_since(self):
        import datetime
        import normalize_listing as nl
        today = datetime.date(2026, 10, 29)
        self.assertEqual(nl.days_since("12 октября в 17:54", today), 17)
        self.assertEqual(nl.days_since("5 декабря", today), 328)
        self.assertEqual(nl.days_since("сегодня в 10:00", today), 0)
        self.assertIsNone(nl.days_since("", today))
