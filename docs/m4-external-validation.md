# M4 External Validation Plan

M4 validates whether RepoStage output is valuable enough that real open-source
maintainers would use, publish, or adapt it.

Current readiness: partially complete.

This branch now includes a local M4 example generator and five generated output
sets under `examples/m4/`. The examples are generated through the current
canonical local RepoStage CLI, record the upstream repository commit used, and
include a short maintainer-style edit pass. External maintainer feedback is
still pending, so M4 is not fully complete yet.

The generated output pipeline produces the M4 file set:

- `repo-profile.json`
- `site/index.html`
- `README-gap-report.md`
- `validation-report.md`
- `review-notes.md`
- desktop and mobile screenshots

M4 should not be considered complete until at least two maintainers or
project-familiar users have given explicit feedback on those outputs.

## Validation Repositories

Use 5 to 10 public repositories that cover different project shapes. The
generated first batch favors variety and repositories with enough README content
to produce a first-pass page.

| Repo | Category | Why It Is Useful For Validation |
|---|---|---|
| `sharkdp/bat` | CLI tool | Clear install commands, screenshots, feature list, and developer audience. |
| `pmndrs/zustand` | UI/library | Strong README, concise value prop, examples, and ecosystem-specific install flow. |
| `modelcontextprotocol/servers` | AI agent infrastructure | Many subprojects and integrations; tests whether RepoStage can avoid overclaiming. |
| `browser-use/browser-use` | AI agent project | Tests whether AI-agent positioning can stay concrete and README-grounded. |
| `docusealco/docuseal` | Developer/product tool | Tests a repo with an obvious end-user workflow and screenshots. |

## Required Output Per Repo

Store outputs under:

```text
examples/m4/<owner>-<repo>/
  repo-profile.json
  README-gap-report.md
  validation-report.md
  review-notes.md
  site/
    index.html
    styles.css
    assets/
  screenshots/
    desktop.png
    mobile.png
```

Each `review-notes.md` should answer:

- Does the hero explain the project in 10 seconds?
- Which claims feel unsupported or too broad?
- Which section would the maintainer edit first?
- Is the generated page better than sending users directly to the README?
- Would the reviewer use, publish, or adapt it?

## Feedback Tracker

Use this table in the M4 report after examples are generated.

| Repo | Reviewer | Relationship To Project | Verdict | Would Use/Publish/Adapt? | Required Edits |
|---|---|---|---|---|---|
| | | Maintainer / contributor / user / domain expert | | Yes / No / Maybe | |

Acceptance requires at least two rows where the reviewer gives a clear
maintainer or target-user verdict.

## Outreach Template

Use plain text and include a preview link or zip attachment.

```text
Hi <name>,

I am validating RepoStage, a small open-source workflow that turns a public
GitHub repository into a one-page static project website grounded in the repo's
README/docs.

I generated a page for <repo> and would like a blunt 5-minute review:

1. Is the page accurate to the project?
2. Would you use, publish, or adapt it after edits?
3. What are the first 2-3 things you would change?

Preview: <link>
Generated files: <link>

No need for a polished answer. A short yes/no/maybe plus edit notes is enough.
```

## Repeated Edit Request Taxonomy

Track repeated requests in these buckets:

- Positioning: hero value prop, audience, problem framing, or tone is wrong.
- Grounding: copy includes unsupported claims or misses source references.
- Quickstart: install or usage commands are missing, stale, or not primary.
- Information architecture: sections are ordered poorly or important content is absent.
- Visual quality: page looks generic, too commercial, or visually mismatched to the project.
- Assets: missing logo, screenshots, demo media, or social preview image.
- Maintainer workflow: output is hard to edit, preview, commit, or deploy.

## M4 Decision Rules

Choose the next scope from evidence:

- If reviewers mostly edit wording, prioritize source-grounded copy planning.
- If reviewers mostly reject visual polish, prioritize template and screenshot quality.
- If reviewers ask how to get started after landing, add an onboarding page.
- If reviewers want better sharing assets, add social preview image generation.
- If reviewers cannot review because outputs are absent or inconsistent, finish M2/M3 first.

## Current Recommendation

Start external review with the five generated examples:

1. Preview each page once to catch obvious rendering problems.
2. Send previews to maintainers or target users for feedback.
3. Use the repeated edit requests to decide whether the next milestone should
   improve page quality, add onboarding, or add social preview images.

The current evidence points first toward page quality and maintainer workflow:
project-specific assets, CTA priority, and multi-package scope selection remain
the most repeated internal edit requests.
