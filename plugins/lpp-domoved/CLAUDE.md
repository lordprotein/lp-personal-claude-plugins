# lpp-domoved

## Language

- Internals are in English: `SKILL.md`, `commands/`, `agents/`, `references/`, schema and config comments, code comments, docstrings, CLI help, and messages only Claude reads (validation warnings, logs, errors).
- Everything the user sees is in Russian: `README.md`, chat replies, questions to the user, the HTML report and every text field that lands in it (summaries, pros and cons, evidence, checklists, verdicts, section titles, the report filename).
- Keep Russian where it is data rather than prose: search queries, names of real sources, documents and laws, regexes and selectors that match Russian listings, test fixtures.

## Checks

- Unit tests: `cd scripts && python3 -m unittest discover -s tests`
- No em dash (—) in agents, `SKILL.md` or `README.md`: a test fails on it.
