import contextlib
import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import render_report as rr  # noqa: E402

SAMPLE = os.path.join(HERE, "fixtures", "sample_scored.json")
BROWSER = rr.find_browser()


def load_sample():
    with open(SAMPLE, encoding="utf-8") as fh:
        return json.load(fh)


def extract_data(html):
    tag = '<script type="application/json" id="data">'
    start = html.index(tag) + len(tag)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


@contextlib.contextmanager
def fake_printer():
    """Fakes printing: writes a small PDF instead of Chrome and remembers the HTML."""
    seen = []
    orig = rr.make_pdf

    def fake(html_path, pdf_path, browser=None):
        with open(html_path, encoding="utf-8") as fh:
            seen.append(fh.read())
        with open(pdf_path, "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
        return pdf_path

    rr.make_pdf = fake
    try:
        yield seen
    finally:
        rr.make_pdf = orig


@contextlib.contextmanager
def domoved_home(path):
    old = os.environ.get("DOMOVED_HOME")
    os.environ["DOMOVED_HOME"] = path
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("DOMOVED_HOME", None)
        else:
            os.environ["DOMOVED_HOME"] = old


def run_main(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = rr.main(args)
    return rc, out.getvalue(), err.getvalue()


class RenderHtmlTest(unittest.TestCase):
    def test_embeds_data_and_title(self):
        html = rr.render_html(load_sample())
        self.assertNotIn(rr.PLACEHOLDER, html)
        self.assertIn("<title>Домовед. Москва, ул. Перерва, 52. 6,6 из 10. 29.10.2026</title>", html)
        self.assertEqual(extract_data(html)["score"]["total"], 6.6)

    def test_script_breakout_is_escaped(self):
        data = load_sample()
        data["object"]["title"] = "</script><script>alert(1)</script>"
        html = rr.render_html(data)
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertEqual(extract_data(html)["object"]["title"], "</script><script>alert(1)</script>")

    def test_minimal_data_renders(self):
        html = rr.render_html({"meta": {"input": "x"}, "object": {"type": "secondary"}, "criteria": {}})
        self.assertNotIn(rr.PLACEHOLDER, html)

    def test_theme(self):
        d = load_sample()
        self.assertIn('data-theme="light"', rr.render_html(d))
        self.assertIn('data-theme="dark"', rr.render_html(d, theme="dark"))
        d.setdefault("meta", {})["theme"] = "dark"
        self.assertIn('data-theme="dark"', rr.render_html(d))
        self.assertIn('data-theme="light"', rr.render_html(d, theme="light"))  # the flag overrides meta
        self.assertEqual(rr.resolve_theme({}, "nope"), "light")

    def test_interactive_parts_present(self):
        html = rr.render_html(load_sample())
        for part in ('id="pdfBtn"', 'id="themeBtn"', 'id="navlinks"', '"details"', 'type: "checkbox"', "localStorage", "window.print()"):
            self.assertIn(part, html)
        # localStorage only inside try
        for m in re.finditer(r"localStorage\.", html):
            self.assertIn("try", html[max(0, m.start() - 60):m.start()])
        self.assertNotIn("\u2014", html)

    def test_verdict_summary_and_fact_dates(self):
        html = rr.render_html(load_sample())
        for part in ("verdict-sum", "sum-list", "Как посчитан балл", "Как считается итог", "VERDICT_TEXT", "function factDate", "fdate-old", "dateLegend()"):
            self.assertIn(part, html)

    def test_pros_cons_colors_in_every_theme(self):
        with open(rr.TEMPLATE, encoding="utf-8") as fh:
            tpl = fh.read()
        css = tpl[:tpl.index("</style>")]
        # light, two dark blocks and print
        self.assertEqual(css.count("--good-text:"), 4)
        self.assertEqual(css.count("--bad-text:"), 4)
        self.assertIn(".pc.good h3, .pc.good h4", css)
        self.assertIn(".pc.bad h3, .pc.bad h4", css)

    def test_print_css_keeps_dark_theme(self):
        with open(rr.TEMPLATE, encoding="utf-8") as fh:
            tpl = fh.read()
        css = tpl[tpl.index("@media print"):tpl.index("</style>")]
        light = re.search(r"([^{}]+)\{\s*--bg: #ffffff", css)
        self.assertIsNotNone(light)
        sel = light.group(1)
        self.assertIn(':root:not([data-theme="dark"])', sel)
        self.assertNotIn(':root[data-theme="dark"]', sel)
        self.assertNotRegex(sel, r"(^|,)\s*:root\s*(,|$)")
        self.assertIn("print-color-adjust: exact", css)
        self.assertRegex(css, r"html,\s*body,\s*\*\s*\{[^}]*print-color-adjust: exact")


class OutputTest(unittest.TestCase):
    def test_default_writes_only_html(self):
        with tempfile.TemporaryDirectory() as tmp, domoved_home(tmp), fake_printer() as seen:
            rc, out, _ = run_main([SAMPLE])
            self.assertEqual(rc, 0)
            reports = os.path.join(tmp, "reports")
            files = os.listdir(reports)
            self.assertEqual(files, ["Домовед. Москва, ул. Перерва, 52. 6,6 из 10. 29.10.2026.html"])
            self.assertEqual(out.strip(), os.path.join(reports, files[0]))
            self.assertEqual(seen, [])  # PDF is not printed by default
            run_main([SAMPLE])
            self.assertIn("Домовед. Москва, ул. Перерва, 52. 6,6 из 10. 29.10.2026 (2).html", os.listdir(reports))
            self.assertFalse([f for f in os.listdir(reports) if f.endswith(".pdf")])

    def test_pdf_flag_adds_pdf_in_theme(self):
        with tempfile.TemporaryDirectory() as tmp, domoved_home(tmp), fake_printer() as seen:
            rc, out, _ = run_main([SAMPLE, "--pdf", "--theme", "dark"])
            self.assertEqual(rc, 0)
            files = sorted(os.listdir(os.path.join(tmp, "reports")))
            self.assertEqual([os.path.splitext(f)[1] for f in files], [".html", ".pdf"])
            self.assertEqual(os.path.splitext(files[0])[0], os.path.splitext(files[1])[0])
            self.assertIn('data-theme="dark"', seen[0])

    def test_out_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, _ = run_main([SAMPLE, "--out", os.path.join(tmp, "x.html")])
            self.assertEqual(rc, 0)
            self.assertEqual(os.listdir(tmp), ["x.html"])

    def test_markdown(self):
        with tempfile.TemporaryDirectory() as tmp, fake_printer():
            out = os.path.join(tmp, "r.html")
            rc, md, _ = run_main([SAMPLE, "--out", out, "--markdown", "--pdf"])
            self.assertEqual(rc, 0)
            self.assertIn("6,6 / 10", md)
            self.assertIn(out, md)
            self.assertIn(out[:-5] + ".pdf", md)

    def test_no_browser_with_pdf(self):
        orig = rr.find_browser
        rr.find_browser = lambda: None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "r.html")
                rc, _, err = run_main([SAMPLE, "--out", out, "--pdf"])
                self.assertEqual(rc, 2)
                self.assertEqual(os.listdir(tmp), ["r.html"])
                self.assertIn("DOMOVED_CHROME", err)
                self.assertIn("Сохранить PDF", err)
        finally:
            rr.find_browser = orig

    def test_default_out_path(self):
        with tempfile.TemporaryDirectory() as tmp, domoved_home(tmp):
            p = rr.default_out_path(load_sample())
            self.assertTrue(p.startswith(os.path.join(tmp, "reports")))
            self.assertTrue(p.endswith("Домовед. Москва, ул. Перерва, 52. 6,6 из 10. 29.10.2026.html"))
            open(p, "w").close()
            folder = os.path.dirname(p)
            p2 = rr.default_out_path(load_sample(), folder)
            self.assertTrue(p2.endswith("29.10.2026 (2).html"))
            open(p2[:-5] + ".pdf", "w").close()  # a PDF with the same name also takes the name
            self.assertTrue(rr.default_out_path(load_sample(), folder).endswith("29.10.2026 (3).html"))

    def test_slugify(self):
        self.assertEqual(rr.slugify("Санкт-Петербург, Невский пр., 1"), "sankt-peterburg-nevskiy-pr-1")
        self.assertEqual(rr.slugify(""), "object")


class NameTest(unittest.TestCase):
    def test_readable_name(self):
        d = load_sample()
        self.assertEqual(rr.readable_name(d), "Домовед. Москва, ул. Перерва, 52. 6,6 из 10. 29.10.2026")
        d["object"]["address"] = "109012, Россия, Москва, Профсоюзная ул., 140к2"
        d["score"]["total"] = 7.25
        self.assertEqual(rr.readable_name(d), "Домовед. Москва, Профсоюзная ул., 140к2. 7,2 из 10. 29.10.2026")

    def test_region_parts_dropped(self):
        d = load_sample()
        d["object"]["address"] = "Ленинградская обл., Всеволожский р-н, Муринское городское поселение, Мурино, Петровский б-р, 11к1"
        self.assertTrue(rr.readable_name(d).startswith("Домовед. Мурино, Петровский б-р, 11к1. "))

    def test_readable_name_without_score(self):
        d = {"meta": {"generated_at": "2026-01-05T10:00:00"}, "object": {"title": "Дом в СНТ"}}
        self.assertEqual(rr.readable_name(d), "Домовед. Дом в СНТ. 05.01.2026")

    def test_compare_name(self):
        d = {"compare": [{}, {}, {}], "compare_meta": {"generated_at": "2026-10-29T12:00:00"}}
        self.assertEqual(rr.readable_name(d), "Домовед. Сравнение 3 объектов. 29.10.2026")

    def test_sanitize(self):
        self.assertEqual(rr.sanitize_filename('a/b\\c:d*e?f"g<h>i|j\nk   l'), "a b c d e f g h i j k l")
        self.assertNotIn("\u2014", rr.sanitize_filename("а \u2014 б"))
        out = rr.sanitize_filename("слово " * 60)
        self.assertLessEqual(len(out), rr.MAX_NAME_LEN)
        self.assertTrue(out.endswith("слово"))

    def test_long_address_keeps_score_and_date(self):
        d = load_sample()
        d["object"]["address"] = "Москва, " + "очень длинная улица " * 20 + "1"
        name = rr.readable_name(d)
        self.assertLessEqual(len(name), rr.MAX_NAME_LEN)
        self.assertTrue(name.endswith("6,6 из 10. 29.10.2026"))


class CompareTest(unittest.TestCase):
    def make_items(self, tmp):
        a = load_sample()
        b = copy.deepcopy(a)
        b["object"]["address"] = "Москва, ул. Тихая, 3"
        b["score"]["total"] = 8.1
        b["criteria"]["noise"]["score"] = 8.0
        c = copy.deepcopy(a)
        c["object"]["address"] = "Москва, ул. Аварийная, 1"
        c["score"]["total"] = 9.0
        c["red_flags"].append({"title": "Дом признан аварийным", "severity": "stop"})
        paths = []
        for i, d in enumerate([a, b, c]):
            p = os.path.join(tmp, "a%d.json" % i)
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False)
            paths.append(p)
        return paths, [a, b, c]

    def test_winner_skips_stop_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, items = self.make_items(tmp)
            self.assertEqual(rr.pick_winner(items)["object"]["address"], "Москва, ул. Тихая, 3")

    def test_compare_cli(self):
        with tempfile.TemporaryDirectory() as tmp, fake_printer():
            paths, _ = self.make_items(tmp)
            out_dir = os.path.join(tmp, "out")
            out = os.path.join(out_dir, "cmp.html")
            rc, md, _ = run_main(["--compare"] + paths + ["--out", out, "--markdown", "--pdf"])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                html = fh.read()
            data = extract_data(html)
            self.assertEqual(len(data["compare"]), 3)
            self.assertRegex(html, r"<title>Домовед\. Сравнение 3 объектов\. \d\d\.\d\d\.\d{4}</title>")
            for item in data["compare"]:
                self.assertTrue(os.path.exists(os.path.join(out_dir, item["report_href"])))
            self.assertTrue(os.path.exists(os.path.join(out_dir, "cmp.pdf")))
            self.assertIn("Лучший вариант:** Москва, ул. Тихая, 3", md)
            self.assertIn("Дом признан аварийным", md)
            self.assertIn("**8,0**", md)

    def test_compare_needs_two(self):
        with self.assertRaises(SystemExit):
            run_main(["--compare", SAMPLE])


