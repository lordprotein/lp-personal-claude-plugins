# Legal check: what to request and where to check

The plugin does not replace a lawyer and does not see closed data. Task: use open data to find risk signs and compile the lists `checklists.documents` and `checklists.questions_to_seller`.

Items of `checklists.documents` and `checklists.questions_to_seller` are written into the report in Russian. In the lists below each item is given as ready-made Russian wording for the report, with an English gloss in parentheses for orientation only: copy or adapt the Russian text, never the gloss.

Legal norms marked **[сверить]** (verify): article numbers and deadlines come from reviews and memory, check them against the current version (Консультант, pravo.gov.ru).

## Resale

### What to check yourself (open sources)

| What | Where | Risk sign |
|---|---|---|
| Seller bankruptcy | fedresurs.ru, kad.arbitr.ru by full name | Bankruptcy procedure or debts. The deal can be challenged within 1 year (if suspicious, up to 3 years) before bankruptcy **[сверить, ст. 61.2 закона о банкротстве]** |
| Court cases on the flat and the seller | District court sites, ГАС «Правосудие» | Title disputes, division of property |
| Enforcement proceedings | fssp.gov.ru | Debts, possible seizure |
| Passport validity | МВД (Interior Ministry) service | Invalid |
| Listing | Price, history, text | Price 20%+ below market, urgency, «собственник за границей» (owner abroad) |
| Emergency status and demolition | ГИС ЖКХ, regional programmes | Building is on the list |

### `checklists.documents` (resale)

