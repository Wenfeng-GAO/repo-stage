<p align="center">
  <img src="assets/readme-banner.svg" alt="RepoStage: README in. Grounded project website out." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-0f766e"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2563eb">
  <img alt="Node 20+" src="https://img.shields.io/badge/node-20%2B-111827">
  <img alt="MVP status" src="https://img.shields.io/badge/status-local%20prototype-f59e0b">
</p>

# RepoStage

RepoStage turns a public GitHub repository into a polished, grounded one-page static website.

It is built for open-source maintainers who already have a useful repo, but need a clearer project page so other developers can understand it, try it, star it, and contribute. The current MVP reads repository facts, writes a structured profile, generates a portable static site, and reports what still needs human attention.

```bash
python3 -m repo_stage.cli generate https://github.com/owner/repo --out ./generated/owner-repo
```

## What It Produces

```text
generated/owner-repo/
  site/
    index.html
    styles.css
    assets/
  repo-profile.json
  README-gap-report.md
  validation-report.md
```

The generated page is static HTML/CSS that can be opened locally, committed to a repo, or adapted for GitHub Pages. Copy is rendered from high/medium confidence facts and repository metadata; unsupported claims are omitted or pushed into the gap report.

<p align="center">
  <img src="assets/readme-workflow.svg" alt="RepoStage workflow: ingest, profile, generate, validate" width="100%">
</p>

## Why RepoStage Exists

Many open-source projects have enough substance in their README, docs, examples, package metadata, and license to support a strong public page. What they often lack is the time to turn that material into a coherent first impression.

RepoStage treats the repository as the source of truth:

- **Grounded by default:** generated claims must trace back to repository inputs.
- **Useful output, not a mockup:** the result is a portable `site/` directory plus profile and validation reports.
- **Maintainer-oriented:** missing install steps, examples, screenshots, license details, and positioning gaps are called out directly.
- **Agent-portable:** the reusable Skill package lives in `skills/repo-stage/` for Codex, Claude, and other file-system-capable coding agents.

## Quickstart

Run the local generator directly with Python:

```bash
python3 -m repo_stage.cli generate https://github.com/owner/repo --out ./generated/owner-repo
```

Or install the console command in editable mode:

```bash
python3 -m pip install -e .
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

`GITHUB_TOKEN` is optional. Public repositories should work without a token until GitHub's unauthenticated rate limit is exhausted; when that happens the report or error explains the degraded path.

## Local Prototype Commands

Ingest a public GitHub repository:

```bash
python3 scripts/repo-stage-ingest https://github.com/owner/repo --out generated/owner-repo-ingestion.json
```

Convert an ingestion report into a sourced profile:

```bash
python3 scripts/repo-stage-profile generate examples/fixtures/ingestion/complete-ingestion.json --out generated/repo-profile.json
```

Validate a profile:

```bash
python3 scripts/repo-stage-profile validate generated/repo-profile.json
```

Generate reports from an existing output set:

```bash
python3 scripts/repo_stage_reports.py --profile repo-profile.json --site site --out .
```

## Node Site Generator

The repository also includes the M2 Node-based profile/site utilities:

```bash
npm run generate:profile -- --input fixtures/ingestion/complete.json --out repo-profile.json
npm run validate:profile -- repo-profile.json
npm run generate:site -- --profile fixtures/profiles/repo-stage/repo-profile.json --out generated/repo-stage
npm run generate:fixtures
npm test
```

The site generator writes the same output contract:

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

## Examples

Checked-in verification outputs live under [examples/outputs/](examples/outputs/). They cover several repository shapes, including CLI tools, React/UI libraries, AI agent projects, developer infrastructure, and design/creative tools.

Fixture URLs for smoke tests live in [examples/fixtures/public-repos.txt](examples/fixtures/public-repos.txt).

## Documentation

- [Product design](docs/product-design.md)
- [Development plan](docs/development-plan.md)
- [Skill specification](docs/skill-spec.md)
- [Repo profile schema](docs/repo-profile-schema.md)
- [Quality checklist](docs/quality-checklist.md)
- [Agent compatibility](docs/agent-compatibility.md)
- [Ingestion details](docs/ingestion.md)

## Status

RepoStage is a local MVP prototype. It can ingest public GitHub repos, generate `repo-profile.json`, produce a static one-page site, and create README gap and validation reports. It is not yet a hosted SaaS, visual editor, pitch-deck generator, or full launch asset suite.

## License

Apache-2.0
