# Investment block: yield, "buy or rent"

The `investment` block in the JSON. It also matters for those buying to live in: it shows whether the buyer overpays for ownership compared to renting and risk-free investments.

Text that lands in the report (`buy_vs_rent` and other comments) is written in Russian.

## 1. Rent

Find the rental rate for similar flats in the building or district (ЦИАН, Авито, Яндекс Недвижимость). Take the median of 3–5 listings, bargaining discount on rent ~3–5%. Write it to `rent_month`.

## 2. Gross yield

```
gross_yield_pct = rent_month × 12 / price × 100
```

## 3. Net yield

```
income = rent_month × 12 × (1 − vacancy)
expenses = tax + property tax + major repair fee + wear reserve + insurance
net_yield_pct = (income − expenses) / (price + renovation + transaction costs) × 100
```

Parameters (guideline, `config/adjustments.json`):
- vacancy 8–15% per year (1–2 months);
- tax: НПД (self-employed tax) 4%, НДФЛ (personal income tax) 13% (15% for high income), ИП УСН (sole proprietor simplified tax) 6%;
- major repair fee (капремонт): by region, ₽/m² per month;
- wear and cosmetic repair reserve: 0.5–1 month's rent per year;
- transaction costs: realtor, registration, notary if needed, 1–3% of the price.

Net yield is usually 1.5–2.5 p.p. below gross.

### Example

Flat 12 000 000 ₽, rent 55 000 ₽/month, НПД 4%, vacancy 10%, major repair 54 m² × 25 ₽ × 12 = 16 200 ₽, reserve 40 000 ₽, property tax 8 000 ₽, transaction costs 200 000 ₽.

- Gross: 55 000 × 12 / 12 000 000 = 5.5%.
- Income: 660 000 × 0.9 = 594 000. Tax: 594 000 × 4% = 23 760.
- Expenses: 23 760 + 8 000 + 16 200 + 40 000 = 87 960.
- Net: (594 000 − 87 960) / 12 200 000 ≈ 4.1%.

## 4. Comparison with risk-free investments

- `ofz_yield_pct`: yield of 3–5 year ОФЗ (government bonds) (moex.com, rusbonds, broker sites).
- `deposit_rate_pct`: average one-year deposit rate (published by the Central Bank, сравни.ру and banks).

Net yield plus expected price growth must exceed the ОФЗ yield for buying to let to make sense. In 2025 deposits were roughly three times more profitable than letting (РГ): this is normal for a period of high rates.

Scale for the report (large cities):
- gross below 5%: typical but weak;
- 5–8%: normal;
- above 8%: high, but check vacancy risk and liquidity (often small cities or complex properties).

## 5. Gross yield benchmarks (guideline)

| City | Gross, % | Source |
|---|---|---|
| Moscow | 4–4.7 | Дом.РФ 2025, «Мир квартир» |
| St Petersburg | 4.9 | Дом.РФ 2025 |
| Regions (average) | 5.5 | Дом.РФ 2025 |
| Astrakhan | 9.4 | «Мир квартир» |
| Nizhny Tagil | 8.6 | «Мир квартир» |
| Khabarovsk | 8.4 | «Мир квартир» |
| Cherepovets | 8.2 | «Мир квартир» |

The data changes every year: when possible, update it with the search `{город} доходность аренды {год}`.

## 6. Price to rent and cost of ownership

```
price_to_rent = price / (rent_month × 12)
```

Cost of ownership (user cost, Himmelberg, Mayer & Sinai 2005):

```
user_cost_pct = risk-free rate + property tax + wear and maintenance (2–3) + risk premium (~2) − expected price growth
```

Buying beats renting if annual rent is greater than `price × user_cost_pct / 100`. Equivalently: fair price to rent = 100 / user_cost_pct.

### Example

ОФЗ 14%, tax 0.1%, wear 2.5%, premium 2%, expected growth 6%: user cost = 14 + 0.1 + 2.5 + 2 − 6 = 12.6%. Fair `price_to_rent` = 100 / 12.6 ≈ 7.9. Actual at 12 млн and 55 тыс.: 12 000 000 / 660 000 ≈ 18.2. In this model renting is 2+ times more profitable than buying while the rate is high.

Important (authors' conclusion): compare price to rent with user cost, not with its historical average. When the Central Bank rate falls, the fair ratio rises.

## 7. `buy_vs_rent`

State the conclusion in one sentence in Russian, for example:
- «При текущей ставке аренда финансово выгоднее; покупка оправдана, если горизонт 7+ лет и ожидается снижение ставки».
- «Покупка близка к паритету с арендой».

## 8. Caveats

- The calculation does not model the mortgage separately: with a mortgage, use the loan rate instead of the risk-free rate for the borrowed part.
- The tax deduction (up to 260 тыс. ₽ on the purchase and up to 390 тыс. ₽ on interest: verify against the current version of the Tax Code, НК) improves the economics of buying to live in.
- This is not investment advice.
