---
name: property-due-diligence
description: Pre-purchase check of an apartment or a private house in Russia (Domoved). Use when the user sends a listing link (ЦИАН, Домклик, Авито, Яндекс Недвижимость), a Яндекс/2ГИС/Google Maps link or an address and asks whether to buy it («стоит ли покупать», «что с домом», «какой район», «шумно ли», «нормальная ли цена», «вырастет ли в цене»). Also for comparing several properties («сравни квартиры»).
---

# Domoved: pre-purchase property check

**Language.** These instructions are in English, but all communication with the user (chat replies, questions, the final line) and all report content (every text field in the fragments and `analysis.json`: summaries, pros and cons, evidence, checklists, comments, review retellings) are in Russian.

Result of the check:
- scores on 11 criteria;
- a recommendation;
- a fair price;
- a growth forecast with confirmed catalysts;
- reviews and checklists;
- **one HTML report** with a readable name in the reports folder: theme switcher, navigation, checklists and a «Сохранить PDF» button that prints in the current theme. No Markdown summary in the chat.

## Paths

`$ROOT` = `${CLAUDE_PLUGIN_ROOT}`. If the variable was not substituted, it is the folder two levels above this SKILL.md.

Paths are printed by `python3 "$ROOT/scripts/paths.py"`:
- **reports** (HTML): `reports/` in the plugin root; `~/Documents/Домовед/reports` if the plugin is installed from a marketplace (any config dir, including `CLAUDE_CONFIG_DIR`);
- **analysis working files**: the system temp folder (`domoved-work`), the system deletes old files itself;
- **cache**: the system cache folder (macOS `~/Library/Caches/domoved`);
- if `$DOMOVED_HOME` is set, everything lives inside it.

At the very start of every check, before any questions, silently run cleanup of expired cache and old working files: `python3 "$ROOT/scripts/cleanup.py" --quiet`. Do not show its output to the user.

## Rules

1. **Facts separate from judgments.** Distances only from the OSM script. Make nothing up. No data: `score: null`, `confidence: "none"`, an item in `check_in_person`.
2. **Every score is backed by `evidence` with a link.**
3. **Future by level of certainty.** Only built, under_construction, aip go into the forecast. Account for `priced_in`.
4. **Stop factors outweigh average scores.**
5. **Retell reviews** in your own words, without long quotes.
6. **Only `score.py` computes the total.**
7. Write to the user and in the report in Russian, simply, without the em dash.

## Source order (everywhere)

1. Scripts and cache: OSM, Nominatim, MOEX, ЦБ (Bank of Russia).
2. WebSearch (snippets).
3. WebFetch with a narrow prompt.
4. **Only for the listing and reviews of the house, and only here, in the main session:** the browser. Per page one `navigate` and one `javascript_tool` with an extraction script (`extract_listing.js`, `find_reviews_link.js`, `extract_reviews.js`). No screenshots, `get_page_text` or `read_page`.
5. Asking the user to paste the listing text.

Do not download Авито and ЦИАН listings with a script that spoofs browser headers: that bypasses their bot protection. Do not pass or bypass check pages («Доступ ограничен», «Пройти проверку», captcha).

## Flow

### 0. Preparation

Parse the arguments:
- links or an address;
- `--profile`: balance (default), family, investment, quiet;
- `--quick`;
- `--theme light|dark`: the theme the report opens with;
- `--fresh`: ignore the cache.

**Report theme.** If `--theme` is not passed, the first action is to ask the user via AskUserQuestion: question «Тема отчёта?», options «Светлая (рекомендуется)» and «Тёмная». Remember the answer as `light` or `dark` and pass it to `assemble.py --theme` and `render_report.py --theme`: the report opens with this theme, and the «Сохранить PDF» button prints the PDF in it.

```bash
WORK=$(python3 "$ROOT/scripts/paths.py" --new-work <short-slug>)
python3 "$ROOT/scripts/parse_input.py" "<input>"
```

If there are several links, suggest `/lpp-domoved:compare`.

### 1. Coordinates and surroundings (in the background right away)

Coordinates come from:
- the map link;
- `geocode.py --address`;
- the listing after step 2.

As soon as they are known, run **in the background**:

```bash
python3 "$ROOT/scripts/osm_nearby.py" --lat <lat> --lon <lon> --radius 1500 --out "$WORK/geo.json"
```

