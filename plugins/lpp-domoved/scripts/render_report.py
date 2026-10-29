#!/usr/bin/env python3
"""Render a Domoved analysis into an interactive HTML report (PDF on a flag).

Usage:
    render_report.py analysis.json [--theme light|dark] [--out path.html] [--pdf] [--open] [--markdown]
    render_report.py --compare a.json b.json [...] [--theme ...] [--out path.html] [--pdf] [--markdown] [--no-full]

Main result: one HTML «Домовед. <адрес>. <балл> из 10. <ДД.ММ.ГГГГ>.html»
in the Domoved reports/ folder (see paths.py). The report has a «Сохранить PDF» button:
it prints in the current theme. The --pdf flag additionally prints a PDF next to it via
headless Chromium in the chosen theme.
"""
import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "report.html")
PLACEHOLDER = "/*__DATA__*/"

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}

TYPE_TITLES = {"secondary": "Вторичка", "new_build": "Новостройка", "private_house": "Частный дом"}
CONF_TITLES = {"high": "высокая", "medium": "средняя", "low": "низкая", "none": "нет данных"}


def slugify(text, max_len=60):
    text = (text or "").lower()
    out = "".join(_TRANSLIT.get(ch, ch) for ch in text)
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return (out[:max_len].rstrip("-")) or "object"


def embed_json(data):
    raw = json.dumps(data, ensure_ascii=False)
    # Do not let the data close <script> from inside.
    raw = raw.replace("</", "<\\/").replace("<!--", "<\\!--")
    raw = raw.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return raw


THEMES = ("light", "dark")


def resolve_theme(data, theme=None):
    """Report theme: the flag overrides meta.theme, light by default."""
    if theme in THEMES:
        return theme
    t = ((data or {}).get("meta") or {}).get("theme")
    if t in THEMES:
        return t
    cm = (data or {}).get("compare_meta") or {}
    return cm.get("theme") if cm.get("theme") in THEMES else "light"


def render_html(data, template_path=TEMPLATE, theme=None):
    with open(template_path, encoding="utf-8") as fh:
        tpl = fh.read()
    if PLACEHOLDER not in tpl:
        raise ValueError("Template has no placeholder " + PLACEHOLDER)
    tpl = tpl.replace("<title>Домовед</title>", "<title>" + _html_escape(readable_name(data)) + "</title>", 1)
    t = resolve_theme(data, theme)
    tpl = tpl.replace('<html lang="ru">', '<html lang="ru" data-theme="%s" data-forced-theme="1">' % t, 1)
    return tpl.replace(PLACEHOLDER, embed_json(data), 1)


def _html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ---------- Readable file names ----------

_BAD_CHARS = re.compile(r'[/\\:*?"<>|\r\n\t\x00-\x1f]')
MAX_NAME_LEN = 120


def sanitize_filename(text, max_len=MAX_NAME_LEN):
    """Removes characters forbidden in file names, collapses spaces, cuts at a word boundary."""
    text = re.sub(r"(?<=\d)/(?=\d)", "-", str(text or ""))  # slash in the house number: 9/8 -> 9-8
    text = _BAD_CHARS.sub(" ", text)
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text).strip(" .")
    if len(text) > max_len:
        cut = text[:max_len]
        sp = cut.rfind(" ")
        if sp > max_len // 2:
            cut = cut[:sp]
        text = cut.rstrip(" .,;")
    return text or "Домовед"


def _report_date(data):
    meta = data.get("meta") or data.get("compare_meta") or {}
    raw = meta.get("generated_at")
    if raw:
        try:
            return _dt.datetime.fromisoformat(str(raw)[:19]).date()
        except ValueError:
            pass
    return _dt.date.today()


def short_address(address):
    a = re.sub(r"^\s*\d{6},?\s*", "", address or "")
    a = re.sub(r"^\s*(Россия|Российская Федерация),\s*", "", a, flags=re.I)
    # drop region, district and settlement if a city and street remain after them
    admin = re.compile(r"(\bобл\b|област|\bкрай\b|\bр-н\b|район|поселени|\bАО\b|автономн|республик|\bг\.?\s?о\.?\b|городской округ|муниципальн)", re.I)
    parts = [p.strip() for p in a.split(",") if p.strip()]
    kept = [p for p in parts if not admin.search(p)]
    if len(kept) >= 2:
        parts = kept
    return ", ".join(parts).strip(" ,")


