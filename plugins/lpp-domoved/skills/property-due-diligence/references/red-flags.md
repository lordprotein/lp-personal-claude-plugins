# Red flags and stop factors

Flags are recorded in `red_flags[]` with the fields `id`, `title`, `severity`, `criterion`, `detail`, `source_url`. The `title` and `detail` fields go into the report: write them in Russian.

Severity levels:
- `stop`: the total is capped at 5.4 («Не рекомендуется» or worse), whatever the other scores are. Set it only when confirmed by a fact or a reliable source.
- `major`: −0.3 to the total per flag, but no more than −1.0 in total. Requires checking before the transaction.
- `minor`: does not affect the total, is shown in the report and goes into the checklist.

If a sign is only a suspicion (one review, indirect data), lower the level by one step and write «требует проверки» ("requires verification") in `detail`.

## Building and structures (criterion: building)

| id | severity | Sign |
|---|---|---|
| `emergency_house` | stop | The building is declared unsafe (аварийный), subject to demolition or resettlement outside the renovation programme |
| `wooden_slabs` | major | Wooden or mixed floor slabs: fire hazard, audibility, refusal by insurers and banks |
| `high_wear` | major | Wear above 60% according to ГИС ЖКХ or реформагкх |
| `structural_cracks` | major | Cracks in load-bearing walls, foundation settlement according to reviews or news |
| `no_capital_repair_long` | minor | No capital repair for more than 30 years and none planned in the next 5 years |
| `bad_management_company` | minor | Management company (УК) with mass complaints, lawsuits, licence revocation |
| `gas_in_highrise` | minor | Gas in a building taller than 10 floors (risk, restrictions on redevelopment) |
| `mold_leaks` | minor | Systematic roof leaks, mould, basement flooding |
| `listing_condition_contradiction` | minor | The listing contradicts itself about condition (e.g. «требует ремонта» in the parameters and «хороший ремонт» in the description): check at the viewing, factor the renovation into the bargaining |

## Legal (criterion: legal)

| id | severity | Sign |
|---|---|---|
| `developer_bankrupt` | stop | The developer is in bankruptcy proceedings, the permit is revoked, construction is frozen |
| `no_escrow` | stop | A new build without escrow accounts (except legal exemptions), payment directly to the developer |
| `preliminary_contract` | stop | A preliminary contract, loan agreement or promissory note scheme instead of a ДДУ |
| `encumbrance_arrest` | stop | Arrest, ban on registration actions, court dispute over the title |
| `seller_bankruptcy` | major | The seller is in bankruptcy proceedings or shows signs of imminent bankruptcy (Федресурс, courts). The transaction may be challenged |
| `frequent_resales` | major | 2+ transfers of title in the last 3 years |
| `recent_inheritance` | major | Title by inheritance less than 3 years ago. If less than 6 months have passed since the inheritance was opened, this is `stop` until the period expires |
| `children_shares_unallocated` | major | Maternity capital was used, but the children's shares were not allocated |
| `minors_owners` | minor | Minors are among the owners: guardianship authority consent is required |
| `privatization_refusers` | major | People who refused privatization are registered there: lifelong right of residence |
| `registered_residents` | minor | People are registered there who will not deregister before the transaction |
| `seller_mortgage_encumbrance` | minor | The apartment is pledged under the seller's mortgage: transaction through the seller's bank, repayment of the debt and removal of the encumbrance, settlement via letter of credit or СБР (secure settlement service) |
| `proxy_sale` | major | Sale by power of attorney, the owner is unavailable |
| `price_far_below_market` | major | Price 20% or more below market without an explainable reason, pressure to close quickly |
| `unapproved_redevelopment` | major | Unapproved redevelopment, especially relocation of wet areas and removal of load-bearing walls |
| `developer_delays` | major | The developer delayed deadlines on this or past residential complexes (ЖК) by more than 6 months |
| `apartments_status` | minor | Apartments (апартаменты), not a flat: no permanent registration, higher taxes and utility bills |
| `share_or_room` | major | A share or a room is for sale: liquidity problems and the pre-emptive purchase right |

