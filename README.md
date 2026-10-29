# lp-personal-claude-plugins

Private Claude Code marketplace. Plugin names start with `lpp-`.

| Plugin | What's inside |
|--------|---------------|
| `lpp-domoved` | `/lpp-domoved:check`, `/lpp-domoved:compare`, `/lpp-domoved:criteria`: pre-purchase check of an apartment or a house |

## Installation

The repository is private, so Claude Code needs SSH access to it.

```
/plugin marketplace add git@github.com:lordprotein/lp-personal-claude-plugins.git
/plugin install lpp-domoved@lp-personal-claude-plugins
```

To bootstrap a new machine automatically, add to the user `settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "lp-personal-claude-plugins": {
      "source": { "source": "git", "url": "git@github.com:lordprotein/lp-personal-claude-plugins.git" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "lpp-domoved@lp-personal-claude-plugins": true
  }
}
```

## Updating

Each plugin has a semver `version` in its `plugin.json`. Installed copies update only when the version changes. Updates arrive via auto-update or `/plugin marketplace update lp-personal-claude-plugins`.

## Local development

```
claude --plugin-dir ./plugins/lpp-domoved
```