def readable_name(data):
    """Human-readable report name: for <title>, HTML and PDF."""
    date = _report_date(data).strftime("%d.%m.%Y")
    if isinstance(data.get("compare"), list):
        n = len(data["compare"])
        return sanitize_filename("Домовед. Сравнение %d объектов. %s" % (n, date))
    obj = data.get("object") or {}
    place = short_address(obj.get("address")) or obj.get("title") or "Объект"
    total = (data.get("score") or {}).get("total")
    parts = ["Домовед", place]
    if isinstance(total, (int, float)):
        parts.append(("%.1f" % total).replace(".", ",") + " из 10")
    parts.append(date)
    # Cut the address first so the score and date always fit.
    tail = ". ".join(parts[2:])
    room = MAX_NAME_LEN - len("Домовед. ") - len(". " + tail)
    place = sanitize_filename(place, max(20, room))
    return sanitize_filename(". ".join(["Домовед", place, tail]))


def unique_base(folder, name, exts=(".html", ".pdf")):
    """Name without extension for which none of the files exists yet."""
    base, n = name, 2
    while any(os.path.exists(os.path.join(folder, base + e)) for e in exts):
        base = "%s (%d)" % (name, n)
        n += 1
    return base


def reports_folder(folder=None):
    """Reports folder: explicit, or reports/ in data_home (paths.py)."""
    folder = folder or paths.reports_dir()
    os.makedirs(folder, exist_ok=True)
    return folder


def default_out_path(data, folder=None):
    """Path to the HTML report with a readable name (never overwrites existing ones)."""
    folder = reports_folder(folder)
    return os.path.join(folder, unique_base(folder, readable_name(data)) + ".html")


def _html_target(out, data, folder=None):
    if not out:
        return default_out_path(data, folder)
    out = os.path.abspath(out)
    if out.lower().endswith(".pdf"):
        out = out[:-4] + ".html"
    elif not out.lower().endswith((".html", ".htm")):
        out += ".html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


# ---------- PDF via headless Chromium ----------

PDF_TIMEOUT = 90


def find_browser():
    env = os.environ.get("DOMOVED_CHROME")
    if env and os.path.exists(env):
        return env
    cands = []
    if sys.platform == "darwin":
        for app, exe in [("Google Chrome", "Google Chrome"), ("Chromium", "Chromium"), ("Microsoft Edge", "Microsoft Edge"),
                         ("Yandex", "Yandex"), ("Brave Browser", "Brave Browser")]:
            for root in ("/Applications", os.path.expanduser("~/Applications")):
                cands.append(os.path.join(root, app + ".app", "Contents", "MacOS", exe))
    elif sys.platform.startswith("win"):
        for envvar in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(envvar)
            if not root:
                continue
            cands += [os.path.join(root, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(root, "Yandex", "YandexBrowser", "Application", "browser.exe"),
                      os.path.join(root, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                      os.path.join(root, "Chromium", "Application", "chrome.exe")]
    for c in cands:
        if os.path.exists(c):
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
                 "yandex-browser", "brave-browser", "chrome"):
        w = shutil.which(name)
        if w:
            return w
    return None


def _file_url(path):
    from urllib.request import pathname2url
    return "file:" + pathname2url(os.path.abspath(path))


def make_pdf(html_path, pdf_path, browser=None):
    """Prints HTML to PDF. Returns the path or raises RuntimeError."""
    browser = browser or find_browser()
    if not browser:
        raise FileNotFoundError("browser")
    url = _file_url(html_path) + "#print"
    attempts = [
        ["--headless=new", "--disable-gpu", "--no-pdf-header-footer"],
        ["--headless", "--disable-gpu", "--print-to-pdf-no-header"],
    ]
    last_err = ""
    for flags in attempts:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        with tempfile.TemporaryDirectory(prefix="domoved-chrome-") as profile:
            cmd = [browser] + flags + ["--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
                                       "--user-data-dir=" + profile, "--print-to-pdf=" + pdf_path,
                                       "--virtual-time-budget=5000", url]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=PDF_TIMEOUT)
                last_err = res.stderr.decode("utf-8", "replace")[-500:]
            except subprocess.TimeoutExpired:
                last_err = "timeout %d s" % PDF_TIMEOUT
                continue
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            return pdf_path
    raise RuntimeError("Failed to print PDF: " + last_err.strip())


