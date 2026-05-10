# Repository Ingestion

RepoStage ingestion turns a public GitHub repository URL into a structured JSON report for the profiler.

## Command

```bash
python3 scripts/repo-stage-ingest https://github.com/owner/repo --out generated/owner-repo-ingestion.json
```

`--out` is optional. Without it, the JSON report is printed to stdout.

`--token` is optional and defaults to `GITHUB_TOKEN` when the environment variable is present. Public repositories are supported without a token, but GitHub may enforce lower unauthenticated rate limits.

When unauthenticated GitHub API metadata is unavailable, ingestion falls back to a shallow public `git clone` and records `rateLimit.degraded: true`. The fallback still captures repository files, docs, examples, package metadata, license files, and assets, but GitHub-only metadata such as topics and primary language may be empty.

## Report Shape

The current report schema version is:

```text
repo-stage-ingestion.v0
```

Top-level fields:

- `repo`: validated URL, owner, name, description, default branch, language, license, topics, homepage, and visibility.
- `rateLimit`: GitHub API limit, remaining count, reset epoch, whether a token was used, and degradation notes.
- `sources`: compact source inventory with stable source IDs for README, license, package files, docs, and examples.
- `readme`: README path, URL, byte count, and content when available.
- `license`: license file path, URL, byte count, and content when available.
- `packageMetadata`: recognized package files and parsed metadata where possible.
- `docs`: text docs from `docs/`.
- `examples`: example text/code files from common example directories.
- `assets`: image-like files with GitHub and raw URLs.
- `gaps`: missing README/install/quickstart/example/demo/license signals for the profiler.
- `warnings` and `errors`: readable non-fatal ingestion issues.

## Failure Behavior

The CLI exits with status `2` and a readable stderr message for:

- invalid GitHub URLs
- private, unavailable, or missing repositories
- GitHub API rate-limit or forbidden responses
- network errors

Missing README, missing package metadata, and sparse examples are represented as report gaps or warnings instead of crashing ingestion.
