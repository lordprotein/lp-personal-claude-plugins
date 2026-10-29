---
description: Show the Domoved methodology: criteria, profile weights, stop factors and sources
argument-hint: "[criterion or profile, optional]"
---

Explain the Domoved scoring methodology to the user briefly and clearly, in Russian.

Request: $ARGUMENTS

Sources:
- weights and thresholds: `${CLAUDE_PLUGIN_ROOT}/config/profiles.json`;
- rubrics: `${CLAUDE_PLUGIN_ROOT}/skills/property-due-diligence/references/criteria.md`;
- stop factors: `${CLAUDE_PLUGIN_ROOT}/skills/property-due-diligence/references/red-flags.md`;
- literature: `${CLAUDE_PLUGIN_ROOT}/skills/property-due-diligence/references/literature.md`.

If the request is empty, show:
1. a table of the 11 criteria with the weights of all four profiles;
2. the verdict scale;
3. the stop factor rule (total no higher than 5,4) and the penalties for serious flags;
4. how data confidence is taken into account;
5. 3 to 5 key studies the methodology is based on.

If a criterion or profile is given, describe only it in detail: what it includes, how the score is set, where the data comes from, what to check in person.
