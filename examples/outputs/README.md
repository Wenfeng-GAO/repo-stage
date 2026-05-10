# M1 Manual Golden Path Outputs

These examples manually exercise the RepoStage output contract before automation.

Each directory contains:

- `repo-profile.json`
- `site/index.html`
- `site/styles.css`
- `site/assets/` when source assets were available
- `README-gap-report.md`
- `validation-report.md`
- `desktop.png` and `mobile.png`

## Samples

| Sample | Source repository | Notes |
|---|---|---|
| `chalk/` | <https://github.com/chalk/chalk> | Strongest page. Real logo, screenshot, clear install command, specific feature set, and enough source material to be publishable after minor maintainer edits. |
| `commander/` | <https://github.com/tj/commander.js> | Tests a documentation-rich project without reusable visual assets. The page relies on code examples and parser concepts rather than branding. |
| `httpie-cli/` | <https://github.com/httpie/cli> | Tests richer product docs, copied media assets, community links, Python package metadata, and docs-first installation routing. |

## Manual Findings

- `repo-profile.v0` is sufficient for hero, features, quickstart, examples, trust, and gap reports.
- The quality checklist catches generic copy such as unsupported "best", "battle-tested", or "beautiful" claims.
- Missing screenshots or logo assets materially affects publishability, but the output can still be useful when the README has strong examples.
- Install CTAs must degrade to sourced documentation links when a README does not provide one canonical install command.
