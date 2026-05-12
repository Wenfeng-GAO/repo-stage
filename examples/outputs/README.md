# RepoStage Example Outputs

These folders capture generated and hand-built outputs used to validate RepoStage milestones.

GitHub shows committed HTML files as source code in `blob` URLs. The repository publishes this directory through GitHub Pages, so use the preview links below to view each static page directly.

## M1 Manual Golden Path Outputs

These examples manually exercise the RepoStage output contract before automation.

Each M1 directory contains:

- `repo-profile.json`
- `site/index.html`
- `site/styles.css`
- `site/assets/` when source assets were available
- `README-gap-report.md`
- `validation-report.md`
- `desktop.png` and `mobile.png`

| Sample | Preview | Source repository | Notes |
|---|---|---|---|
| `chalk/` | [Open page](https://wenfeng-gao.github.io/repo-stage/chalk/site/) | <https://github.com/chalk/chalk> | Strongest page. Real logo, screenshot, clear install command, specific feature set, and enough source material to be publishable after minor maintainer edits. |
| `commander/` | [Open page](https://wenfeng-gao.github.io/repo-stage/commander/site/) | <https://github.com/tj/commander.js> | Tests a documentation-rich project without reusable visual assets. The page relies on code examples and parser concepts rather than branding. |
| `httpie-cli/` | [Open page](https://wenfeng-gao.github.io/repo-stage/httpie-cli/site/) | <https://github.com/httpie/cli> | Tests richer product docs, copied media assets, community links, Python package metadata, and docs-first installation routing. |

Manual findings:

- `repo-profile.v0` is sufficient for hero, features, quickstart, examples, trust, and gap reports.
- The quality checklist catches generic copy such as unsupported "best", "battle-tested", or "beautiful" claims.
- Missing screenshots or logo assets materially affects publishability, but the output can still be useful when the README has strong examples.
- Install CTAs must degrade to sourced documentation links when a README does not provide one canonical install command.

## M2 Representative Runs

These folders were generated with:

```bash
python3 -m repo_stage.cli generate <repo-url> --out examples/outputs/<name>
```

| Category | Repository | Output | Preview | Validation |
|---|---|---|---|---|
| CLI tool | `https://github.com/sharkdp/fd` | `cli-tool-fd/` | [Open page](https://wenfeng-gao.github.io/repo-stage/cli-tool-fd/site/) | Passed |
| React/UI library | `https://github.com/radix-ui/primitives` | `react-ui-radix-primitives/` | [Open page](https://wenfeng-gao.github.io/repo-stage/react-ui-radix-primitives/site/) | Passed |
| AI agent project | `https://github.com/openai/openai-agents-python` | `ai-agent-openai-agents-python/` | [Open page](https://wenfeng-gao.github.io/repo-stage/ai-agent-openai-agents-python/site/) | Passed |
| Developer infrastructure | `https://github.com/astral-sh/uv` | `dev-infra-uv/` | [Open page](https://wenfeng-gao.github.io/repo-stage/dev-infra-uv/site/) | Passed |
| Design/creative tool | `https://github.com/excalidraw/excalidraw` | `design-tool-excalidraw/` | [Open page](https://wenfeng-gao.github.io/repo-stage/design-tool-excalidraw/site/) | Passed |

Each M2 output directory contains `site/`, `repo-profile.json`, `README-gap-report.md`, and `validation-report.md`.
