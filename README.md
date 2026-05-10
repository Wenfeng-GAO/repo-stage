# RepoStage

RepoStage turns a public GitHub repository into a polished one-page static website.

It is for open-source maintainers who already have a useful repo, but need a clearer project page so other developers can understand it, try it, star it, and contribute.

## MVP

Input:

```text
https://github.com/owner/repo
```

Output:

```text
site/
  index.html
  styles.css
  assets/
repo-profile.json
README-gap-report.md
```

For external validation, the repository also includes a local M4 example
generator:

```bash
node scripts/generate-m4-examples.mjs
```

It creates first-pass examples under `examples/m4/` for real public
repositories, including `repo-profile.json`, static site files, review notes,
validation reports, and screenshots when Playwright screenshot support is
available.

The first version focuses on one job: generate a static landing page grounded in real repository facts from the README, docs, package metadata, examples, license, and project assets.

## Product Direction

Read the product documents:

- [docs/product-design.md](docs/product-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/skill-spec.md](docs/skill-spec.md)
- [docs/repo-profile-schema.md](docs/repo-profile-schema.md)
- [docs/quality-checklist.md](docs/quality-checklist.md)
- [docs/agent-compatibility.md](docs/agent-compatibility.md)
- [docs/m4-external-validation.md](docs/m4-external-validation.md)

## Status

RepoStage is currently in product planning. The product name is confirmed, the public repository is created, and the first reviewable product, development, agent-portable Skill, schema, compatibility, and quality documents are checked in.

## License

Apache-2.0
