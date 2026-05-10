# RepoStage

RepoStage turns a public GitHub repository into a polished one-page static website.

It is for open-source maintainers who already have a useful repo, but need a clearer project page so other developers can understand it, try it, star it, and contribute.

## MVP

Input:

```text
https://github.com/owner/repo
```

Output:

```text
site/
  index.html
  styles.css
  assets/
repo-profile.json
README-gap-report.md
```

The first version focuses on one job: generate a static landing page grounded in real repository facts from the README, docs, package metadata, examples, license, and project assets.

## Local Ingestion Prototype

Run the public GitHub repository ingestion step directly:

```bash
python3 scripts/repo-stage-ingest https://github.com/owner/repo --out generated/owner-repo-ingestion.json
```

The command writes a structured JSON report containing:

- validated repository owner/name and GitHub metadata
- README content when available
- docs and example text files
- package metadata from files such as `package.json`, `pyproject.toml`, `Cargo.toml`, and `go.mod`
- license metadata and reusable image assets
- rate-limit details, warnings, readable errors, and content gaps for downstream profiling

`GITHUB_TOKEN` is optional. Public repositories should work without a token until GitHub's unauthenticated rate limit is exhausted; when that happens the report or error explains the degraded path.

Three smoke-test fixture URLs live in [examples/fixtures/public-repos.txt](examples/fixtures/public-repos.txt).

## Product Direction

Read the product documents:

- [docs/product-design.md](docs/product-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/skill-spec.md](docs/skill-spec.md)
- [docs/repo-profile-schema.md](docs/repo-profile-schema.md)
- [docs/quality-checklist.md](docs/quality-checklist.md)
- [docs/agent-compatibility.md](docs/agent-compatibility.md)

## Skill Package

The reusable agent-portable Skill lives in [skills/repo-stage/SKILL.md](skills/repo-stage/SKILL.md).

Run the included fixture:

```bash
python3 skills/repo-stage/scripts/repo_stage_generate.py \
  --repo-path examples/fixtures/tiny-cli-tool \
  --repo-url https://github.com/example/tiny-cli-tool \
  --out examples/outputs/tiny-cli-tool

python3 skills/repo-stage/scripts/validate_output.py examples/outputs/tiny-cli-tool
```

## Status

RepoStage is currently in skill packaging. The product name is confirmed, the public repository is created, and the first reviewable product, development, agent-portable Skill, schema, compatibility, quality documents, templates, scripts, checklist, and fixture output are checked in.

## License

Apache-2.0
