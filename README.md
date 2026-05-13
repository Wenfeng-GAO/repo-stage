<p align="center">
  <img src="assets/readme-banner.svg" alt="RepoStage: README in. Grounded project website out." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-0f766e"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2563eb">
  <img alt="Node 20+" src="https://img.shields.io/badge/node-20%2B-111827">
  <img alt="MVP status" src="https://img.shields.io/badge/status-local%20prototype-f59e0b">
</p>

<p align="center">
  English | <a href="README.zh-CN.md">Chinese</a>
</p>

# RepoStage

RepoStage is an agent skill for turning a public GitHub repository into a grounded one-page landing page.

It is meant to be used through agents such as Claude, Codex, or other coding agents. You tell the agent to install the skill, then ask it to generate a landing page for a repository.

## Install

Tell your agent:

```text
Install the repo-stage skill from https://github.com/Wenfeng-GAO/repo-stage
```

If the agent asks what to install, tell it to use the skill in:

```text
skills/repo-stage
```

No npm, pip, or manual CLI setup is required for normal agent use.

## Use

Use the skill by name:

```text
$repo-stage generate a landing page for https://github.com/owner/repo
```

You can also ask in natural language:

```text
Use repo-stage to generate a landing page for https://github.com/owner/repo
```

```text
Use repo-stage to create a GitHub Pages-ready project page for https://github.com/owner/repo
```

Optional details you can include:

- Output directory, such as `./generated/owner-repo`
- Visual direction, such as `minimal`, `technical`, `editorial`, or `playful`
- Audience, such as developers, maintainers, contributors, or users evaluating the project

## Output

RepoStage asks the agent to create this output structure:

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

The generated `site/` directory is static HTML/CSS. It can be opened locally, committed to a repository, or adapted for GitHub Pages.

<p align="center">
  <img src="assets/readme-workflow.svg" alt="RepoStage workflow: ingest, profile, generate, validate" width="100%">
</p>

## Why Use RepoStage

- **Agent-native:** install and run it by asking Claude, Codex, or another coding agent.
- **Grounded copy:** page content comes from repository files and metadata instead of invented marketing claims.
- **Useful first page:** turn an existing public repo into a clear landing page without rewriting the README by hand.
- **Maintainer feedback:** get a gap report for missing install steps, examples, screenshots, license details, and positioning.
- **Portable output:** keep the generated static site, profile JSON, gap report, and validation report.

`GITHUB_TOKEN` is optional. Public repositories should work without a token until GitHub's unauthenticated rate limit is exhausted; when that happens the agent should report the degraded path.

## Developer Notes

The reusable skill lives in [skills/repo-stage/SKILL.md](skills/repo-stage/SKILL.md). It is designed for file-system-capable coding agents that can clone repositories, read files, write files, and run local commands.

Local helper scripts are included for development and fixture testing:

```bash
python3 skills/repo-stage/scripts/repo_stage_generate.py \
  --repo-path examples/fixtures/tiny-cli-tool \
  --repo-url https://github.com/example/tiny-cli-tool \
  --out examples/outputs/tiny-cli-tool

python3 skills/repo-stage/scripts/validate_output.py examples/outputs/tiny-cli-tool
```

Node profile/site utilities are also available for fixture work:

```bash
npm run generate:profile -- --input fixtures/ingestion/complete.json --out repo-profile.json
npm run validate:profile -- repo-profile.json
npm run generate:site -- --profile fixtures/profiles/repo-stage/repo-profile.json --out generated/repo-stage
npm test
```

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

RepoStage is a local MVP prototype. It can inspect public GitHub repos, generate `repo-profile.json`, produce a static one-page site, and create README gap and validation reports. It is not yet a hosted SaaS, visual editor, pitch-deck generator, or full launch asset suite.

## License

Apache-2.0
