# Catalysts and threats: how to verify and how to estimate growth

Text that lands in the report (catalyst and threat descriptions, `assumptions`) is written in Russian.

## Certainty scale (`status`)

| status | Meaning | How to confirm |
|---|---|---|
| `built` | The facility already operates | Map, operator site, opening news |
| `under_construction` | Construction is under way | Construction permit, government contract on zakupki.gov.ru, construction photos, stroi.mos.ru and equivalents |
| `aip` | In the targeted investment programme (АИП) with funding | Regional АИП document with year and amount |
| `plan` | In the general plan or an approved territory planning project (ППТ) | ФГИС ТП, administration site, public hearing minutes |
| `announced` | Announced by officials or the developer | News, interviews. No document |
| `rumor` | Rumours, forums, "people say" | No confirmation |

Rules:
- Only `built` (if opened less than 2 years ago), `under_construction` and `aip` go into the growth forecast (`forecast`).
- `plan` counts with a low weight. `announced` and `rumor` are shown in the report as «опционально» and do not enter the forecast.
- If there is a single source and it is a news announcement, the status is no higher than `announced`.

## Anticipation effect (`priced_in`)

The main premium is priced in at announcement, funding and start of construction, not at opening (McDonald & Osuji 1995: +17% before opening; Gibbons & Machin 2005; Crossrail experience).

How to determine `priced_in`:
- `true` if the facility was announced more than 2 years ago, construction is under way, and district prices have already grown faster than the city.
- `false` if the facility has just entered the АИП or received a permit, and district prices are still at the level of neighbouring ones.
- When in doubt, set `true` and estimate the effect at the lower bound.

For the buyer, the most profitable projects are confirmed but not yet priced in. Projects announced long ago mostly give liquidity, not growth.

## Effect guidelines (`effect_pct`, over 2–5 years relative to the city)

| Type | Effect | Conditions |
|---|---|---|
| Metro or МЦД station where transport is currently poor | +3…+10% | 400–1200 m from the building (Debrezion 2007, ЦИАН, Миэль, IRN.RU) |
| Metro station in a district that already has metro nearby | 0…+3% | Effect is mostly in liquidity |
| Exception: МЦД in Podolsk | up to +100% in new builds over 2019–2021 | Outlier, do not use as a norm |
| Renovation programme (реновация, Moscow), original flat | 0…+10% per year | ЦИАН 2019, data is heterogeneous, confidence medium |
| New large park nearby | qualitative, +0…+5% guideline | No quantitative Russian data |
| Integrated territorial development (КРТ) nearby | qualitative | Depends on what is built |
| New school or kindergarten in a new district | qualitative | Important for families |
| Transport hub (ТПУ), shopping centre | 0…+3% | May also bring noise |

## Threats (`threats`)

| Type | Effect | How to find |
|---|---|---|
| Construction in front of the windows | −3…−10% (view, light, construction noise for 2–4 years) | ГПЗУ, permits, public hearings on neighbouring plots, vacant lots and parking next to the building |
| Highway widening, new overpass | −0.4…−0.9% per dB of noise above 55 | ППТ of transport facilities |
| ТПУ or a large shopping centre under the windows | noise, traffic | ППТ |
| Industrial facility, waste incinerator (МСЗ), landfill | up to −13% nearby (Ready 2010) | General plan, АИП, news |
| Felling of a park or square | loss of greenery | Hearings, protests in the news |

A threat with status `aip` or higher closer than 2 km, if it is a harmful facility: `red_flags` `harmful_facility_planned` with level `stop`.

## Price growth scenarios for 3 and 5 years

Basis: Case & Shiller 1989 (the market is inertial: the annual change repeats at ¼–½ the next year), long-term reversion to fundamentals (price to rent and to incomes).

### Steps

1. **Base city dynamics.** Find the change in resale prices over the last year (`market_trend_1y_pct`) and over 3–5 years. Sources: IRN.RU, ЦИАН analytics, Домклик.
2. **Momentum (1–2 years).** `momentum = market_trend_1y_pct × (0.25…0.5)`.
3. **Long horizon (3–5 years).** Shift growth toward inflation (guideline: Central Bank forecast); if price to rent is above the historical norm (overheated market), bring it below inflation. If price to rent is low, allow growth above inflation.
4. **Catalyst premiums.** Add the midpoint of `effect_pct` for `under_construction` and `aip` with `priced_in: false`. For `priced_in: true` add the lower bound or 0.
5. **Threats.** Subtract the midpoint of the effect for confirmed threats.
6. **Widening for a single flat.** A forecast for a specific property is wider than the market one: widen the spread 1.5 times relative to the base.

### Formulas (guideline)

```
base_y3 = (1 + infl)^3 × (1 + momentum_adj) − 1 + Σ premiums − Σ threats
bear_y3 = base_y3 − 1.5 × σ3
bull_y3 = base_y3 + 1.5 × σ3
```

where `infl` is annual inflation per the Central Bank forecast, `momentum_adj` is the momentum adjustment for the first 1–2 years, `σ3` is the typical 3-year spread (guideline 8–12 p.p. for large cities).

Example: inflation 6%, last year trend +8%, metro station in the АИП at 700 m, not priced in (+3…+10%, take 6%), no threats.
- Base 3 years: 1.06³ − 1 ≈ 19%, momentum +2% in the first year, premium +6%: ≈ +27%.
- Bear: 27 − 15 ≈ +12%. Bull: 27 + 15 ≈ +42%.

Write the result to `future.forecast.y3/y5` in percent (nominal), and list the assumptions in `assumptions` (in Russian): inflation, trend, which catalysts are included.

## Mandatory disclaimer

A forecast is not a guarantee. Property prices depend on the Central Bank rate, mortgage programmes and the economy. The most reliable part of the forecast: catalysts and threats confirmed by actual construction. State this in the report in Russian.
