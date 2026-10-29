# Data sources and search templates

For any city in Russia. Federal sources first, then regional ones. Placeholders: `{адрес}` (address), `{ЖК}` (residential complex), `{застройщик}` (developer), `{район}` (district), `{город}` (city), `{улица}` (street), `{дом}` (building). Search templates are in Russian: use them verbatim with placeholders filled in.

**Rule:** every fact in the report must have a `source_url`. Retell reviews in your own words (in Russian), verbatim quotes no longer than 15 words.

## Listings

| Source | What it gives | Access |
|---|---|---|
| cian.ru | Parameters, price history, publication date, comparables in the building | WebFetch is often blocked, a browser is needed |
| domclick.ru | Parameters, Sber valuation, mortgage, building analytics | Partially available |
| avito.ru | Parameters, private houses, often without price history | Almost always blocks bots, needs a browser or text from the user |
| realty.yandex.ru | Parameters, price history, building price analytics | Partially |
| etagi.com, n1.ru | Regional listings | Usually available |

If a page is unavailable, ask the user to paste the listing text.

## Building data

| Source | What it gives |
|---|---|
| reformagkh.ru | Year, series, material, floor slabs, wear, management company (УК), major repairs (капремонт) |
| dom.gosuslugi.ru (ГИС ЖКХ) | Official building passport data, emergency status, management company |
| Regional major repair fund (`фонд капремонта {город}`) | Schedule and completed works |
| dom.mingkh.ru | Series, wear, management company, emergency status |
| flatinfo.ru | Series, building passports, residents forum (especially Moscow) |
| citywalls.ru | Architecture, series, photos (Moscow, St Petersburg, others) |
| Management company site, regional management company ratings | Licence, complaints |

## Reviews

| Source | What |
|---|---|
| Яндекс Карты (building, ЖК, УК card) | Residents' reviews, ratings |
| 2ГИС | Reviews of the ЖК and УК |
| otzovik.com, irecommend.ru | Reviews of the ЖК and developers |
| ЖК forums (forumhouse, shared-construction investor sites) | Detailed reviews of construction and quality |
| VK groups of the district or ЖК | Complaints, district news, local problems |
| Telegram channels of the district | News, traffic jams, construction |

## Developers (new builds)

| Source | What |
|---|---|
| наш.дом.рф (ЕИСЖС) | Project declarations and their changes, permits, escrow bank, construction progress |
| erzrf.ru (ЕРЗ.РФ) | Developer rating by deadlines, share of delays |
| kad.arbitr.ru | Arbitration cases by ИНН (tax ID) |
| fedresurs.ru | Bankruptcy, material facts |
| rusprofile.ru, egrul.nalog.ru | Founders, finances, company age |

## Urban planning and future

| Source | What |
|---|---|
| fgistp.economy.gov.ru (ФГИС ТП) | General plans, zoning rules (ПЗЗ), territorial planning documents |
| nspd.gov.ru (НСПД, formerly ПКК) | Cadastral data, permitted use (ВРИ), zones with special use conditions (ЗОУИТ), boundaries |
| Administration sites | ПЗЗ, public hearings, territory planning projects (ППТ) |
| zakupki.gov.ru | Government construction contracts (status confirmation) |
| Regional АИП | Targeted investment programmes |

## Ecology

| Source | What |
|---|---|
| meteoinfo.ru / Росгидромет | Air quality by city |
| Regional monitoring (Мосэкомониторинг and equivalents) | Air stations |
| ecomap, landfill maps | Illegal dumps |
| iqair.com | Live air index |
| News «{район} запах», «{район} выбросы» | Residents' complaints |

## Safety

| Source | What |
|---|---|
| District news, regional media | Criminal incidents |
| мвд.рф, regional ГУ МВД | Statistics by district (if published) |
| District reviews | Perceived safety |

## Schools

| Source | What |
|---|---|
| Ratings of regional education departments | School position |
| School sites | Assigned catchment areas |
| schoolotzyv and equivalents | School reviews |

## Regional portals

- **Moscow:** mos.ru (renovation, programmes), stroi.mos.ru (construction, metro, transport hubs ТПУ), Мосгорстройнадзор, Moscow АИП, ag.mos.ru (public hearings), metro.mos.ru.
- **St Petersburg:** gov.spb.ru, КГА (kgainfo.spb.ru), metro site, РГИС СПб.
- **Other cities:** city and regional administration sites, regional urban planning portal, regional construction ministry site.

## Market

| Source | What |
|---|---|
| irn.ru | Price indices, Moscow analytics |
| ЦИАН analytics (cian.ru/analitika) | Prices by district, exposure time |
| Домклик analytics | Exposure time, bargaining |
| Индикаторы рынка недвижимости (irn.ru) | Dynamics |
| Дом.РФ (дом.рф analytics) | Rental yield, mortgage |
| cbr.ru | Key rate |
| moex.com (ОФЗ), bank sites | ОФЗ and deposit yields |

## Search templates

Building:
- `{адрес} серия дома год постройки`
- `{адрес} reformagkh`
- `{адрес} отзывы жильцов`
- `{адрес} слышимость шумоизоляция`
- `{адрес} аварийный OR снос OR расселение`
- `{адрес} управляющая компания отзывы`
- `{адрес} капремонт`

Residential complex and developer:
- `{ЖК} отзывы жильцов`
- `{ЖК} межквартирные стены слышимость`
- `{застройщик} перенос сроков сдачи`
- `{застройщик} банкротство OR арбитраж`
- `{ЖК} наш.дом.рф проектная декларация`

District:
- `{район} {город} отзывы жителей`
- `{район} {город} криминал новости`
- `{район} {город} экология запах промзона`
- `{район} {город} пробки утром выезд`
- `{район} {город} лучшие школы рейтинг`

Future:
- `{район} {город} строительство метро станция срок`
- `{район} {город} проект планировки территории`
- `{район} {город} КРТ комплексное развитие`
- `{улица} {город} публичные слушания строительство`
- `{район} {город} расширение дороги развязка`

Market:
- `{район} {город} цена квадратного метра вторичка {год}`
- `{город} срок экспозиции квартир {год}`
- `{город} доходность аренды квартир {год}`
- `{город} скидка на торг вторичка`