- Выписка ЕГРН об объекте (основные характеристики и обременения), свежая, не старше 30 дней (ЕГРН extract on the property: main characteristics and encumbrances, fresh, not older than 30 days)
- Выписка ЕГРН о переходе прав (история собственников) (ЕГРН extract on transfers of rights: ownership history)
- Правоустанавливающий документ: договор купли-продажи, дарения, приватизации, свидетельство о наследстве (title document: sale, gift or privatization contract, inheritance certificate)
- Выписка из домовой книги или ЕЖД (кто зарегистрирован, кто выписан) (house register extract or unified housing document: who is registered, who was deregistered)
- Справка об отсутствии долгов за коммуналку и капремонт (certificate of no utility and major repair debts)
- Технический план или поэтажный план БТИ (сверка перепланировок) (technical plan or БТИ floor plan: check of redevelopments)
- Нотариальное согласие супруга на продажу, если квартира куплена в браке **[сверить, ст. 35 СК РФ]** (notarized spouse consent to the sale if the flat was bought during marriage)
- Справки из ПНД и НД о дееспособности продавца (или медосвидетельствование в день сделки) (psychiatric and narcological dispensary certificates of the seller's legal capacity, or a medical examination on the deal day)
- Если был маткапитал: документы о выделении долей детям **[сверить, 256-ФЗ ст. 10]** (if maternity capital was used: documents allotting shares to the children)
- Если собственники несовершеннолетние: разрешение органов опеки (if owners are minors: guardianship authority permission)
- Если наследство: свидетельство о наследстве, дата открытия наследства. Срок принятия 6 месяцев, суд может восстановить **[сверить, ГК ст. 1155]** (if inherited: inheritance certificate and date the inheritance opened; acceptance period is 6 months, a court can restore it)

### `checklists.questions_to_seller` (resale)

- Сколько лет вы владеете квартирой и как она к вам перешла? (how long have you owned the flat and how did you acquire it?)
- Кто зарегистрирован в квартире, все ли выпишутся до сделки? (who is registered in the flat, will everyone deregister before the deal?)
- Были ли отказники от приватизации? (were there people who declined privatization?)
- Использовали ли маткапитал? Выделены ли доли детям? (was maternity capital used? were shares allotted to the children?)
- Есть ли супруг(а), будет ли согласие? (is there a spouse, will there be consent?)
- Были ли перепланировки и узаконены ли они? (were there redevelopments and are they legalized?)
- Есть ли долги за ЖКУ и капремонт? (are there utility or major repair debts?)
- Почему продаёте и есть ли встречная покупка (цепочка)? (why are you selling and is there a linked purchase, i.e. a chain?)
- Готовы ли к расчёту через аккредитив или безопасные расчёты банка? (are you ready to settle via a letter of credit or a bank's safe settlement service?)

### Risk signs

- Frequent resales (2+ transfers in 3 years): `frequent_resales`.
- Sale by power of attorney, owner absent at the deal: `proxy_sale`.
- Recent inheritance (less than 3 years): `recent_inheritance`.
- Elderly single seller, relatives unaware: higher risk of the deal being challenged.
- Refusal of safe settlement.

## New build

### What to check yourself

| What | Where | Risk sign |
|---|---|---|
| Construction permit | наш.дом.рф | Missing, expired |
| Project declaration and its changes | наш.дом.рф | Frequent deadline shifts (`developer_delays`) |
| Escrow | наш.дом.рф (escrow bank) | No escrow (`no_escrow`, stop) |
| Developer rating | erzrf.ru | High share of delays |
| Courts | kad.arbitr.ru by ИНН | Lawsuits from shared-construction investors, bankruptcy (`developer_bankrupt`, stop) |
| Finances and founders | rusprofile.ru, ФНС | Shell company, founders with bankruptcies |
| Construction progress | наш.дом.рф (photos), forums | Construction stalled |

### `checklists.documents` (new build)

- ДДУ по 214-ФЗ **[сверить]** с условием об эскроу-счёте (shared construction agreement under 214-ФЗ with an escrow account clause)
- Разрешение на строительство (construction permit)
- Проектная декларация (актуальная версия) (project declaration, current version)
- Документы на земельный участок (собственность или аренда застройщика) (land plot documents: developer's ownership or lease)
- Для готового дома: разрешение на ввод, акт приёма-передачи (for a completed building: commissioning permit, acceptance certificate)

### Risk signs

- Preliminary contract, loan agreement, promissory note, housing cooperative (ЖСК) instead of ДДУ: `preliminary_contract` (stop).
- Payment directly to the developer, bypassing escrow.
- Price noticeably below market from a little-known developer.

## Private house and land plot (ИЖС, ЛПХ, СНТ)

### What to check yourself

| What | Where |
|---|---|
| Land category and permitted use (ВРИ) | nspd.gov.ru, ЕГРН extract |
| Boundaries (land survey, межевание) | nspd.gov.ru |
| ЗОУИТ | nspd.gov.ru (layer of zones with special use conditions) |
| ПЗЗ and general plan | fgistp.economy.gov.ru, administration site |
| Seizure plans, roads | General plan, ППТ |

### `checklists.documents` (private house)

- Выписки ЕГРН на участок и дом (ЕГРН extracts on the plot and the house)
- Межевой план (land survey plan)
- Технический план дома (technical plan of the house)
- ТУ и договоры на газ, электричество, воду, канализацию (technical connection conditions and contracts for gas, electricity, water, sewerage)
- Справка об отсутствии долгов в СНТ или ТСН (certificate of no debts to the СНТ or ТСН)
- Документы основания права (договор, наследство) (documents establishing title: contract, inheritance)
- Согласие супруга, если покупалось в браке (spouse consent if bought during marriage)

### `checklists.questions_to_seller` (private house)

- Какой ВРИ участка, можно ли прописаться? (what is the plot's permitted use, can one register residence there?)
- Установлены ли границы, были ли споры с соседями? (are boundaries established, were there disputes with neighbours?)
- Какие коммуникации подключены по договорам, какая мощность электричества? (which utilities are connected under contracts, what is the electrical capacity?)
- Чистят ли дорогу зимой, кто отвечает? (is the road cleared in winter, who is responsible?)
- Было ли подтопление весной? (was there spring flooding?)
- Сколько стоит отопление зимой в месяц? (how much does heating cost per month in winter?)

## Settlement safety

Recommend in the report (in Russian): a letter of credit (аккредитив) or a bank's safe settlement service, a check of the seller by a lawyer, title insurance when the history is risky (inheritance, frequent resales).