- The script uses the cache itself and writes `$WORK/geo_brief.json` (up to 2 KB). Only the brief is passed to agents.
- Overpass can be slow (2 to 6 min).
- `brief.partial = true` means major roads did not load. One background retry with `--fresh` is allowed, then continue without them.

In parallel, get the rates:

```bash
python3 "$ROOT/scripts/market_rates.py"
```

Pass the result to the price and future agents.

### 2. Listing

1. Try **WebFetch** with a narrow prompt (price, parameters, address, description, price history). If data came back, save the text to `$WORK/page.txt` and run:
   ```bash
   python3 "$ROOT/scripts/normalize_listing.py" --text "$WORK/page.txt" --url "<link>" --out "$WORK/listing.json"
   ```
2. **Blocked:** the browser. One `navigate` to the link. Then `javascript_tool` with the contents of `$ROOT/scripts/extract_listing.js`. Save the result to `$WORK/extract.json` and run:
   ```bash
   python3 "$ROOT/scripts/normalize_listing.py" --json "$WORK/extract.json" --url "<link>" --out "$WORK/listing.json"
   ```
   Do not pass captchas and do not log into accounts.
3. **Did not work:** ask the user to paste the listing text, save it to a file and run `normalize_listing.py --text`.
4. **Reviews of the house from the listing site** (Авито, ЦИАН, Домклик), right after extracting the listing, in the same tab:
   1. `javascript_tool` with the contents of `$ROOT/scripts/find_reviews_link.js`. It returns `{"href": ...}`. If `href` is empty, skip this step.
   2. One `navigate` to `href`, then `javascript_tool` with the contents of `$ROOT/scripts/extract_reviews.js`. Save the result to `$WORK/reviews_p1.json`.
      - If the response has `next_page_url` and `pages` > 1, open up to 2 more pages: `navigate` to `next_page_url` + number (2, then 3) and the same script, results in `reviews_p2.json`, `reviews_p3.json`. **No more than 3 pages:** on the 4th Авито usually turns on an access restriction. If a page returned `blocked: true`, stop immediately and work with what is already collected (retrying and passing the check is not allowed).
      - Merge the pages: `python3 "$ROOT/scripts/merge_reviews.py" "$WORK"/reviews_p*.json --out "$WORK/reviews_site.json"`.
      - The key content of Авито reviews is in the `summary` field (the site's summary of all reviews): it matters more than individual reviews, always take it into account.
   3. If the response has `"blocked": true`, the site showed a check or a restriction. Do not pass or bypass it. Call `tabs_context` to make sure the browser panel is visible (if hidden, ask the user to open it: Cmd+Shift+B on Mac or Ctrl+Shift+B on Windows). Then ask the user (in Russian): pass the check themselves in the browser window or skip the site reviews. If they passed it, repeat item 2 once. Make no further attempts. If the check was already passed for the listing itself during this check, do not ask the user a second time: after it Авито keeps restricting access by IP for a while. Just note in the report that the site reviews were not collected, and put the link to them in `reviews.site.url` so the user can open them themselves.
   4. Pass `reviews_site.json` to the `house-inspector` agent (or `local-analyst`): it is the main source of reviews of the house.
5. **Extra flag extraction:** the `listing-extractor` agent (Haiku) reads `listing.json` and adds risk flags and missing fields.

If the input is a map or an address, briefly ask (in Russian) for the property type, price, area and floor. Then write a minimal `listing.json`: `{"object": {...}}`.

### 3. House and district cache

```bash
HK=$(python3 "$ROOT/scripts/cache.py" key --house "<address>")
DK=$(python3 "$ROOT/scripts/cache.py" key --coords <lat> <lon> --step 300)
python3 "$ROOT/scripts/cache.py" get house "$HK" --max-age-days 30
python3 "$ROOT/scripts/cache.py" get district "$DK" --max-age-days 30
```

- If `get` returned a path, copy the file to `$WORK/house.json` or `$WORK/district.json` and do not run the corresponding agent.
- `--fresh` skips this step.

### 4. Agents (in parallel, in one message)

**full**, 4 agents:

| Agent | Criteria | File |
|---|---|---|
| `house-inspector` | noise, building, legal | house.json |
| `district-analyst` | transport, ecology, green, kids, amenities, safety | district.json |
| `market-valuator` | value_liquidity, valuation, investment | market.json |
| `future-scout` | future, forecast | future.json |

**quick**, 2 agents:

| Agent | What it does | Files |
|---|---|---|
| `local-analyst` | house and district | house.json and district.json |
| `market-future` | price and future | market.json and future.json |

**Agent type:** `lpp-domoved:<name>`. The model is set in the frontmatter: Sonnet, Haiku for listing-extractor.

If the plugin is not installed and the type does not exist: `subagent_type: general-purpose`, `model: sonnet` (`haiku` for listing-extractor). Prompt: "Read $ROOT/agents/<name>.md and follow it. $ROOT=…, $WORK=…, mode=…".

**What to pass to each:**
- `$ROOT`, `$WORK`, mode, property type, city, address, coordinates;
- the contents of `listing.json` (object only);
- `geo_brief.json`;
- `market_rates` (to the price and future agents);
- `reviews_site.json`, if present (to the house agent).

Do not pass the full `geo.json` or the references: agents have their own digests.

After the agents, put the new fragments into the cache:

```bash
python3 "$ROOT/scripts/cache.py" put house "$HK" "$WORK/house.json"
python3 "$ROOT/scripts/cache.py" put district "$DK" "$WORK/district.json"
```

### 5. Assembly, scoring, validation

```bash
python3 "$ROOT/scripts/assemble.py" --dir "$WORK" --input "<input>" --profile <profile> --mode <full|quick> --theme <light|dark>
python3 "$ROOT/scripts/score.py" "$WORK/analysis.json" --in-place
python3 "$ROOT/scripts/validate.py" "$WORK/analysis.json"
```

`validate.py` prints only problems, including texts that read poorly: service words, numbers like «10.57 млн», pros and cons without links. The assembler itself adds map facts with links and a link to the property on Яндекс Карты to evidence. Fix the remarks precisely: add a missing criterion with `score: null` or a checklist item. Do not read the fragments or `analysis.json` in full.

**Noise viewing checklist** (add it if missing; items in Russian):
- визит вечером в будни;
- слышимость соседей и лифта;
- улица при закрытых окнах.

### 6. Report: one HTML (one call)

```bash
python3 "$ROOT/scripts/render_report.py" "$WORK/analysis.json" --theme <light|dark>
```

- The command saves **one HTML** to the reports folder with a readable name («Домовед. <адрес>. <балл> из 10. <дата>.html») and prints its path. A repeated call creates a copy « (2)».
- The report has a theme switcher, navigation, checklists and a «Сохранить PDF» button: it prints the PDF in the current theme (the dark theme gives a dark PDF).
- No PDF is made by a script by default. If the user explicitly asks for a PDF file, call the same render with `--pdf`. Exit code 2 means there is no browser for printing: tell the user to install Chrome, Chromium, Edge or Яндекс Браузер or set its path in `DOMOVED_CHROME`.
- If there is a tool for sending files to the user, send the HTML.

**Chat reply (in Russian):** one line «Готово: <балл> из 10, <вердикт>», the path to the HTML and a short note that the PDF is saved with the «Сохранить PDF» button in the report. No Markdown summary, tables or retelling of the report.

## Comparison (`/lpp-domoved:compare`)

1. For each link, steps 0 to 5 in quick mode with one profile. No more than 2 properties at once. The district cache is shared.
2. Then:
   ```bash
   python3 "$ROOT/scripts/render_report.py" --compare <a.json> <b.json> ... --theme <light|dark>
   ```
3. A property with a stop factor cannot be the winner.

## Token economy

- Analysts run on Sonnet, listing extraction on Haiku.
- Agents get digests and `geo_brief` instead of references and the full `geo.json`.
- Search budget: full 6 to 8, quick 3. Stop when there are 2 sources.
- In quick, 2 agents instead of 4.
- Cache for OSM, rates, house (30 days) and district (30 days).
- The orchestrator works with short script outputs (`validate.py`, report path), not with full JSON.
- A full reference is read one section at a time: `python3 "$ROOT/scripts/refs.py" <file> "<section>"`. References live in `references/`: criteria, red-flags, house-series, sources, future-catalysts, valuation-method, investment, legal-checklist, private-house, literature.
