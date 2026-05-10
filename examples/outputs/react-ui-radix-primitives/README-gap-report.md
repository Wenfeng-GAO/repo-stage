# README Gap Report: radix-ui/primitives

RepoStage only uses sourced repository facts. The items below explain what was missing or weak.

- **medium / missing-install**: No obvious installation command was found.
- **medium / missing-quickstart**: No clear quickstart or usage section was found.
- **medium / missing-example**: No examples directory or obvious example text was found.
- **low / ingestion-warning**: GitHub API metadata was unavailable; used shallow git clone fallback with reduced metadata.
- **medium / ingestion-error**: GitHub API request was forbidden or rate limited. Set GITHUB_TOKEN if the public API limit is exhausted.
- **medium / unclear-positioning**: Repository sources did not expose clear feature bullets.
- **low / unclear-use-cases**: Heuristic use-case suggestions are kept out of the generated site until they can be tied to exact source facts.

## Output Contract

- `site/index.html`
- `site/styles.css`
- `repo-profile.json`
- `README-gap-report.md`
- `validation-report.md`
