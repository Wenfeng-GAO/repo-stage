# RepoStage Development Plan

This document defines the product documentation, implementation path, technical plan, and validation method for the first reviewable version of RepoStage.

## CTO Decision

RepoStage should be developed as an agent-portable Skill first, with a small supporting open-source repository around it.

The first product boundary is:

```text
Public GitHub repo URL in -> one-page static project website out
```

RepoStage is not an independent SaaS, visual website builder, hosted deployment platform, or commercial launch suite in the MVP. The deliverable should be a reusable Skill workflow plus local templates, scripts, fixtures, and validation checks that allow Codex, Claude, and other file-system-capable coding agents to repeatedly perform the same job with high quality.

The Skill must avoid platform lock-in. Codex/Multica can be the first implementation and test environment, but the instructions, assets, and scripts should be understandable by any agent that can read files, run local commands, fetch a public GitHub repo, and write output files.

## Required Development Documents

The repo should keep the following documents as source of truth:

| Document | Purpose | Owner |
|---|---|---|
| `README.md` | Public project overview, quickstart, current status, and links to docs. | Product/engineering |
| `docs/product-design.md` | Product positioning, target users, MVP scope, output shape, and non-goals. | Product |
| `docs/development-plan.md` | Implementation path, architecture, milestones, validation, and review criteria. | CTO/engineering |
| `docs/skill-spec.md` | Exact Skill behavior: triggers, inputs, workflow, outputs, failure modes, and acceptance criteria. | Engineering |
| `docs/repo-profile-schema.md` | Versioned schema for extracted repository facts and source grounding. | Engineering |
| `docs/quality-checklist.md` | Manual and automated QA checklist for generated websites. | Engineering/design |
| `docs/agent-compatibility.md` | Portability requirements for Codex, Claude, and other agent runtimes. | Engineering |
| `examples/` | Golden input repos, generated output snapshots, and review notes. | Engineering |

Only the first three documents need to exist immediately. The next implementation step should add `skill-spec.md`, `repo-profile-schema.md`, `quality-checklist.md`, and `agent-compatibility.md` before writing significant generator code.

## Implementation Strategy

Build from the workflow contract inward:

1. Define the Skill contract.
   - Trigger: user asks to turn a GitHub repo into a one-page website.
   - Input: public GitHub repo URL, optional output directory, optional style direction.
   - Output: static site directory, `repo-profile.json`, `README-gap-report.md`, and validation notes.
   - Failure behavior: invalid URL, private repo, missing README, sparse facts, network failure, or generated site failing QA.

2. Define the fact model.
   - Create a versioned `repo-profile.json` schema.
   - Store extracted facts with source references.
   - Separate confirmed facts from inferred positioning suggestions.
   - Prohibit unsourced claims in generated page copy.

3. Create a static site template.
   - Start with plain HTML/CSS/JS to keep output portable.
   - Include sections for hero, problem/solution, features, quickstart, examples, trust, and contribution CTA.
   - Keep the first version framework-free unless a later milestone proves Astro or another static framework is worth the complexity.

4. Implement the generator.
   - Fetch or clone the public repo.
   - Read README, package metadata, docs, examples, license, topics, and available assets.
   - Produce `repo-profile.json`.
   - Generate site files from profile plus template.
   - Produce `README-gap-report.md` for missing or weak source material.

5. Add validation.
   - Check generated claims against `repo-profile.json` sources.
   - Run link checks for internal and GitHub links.
   - Render desktop and mobile screenshots.
   - Confirm the page is static, readable, and commit-ready.

6. Package as a Skill.
   - Add `SKILL.md` with trigger rules and the full workflow.
   - Include templates and scripts as skill assets.
   - Document local usage and expected outputs.
   - Keep the Skill runtime-neutral: no hidden Multica-only assumptions in the core instructions.

## Proposed Repository Structure

```text
repo-stage/
  README.md
  LICENSE
  docs/
    product-design.md
    development-plan.md
    skill-spec.md
    repo-profile-schema.md
    quality-checklist.md
    agent-compatibility.md
  skills/
    repo-stage/
      SKILL.md
      templates/
      scripts/
      references/
  examples/
    fixtures/
    outputs/
  tests/
```

The `skills/repo-stage/` directory is the core product surface. The rest of the repository exists to make the Skill understandable, testable, and maintainable.

## Milestones

### M0: Reviewable Product Contract

Status target: ready for review.

Deliverables:

- Product design document.
- Development plan.
- Skill spec draft.
- Repo profile schema draft.
- Quality checklist draft.

Review question:

```text
Do we agree this is an agent-portable Skill-first product whose MVP is repo URL to one-page static website?
```

### M1: Manual Golden Path

