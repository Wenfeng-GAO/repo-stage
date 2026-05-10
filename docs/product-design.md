# RepoStage Product Design

RepoStage is an open-source MVP for turning a public GitHub repository URL into a launch-ready one-page static website.

The first version is intentionally narrow:

> Paste a GitHub repo URL. Get a beautiful static site that helps the project get understood, used, starred, and contributed to.

RepoStage is not a commercial website builder, hosted SaaS, pitch-deck generator, or full visual editor in the MVP. It is a local, repo-aware generation workflow for open-source maintainers.

The first implementation shape should be an agent-portable Skill with supporting templates, scripts, examples, and validation checks. Codex/Multica can be the first validation environment, but the Skill should also be usable by Claude and other file-system-capable coding agents.

## Name

Confirmed product name:

```text
RepoStage
```

Public repository:

```text
https://github.com/Wenfeng-GAO/repo-stage
```

Why the name works:

- Short and pronounceable.
- Clearly connected to repositories.
- Suggests giving a project a public stage.
- Does not overclaim as a full design platform.
- Can grow from one-page project sites into broader launch assets later.

## Positioning

RepoStage turns an existing open-source repo into a launch-ready project page.

It starts from the repo as the source of truth rather than a blank prompt. README content, package metadata, docs, examples, license, topics, and available project assets are converted into a clear external story.

Core promise:

```text
README in, project website out.
```

More specific MVP promise:

```text
Turn your GitHub repo into a one-page static website in minutes.
```

## Target Users

Primary users:

- Independent open-source maintainers with useful projects but weak external presentation.
- Developer-tool authors who want a stronger first impression than a long README.
- Hackathon and demo authors who need a presentable page quickly.
- Small teams launching an open-source repo and trying to earn adoption and stars.

Non-goals for the first version:

- Non-technical business websites.
- Multi-page marketing sites.
- Full visual editing.
- Hosting, analytics, domains, and user accounts.
- Pricing pages, enterprise copy, lead capture, or CRM integrations.
- Pitch decks and social media asset generation.

## MVP Workflow

Command-line shape:

```bash
repo-stage generate https://github.com/owner/repo --out site
```

Interactive shape:

1. Paste a public GitHub repository URL.
2. RepoStage reads the repository files and metadata.
3. RepoStage produces a structured project profile.
4. The user reviews or accepts the extracted facts.
5. RepoStage generates a one-page static website.
6. The user previews locally.
7. The user asks for edits or commits the generated files.

The product should bias toward direct file output. A hosted preview can come later, but the open-source MVP should work with local files and GitHub Pages-compatible static output.

## Required Output

Initial generated output:

```text
site/
  index.html
  styles.css
  script.js        # optional
  assets/          # copied or generated assets when needed
repo-profile.json
README-gap-report.md
validation-report.md
```

The generated page should include:

- Hero with project name, one-sentence value proposition, install/use CTA, and GitHub CTA.
- Problem and solution framing derived from repository facts.
- Feature section grounded in README/docs.
- Quickstart section using real commands from the repo.
- Example or use-case section.
- Trust section with license, language/ecosystem, and repository links.
- Contributor CTA if contribution docs or issue metadata are available.

## Fact Model

Every generated claim should be traceable to repository input.

Initial `repo-profile.json` shape:

```json
{
  "repo": {
    "url": "https://github.com/owner/repo",
    "owner": "owner",
    "name": "repo",
    "description": "Repository description",
    "license": "MIT",
    "primaryLanguage": "TypeScript",
    "topics": []
  },
  "product": {
    "oneLiner": "",
    "audience": [],
    "problems": [],
    "features": [],
    "useCases": [],
    "quickstart": []
  },
  "sources": [
    {
      "path": "README.md",
      "facts": ["installation command", "main feature"]
    }
  ],
  "gaps": []
}
```

If a claim cannot be sourced, the page should omit it or place it in `README-gap-report.md` as a suggested positioning idea, not present it as fact.

## Quality Bar

The first page must feel specific to the repo, not like a generic template with the project name swapped in.

Required checks:

- Uses the actual project name and repository URL.
- Uses real install or usage commands when available.
- Does not invent stars, downloads, customers, benchmarks, testimonials, or integrations.
- Avoids commercial SaaS copy unless the repo itself is a commercial product.
- Renders on desktop and mobile.
- Produces static assets that can be committed to the repo.
- Keeps the visual system appropriate for developer audiences: high clarity, strong typography, restrained effects, fast scanning.

## Architecture

Recommended components:

| Component | Responsibility |
|---|---|
| Repo ingest | Clone or fetch repository files and GitHub metadata. |
| Project profiler | Convert README/docs/package files into `repo-profile.json`. |
| Narrative planner | Decide page sections, value proposition, and missing facts. |
| Site generator | Produce static HTML/CSS/JS from the profile and selected visual direction. |
| QA checker | Validate source grounding, links, responsive layout, and missing content. |
| Exporter | Write local files and optional ZIP. |

## First Implementation Milestone

Ship a working proof of concept against five public repositories:

1. CLI tool.
2. React or UI library.
3. AI agent project.
4. Developer infrastructure project.
5. Design or creative tool.

For each repo, produce:

- `repo-profile.json`
- `site/index.html`
- `README-gap-report.md`
- Desktop and mobile screenshots

The milestone is complete when at least one maintainer says they would use or publish the generated page after minor edits.

## Resolved Direction

- First product shape: agent-portable Skill first, not a standalone SaaS.
- Target users of the Skill itself: Codex, Claude, and similar coding agents that can read files, run commands, and write local outputs.
- First output path: default to `site/`.
- GitHub credentials: optional for public repos; degrade gracefully under rate limits.
- Page generator: static HTML/CSS first; add a framework only after the static version is validated.

## Open Questions

- Should RepoStage also expose a CLI wrapper after the Skill workflow is stable?
- Which three public repos should become the first golden examples?
- Should generated pages be optimized first for GitHub Pages, plain ZIP export, or both?
