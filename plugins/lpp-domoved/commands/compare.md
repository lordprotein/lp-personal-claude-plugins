---
description: Compare several apartments or houses on all criteria and pick the best one
argument-hint: "<link1> <link2> [...] [--profile balance|family|investment|quiet] [--theme light|dark]"
---

Compare the properties using the Domoved methodology.

User input: $ARGUMENTS

Follow the "Comparison" section in the `property-due-diligence` skill: `${CLAUDE_PLUGIN_ROOT}/skills/property-due-diligence/SKILL.md`.

Requirements:
- Talk to the user in Russian; all report text is in Russian.
- 2 to 6 properties are needed. If there is only one, suggest `/lpp-domoved:check`.
- Each property is checked in quick mode with the same profile so the scores are comparable.
- Result: one comparison HTML with a «Сохранить PDF» button (a "criterion × property" table, the winner and an explanation of where it wins and where it loses). In the chat, one line (in Russian) with the winner and the path to the HTML.
- If a property has a stop factor, it cannot be the winner until the stop factor is cleared by a check.
