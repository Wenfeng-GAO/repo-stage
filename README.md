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

## Status

RepoStage is currently in product planning. The product name is confirmed, the public repository is created, and the first reviewable product, development, agent-portable Skill, schema, compatibility, and quality documents are checked in.

## Local Prototype

Generate a sourced `repo-profile.json` from an ingestion fixture:

```bash
npm run generate:profile -- --input fixtures/ingestion/complete.json --out repo-profile.json
```

Validate a profile:

```bash
npm run validate:profile -- repo-profile.json
```

Generate a portable static site from a sourced profile:

```bash
npm run generate:site -- --profile fixtures/profiles/repo-stage/repo-profile.json --out generated/repo-stage
```

Generate the checked-in site fixtures:

```bash
npm run generate:fixtures
```

Run regression tests:

```bash
npm test
```

The site generator writes:

```text
output/
  site/
    index.html
    styles.css
    assets/
  repo-profile.json
  README-gap-report.md
  validation-report.md
```

Website copy is rendered from high/medium confidence facts and repository metadata. Product fields that are not backed by matching sourced facts are rejected before generation.

## License

Apache-2.0