NO_BROWSER_MSG = ("PDF not created: printing needs a Chromium-based browser (Google Chrome, Chromium, "
                  "Microsoft Edge or Yandex Browser) or its path in the DOMOVED_CHROME variable. "
                  "The HTML report is saved: a PDF can be made with its «Сохранить PDF» button.")


def try_pdf(html_path):
    """PDF next to the HTML in the same theme. Returns (path or None, exit code)."""
    pdf = os.path.splitext(html_path)[0] + ".pdf"
    try:
        return make_pdf(html_path, pdf), 0
    except FileNotFoundError:
        sys.stderr.write(NO_BROWSER_MSG + "\n")
    except RuntimeError as e:
        sys.stderr.write("%s\nThe HTML report is saved: a PDF can be made with its «Сохранить PDF» button.\n" % e)
    return None, 2


# ---------- Markdown ----------

def fmt_money(v):
    if v is None:
        return "н/д"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(v) >= 1_000_000:
        return ("%.2f" % (v / 1_000_000)).rstrip("0").rstrip(".").replace(".", ",") + " млн ₽"
    return "{:,.0f}".format(v).replace(",", " ") + " ₽"


def fmt_num(v, digits=1):
    if v is None:
        return "н/д"
    return ("%." + str(digits) + "f") % float(v)


def fmt_pct(v, sign=True):
    if v is None:
        return "н/д"
    s = ("%+.1f" if sign else "%.1f") % float(v)
    return s.replace(".", ",") + "%"


def _collect(data, key, limit):
    """Collects pros or cons, starting from the heaviest criteria."""
    crit = data.get("criteria") or {}
    per = ((data.get("score") or {}).get("per_criterion")) or {}
    order = sorted(crit.keys(), key=lambda k: -float((per.get(k) or {}).get("weight") or 0))
    out = []
    for k in order:
        for item in (crit.get(k) or {}).get(key) or []:
            if item and item not in out:
                out.append(item)
                break
        if len(out) >= limit:
            break
    return out


def render_markdown(data, html_path=None, pdf_path=None):
    sc = data.get("score") or {}
    obj = data.get("object") or {}
    val = data.get("valuation") or {}
    fut = (data.get("future") or {}).get("forecast") or {}
    lines = []
    head = short_address(obj.get("address")) or obj.get("title") or "Объект"
    lines.append("## 🏠 Домовед: %s" % head)
    total = sc.get("total")
    lines.append("")
    lines.append("**%s** · итог **%s / 10** · профиль: %s · уверенность: %s · покрытие данных: %s"
                 % (sc.get("verdict_title", "н/д"), fmt_num(total).replace(".", ",") if total is not None else "н/д",
                    sc.get("profile_title") or sc.get("profile") or "н/д",
                    CONF_TITLES.get(sc.get("confidence"), "н/д"),
                    ("%d%%" % round(float(sc["coverage"]) * 100)) if sc.get("coverage") is not None else "н/д"))
    facts = [TYPE_TITLES.get(obj.get("type"), "")]
    if obj.get("price"):
        facts.append(fmt_money(obj["price"]))
    if obj.get("area_total"):
        facts.append(("%s м²" % obj["area_total"]).replace(".", ","))
    if obj.get("floor"):
        facts.append("этаж %s/%s" % (obj.get("floor"), obj.get("floors_total") or "?"))
    if obj.get("year_built"):
        facts.append("%s г." % obj["year_built"])
    if obj.get("series"):
        facts.append(obj["series"])
    lines.append("")
    lines.append(" · ".join(f for f in facts if f))

    stops = sc.get("stop_flags") or []
    majors = sc.get("major_flags") or []
    if stops:
        lines.append("")
        lines.append("⛔ **Стоп-факторы:** " + "; ".join(stops))
    if sc.get("capped"):
        lines.append("Итог ограничен сверху из-за стоп-факторов.")

    pros = _collect(data, "pros", 3)
    risks = list(majors) + [c for c in _collect(data, "cons", 6) if c not in majors]
    risks = risks[:3]
    if pros:
        lines.append("")
        lines.append("**Плюсы**")
        lines.extend("- " + p for p in pros)
    if risks:
        lines.append("")
        lines.append("**Риски**")
        lines.extend("- " + r for r in risks)

    if val.get("fair_price"):
        lines.append("")
        rng = ""
        if val.get("fair_low") and val.get("fair_high"):
            rng = " (%s – %s)" % (fmt_money(val["fair_low"]), fmt_money(val["fair_high"]))
        over = val.get("over_under_pct")
        tail = ""
        if over is not None:
            tail = ", %s %s" % ("переплата" if over > 0 else "недооценка", fmt_pct(abs(over), sign=False))
        lines.append("**Справедливая цена:** %s%s%s" % (fmt_money(val["fair_price"]), rng, tail))

    y3 = (fut.get("y3") or {}).get("base")
    y5 = (fut.get("y5") or {}).get("base")
    if y3 is not None or y5 is not None:
        lines.append("**Прогноз (базовый):** 3 года %s, 5 лет %s. Это сценарий, а не гарантия." % (fmt_pct(y3), fmt_pct(y5)))

    pc = sc.get("per_criterion") or {}
    if pc:
        lines.append("")
        lines.append("| Критерий | Балл | Уверенность |")
        lines.append("|---|---|---|")
        for k, c in pc.items():
            s = c.get("score")
            lines.append("| %s %s | %s | %s |" % (c.get("icon", ""), c.get("title", k),
                                                 fmt_num(s).replace(".", ",") if s is not None else "проверить лично",
                                                 CONF_TITLES.get(c.get("confidence"), "")))
    if html_path:
        lines.append("")
        lines.append("📄 Отчёт (HTML): `%s`" % html_path)
    if pdf_path:
        lines.append("📑 PDF: `%s`" % pdf_path)
    return "\n".join(lines)