def dump_dom(data, theme=None):
    """Renders the template in headless Chrome and returns the DOM after JS."""
    with tempfile.TemporaryDirectory(prefix="domoved-test-") as tmp:
        html = os.path.join(tmp, "r.html")
        with open(html, "w", encoding="utf-8") as fh:
            fh.write(rr.render_html(data, theme=theme))
        with tempfile.TemporaryDirectory(prefix="domoved-chrome-") as prof:
            res = subprocess.run([BROWSER, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + prof,
                                  "--virtual-time-budget=3000", "--dump-dom", rr._file_url(html)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        return res.stdout.decode("utf-8", "replace")


def section(dom, sid):
    m = re.search(r'<section id="%s">(.*?)</section>' % sid, dom, re.S)
    return m.group(1) if m else ""


def text_of(fragment):
    # number highlights are inline: drop them without adding a space
    fragment = re.sub(r'<span class="n">(.*?)</span>', r"\1", fragment)
    return re.sub(r"<[^>]+>", " ", fragment)


@unittest.skipUnless(BROWSER, "Chromium browser not found")
class DomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = load_sample()
        geo = d.setdefault("geo", {})
        cats = geo.setdefault("categories", {})
        cats["rail_station"] = [{"name": "Девяткино", "distance_m": 1348, "osm": "node/1"}]
        cats["stop_bus_tram"] = [{"name": "Петровский бульвар", "distance_m": 101}, {"name": "Петровский бульвар", "distance_m": 148},
                                 {"name": "Петровский бульвар", "distance_m": 230}, {"name": "Петровский бульвар", "distance_m": 260}]
        cats["university"] = []
        cats["playground"] = [{"name": None, "distance_m": 109}]
        geo["noise_estimate"] = {"est_db_combined": 49.8, "sources": [{"kind": "road_tertiary", "name": "улица Шувалова", "distance_m": 268, "est_db": 49.8}],
                                 "price_discount_pct": [0.0, 0.0]}
        geo["errors"] = ["overpass: 504"]
        for k in ("major_road", "railway_line", "tram_line", "powerline"):
            cats.pop(k, None)
        d["valuation"].pop("comment_points", None)
        d["valuation"]["comment"] = ("Сравнительный подход по 7 аналогам у Девяткино. Поправки: торг 6% (СПб, конфиг), этаж и ремонт. "
                                     "Взвешенная цена 199,342 ₽/м², диапазон 9.62–11,41 млн. Запрос выше на 14,5%. "
                                     "Экспозиция 2 дня, медиана района 185 882 ₽/м². Ставка ипотеки снижает спрос.")
        d["investment"]["comment_points"] = ["Аренда около 46 тыс. ₽", "Чистая доходность 3,3%"]
        d["criteria"]["noise"]["pros"] = [{"text": "Окна во двор", "url": "https://example.org/proof"}, "Монолит"]
        d["criteria"]["noise"]["cons"] = [{"text": "Слышно соседей", "url": "https://example.org/r1", "date": "2025-06"}]
        d["criteria"]["building"]["cons"] = [{"text": "Грязно в холлах", "url": "https://example.org/r2", "date": "2021"}]
        cls.dom = dump_dom(d, theme="dark")

    def test_theme_applied(self):
        self.assertIn('data-theme="dark"', self.dom)

    def test_date_legend_once(self):
        self.assertEqual(self.dom.count('class="fdate-legend"'), 1)

    def test_numbers_highlighted(self):
        self.assertIn('<span class="n">199 342 ₽/м²</span>', section(self.dom, "price"))

    def test_score_calc_is_one_line(self):
        summary = section(self.dom, "summary")
        self.assertIn("calc-line", summary)
        self.assertNotIn("Покрытие данных</b>", summary)
        self.assertIn("Как считается итог", section(self.dom, "criteria"))

    def test_price_why_block(self):
        t = text_of(section(self.dom, "price"))
        self.assertIn("Продавец просит за м²", t)
        self.assertIn("Обычно в районе за м²", t)

    def test_env_groups_human_labels(self):
        geo = text_of(section(self.dom, "geo"))
        for latin in ("rail_station", "stop_bus_tram", "university", "playground", "без названия"):
            self.assertNotIn(latin, geo)
        for ru in ("Транспорт", "Ж/д станции и МЦД", "Остановки", "Детская площадка", "Что может мешать"):
            self.assertIn(ru, geo)
        self.assertIn("4 остановки", geo)
        self.assertNotIn("Вузы", geo)  # empty category is hidden

    def test_noise_box_inside_noise_criterion(self):
        noise = re.search(r'<details class="crit" id="c-noise".*?</details>', self.dom, re.S).group(0)
        t = text_of(noise)
        self.assertIn("Шум с улицы", t)
        self.assertIn("Скидка за шум в справедливой цене", t)
        self.assertIn("не загрузились", t)
        self.assertNotIn("Шум с улицы", text_of(section(self.dom, "geo")))
        self.assertNotIn("Скидка за шум", text_of(section(self.dom, "price")))

    def test_summary_without_repeats(self):
        t = text_of(section(self.dom, "summary"))
        self.assertNotIn("Уверенность:", t)
        self.assertEqual(t.count("рынк"), 1)

    def test_long_comment_is_split(self):
        price = section(self.dom, "price")
        self.assertGreaterEqual(price.count("<li"), 4)
        t = text_of(price)
        self.assertNotIn("конфиг", t)
        self.assertIn("199 342", t)
        self.assertIn("9,62", t)
        self.assertIn("Аренда около 46 тыс. ₽", text_of(section(self.dom, "invest")))

    def test_interactive_dom(self):
        self.assertIn('<details class="crit"', self.dom)
        self.assertIn('type="checkbox"', self.dom)
        self.assertRegex(self.dom, r'id="navlinks"[^>]*>\s*<a ')

    def test_pros_with_links(self):
        self.assertIn('href="https://example.org/proof"', section(self.dom, "details"))


@unittest.skipUnless(BROWSER, "Chromium browser not found")
class RealPdfTest(unittest.TestCase):
    def test_pdf_from_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, rr.readable_name(load_sample()) + ".html")
            rc, md, _ = run_main([SAMPLE, "--out", out, "--markdown", "--pdf", "--theme", "dark"])
            self.assertEqual(rc, 0)
            pdf = out[:-5] + ".pdf"
            self.assertEqual(sorted(os.listdir(tmp)), sorted([os.path.basename(out), os.path.basename(pdf)]))
            self.assertGreater(os.path.getsize(pdf), 20 * 1024)
            with open(pdf, "rb") as fh:
                self.assertEqual(fh.read(4), b"%PDF")
            self.assertIn(pdf, md)


if __name__ == "__main__":
    unittest.main()
