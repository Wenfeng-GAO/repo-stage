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

Use it when you already have a useful open-source repo and want a clearer project page that helps other developers understand it, try it, star it, and contribute.

## Installation

### Quick Install from GitHub

Install the `repo-stage` command into an isolated Python environment:

```bash
pipx install git+https://github.com/Wenfeng-GAO/repo-stage.git
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

`pipx` is recommended for regular use because it keeps RepoStage out of your project environment. If you use `uv`, the equivalent tool install path is:

```bash
uv tool install git+https://github.com/Wenfeng-GAO/repo-stage.git
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

### Install from a Local Checkout

```bash
git clone https://github.com/Wenfeng-GAO/repo-stage.git
cd repo-stage
python3 -m pip install -e .
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

You can also run the generator without installing:

```bash
python3 -m repo_stage.cli generate https://github.com/owner/repo --out ./generated/owner-repo
```

### Agent Skill Install

The reusable skill lives in `skills/repo-stage/`. For agents that load file-system skills, copy or symlink that directory into the agent's skill directory, then invoke it by name:

```bash
# Example manual install path; adjust for your agent runtime.
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/repo-stage" ~/.claude/skills/repo-stage
```

RepoStage is not currently published as an npm package. The repository does include Node-based profile and site utilities, but `package.json` is marked `private` and the Python CLI is the complete public-repo ingestion path today. A future npm install would need a published package and a `repo-stage` bin that wraps or ports the full CLI workflow.

## Usage

RepoStage can be used as a local CLI or as an agent skill.

### CLI

Generate a grounded static site from a public GitHub repository:

```bash
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

The output directory is portable and can be opened locally, committed to a repo, or adapted for GitHub Pages.

### Agent Invocation

After installing the skill in an agent runtime that supports slash commands, invoke it directly:

```text
/repo-stage https://github.com/owner/repo
/repo-stage https://github.com/owner/repo --out ./generated/owner-repo
```

In runtimes that trigger skills with `$skill-name`, use:

```text
$repo-stage generate a one-page project site for https://github.com/owner/repo
$repo-stage use ./generated/owner-repo as the output directory
```

## Output

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

## Why Use RepoStage

RepoStage is for maintainers who want a public-facing project page without rewriting their README by hand.

- **Fast first page:** turn an existing public repo into a static site output in one command.
- **Grounded copy:** page content comes from README files, docs, package metadata, examples, and license files instead of invented marketing claims.
- **Useful artifacts:** get the generated `site/`, a structured `repo-profile.json`, a README gap report, and a validation report.
- **Maintainer feedback:** see missing install steps, examples, screenshots, license details, and positioning gaps directly.
- **Agent-portable workflow:** use the same `skills/repo-stage/` package from Codex, Claude, or other file-system-capable coding agents.

Many open-source projects have enough substance in their README, docs, examples, package metadata, and license to support a strong public page. What they often lack is the time to turn that material into a coherent first impression.

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

Rendered previews are published with GitHub Pages after changes land on `main`. For example, the HTTPie CLI output opens at <https://wenfeng-gao.github.io/repo-stage/httpie-cli/site/>.

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
