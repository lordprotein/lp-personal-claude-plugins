# CLAUDE.md

Private Claude Code marketplace `lp-personal-claude-plugins`. Mostly markdown, JSON and YAML executed by Claude Code; `lpp-domoved` also has Python and JS scripts with unit tests.

## Structure

- `.claude-plugin/marketplace.json`: marketplace manifest, lists every plugin in `plugins/`
- `plugins/lpp-domoved/`: invoked as `/lpp-domoved:<name>`: `commands/`, `skills/property-due-diligence/`, `agents/`, `scripts/` (tests: `cd plugins/lpp-domoved/scripts && python3 -m unittest discover -s tests`)

## Editing guidelines

- Every plugin name starts with `lpp-`
- New plugin: new folder in `plugins/` with `.claude-plugin/plugin.json`, an entry in `marketplace.json` and a row in `README.md`
- Plugin-specific rules live in the plugin's own `CLAUDE.md`
- Every commit that changes a plugin bumps `version` in its `plugin.json` (semver: patch for fixes and wording, minor for new commands, skills or behavior, major for renames and removals). Without a bump installed copies do not update
- Run `claude plugin validate .` before pushing
