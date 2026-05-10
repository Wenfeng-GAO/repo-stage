# RepoStage Skill Spec

This document defines the expected behavior of the RepoStage Skill across Codex, Claude, and other file-system-capable coding agents.

## Purpose

RepoStage helps an agent turn a public open-source GitHub repository into a polished one-page static website grounded in repository facts.

The Skill is successful when it produces files a maintainer can preview locally and consider publishing after minor edits.

The Skill should be portable. Its core behavior must not depend on Codex-only, Claude-only, or Multica-only runtime features.

## Trigger

Use this Skill when the user asks for any of the following:

- Turn a GitHub repo into a website.
- Generate a landing page from a README.
- Create a one-page open-source project site.
- Improve a repo's external presentation using the repo as source material.
- Produce static website files for an open-source repo.

Do not use this Skill for:

- General business websites without a GitHub repo.
- Multi-page documentation sites.
- Hosted SaaS setup.
- Pitch decks, social images, or README rewrites as the primary task.
- Private repositories unless credentials and access are explicitly available.

## Inputs

Required:

- Public GitHub repository URL.

Optional:

- Output directory.
- Style direction, such as minimal, technical, playful, editorial, or enterprise.
- Target audience emphasis.
- Whether to include generated assets.
- Whether to prepare files for GitHub Pages.

## Outputs

Default output:

```text
site/
  index.html
  styles.css
  assets/
repo-profile.json
README-gap-report.md
validation-report.md
```

The site must be static and portable. It should work when opened locally or committed into a repository.

## Workflow

1. Validate the GitHub URL.
2. Fetch or clone the public repository.
3. Read README, docs, package metadata, examples, license, and available project assets.
4. Extract sourced facts into `repo-profile.json`.
5. Identify missing or weak source material in `README-gap-report.md`.
6. Plan the page structure and copy from sourced facts.
7. Generate static HTML/CSS and copy usable assets.
8. Validate schema, source grounding, links, desktop rendering, and mobile rendering.
9. Write `validation-report.md`.
10. Report output paths and any quality caveats.

## Source Grounding Rules

The generated website may state:

- Facts found in README, docs, metadata, examples, license, or GitHub metadata.
- Reasonable summaries of sourced facts.
- Clearly conservative positioning derived from repository material.

The generated website must not state:

- Fake star counts, download counts, customers, testimonials, revenue, benchmarks, or adoption.
- Integrations not found in the repo.
- Compatibility promises not found in the repo.
- Enterprise, pricing, compliance, or security claims unless explicitly sourced.

Suggestions without source support belong in `README-gap-report.md`, not in the website.

## Report Contract

Every successful or partially successful generation must write both reports:

- `README-gap-report.md`
- `validation-report.md`

`README-gap-report.md` must be derived from `repo-profile.json.gaps`. It should summarize missing or weak install, quickstart, example, demo, screenshot, license, contributing, audience, positioning, and documentation source material. If the agent finds positioning ideas that may be valuable but are not supported by sources, those ideas must be listed in the gap report and omitted from the generated website.

`validation-report.md` must record the repository URL, output directory, required output files, schema validation, source grounding, visible HTML claim grounding, local link checks, HTML content checks, HTML render review, desktop review, and mobile review. Each check must use one of these statuses:

- `pass`: completed successfully.
- `warn`: completed with a caveat the maintainer should review.
- `fail`: failed and must be fixed before publishing.
- `skipped`: not run because an optional capability was unavailable or a prerequisite failed.

Skipped checks must include the reason. Browser-based rendering and screenshot checks are optional capabilities; when unavailable, the Skill should still produce files and mark those checks as skipped.

The portable report helper can be run after `repo-profile.json` and `site/` exist:

```bash
python3 scripts/repo_stage_reports.py --profile repo-profile.json --site site --out .
```

## Failure Modes

The Skill should stop or degrade gracefully when:

- URL is not a GitHub repo URL.
- Repo is private or unavailable.
- Repo has no README or usable docs.
- GitHub rate limits prevent metadata access.
- The generated site fails required validation.

In these cases, the Skill should produce a short failure report with the blocked step and the minimum user action needed to continue.

## Agent Runtime Requirements

Required:

- File read/write access.
- Ability to run local commands or equivalent scripts.
- Network access to fetch public GitHub repository contents.
- Ability to produce Markdown, JSON, HTML, and CSS files.

Optional:

- Browser automation for screenshots.
- GitHub API token for richer metadata.
- Git commands for clone-based ingestion.

If an optional capability is missing, the Skill should continue where possible and record skipped validation in `validation-report.md`.

## Acceptance Criteria

Minimum acceptable result:

- `repo-profile.json` exists and is valid JSON.
- `site/index.html` and `site/styles.css` exist.
- The page includes the real project name and GitHub URL.
- The quickstart uses real commands when the repo provides them.
- Unsourced claims are excluded from the page.
- `README-gap-report.md` lists missing information.
- Desktop and mobile review notes are recorded.

High-quality result:

- The page feels specific to the repo.
- The hero explains the project within 10 seconds.
- The page gives a developer enough confidence to try the project.
- The maintainer can see what to edit or improve next.
