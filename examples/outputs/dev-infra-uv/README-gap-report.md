# README Gap Report: astral-sh/uv

RepoStage only uses sourced repository facts. The items below explain what was missing or weak.

- **low / ingestion-warning**: GitHub API metadata was unavailable; used shallow git clone fallback with reduced metadata.
- **medium / ingestion-error**: GitHub API request was forbidden or rate limited. Set GITHUB_TOKEN if the public API limit is exhausted.
- **low / unclear-use-cases**: Heuristic use-case suggestions are kept out of the generated site until they can be tied to exact source facts.

## Output Contract

- `site/index.html`
- `site/styles.css`
- `repo-profile.json`
- `README-gap-report.md`
- `validation-report.md`
