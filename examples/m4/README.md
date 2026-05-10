# M4 External Validation Examples

This directory contains first-pass RepoStage outputs for five real public
repositories. Each example was generated with:

```bash
node scripts/generate-m4-examples.mjs
```

## Generated Examples

| Repo | Output Directory | Profile | Site | Review Notes | Screenshots |
|---|---|---|---|---|---|
| `sharkdp/bat` | `examples/m4/sharkdp-bat/` | yes | yes | yes | desktop + mobile |
| `pmndrs/zustand` | `examples/m4/pmndrs-zustand/` | yes | yes | yes | desktop + mobile |
| `modelcontextprotocol/servers` | `examples/m4/modelcontextprotocol-servers/` | yes | yes | yes | desktop + mobile |
| `browser-use/browser-use` | `examples/m4/browser-use-browser-use/` | yes | yes | yes | desktop + mobile |
| `docusealco/docuseal` | `examples/m4/docusealco-docuseal/` | yes | yes | yes | desktop + mobile |

Each output directory contains:

```text
repo-profile.json
README-gap-report.md
validation-report.md
review-notes.md
site/
  index.html
  styles.css
screenshots/
  desktop.png
  mobile.png
```

## Review Status

These are generated outputs with internal review notes, not maintainer-approved
pages. External feedback is still required before M4 can be called fully
validated.

| Repo | Reviewer | Relationship To Project | Verdict | Would Use/Publish/Adapt? | Required Edits |
|---|---|---|---|---|---|
| `sharkdp/bat` | pending | maintainer or target user needed | pending | pending | pending |
| `pmndrs/zustand` | pending | maintainer or target user needed | pending | pending | pending |
| `modelcontextprotocol/servers` | pending | maintainer or target user needed | pending | pending | pending |
| `browser-use/browser-use` | pending | maintainer or target user needed | pending | pending | pending |
| `docusealco/docuseal` | pending | maintainer or target user needed | pending | pending | pending |

## Repeated Edit Requests From Internal Review

These repeated requests appeared across the generated examples before external
maintainer review:

- Hero positioning needs maintainer-approved wording before publication.
- Primary CTA needs project-specific choice: install, docs, demo, or GitHub.
- Visual identity is too generic without project logos, screenshots, or demo media.
- Quickstart extraction works when command blocks are clear, but needs manual confirmation.
- License detection is conservative and should read package metadata or GitHub metadata next.
- Multi-package repos need better scope selection so the page does not summarize too broadly.

## Recommendation

The next milestone should prioritize page quality and maintainer workflow before
adding onboarding pages or social preview images.

Evidence:

- The generator can create five complete static examples with profiles, reports,
  and screenshots.
- The repeated weakness is not absence of more page types; it is that first-pass
  page copy and visual identity need tighter maintainer review loops.
- Social preview images should wait until the core page narrative is accurate.

Concrete next scope:

1. Improve source extraction for license, screenshots, demos, and primary install commands.
2. Add a short maintainer editing pass that rewrites hero, CTA, and feature order.
3. Send the five generated examples for external review using the outreach template in `docs/m4-external-validation.md`.
