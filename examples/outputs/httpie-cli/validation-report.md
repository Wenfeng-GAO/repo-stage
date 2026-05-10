# Validation Report: HTTPie CLI

## Files

- `repo-profile.json`: present and valid JSON.
- `site/index.html`: present.
- `site/styles.css`: present.
- `site/assets/httpie-logo.svg`: copied from `docs/httpie-logo.svg`.
- `site/assets/httpie-animation.gif`: copied from `docs/httpie-animation.gif`.

## Source Grounding

- Hero claim maps to `fact-oneliner` and `fact-purpose`.
- CTA link maps to `fact-install-docs`.
- Feature cards map to `fact-output`, `fact-features`, and `fact-commands`.
- Examples map to `fact-examples`.
- Community section maps to `fact-community`.
- Trust section maps to `fact-python`, `fact-console`, and `fact-license`.

## Checklist Result

- Generic copy check: passed. The page uses HTTPie-specific commands, API debugging language, offline mode, console scripts, and project support links.
- Unsourced claim check: passed. Unsupported claims about current stars, downloads, benchmarks, customers, or "best" status were excluded.
- Local link check: passed by static inspection.
- Browser visual check: passed. Captured `desktop.png` at 1440x1000 and `mobile.png` at 390x844 with Playwright.

## Quality Notes

This sample is close to publishable because the source repository already provides strong positioning, visual assets, examples, and community links. The main maintainer edit would be choosing the preferred installation CTA.

Desktop and mobile screenshots show no visible overlap, clipped text, or broken hero layout in the first viewport. The hero uses a static transcript from README examples so captured screenshots communicate the product without depending on GIF timing.
