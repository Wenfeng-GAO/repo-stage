---
name: repo-stage
description: Turn a public open-source GitHub repository into a polished, source-grounded, one-page static website. Use when the user wants to generate a static project site, landing page, or GitHub Pages-ready page from a public repo URL.
---

# RepoStage

Use RepoStage when a user wants to turn a public open-source GitHub repository into a polished, source-grounded, one-page static website.

RepoStage's product boundary is:

```text
Public GitHub repo URL in -> static project website files out
```

The core workflow is agent-portable. It must work for Codex, Claude, and generic coding agents that can read files, write files, run local commands, and fetch a public GitHub repository. Do not rely on Multica issue state, Codex-only tools, Claude-only tools, or hidden platform context for the main path.

## Trigger

Use this Skill when the user asks to:

- Turn a GitHub repository into a website or landing page.
- Generate a one-page open-source project site from a README.
- Improve a repo's external presentation using repository files as source material.
- Produce static website files for an open-source repo.
- Prepare a GitHub Pages-ready project page for a public repo.

Do not use this Skill for:

- General business websites without a repository source.
- Multi-page documentation sites.
- Hosted SaaS setup, deployment accounts, analytics, domains, or CRM flows.
- Pitch decks, social images, or README rewrites as the primary deliverable.
- Private repositories unless the user has explicitly provided access.

## Inputs

Required:

- `repo_url`: public GitHub repository URL in `https://github.com/owner/repo` form.

Optional:

- `out_dir`: output directory. Default: `./repo-stage-output/owner-repo`.
- `style_direction`: restrained visual direction such as `minimal`, `technical`, `editorial`, `playful`, or `enterprise`.
- `audience`: developer audience emphasis, if provided by the user.
- `include_generated_assets`: whether generated raster assets are allowed. Default: no.
- `github_pages`: whether to keep the output GitHub Pages-friendly. Default: yes.
- `github_token`: optional token for richer GitHub metadata. The workflow must degrade without it.

## Outputs

The default output contract is:

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

`site/index.html` and `site/styles.css` must be static and portable. They should open locally and be suitable for committing into a repository or publishing with GitHub Pages.

## Workflow

1. Validate the input URL.
   - Accept public GitHub repository URLs only.
   - Stop with a short failure report if the URL is invalid.

2. Fetch the repository.
   - Clone the repo with `git clone --depth 1 <repo_url> <work_dir>` when git is available.
   - If git is unavailable but another fetch method exists, use that method and record the fallback.
   - Stop with a failure report if the repo is private, unavailable, or blocked by network/rate limits.

3. Inspect source material.
   - Read README files, docs, package metadata, examples, license files, and visible assets.
   - Prefer structured files such as `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, and license files over guesses.
   - Treat GitHub description, topics, default branch, stars, and language as optional metadata only when actually available.

4. Build `repo-profile.json`.
   - Follow `../../docs/repo-profile-schema.md`.
   - Include source records for every file or metadata source used.
   - Store concrete facts with `sourceIds`.
   - Use only `high` or `medium` confidence facts for website copy.
   - Leave unsupported fields empty and add gaps instead of inventing claims.

5. Write `README-gap-report.md`.
   - List missing installation, quickstart, examples, screenshots, demos, license, contribution, audience, or positioning material.
   - Put suggested improvements here when they are not sourced strongly enough for the website.

6. Plan the page.
   - Use the project name, GitHub URL, sourced one-liner, sourced features, quickstart commands, examples, license, and contribution facts.
   - Keep developer-facing language concrete and restrained.
   - Do not include fake stars, download counts, customers, testimonials, benchmarks, revenue, integrations, pricing, compliance, security, or enterprise claims.

7. Generate the static site.
   - Produce `site/index.html` and `site/styles.css`.
   - Use templates in `templates/site/` where practical.
   - Copy real repo assets only when they support comprehension.
   - If generated assets are requested, label them as generated in the report and keep them non-essential.

8. Validate.
   - Run the included validator when available:

     ```bash
     python3 skills/repo-stage/scripts/validate_output.py <out_dir>
     ```

   - Confirm required files exist.
   - Confirm `repo-profile.json` parses.
   - Confirm the HTML contains the real project name and GitHub URL.
   - Confirm no blocked unsourced metric phrases appear.
   - Record skipped checks, including browser screenshots, in `validation-report.md`.

9. Report results.
   - Return the output directory and the most important caveats.
   - Mention whether desktop/mobile visual QA was completed, skipped, or manually reviewed.

## Runnable Helper

This repository includes a lightweight helper that implements the portable file contract for local testing and simple repos:

```bash
python3 skills/repo-stage/scripts/repo_stage_generate.py \
  https://github.com/owner/repo \
  --out ./repo-stage-output/owner-repo
```

For fixture or offline validation, pass a local repository path and a source URL:

```bash
python3 skills/repo-stage/scripts/repo_stage_generate.py \
  --repo-path examples/fixtures/tiny-cli-tool \
  --repo-url https://github.com/example/tiny-cli-tool \
  --out examples/outputs/tiny-cli-tool
```

The helper is intentionally conservative. If richer project understanding is needed, an agent may improve the generated profile and page manually, but must preserve source grounding and the output contract.

## Failure Handling

When blocked, write or report:

- The failed step.
- The reason, using concrete evidence.
- The smallest user action needed to continue.
- Any partial output path, if files were created.

Examples:

- Invalid URL: ask for a public GitHub repository URL.
- Private or unavailable repo: ask for access or a different public repo.
- Missing README or sparse docs: produce a gap report and either stop or generate a clearly limited page.
- Rate limit or metadata failure: continue with cloned file contents when possible and record missing metadata.
- Validation failure: keep output files, mark `validation-report.md` as failed, and list required fixes.

## Acceptance Criteria

Minimum acceptable result:

- `repo-profile.json` exists and is valid JSON.
- `site/index.html` and `site/styles.css` exist.
- The page includes the real project name and GitHub URL.
- Quickstart commands come from source files when available.
- Unsourced claims are excluded from the page.
- `README-gap-report.md` lists missing or weak information.
- `validation-report.md` records checks run, warnings, skipped checks, and known limitations.
- Desktop and mobile review notes are present, even when screenshots are unavailable.

High-quality result:

- The page is specific to the repo, not a name-swapped generic template.
- The hero explains the project within 10 seconds.
- The quickstart is readable and copyable.
- A developer can decide whether to try the project.
- The maintainer can see what source material to improve next.

## Runtime Notes

- Codex and Multica may manage issues, branches, comments, screenshots, and final status outside this Skill. Those orchestration details are not part of the core workflow.
- Claude should use the same files, scripts, templates, and checklists. If browser automation is unavailable, it should record visual QA as skipped.
- Generic coding agents can use the Markdown instructions and shell scripts directly. Optional browser and GitHub API capabilities may be skipped when unavailable.

For more detail, see:

- `../../docs/skill-spec.md`
- `../../docs/repo-profile-schema.md`
- `../../docs/quality-checklist.md`
- `../../docs/agent-compatibility.md`
- `references/output-contract.md`
- `references/runtime-compatibility.md`
- `checklists/acceptance-checklist.md`
