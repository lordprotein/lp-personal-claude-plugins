# Fair price and liquidity

Method: sales comparison approach (Russian valuation standards ФСО, The Appraisal of Real Estate, RICS Red Book). Numeric guidelines live in `config/adjustments.json`; they are not reconciled with the paid Leifer (Лейфер) and СтатРиелт handbooks.

Text that lands in the report (`valuation.comment` and similar fields) is written in Russian.

## 1. Selecting comparables

- **Count:** 3–7. Fewer than 3: `confidence: "low"`.
- **Where:** the same building, neighbouring buildings of the same type, the same district. First the building, then a 500 m radius, then 1.5 km.
- **Similarity criteria:** property type (resale/new build), number of rooms, area ±25%, building type, number of floors, year ±10 years.
- **Asking prices**, not transaction prices: apply a bargaining discount to each.
- Save every comparable in `valuation.comparables[]`: `url`, `price`, `area`, `price_per_m2`.

## 2. Order of adjustments

Adjustments are applied to the comparable's price per m² **sequentially**, in this order:

1. **Bargaining** (`bargain`): asking price → transaction price.
2. **Date** (`date`): if the listing is older than 3 months, adjust for market change.
3. **Location and metro** (`location_metro`).
4. **Building type and walls** (`house_type_walls`).
5. **Floor** (`floor`).
6. **Area** (`area`).
7. **Condition and finish** (`condition`).

An adjustment always brings the comparable to the characteristics of the **subject** property. If the comparable is better, the adjustment is negative.

## 3. Adjustment guidelines (% of price per m²)

| Factor | Guideline |
|---|---|
| 1st floor vs a middle floor | −10…−5 |
| Top floor | −5…−2 (new build with a technical floor: 0) |
| Monolithic or brick vs panel | +5…+10 |
| Block vs panel | −3…0 |
| Wooden building | −20…−10 |
| Metro within 10 minutes walk vs transport access (Moscow, St Petersburg) | +5…+15 |
| Area: every +10% of area | −3…−1 to price per m² |
| No finish / needs renovation | −15…−8 / −10…−5 |
| Cosmetic finish | 0 (base) |
| Euro-renovation / designer | +5…+10 / +8…+15 |
| Apartments status (апартаменты) vs a flat | −20…−10 |

For floor adjustments do not use the АВОК coefficients 0.8/0.9: they are for utility calculations, not market coefficients.

## 4. Bargaining discount by city

| City | Discount, % |
|---|---|
| Default | 5 (range 3–11) |
| Moscow | 6 (5–10 per IRN.RU) |
| St Petersburg | 6 |
| Nizhny Novgorod | 10.8 |
| Krasnodar | 9.5 |
| Krasnoyarsk | 9.3 |
| Yekaterinburg | 7.5 |
| Voronezh | 7.3 |
| Ufa | 7.0 |

Sources differ roughly twofold («Этажи» 2025: average 6.3%; Норматив: 3.5–4%). If the property has been listed for long or the price was cut, take the upper bound.

## 5. Weighting and quality check

For each comparable:
- `net_adj_pct` = sum of signed adjustments.
- `gross_adj_pct` = sum of absolute adjustments.
- Comparable weight = `1 / (1 + gross_adj_pct)`, then normalize.

Quality rules:
- `net_adj_pct` greater than 15% in absolute value or `gross_adj_pct` greater than 25%: weak comparable. Keep it, but lower `confidence`. If more than half are like this, look for other comparables.
- Spread of adjusted prices per m² greater than 20%: `confidence: "low"`.

**Same-building check.** If a comparable in the same building differs from the final fair price per m² by more than 10%, you must explain it in `valuation.comment` (in Russian):
- which adjustments produced the difference (floor, area, renovation, bargaining, exposure date);
- why the result is more reliable than the neighbour's price.

If there is no explanation, revisit the adjustments: a price in the same building is usually the strongest reference.

## 6. Calculation example

