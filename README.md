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
validation-report.md
```

For external validation, the repository also includes a local M4 example
generator that wraps the canonical local generator:

```bash
node scripts/generate-m4-examples.mjs
```

It creates examples under `examples/m4/` for real public repositories,
including `repo-profile.json`, static site files, review notes, validation
reports, upstream commit metadata, and screenshots when Playwright screenshot
support is available.

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

## Local Generate Prototype

Run the M2 local generator directly with Python:

```bash
python3 -m repo_stage.cli generate https://github.com/owner/repo --out ./generated/owner-repo
```

Or install the console command in editable mode:

```bash
python3 -m pip install -e .
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

The command reuses the ingestion pipeline above, then writes:

```text
site/
  index.html
  styles.css
  assets/
repo-profile.json
README-gap-report.md
validation-report.md
```

The prototype extracts conservative facts from the ingestion report, generates a static one-page site, and validates the output. Missing README material is recorded as gaps or warnings; unsupported or failed generation writes failure reports instead of presenting a partial site as successful.

## Report Helper

Generate reports from an existing output set with:

```bash
python3 scripts/repo_stage_reports.py --profile repo-profile.json --site site --out .
```

## Local Profile Prototype

Convert an ingestion report into a sourced `repo-profile.json`:

```bash
python3 scripts/repo-stage-profile generate examples/fixtures/ingestion/complete-ingestion.json --out generated/repo-profile.json
```

Validate a profile:

```bash
python3 scripts/repo-stage-profile validate generated/repo-profile.json
```

The profile generator consumes the M1 ingestion report shape (`readme`, `packageMetadata`, `docs`, `examples`, `assets`, and `gaps`) and preserves M1 source IDs such as `src-package-1`, `src-doc-1`, and `src-example-1` in fact references.

## Product Direction

Read the product documents:

- [docs/product-design.md](docs/product-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/skill-spec.md](docs/skill-spec.md)
- [docs/repo-profile-schema.md](docs/repo-profile-schema.md)
- [docs/quality-checklist.md](docs/quality-checklist.md)
- [docs/agent-compatibility.md](docs/agent-compatibility.md)
- [docs/m4-external-validation.md](docs/m4-external-validation.md)
- [docs/m4-verification.md](docs/m4-verification.md)

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

RepoStage now includes an M2 local prototype CLI. The first verification outputs are saved under `examples/outputs/` for a CLI tool, React/UI library, AI agent project, developer infrastructure project, and design/creative tool.

The M3 agent-portable Skill package is also checked in with templates, scripts, references, a checklist, a fixture, and generated fixture output.

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
