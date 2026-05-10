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

## Product Direction

Read the product documents:

- [docs/product-design.md](docs/product-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/skill-spec.md](docs/skill-spec.md)
- [docs/repo-profile-schema.md](docs/repo-profile-schema.md)
- [docs/quality-checklist.md](docs/quality-checklist.md)
- [docs/agent-compatibility.md](docs/agent-compatibility.md)

## Status

RepoStage now includes an M2 local prototype CLI. The first verification outputs are saved under `examples/outputs/` for a CLI tool, React/UI library, AI agent project, developer infrastructure project, and design/creative tool.

## License

Apache-2.0
