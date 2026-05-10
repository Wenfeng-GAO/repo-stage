# RepoStage Output Contract

Every successful RepoStage run writes a single output directory with this shape:

```text
<out_dir>/
  site/
    index.html
    styles.css
    assets/
  repo-profile.json
  README-gap-report.md
  validation-report.md
```

## File Requirements

- `repo-profile.json` must parse as JSON and follow `docs/repo-profile-schema.md`.
- `site/index.html` must reference `./styles.css`, include the real project name, and link to the source GitHub repository.
- `site/styles.css` must be local and must not require a hosted build step.
- `README-gap-report.md` must list missing or weak source material.
- `validation-report.md` must record checks, warnings, skipped checks, and final pass/fail status.

## Claim Requirements

Website copy may use:

- Explicit README, docs, metadata, example, and license facts.
- Conservative summaries of nearby sourced material.
- Empty or generic fallback copy only when it is labeled as a limitation in the reports.

Website copy must not use:

- Fake stars, downloads, users, customers, testimonials, benchmarks, revenue, or adoption.
- Integrations, platforms, compatibility, security, compliance, pricing, or enterprise claims that are not present in source material.
- Low-confidence inferences as final page claims.
