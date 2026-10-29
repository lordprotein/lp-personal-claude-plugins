# Scoring rubrics: 11 criteria, 0–10 scale

Each criterion in the final JSON (`criteria.<id>`) contains: `score` (0–10 or `null`), `confidence`, `summary`, `pros`, `cons`, `evidence` (with `source_url`), `check_in_person`. Pros, cons and evidence items carry `date` (`YYYY-MM-DD`, `YYYY-MM` or `YYYY`) when the fact is dated: reviews, news, documents.

These rubrics are instructions in English, but every text field that goes into the report (`summary`, `pros`, `cons`, `evidence` text, `check_in_person`) is written in Russian.

## General rules

- **Starting point.** If `geo.suggested_scores.<id>` from `scripts/osm_nearby.py` exists, start from that value. Move it based on the facts you find, but explain every deviation larger than 1.5 points in `summary` or `evidence`.
- **No data: do not give an average.** If nothing was found for a criterion, write `score: null`, `confidence: "none"` and add items to `check_in_person`. `score.py` will exclude it from the total and lower the coverage.
- **Fractional scores** are allowed in steps of 0.5.
- **Anchors** below describe a typical picture. A property rarely matches one completely: pick the nearest anchor and adjust.
- **Stop factors** are not put into the score as "0"; record them in `red_flags` (see `red-flags.md`). The criterion score in that case is usually 0–3.

## Confidence levels

| Level | When to use |
|---|---|
| `high` | There are 2+ independent sources or objective geodata (OSM, official registry), and they agree |
| `medium` | One reliable source, or geodata without on-site verification, or there are reviews but few of them (3–5) |
| `low` | Only indirect signs: building type without a series, a single review, data older than 3 years, data for the district rather than the building |
| `none` | No data. `score` = `null` |

## 1. noise: quietness and sound insulation

Two components: **internal** (series, floor slabs, walls between apartments, reviews about audibility) and **external** (roads, railway, tram, airport, bars, courtyards). The total is roughly 50/50. If the internal part is clearly bad (П-44 without sound insulation, reviews saying "you can hear conversations" («слышно разговоры»)), the total is no higher than 5 even in a quiet location.

| Score | Anchor |
|---|---|
| 10 | Brick or monolith with brick or thick walls between apartments, reviews praising the insulation, windows facing the courtyard, nearest major road farther than 300 m, no railway or airport, external noise estimate below 45 dB |
| 8 | A good series or a quality monolith, major road 150–300 m away or shielded by buildings, rare complaints |
| 6 | Average panel (П-3М, П-44Т with screed) or economy monolith with aerated concrete; a secondary street nearby; occasional complaints about neighbours |
| 4 | Weak panel, frequent complaints in reviews, or windows onto a busy street (60–65 dB), or a tram closer than 100 m |
| 2 | Windows onto a major road or railway closer than 50 m, a bar or night venue under the windows, airport glide path, mass complaints about audibility |
| 0 | Strong external noise combined with poor insulation, e.g. a khrushchyovka (хрущёвка) by the MKAD ring road with windows facing the highway |

Data: `geo.noise_estimate` (est_db_combined, est_db_max and sources with dB) and `geo.suggested_scores.noise_external`, `house-series.md`, resident reviews on the topic "noise" («шум»), the listing description (which side the windows face, double glazing). For the estimate in rubles use `valuation.noise_discount_pct` (see `valuation-method.md`).

## 2. building: the building and its condition

| Score | Anchor |
|---|---|
| 10 | Building younger than 10 years or after a comprehensive capital repair, monolith or brick, a good management company (УК) with a high rating, well-kept entrances, underground parking, new lifts |
| 8 | 10–30 years old, no serious complaints, capital repair on schedule, management company without mass complaints |
| 6 | 30–50 years old, partial wear, roof or facade capital repair due in the coming years, average management company |
| 4 | Old housing stock with wear above 50%, leaks, utility problems, many complaints about the management company |
| 2 | Wooden floor slabs, gas water heaters in old housing stock, mould, cracks in load-bearing structures |
| 0 | Declared unsafe (аварийный) or slated for demolition (this is also a stop factor) |