Subject: 2-room, 54 m², panel П-44Т, 3rd floor of 17, cosmetic finish, 12 minutes to metro. Price 14 500 000 ₽ (268 519 ₽/m²). Moscow, bargaining 6%.

| Comparable | ₽/m² | Bargain | Walls | Floor | Area | Condition | Net total | Adj. ₽/m² | gross |
|---|---|---|---|---|---|---|---|---|---|
| A: same building, 1st floor, 52 m² | 255 000 | −6 | 0 | +7 | 0 | 0 | +1 | 257 550 | 13 |
| B: neighbouring monolithic, 7th floor, 58 m², euro | 310 000 | −6 | −8 | 0 | +1 | −7 | −20 | 248 000 | 22 |
| C: П-44Т, 9th floor, 54 m² | 270 000 | −6 | 0 | 0 | 0 | 0 | −6 | 253 800 | 6 |

(Adjustments are added in a simplified way here; for accuracy apply them sequentially.)

Weights: A 1/1.13 = 0.885; B 1/1.22 = 0.820; C 1/1.06 = 0.943. Sum 2.648.
Fair price per m² = (257 550 × 0.885 + 248 000 × 0.820 + 253 800 × 0.943) / 2.648 ≈ 253 250 ₽.
Fair price = 253 250 × 54 ≈ 13 676 000 ₽. Range ±5% (`fair_low`, `fair_high`).
Comparable B violates the net 15% rule: confidence `medium`.

## 7. Overpayment or underpayment

```
over_under_pct = (asking_price − fair_price) / fair_price × 100
```

In the example: (14 500 000 − 13 676 000) / 13 676 000 ≈ +6.0%: 6% overpayment, there is room to bargain.

Interpretation: below −5% is a bargain (but find the reason), −5…+3% at market, +3…+7% moderate overpayment, +7…+15% noticeable, above +15% flag `overpriced_15`.

## 8. Liquidity

**Exposure time** (Домклик, Яндекс 2025):
- up to 60 days: fast;
- 60–110 days: normal (Russia ~100, Moscow ~107);
- 110–150: slow;
- over 150: illiquid, flag `long_exposure`.

**Atypicality** (Haurin 1988): the more the property differs from the typical one in the building and district (area, layout, price per m², type), the longer it takes to sell. Signs: area differs from the district median by more than 50%, unusual layout, price per m² differs from the building median by more than 20%.

**Overpricing** (Genesove & Mayer 2001): sellers unwilling to sell at a loss overprice and sell longer. Price cuts in the listing history confirm this and give an argument for bargaining.

**Illiquidity flags** (`valuation.liquidity_flags`): `first_floor`, `walk_through_rooms`, `kitchen_lt_6`, `combined_bathroom_2plus_rooms`, `wooden_slabs`, `share_or_room`, `apartments_status`, `old_series`, `unapproved_redevelopment`, `not_mortgage_eligible`, `atypical_size`, `overpriced_vs_fair`, `price_cuts_history`.

**Mortgage** (`mortgage_eligible`): `false` with unapproved redevelopment, wooden floor slabs, emergency status, stove heating, debts and encumbrances, a very old building. This is the flag `not_mortgage_eligible` (major): most future buyers take a mortgage.

## 9. Noise discount (`noise_discount_pct`)

NDI index (Nelson 1982, 2004; Bristow 2015): every dB above 55 lowers the price.

```
noise_discount_pct = max(0, L_дБ − 55) × NDI
```

NDI: road 0.4–0.9 (use 0.6), aircraft 0.67, railway 0.2–0.7 (use 0.4).

Example: windows facing the street, 65 dB from the road: (65 − 55) × 0.6 = 6%. For a 14 млн flat that is about 840 тыс. ₽. Show the amount in the report as «цена шума».

Take `L_дБ` from `geo.noise_estimate.est_db_combined` (script estimate). It is an approximation: check it yourself at the viewing.
