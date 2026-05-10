# RepoStage Quality Checklist

Use this checklist before marking a generated RepoStage output as acceptable.

## Input Quality

- GitHub URL is valid and accessible.
- Repo name, owner, default branch, and README are detected.
- License is detected or listed as missing.
- Package metadata is read when present.
- Existing images, logos, screenshots, or demo links are detected when present.

## Source Grounding

- Every major page claim maps to `repo-profile.json`.
- Install and quickstart commands come from repository files.
- Features are specific to the repo, not generic category filler.
- No fake stars, downloads, customers, testimonials, benchmarks, revenue, or integrations.
- Inferred improvements are placed in `README-gap-report.md`, not presented as facts.

## Website Content

- Hero explains what the project is and who it is for.
- Primary CTA points to a real install, quickstart, or GitHub action.
- Feature section is concrete and scannable.
- Quickstart is readable and copyable.
- Examples or use cases are grounded in repo material.
- Trust section uses real license, ecosystem, and repository links.
- Contributor CTA appears only if there is enough supporting material.

## Visual Quality

- Page is specific enough that it does not look like a name-swapped template.
- Typography is readable and hierarchy is clear.
- Developer-facing tone is restrained and credible.
- Desktop layout has no overlapping content.
- Mobile layout has no clipped text or broken spacing.
- Code blocks fit or scroll cleanly on small screens.
- Images or icons support comprehension rather than decoration.

## Technical Quality

- `site/index.html` exists.
- `site/styles.css` exists.
- Output can be opened locally.
- Local links resolve.
- External links point to the correct GitHub repo or sourced URLs.
- Console has no blocking errors.
- Files are suitable to commit into a repo.

## Reports

- `repo-profile.json` is valid.
- `README-gap-report.md` lists missing facts and improvement opportunities.
- `validation-report.md` records checks run, warnings, and known limitations.
- Desktop and mobile screenshots are captured for review when browser tooling is available.

## Review Questions

Ask these before accepting the result:

- Would a developer understand the project in 10 seconds?
- Would the maintainer feel the page is fair to the project?
- Are any claims likely to embarrass the maintainer because they are overstated?
- Is the generated output better than linking directly to the README?
- What is the smallest edit that would make this publishable?
