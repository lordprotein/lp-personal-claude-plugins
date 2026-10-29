# Private house and land plot: inspection

`object.type = "private_house"`. The `building` criterion is called «Дом и участок» in the report.

Text that lands in the report (findings, checklists, recommendations) is written in Russian.

## 1. Land and status

| What to check | Where | Good | Bad |
|---|---|---|---|
| Land category | НСПД (nspd.gov.ru), ЕГРН extract | Settlement lands (земли населённых пунктов) | Agricultural without residential permitted use, forest fund (`wrong_land_category`, stop) |
| Permitted use (ВРИ) | НСПД, ЕГРН | ИЖС | ЛПХ field plot (полевой участок, building not allowed); garden plot in an СНТ (allowed, with caveats) |
| ИЖС / ЛПХ household plot (приусадебный) / СНТ | ЕГРН, СНТ charter | ИЖС: residence registration, gas, tax deduction, mortgage | СНТ: road and utilities on the partnership's balance, fees, harder mortgage (`snt_no_izhs`, major) |
| Land survey (межевание) | НСПД (boundaries visible on the map) | Boundaries established | No boundaries (`no_survey`, major), overlap with neighbours |
| ЗОУИТ | НСПД, zones layer | None | Protection zones of power lines, gas pipeline, water protection, aerodrome vicinity (`zouit_restrictions`, major) |
| ПЗЗ and general plan | ФГИС ТП, administration site | Residential zone | Road plans, seizure (`public_seizure_plan`, stop) |
| House registration | ЕГРН | House registered, area matches | Not registered or area differs a lot (`house_not_registered`, major) |

## 2. Utilities

| What | Norm | What to look at |
|---|---|---|
| Gas | Mains gas brought into the house | If there is no gas, find out about the free gas connection programme (догазификация), cost and timing. Gas cylinder or electric heating: expensive heating |
| Electricity | 15 kW or more | Less than 15 kW without technical conditions (ТУ) for an increase: `no_gas_no_power` (major) if there is also no gas |
| Water | Central or a borehole with water analysis | Well, poor water, high iron |
| Sewerage | Central, septic tank or local treatment plant (ЛОС) | Cesspit, no pump-out |
| Heating | Gas boiler, underfloor heating | Stove only (banks and insurers are cautious) |
| Internet and connectivity | Fibre, stable 4G | No connectivity |

Ask to see the ТУ (technical connection conditions) and connection contracts.

## 3. Structure

| Element | What to check |
|---|---|
| Foundation | Type (strip, slab, piles), cracks, settlement, waterproofing |
| Walls | Material: brick, aerated concrete, timber, frame. Year, insulation |
| Roof | Material, leaks, attic insulation |
| Insulation | Winter heat loss, heating bills |
| Moisture | Mould, damp basement, smell |
| Windows and doors | Type, condition |

Sound insulation inside a private house hardly matters (no neighbours behind the wall). External noise matters: highway, railway, airport.

## 4. Access and surroundings

- **Winter access:** asphalt or dirt road, whether it is cleared, who is responsible (`seasonal_access`, major).
- **Seasonal flooding:** lowland, groundwater, spring floods (`seasonal_flooding`, major). Search: `{посёлок} подтопление весна`.
- **Settlement status:** gated cottage settlement, old village, СНТ. Fees, roads, lighting.
- **Neighbours:** abandoned plots, dumps, noisy farms, temporary cabins.
- **Water nearby:** a plus for the view, a minus if there is a flood risk.

## 5. Criteria adaptation

| Criterion | How to score for a private house |
|---|---|
| noise | External noise only: highway (an arterial road closer than 300 m is noticeable), railway, airport, neighbouring production, shooting ranges. A quiet settlement far from highways: 9–10 |
| building | Structure, utilities, plot (area, shape, terrain). Gas + 15 kW + central water: good |
| legal | Land, ВРИ, land survey, ЗОУИТ, house registration |
| transport | Driving time to the city at rush hour, commuter train (walk or drive to the station), bus. Impossible to live without a car: 4 and below |
| ecology | Industrial facilities, landfills, fertilized fields, poultry farms, power lines |
| green | Usually high, a forest nearby gives 9–10 |
| kids | School in the settlement or school bus, kindergartens |
| amenities | A shop in the settlement is normal, everything else in the city. Scale is 2 points softer |
| safety | Settlement security, thefts, reviews |
| value_liquidity | Private houses sell slower than flats (exposure of 6–12 months is normal). A non-standard house is even less liquid |
| future | New roads (plus for access, minus for noise), gasification, city expansion |

## 6. Document checklist

Ready-made Russian wording for the report, English gloss in parentheses:

- Выписка ЕГРН на дом и участок (ЕГРН extract on the house and plot)
- Межевой план (land survey plan)
- Технический план дома (technical plan of the house)
- ТУ и договоры на газ, электричество, воду (technical conditions and contracts for gas, electricity, water)
- Справка об отсутствии долгов в СНТ или посёлке (certificate of no debts to the СНТ or settlement)
- Устав СНТ и размер взносов (СНТ charter and fee amount)
- Градостроительный план земельного участка (ГПЗУ) при планах достройки (urban planning plan of the plot, if extension is planned)

## 7. What to check at the viewing

- Come in the rain or after snow: see how the road and water behave
- Look at the basement and attic
- Find out the winter heating bills
- Talk to neighbours: water, power, roads, thefts
- Check water pressure and power capacity (switch on several appliances)
