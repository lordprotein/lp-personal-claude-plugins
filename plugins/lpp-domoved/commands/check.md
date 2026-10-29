---
description: Check an apartment or house before purchase by link (ЦИАН, Домклик, Авито, maps) or address
argument-hint: "<link or address> [--profile balance|family|investment|quiet] [--quick] [--theme light|dark] [--fresh]"
---

Run a pre-purchase check of the property using the Domoved methodology.

User input: $ARGUMENTS

Follow the `property-due-diligence` skill of this plugin strictly: the file `${CLAUDE_PLUGIN_ROOT}/skills/property-due-diligence/SKILL.md`. Read it if it is not loaded yet.

Talk to the user in Russian. If the input is empty, briefly ask (in Russian) for a link or an address and show examples:
- `/lpp-domoved:check https://www.cian.ru/sale/flat/123456789/`
- `/lpp-domoved:check https://yandex.ru/maps/?ll=37.6176,55.7558&z=17 --profile family`
- `/lpp-domoved:check "Москва, Профсоюзная 140к2" --quick`

Profiles:
- `balance` (default, noise first)
- `family` (schools, kindergartens, greenery)
- `investment` (price, liquidity, growth)
- `quiet` (maximum weight of quietness)

Result: one HTML report with a readable name in the reports folder, with a «Сохранить PDF» button inside. If `--theme` is not passed, first ask the user (in Russian) for the report theme (light or dark): the report opens with it. At the end, only one line in the chat (in Russian) with the score and verdict, the path to the HTML and a note about the PDF button.
