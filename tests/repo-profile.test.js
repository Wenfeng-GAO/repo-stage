import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { buildRepoProfile, validateRepoProfile } from "../src/repo-profile.js";

test("generates a valid deterministic repo-profile from a complete ingestion fixture", async () => {
  const ingestion = await readFixture("complete");
  const profile = buildRepoProfile(ingestion);
  const profileAgain = buildRepoProfile(ingestion);
  const validation = validateRepoProfile(profile);

  assert.equal(profile.schemaVersion, "repo-profile.v0");
  assert.equal(profile.repo.owner, "example");
  assert.equal(profile.repo.name, "toolkit");
  assert.equal(validation.valid, true);
  assert.deepEqual(validation.errors, []);
  assert.equal(JSON.stringify(profile), JSON.stringify(profileAgain));
  assert.ok(profile.facts.length > 0);
  assert.ok(profile.facts.every((fact) => fact.sourceIds.length > 0));
  assert.ok(profile.facts.every((fact) => ["high", "medium"].includes(fact.confidence)));
});

test("records gaps and warnings instead of inventing missing install, license, and examples", async () => {
  const profile = buildRepoProfile(await readFixture("missing-info"));
  const validation = validateRepoProfile(profile);
  const gapKinds = profile.gaps.map((gap) => gap.kind);

  assert.equal(validation.valid, true);
  assert.ok(gapKinds.includes("missing-install"));
  assert.ok(gapKinds.includes("missing-license"));
  assert.ok(gapKinds.includes("missing-example"));
  assert.ok(validation.warnings.includes("No install or quickstart command is available."));
  assert.ok(validation.warnings.includes("No license is available."));
  assert.ok(validation.warnings.includes("No examples are available."));
});

test("validator fails unknown fact source references", () => {
  const profile = {
    schemaVersion: "repo-profile.v0",
    repo: {
      url: "https://github.com/example/toolkit",
      owner: "example",
      name: "toolkit"
    },
    sources: [{ id: "src-readme", type: "file", path: "README.md" }],
    facts: [
      {
        id: "fact-unknown",
        kind: "feature",
        value: "Generates clients",
        sourceIds: ["src-missing"],
        confidence: "high"
      }
    ],
    product: {},
    gaps: []
  };

  const validation = validateRepoProfile(profile);

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.some((error) => error.includes("unknown source ID: src-missing")));
});

test("validator fails missing required repo URL, owner, and name", () => {
  const validation = validateRepoProfile({
    schemaVersion: "repo-profile.v0",
    repo: {},
    sources: [],
    facts: [],
    product: {},
    gaps: []
  });

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.includes("repo.url is required."));
  assert.ok(validation.errors.includes("repo.owner is required."));
  assert.ok(validation.errors.includes("repo.name is required."));
});

test("validator fails generated website claims without corresponding facts", () => {
  const validation = validateRepoProfile({
    schemaVersion: "repo-profile.v0",
    repo: {
      url: "https://github.com/example/toolkit",
      owner: "example",
      name: "toolkit"
    },
    sources: [{ id: "src-readme", type: "file", path: "README.md" }],
    facts: [
      {
        id: "fact-feature-1",
        kind: "feature",
        value: "Generates clients",
        sourceIds: ["src-readme"],
        confidence: "high"
      }
    ],
    product: {},
    gaps: [],
    websiteClaims: [
      {
        text: "Used by thousands of teams",
        factIds: []
      }
    ]
  });

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.includes("websiteClaims[0].factIds must include at least one fact ID."));
});

test("validator reports JSON parse failures", () => {
  const validation = validateRepoProfile("{not json");

  assert.equal(validation.valid, false);
  assert.ok(validation.errors[0].startsWith("JSON parse failed:"));
});

async function readFixture(name) {
  return JSON.parse(await readFile(new URL(`../fixtures/ingestion/${name}.json`, import.meta.url), "utf8"));
}
