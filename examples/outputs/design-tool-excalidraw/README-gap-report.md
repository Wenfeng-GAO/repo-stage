# README Gap Report: excalidraw/excalidraw

RepoStage only uses sourced repository facts. The items below explain what was missing or weak.

- **low / ingestion-warning**: GitHub API metadata was unavailable; used shallow git clone fallback with reduced metadata.
- **medium / ingestion-error**: GitHub API request was forbidden or rate limited. Set GITHUB_TOKEN if the public API limit is exhausted.

## Output Contract

- `site/index.html`
- `site/styles.css`
- `repo-profile.json`
- `README-gap-report.md`
- `validation-report.md`