def open_file(path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            webbrowser.open("file://" + os.path.abspath(path))
    except Exception:  # noqa: BLE001
        pass


CRIT_ORDER = ["noise", "building", "legal", "transport", "ecology", "green", "kids", "amenities",
              "safety", "value_liquidity", "future"]
CRIT_TITLES = {
    "noise": "Тишина", "building": "Дом", "legal": "Юр. чистота", "transport": "Транспорт",
    "ecology": "Экология", "green": "Зелень", "kids": "Школы и сады", "amenities": "Инфраструктура",
    "safety": "Безопасность", "value_liquidity": "Цена и ликвидность", "future": "Потенциал роста",
}


def _crit_score(a, k):
    c = (a.get("criteria") or {}).get(k) or {}
    if isinstance(c.get("score"), (int, float)):
        return float(c["score"])
    p = ((a.get("score") or {}).get("per_criterion") or {}).get(k) or {}
    return float(p["score"]) if isinstance(p.get("score"), (int, float)) else None


def _flags(a, severity):
    out = [f.get("title") for f in a.get("red_flags") or [] if f.get("severity") == severity and f.get("title")]
    if not out:
        out = list((a.get("score") or {}).get(severity + "_flags") or [])
    return out


def pick_winner(items):
    ok = [a for a in items if not _flags(a, "stop") and isinstance((a.get("score") or {}).get("total"), (int, float))]
    if not ok:
        return None
    return max(ok, key=lambda a: a["score"]["total"])


def render_compare_markdown(items, html_path=None, pdf_path=None):
    def name(i, a):
        o = a.get("object") or {}
        return "%d. %s" % (i + 1, o.get("address") or o.get("title") or "Объект")

    heads = [name(i, a) for i, a in enumerate(items)]
    lines = ["## ⚖️ Домовед: сравнение %d объектов" % len(items), ""]
    win = pick_winner(items)
    if win is not None:
        o = win.get("object") or {}
        lines.append("**Лучший вариант:** %s, %s / 10 (%s)" % (
            o.get("address") or o.get("title") or "Объект",
            fmt_num(win["score"]["total"]).replace(".", ","), win["score"].get("verdict_title", "")))
    else:
        lines.append("**Победителя нет:** у всех объектов стоп-факторы или нет итогового балла.")
    lines.append("")
    lines.append("| Критерий | " + " | ".join(heads) + " |")
    lines.append("|---|" + "---|" * len(items))

    def row(label, vals, best=None, fmt=None):
        present = [x for x in vals if x is not None]
        if present and min(present) == max(present):
            best = None
        cells = []
        for v in vals:
            if v is None:
                cells.append("н/д")
                continue
            t = fmt(v) if fmt else str(v)
            if best is not None and v == best and len([x for x in vals if x is not None]) > 1:
                t = "**%s**" % t
            cells.append(t)
        lines.append("| %s | %s |" % (label, " | ".join(cells)))

    def num1(v):
        return fmt_num(v).replace(".", ",")

    totals = [(a.get("score") or {}).get("total") for a in items]
    row("**Итог**", totals, max([t for t in totals if t is not None], default=None), num1)
    row("Вердикт", [(a.get("score") or {}).get("verdict_title") for a in items])
    row("Цена", [(a.get("object") or {}).get("price") or (a.get("valuation") or {}).get("asking_price") for a in items], None, fmt_money)
    for k in CRIT_ORDER:
        vals = [_crit_score(a, k) for a in items]
        nums = [v for v in vals if v is not None]
        row(CRIT_TITLES[k], vals, max(nums) if nums else None, num1)
    row("Справедливая цена", [(a.get("valuation") or {}).get("fair_price") for a in items], None, fmt_money)
    ou = [(a.get("valuation") or {}).get("over_under_pct") for a in items]
    nums = [v for v in ou if v is not None]
    row("Переплата", ou, min(nums) if nums else None, fmt_pct)
    row("Стоп-факторы", ["; ".join(_flags(a, "stop")) or "нет" for a in items])
    if html_path:
        lines.append("")
        lines.append("📄 Сравнение (HTML): `%s`" % html_path)
    if pdf_path:
        lines.append("📑 PDF: `%s`" % pdf_path)
    return "\n".join(lines)


def run_compare(paths, out=None, markdown=False, do_open=False, full=True, pdf=False, theme=None):
    items = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            items.append(json.load(fh))
    payload = {"compare": items, "compare_meta": {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "profile_title": ((items[0].get("score") or {}).get("profile_title")) if items else None,
        "theme": resolve_theme(items[0] if items else {}, theme),
    }}
    th = payload["compare_meta"]["theme"]
    out = _html_target(out, payload)
    out_dir = os.path.dirname(out)
    for a in items:
        rp = (a.get("meta") or {}).get("report_path")
        if not rp and full:
            rp = os.path.join(out_dir, unique_base(out_dir, readable_name(a)) + ".html")
            with open(rp, "w", encoding="utf-8") as fh:
                fh.write(render_html(a, theme=th))
        if rp:
            a["report_href"] = os.path.relpath(os.path.abspath(rp), out_dir).replace(os.sep, "/")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_html(payload, theme=th))
    pdf_path, code = (None, 0)
    if pdf:
        pdf_path, code = try_pdf(out)
    if markdown:
        print(render_compare_markdown(items, out, pdf_path))
    else:
        print(out)
        if pdf_path:
            print(pdf_path)
    if do_open:
        open_file(pdf_path or out)
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render the Domoved report (HTML, PDF on a flag)")
    ap.add_argument("analysis", nargs="?", help="analysis JSON (after score.py)")
    ap.add_argument("--compare", nargs="+", metavar="JSON", help="compare several analyses on one page")
    ap.add_argument("--no-full", action="store_true", help="in compare mode, do not render full per-object reports")
    ap.add_argument("--out", help="HTML path (default reports/ with a readable name)")
    ap.add_argument("--open", action="store_true", help="open the report after rendering")
    ap.add_argument("--markdown", action="store_true", help="print a short Markdown summary")
    ap.add_argument("--theme", choices=THEMES, help="initial report theme and PDF theme: light or dark (default meta.theme, otherwise light)")
    ap.add_argument("--pdf", action="store_true", help="also save a PDF next to it (needs Chrome/Chromium/Edge/Yandex/Brave)")
    args = ap.parse_args(argv)

    if args.compare:
        paths_ = ([args.analysis] if args.analysis else []) + args.compare
        if len(paths_) < 2:
            ap.error("comparison needs at least two files")
        return run_compare(paths_, args.out, args.markdown, args.open, full=not args.no_full, pdf=args.pdf, theme=args.theme)
    if not args.analysis:
        ap.error("pass an analysis JSON or --compare")

    with open(args.analysis, encoding="utf-8") as fh:
        data = json.load(fh)

    out = _html_target(args.out, data)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_html(data, theme=args.theme))

    pdf_path, code = (None, 0)
    if args.pdf:
        pdf_path, code = try_pdf(out)

    if args.markdown:
        print(render_markdown(data, out, pdf_path))
    else:
        print(out)
        if pdf_path:
            print(pdf_path)
    if args.open:
        open_file(pdf_path or out)
    return code


if __name__ == "__main__":
    sys.exit(main())
