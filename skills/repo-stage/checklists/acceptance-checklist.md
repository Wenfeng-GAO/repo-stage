# RepoStage Acceptance Checklist

Use this checklist before calling a RepoStage output complete.

## Required Files

- [ ] `repo-profile.json` exists and parses.
- [ ] `README-gap-report.md` exists.
- [ ] `validation-report.md` exists.
- [ ] `site/index.html` exists.
- [ ] `site/styles.css` exists.
- [ ] `site/assets/` exists, even if empty.

## Source Grounding

- [ ] Every major page section maps to `repo-profile.json` facts or conservative summaries.
- [ ] Quickstart commands come from repository files when available.
- [ ] Missing install, example, demo, screenshot, license, or contribution facts are listed as gaps.
- [ ] No fake stars, downloads, customers, testimonials, benchmarks, revenue, or adoption claims appear.

## Page Quality

- [ ] The hero states the project name and a clear sourced one-liner.
- [ ] The GitHub repository URL is visible or linked.
- [ ] Features are specific to source material.
- [ ] Code blocks fit or scroll on small screens.
- [ ] Desktop review notes are recorded.
- [ ] Mobile review notes are recorded.

## Compatibility

- [ ] Core workflow does not rely on Multica issue IDs.
- [ ] Core workflow does not rely on Codex-only or Claude-only tools.
- [ ] Skipped optional checks are explicitly recorded.