Data: реформагкх.ру, ГИС ЖКХ (wear, year, floor slabs, capital repair), the regional capital repair fund, reviews of the management company, listing photos.

**new_build:** assess the developer (timeliness of past deliveries, quality, complaints about finishing and defects), the residential complex (ЖК) class, materials, availability of parking. For a property under construction confidence is usually no higher than `medium`.

**private_house:** the criterion is named «Дом и участок». See `private-house.md`: foundation, walls, roof, insulation, utilities (gas, kW, water, sewage), plot area and shape, access road.

## 3. legal: legal clearance and transaction risks

Not everything can be checked remotely. The score reflects the visible risks and the completeness of open data.

| Score | Anchor |
|---|---|
| 10 | Secondary: one owner for more than 5 years, no inheritance and no children, no encumbrances, seller ready to provide the ЕГРН extract and use safe settlement. New build: a large developer without delays, escrow, ДДУ (shared construction participation agreement) |
| 8 | Ownership 3–5 years, clear history, minor questions resolved by documents |
| 6 | There are factors that need checking (inheritance older than 3 years, maternity capital with allocated shares, a sale by power of attorney) |
| 4 | Several risk factors or the seller avoids providing documents; a developer with delayed deadlines |
| 2 | Frequent resales, inheritance younger than 6 months, signs of seller bankruptcy, children's shares not allocated |
| 0 | Stop factor: developer bankruptcy, no escrow, a preliminary contract instead of a ДДУ, arrest |

Without data from the listing and open registries, set `confidence: "low"` and fill `checklists.documents` per `legal-checklist.md`.

**private_house:** permitted use (ВРИ), land category, land survey (межевание), zones with special use conditions (ЗОУИТ), registration of the house in ЕГРН. An СНТ (gardening partnership) without the possibility of permanent registration (прописка) lowers the score to 4–6.

## 4. transport: transport and traffic jams

| Score | Anchor |
|---|---|
| 10 | Metro or МЦД within 7 minutes on foot, up to 30 minutes to the centre or business district at rush hour, several transport options |
| 8 | Metro 7–15 minutes on foot or a station with a direct route, 30–45 minutes to the centre |
| 6 | Metro 10–15 minutes by bus, or a suburban train station nearby, 45–60 minutes to the centre |
| 4 | Bus only, exit through a congested interchange, more than 60 minutes at rush hour |
| 2 | No public transport within walking distance, traffic jams on the only exit road |
| 0 | Isolation: one exit, constant congestion, infrequent transport |

Data: `geo.categories.metro`, `rail_station`, `stop_bus_tram`, `geo.nearest`, `geo.suggested_scores.transport`, search «пробки {район} выезд», reviews on the topic "transport" («транспорт»). For cities without a metro, the anchors are the time to the centre and transport frequency.

## 5. ecology: ecology and surroundings

| Score | Anchor |
|---|---|
| 10 | No industrial zones or thermal power plants (ТЭЦ) within 2 km, forest or a large park nearby, no power lines (ЛЭП), landfills or waste incinerators (МСЗ) |
| 8 | A small industrial zone farther than 1 km, normal air according to monitoring data |
| 6 | Industrial facilities at 500–1000 m, a ТЭЦ at 1–2 km, occasional complaints about smells |
| 4 | Industrial zone or sanitary protection zone (СЗЗ) closer than 500 m, a vehicle depot, frequent complaints about smells |
| 2 | Power line closer than 100 m, landfill or МСЗ closer than 2 km, a ТЭЦ right next door |
| 0 | A combination: dump, chemical production and flooding |

Data: `geo.categories` (industrial, powerline, substation, power_plant, landfill, waste, cemetery, fuel, major_road), `geo.suggested_scores.ecology`, air monitoring, reviews mentioning «запах» (smell), «гарь» (burning smell). Check flood risk separately.

## 6. green: greenery and recreation

