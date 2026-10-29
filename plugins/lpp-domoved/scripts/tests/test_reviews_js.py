import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..")
NODE = shutil.which("node")

STUB = r"""
const fs = require('fs');
const cfg = JSON.parse(process.argv[process.argv.length - 1]);
global.location = { href: cfg.url, hostname: new URL(cfg.url).hostname };
global.URL = URL;
const mk = (l) => ({ innerText: l.text, textContent: l.text, getAttribute: (k) => k === 'href' ? l.href : null });
global.document = {
  title: cfg.title || '',
  body: { innerText: cfg.body || '' },
  querySelector: () => null,
  querySelectorAll: (sel) => (sel === 'a[href]' ? (cfg.links || []).map(mk) : []),
};
const code = fs.readFileSync(cfg.file, 'utf8');
process.stdout.write(eval(code));
"""


def run(file, **cfg):
    cfg["file"] = os.path.join(SCRIPTS, file)
    out = subprocess.check_output([NODE, "-e", STUB, json.dumps(cfg)], timeout=20)
    return json.loads(out.decode("utf-8"))


@unittest.skipUnless(NODE, "node is not installed")
class ReviewsJsTest(unittest.TestCase):
    def test_blocked_page(self):
        r = run("extract_reviews.js", url="https://www.avito.ru/catalog/houses/x/1/reviews",
                title="Доступ ограничен: проблема с IP", body="Пройти проверку")
        self.assertTrue(r["blocked"])
        self.assertEqual(r["reviews"], [])

    def test_text_fallback(self):
        body = ("О доме\n4,6 · 23 отзыва\n"
                "Анна\n12 марта 2025\n5 из 5\nДостоинства: тихий двор, хорошие соседи. Недостатки: один лифт на секцию\n"
                "Игорь\n3 февраля 2025\n3 из 5\nСлышимость между квартирами высокая, слышно разговоры соседей и ремонт\n"
                "Ольга\n20 января 2025\nУправляющая компания отвечает долго, но двор чистый и есть детские площадки\n")
        r = run("extract_reviews.js", url="https://www.avito.ru/catalog/houses/murino/x/236919/reviews", body=body)
        self.assertFalse(r["blocked"])
        self.assertEqual(r["site"], "avito")
        self.assertEqual(r["rating"], 4.6)
        self.assertEqual(r["count"], 23)
        self.assertEqual(len(r["reviews"]), 3)
        first = r["reviews"][0]
        self.assertEqual(first["date"], "12 марта 2025")
        self.assertEqual(first["rating"], 5)
        self.assertIn("тихий двор", first["pros"])
        self.assertIn("один лифт", first["cons"])
        self.assertIn("Слышимость", r["reviews"][1]["text"])
        self.assertLessEqual(len(json.dumps(r, ensure_ascii=False)), 4000)

    def test_find_link_prefers_reviews(self):
        links = [
            {"text": "Узнать больше о доме", "href": "/catalog/houses/murino/x/236919?context=abc"},
            {"text": "4,6 · 23 отзыва", "href": "/catalog/houses/murino/x/236919/reviews?context=zzz"},
        ]
        r = run("find_reviews_link.js", url="https://www.avito.ru/murino/kvartiry/1", links=links)
        self.assertEqual(r["href"], "https://www.avito.ru/catalog/houses/murino/x/236919/reviews")

    def test_find_link_from_house_page(self):
        links = [{"text": "О доме", "href": "/catalog/houses/murino/x/236919?context=abc"}]
        r = run("find_reviews_link.js", url="https://www.avito.ru/murino/kvartiry/1", links=links)
        self.assertEqual(r["href"], "https://www.avito.ru/catalog/houses/murino/x/236919/reviews")

    def test_find_link_none(self):
        r = run("find_reviews_link.js", url="https://www.cian.ru/sale/flat/1/", links=[{"text": "Купить", "href": "/buy"}])
        self.assertIsNone(r["href"])


if __name__ == "__main__":
    unittest.main()