Goal: prove the output shape before automating everything.

Deliverables:

- Choose 3 public open-source repos as fixtures.
- Manually create `repo-profile.json` for each.
- Generate static pages from a template.
- Capture desktop and mobile screenshots.
- Record quality notes in `examples/outputs/`.

Exit criteria:

- At least one generated page feels specific enough that the maintainer might publish it after edits.
- The schema is sufficient for the page sections.
- The quality checklist catches generic or unsourced copy.

### M2: Automated Local Prototype

Goal: one command produces all MVP files for a public repo.

Suggested command:

```bash
repo-stage generate https://github.com/owner/repo --out ./generated/owner-repo
```

Deliverables:

- Repo ingestion script.
- Profile generation.
- Static site generation.
- README gap report.
- Basic validation report.

Exit criteria:

- Works on 5 representative repos.
- Does not invent metrics, users, integrations, benchmarks, or testimonials.
- Output is readable on desktop and mobile.

### M3: Skill Packaging

Goal: make the workflow reusable by Codex, Claude, and other file-system-capable coding agents.

Deliverables:

- `skills/repo-stage/SKILL.md`.
- Skill assets: templates, scripts, references, checklist.
- Example invocation and expected output.
- Failure-handling guidance.
- Runtime compatibility notes for Codex, Claude, and generic shell/file agents.

Exit criteria:

- An agent can decide when to use the Skill from a user request.
- An agent can run the workflow without needing hidden context.
- The generated files match the documented output contract.
- The workflow can be followed outside Multica when the agent has equivalent file, shell, and network access.

### M4: External Validation

Goal: test whether open-source maintainers actually value the result.

Deliverables:

- 5 to 10 generated examples for real public repos.
- Maintainer feedback notes.
- List of repeated edit requests.
- Decision on next scope: improve site quality, add onboarding page, or add social preview image.

Exit criteria:

- At least 2 maintainers say they would use, publish, or adapt the generated page.
- The most common failure modes are understood.
- Next milestone is based on user evidence, not speculation.

## Technical Plan

### Ingestion

Initial sources:

- GitHub URL owner/repo.
- README and docs files.
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or similar package metadata.
- License file.
- Example files.
- Existing images or logos.
- GitHub topics, description, default branch, and primary language when available.

GitHub API credentials should be optional. The MVP must work for public repositories using unauthenticated access where possible, with graceful degradation if rate limits block richer metadata.

### Profiling

The profile generator should extract:

- Project name and repository URL.
- Short description.
- Audience and use cases.
- Key features.
- Install or quickstart commands.
- Example usage.
- License and ecosystem.
- Source references for every fact.
- Gaps where the repo does not provide enough information.

The profile should be deterministic enough for tests. LLM-assisted summarization is acceptable, but the output must preserve source references and distinguish fact from inference.

### Site Generation

Use a restrained developer-facing visual system:

- Strong typography.
- Clear information hierarchy.
- Fast scanning.
- Real commands in code blocks.
- No fake customer logos.
- No invented traction metrics.
- No enterprise/pricing copy unless the repo itself supports it.

First output format:

```text
site/
  index.html
  styles.css
  assets/
repo-profile.json
README-gap-report.md
validation-report.md
```

### Validation

Automated checks:

- URL format and repo accessibility.
- Required output files exist.
- `repo-profile.json` parses and matches schema.
- Generated HTML contains project name and GitHub URL.
- No banned unsourced metric phrases such as fake stars, downloads, customers, or benchmark claims.
- Local links resolve.
- HTML renders without console errors.

Manual review checks:

- Does the hero explain the project in under 10 seconds?
- Are features specific to the repo?
- Is the quickstart real and usable?
- Does mobile layout preserve readability?
- Would the maintainer feel comfortable publishing this page?

## Review Checklist

Before moving from planning to implementation, review these decisions:

- Skill-first product boundary is accepted.
- Skill portability across Codex, Claude, and similar agents is accepted.
- MVP stays limited to one-page static website generation.
- Output directory contract is accepted.
- Source-grounding rule is accepted: unsourced claims cannot appear as facts.
- Static HTML/CSS is accepted for the first generator.
- Validation must include both schema checks and rendered screenshot review.
- Pitch deck, hosting, social cards, onboarding page, and README rewrite remain post-MVP.

## Immediate Next Actions

1. Add `docs/skill-spec.md`.
2. Add `docs/repo-profile-schema.md`.
3. Add `docs/quality-checklist.md`.
4. Add `docs/agent-compatibility.md`.
5. Create 3 example fixture folders.
6. Build the first manual generated site from a real repo.
7. Review the manual output before implementing automation.

This sequence keeps the project grounded in a narrow, reviewable Skill contract before code volume increases.