## Surroundings and ecology (criterion: ecology, noise, safety)

| id | severity | Sign |
|---|---|---|
| `powerline_close` | major | High-voltage power line (ЛЭП) closer than 100 m (closer than 30 m is usually `stop` for housing) |
| `landfill_incinerator` | stop | Solid waste landfill (полигон ТБО) or waste incineration plant closer than 2 km |
| `landfill_far` | major | Landfill or incinerator (МСЗ) 2–5 km away on the downwind side |
| `industrial_szz` | major | The property falls within the sanitary protection zone (СЗЗ) of an industrial enterprise or thermal power plant (ТЭЦ) |
| `flood_zone` | major | Flood or waterlogging zone, complaints about basements and roads in spring |
| `airport_glide_path` | major | Under an airport glide path or in an aircraft noise zone |
| `railway_close` | major | Railway tracks closer than 100 m, especially freight and night trains |
| `highway_close` | major | A major road or outbound highway closer than 50 m with windows facing it |
| `bar_under_windows` | major | A bar, hookah lounge, nightclub or 24/7 cafe on the ground floor of the building or in the courtyard |
| `cemetery_close` | minor | Cemetery closer than 300 m (affects liquidity) |
| `cell_tower_roof` | minor | Cellular base station on the building's roof |
| `problem_facility` | minor | Psychiatric clinic (ПНД), drug treatment clinic, correctional facility, homeless shelter nearby |
| `market_station_close` | minor | Market, railway station, dormitories near the entrance |

## Future (criterion: future)

| id | severity | Sign |
|---|---|---|
| `construction_blocks_view` | major | Confirmed construction (ГПЗУ, permit) in front of the windows, will block the view and light |
| `road_expansion` | major | Road widening, a new overpass or interchange nearby under an approved territory planning project (ППТ) |
| `harmful_facility_planned` | stop | An МСЗ, landfill or large harmful production planned closer than 2 km with status `aip` or higher |
| `krt_demolition` | minor | The building is in a comprehensive territory development (КРТ) zone: can be a plus (resettlement) or an uncertainty |

## Liquidity (criterion: value_liquidity)

| id | severity | Sign |
|---|---|---|
| `not_mortgage_eligible` | major | The property is not mortgage eligible: floor slabs, unsafe status, redevelopment, debts. Narrows the pool of buyers on resale |
| `overpriced_15` | major | Overpayment above 15% of fair price |
| `atypical_object` | minor | Atypical area, layout or price per m² for the building and district |
| `long_exposure` | minor | Exposure longer than 150 days or repeated price reductions |
| `first_floor_no_commercial` | minor | Ground floor without commercial potential |
| `walk_through_rooms` | minor | Walk-through rooms |
| `small_kitchen` | minor | Kitchen smaller than 6 m² |

## Private house (criterion: legal, building, ecology)

| id | severity | Sign |
|---|---|---|
| `snt_no_izhs` | major | СНТ or ЛПХ without the possibility of permanent registration and building a residential house |
| `wrong_land_category` | stop | Agricultural or forest fund land without a permitted use (ВРИ) for housing |
| `zouit_restrictions` | major | The plot is in a ЗОУИТ (protection zones of power lines, gas pipelines, water protection, airfield vicinity): construction restrictions |
| `no_survey` | major | Plot boundaries are not established (no land survey, межевание) |
| `house_not_registered` | major | The house is not registered in ЕГРН |
| `no_gas_no_power` | major | No gas and power below 15 kW without technical conditions (ТУ) for an increase |
| `seasonal_access` | major | No year-round access, the road is not cleared |
| `seasonal_flooding` | major | Seasonal flooding of the plot or basement |
| `public_seizure_plan` | stop | The plot is subject to seizure for state needs under the master plan (генплан) or ППТ |

## Total capping rule

1. If there is at least one `stop`, the total is `min(total, 5.4)`. The verdict is no higher than «Не рекомендуется».
2. Each `major` deducts 0.3, no more than 1.0 in total.
3. In the report the «Стоп-факторы» block comes second, right after the total.
