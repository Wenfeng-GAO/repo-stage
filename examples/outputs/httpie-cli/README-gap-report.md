# README Gap Report: HTTPie CLI

## Strong Source Material

- README has a clear headline and a plain-language product description.
- Feature list is concrete and maps well to page sections.
- README includes multiple realistic examples.
- README links to installation docs, full docs, Discord, StackOverflow, GitHub Issues, newsletter, and contribution guide.
- Repository includes logo and animation assets.
- `setup.cfg` provides Python requirement, project URLs, package metadata, console scripts, dependencies, and BSD license metadata.

## Gaps

| Gap | Severity | Notes |
|---|---:|---|
| Inline install command | Medium | README sends readers to installation docs rather than embedding one canonical install command. The generated page therefore links to the docs instead of inventing `pipx`, `brew`, or `pip` guidance. |
| Product-story interruption | Low | The README includes a prominent note about lost GitHub stars. It is important context, but a website may want to move it below onboarding content. |
| Version/source freshness | Low | The page avoids current version and download claims because badges are dynamic and were not converted into stable profile facts. |

## Checklist Findings

- The generic claim "the easiest HTTP client" was rejected because the source says "human-friendly" and "simple and natural syntax."
- Install CTAs link to sourced docs instead of adding an unsourced package-manager command.
- Community claims are limited to links present in the README.
