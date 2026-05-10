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

The first version focuses on one job: generate a static landing page grounded in real repository facts from the README, docs, package metadata, examples, license, and project assets.

## Product Direction

Read the product design document:

- [docs/product-design.md](docs/product-design.md)

## Status

RepoStage is currently in project initialization. The product name is confirmed, the public repository is created, and the first product design document is checked in.

## License

Apache-2.0
