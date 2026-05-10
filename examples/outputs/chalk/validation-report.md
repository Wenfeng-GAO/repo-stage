# Validation Report: Chalk

## Files

- `repo-profile.json`: present and valid JSON.
- `site/index.html`: present.
- `site/styles.css`: present.
- `site/assets/logo.svg`: copied from `media/logo.svg`.
- `site/assets/screenshot.png`: copied from `media/screenshot.png`.

## Source Grounding

- Hero one-liner maps to `fact-oneliner`.
- Install command maps to `fact-install`.
- Usage snippet maps to `fact-usage`.
- Feature cards map to `fact-features`, `fact-colors`, and `fact-esm`.
- Trust section maps to `fact-license`, `fact-esm`, and `fact-dependents`.

## Checklist Result

- Generic copy check: passed. The page uses Chalk-specific terms: ESM, chainable API, nested styles, 256/Truecolor, and `String.prototype`.
- Unsourced claim check: passed. Unsupported claims about customers, benchmarks, integrations, or current download counts were excluded.
- Local link check: passed by static inspection.
- Browser visual check: passed. Captured `desktop.png` at 1440x1000 and `mobile.png` at 390x844 with Playwright.

## Quality Notes

This is the strongest M1 sample. It has real assets, clear positioning, copyable quickstart, and enough specific README material that a maintainer could plausibly publish it after minor copy and style edits.

Desktop and mobile screenshots show no visible overlap, clipped text, or broken hero layout in the first viewport.
