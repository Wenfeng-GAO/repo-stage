# Repo Profile Schema

`repo-profile.json` is the factual contract between repository ingestion and website generation.

The schema should remain small until real examples prove more fields are needed.

## Version

Current draft version:

```text
repo-profile.v0
```

## Draft Shape

```json
{
  "schemaVersion": "repo-profile.v0",
  "repo": {
    "url": "https://github.com/owner/repo",
    "owner": "owner",
    "name": "repo",
    "description": "",
    "defaultBranch": "main",
    "primaryLanguage": "",
    "license": "",
    "topics": []
  },
  "sources": [
    {
      "id": "src-readme",
      "type": "file",
      "path": "README.md",
      "url": "",
      "notes": ""
    }
  ],
  "facts": [
    {
      "id": "fact-install-command",
      "kind": "quickstart",
      "value": "npm install example",
      "sourceIds": ["src-readme"],
      "confidence": "high"
    }
  ],
  "product": {
    "name": "",
    "oneLiner": "",
    "audiences": [],
    "problems": [],
    "features": [],
    "useCases": [],
    "quickstart": [],
    "examples": [],
    "contribution": {
      "hasContributionGuide": false,
      "notes": []
    }
  },
  "assets": [
    {
      "path": "",
      "kind": "logo",
      "sourceIds": []
    }
  ],
  "gaps": [
    {
      "kind": "missing-demo",
      "message": "No screenshot or demo link found.",
      "severity": "medium"
    }
  ]
}
```

## Field Rules

Required top-level fields:

- `schemaVersion`
- `repo`
- `sources`
- `facts`
- `product`
- `gaps`

Every `facts[]` entry must include at least one `sourceIds[]` value.

Every page section should be generated from either:

- a direct fact, or
- a conservative summary of multiple facts.

If a field cannot be sourced, leave it empty and add a gap instead of inventing content.

## Confidence Levels

Use:

- `high`: explicitly stated in a source.
- `medium`: direct summary of nearby sourced material.
- `low`: plausible inference, allowed only in reports or drafts, not final website claims.

Generated website copy should use only `high` or `medium` facts.

## Gap Kinds

Initial gap kinds:

- `missing-readme`
- `missing-install`
- `missing-quickstart`
- `missing-example`
- `missing-demo`
- `missing-screenshot`
- `missing-license`
- `missing-contributing`
- `unclear-audience`
- `unclear-positioning`
- `sparse-docs`

## Validation Rules

The schema validator should fail when:

- JSON cannot parse.
- `schemaVersion` is missing.
- `repo.url`, `repo.owner`, or `repo.name` is missing.
- A fact references an unknown source ID.
- A generated website claim has no corresponding fact.

The validator should warn when:

- No install or quickstart command is available.
- No license is available.
- No examples are available.
- Product one-liner is empty.
- More than half of page sections depend on medium-confidence facts.