| Score | Anchor |
|---|---|
| 10 | Large park or forest within 300 m, water (river, pond) nearby, lots of greenery in the courtyard |
| 8 | Park within 600 m or forest within 1 km |
| 6 | Small public gardens nearby, park at 1–1.5 km |
| 4 | Little greenery, the nearest park farther than 1.5 km |
| 2 | Continuous development or an industrial zone all around |
| 0 | No greenery at all |

Data: `geo.categories.park`, `forest`, `water`, `geo.suggested_scores.green`. Active parks with attractions, stadiums and concerts can produce noise: account for this in noise.

## 7. kids: schools and kindergartens

| Score | Anchor |
|---|---|
| 10 | A strong school (high regional rating) in the catchment area within 500 m, several kindergartens nearby without waiting lists |
| 8 | A good school within 1 km, a kindergarten nearby |
| 6 | An average school nearby, kindergartens with waiting lists |
| 4 | Overcrowded schools (second shift), kindergartens far away |
| 2 | No school within walking distance in a new district |
| 0 | No schools or kindergartens, none even planned |

What matters is the school assigned by registered address, not the nearest one. Look up the catchment on the school website or at the education department. For new_build check whether social facilities are being built and by when.

## 8. amenities: everyday infrastructure

| Score | Anchor |
|---|---|
| 10 | Groceries within 200 m, outpatient clinic within 1 km, pharmacies, cafes, sports and a shopping mall nearby |
| 8 | Everything within 500 m, shopping mall within 1.5 km |
| 6 | Groceries nearby, clinic and mall farther away |
| 4 | Most services require a trip |
| 2 | Only one shop nearby |
| 0 | Nothing within walking distance |

Data: `geo.categories` (grocery, pharmacy, clinic, hospital, mall, sport), `geo.suggested_scores.amenities`. For private_house the norm is a shop in the village and trips for everything else: shift the anchors 2 points down in terms of requirements.

## 9. safety: safety and social environment

| Score | Anchor |
|---|---|
| 10 | Quiet district, no negative reviews, closed courtyard, good lighting |
| 8 | Rare complaints, no problem facilities nearby |
| 6 | Occasional complaints (noisy groups, petty theft) |
| 4 | A market, railway station, dormitories, night venues nearby, frequent complaints |
| 2 | A district with a persistently bad reputation, crime news |
| 0 | Systematic serious crime |

Data: reviews of the district, district news, `geo.categories` (nightlife, rail_station, prison, psychiatric). Do not use judgements based on residents' ethnicity or social status: only facts and complaints.

## 10. value_liquidity: price and liquidity

| Score | Anchor |
|---|---|
| 10 | Price 5% or more below fair value, a typical property, eligible for a mortgage, high demand |
| 8 | Price at market (±3%), good liquidity |
| 6 | Overpayment of 3–7% or one illiquidity flag |
| 4 | Overpayment of 7–15% or several flags, exposure longer than 150 days |
| 2 | Overpayment above 15%, an atypical property, not mortgage eligible |
| 0 | A share, a room or apartments (апартаменты) with overpayment and no demand |

Data: `valuation` (see `valuation-method.md`).

## 11. future: growth potential

| Score | Anchor |
|---|---|
| 10 | A confirmed metro station (`under_construction` or `aip`) nearby in a district with poor transport, not yet priced in; no threats |
| 8 | Confirmed improvements (park, school, transport hub (ТПУ)), a growing district |
| 6 | Neutral: an established district, plans without confirmation |
| 4 | There is a threat: construction in front of the windows, road widening |
| 2 | Several threats or a harmful facility in the plans |
| 0 | A confirmed harmful facility nearby (МСЗ, landfill, an outbound highway under the windows) |

Data: `future.catalysts` and `future.threats` (see `future-catalysts.md`). Rumours and announcements do not raise the score above 6.

## Specifics by property type

- **secondary:** the main focus is on resident reviews, the building's history and legal clearance.
- **new_build:** reviews of the building have no history. Use reviews of the developer's past residential complexes (ЖК), construction progress and delays instead. Internal noise is assessed by materials (see `house-series.md`, the monolith section). Check kindergartens and schools by the project plan and deadlines.
- **private_house:** see `private-house.md`. Transport is assessed by travel time by car and suburban train, noise by highway, railway and airport.
