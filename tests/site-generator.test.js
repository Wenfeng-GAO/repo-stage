import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, stat, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { generateSiteFromProfile, validateProfileForSite } from "../src/site-generator.js";

const profileFixtures = ["repo-stage", "ripgrep", "vite"];

test("generates portable static sites from three sourced repo-profile fixtures", async () => {
  const tmp = await mkdtemp(path.join(tmpdir(), "repo-stage-site-"));
  try {
    for (const fixture of profileFixtures) {
      const outDir = path.join(tmp, fixture);
      await generateSiteFromProfile({
        profilePath: path.join("fixtures", "profiles", fixture, "repo-profile.json"),
        outDir
      });

      const profile = JSON.parse(await readFile(path.join(outDir, "repo-profile.json"), "utf8"));
      const html = await readFile(path.join(outDir, "site", "index.html"), "utf8");
      const css = await readFile(path.join(outDir, "site", "styles.css"), "utf8");
      const report = await readFile(path.join(outDir, "validation-report.md"), "utf8");

      assert.match(html, /<!doctype html>/i);
      assert.ok(html.includes(profile.product.name));
      assert.ok(html.includes(profile.repo.url));
      assert.ok(html.includes(profile.product.quickstart[0]));
      assert.ok(css.includes("@media (max-width: 820px)"));
      assert.ok(report.includes("website copy is limited to high/medium sourced facts"));
      assert.doesNotMatch(html, /\btrusted by\b/i);
      assert.doesNotMatch(html, /\b\d+[,.]?\d*\s*(stars?|downloads?|customers?)\b/i);
    }
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});

test("copies and renders sourced local profile assets", async () => {
  const tmp = await mkdtemp(path.join(tmpdir(), "repo-stage-asset-"));
  try {
    await generateSiteFromProfile({
      profilePath: path.join("fixtures", "profiles", "repo-stage", "repo-profile.json"),
      outDir: tmp
    });

    await stat(path.join(tmp, "site", "assets", "logo-repo-stage-mark.svg"));
    const html = await readFile(path.join(tmp, "site", "index.html"), "utf8");
    assert.ok(html.includes("./assets/logo-repo-stage-mark.svg"));
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});

test("rejects product copy that is not backed by a high or medium sourced fact", () => {
  const profile = minimalProfile({
    product: {
      name: "Toolkit",
      oneLiner: "Used by thousands of teams.",
      features: ["Invented workflow automation"],
      quickstart: ["npm install toolkit"],
      useCases: [],
      examples: [],
      contribution: { hasContributionGuide: false, notes: [] }
    }
  });

  const validation = validateProfileForSite(profile);

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.some((error) => error.includes("product.oneLiner")));
  assert.ok(validation.errors.some((error) => error.includes("product.features[0]")));
});

test("rejects low-confidence product copy even when the text appears in facts", () => {
  const profile = minimalProfile({
    facts: [
      {
        id: "fact-low",
        kind: "feature",
        value: "Probably supports every framework.",
        sourceIds: ["src-readme"],
        confidence: "low"
      }
    ],
    product: {
      name: "Toolkit",
      oneLiner: "",
      features: ["Probably supports every framework."],
      quickstart: [],
      useCases: [],
      examples: [],
      contribution: { hasContributionGuide: false, notes: [] }
    }
  });

  const validation = validateProfileForSite(profile);

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.some((error) => error.includes("product.features[0]")));
});

test("rejects profile assets without known source references", () => {
  const profile = minimalProfile({
    assets: [
      {
        kind: "logo",
        path: "assets/logo.svg",
        sourceIds: ["src-missing"]
      }
    ]
  });

  const validation = validateProfileForSite(profile);

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.some((error) => error.includes("assets[0] references unknown source ID")));
});

test("rejects contributor CTA boolean without a sourced contribution fact", () => {
  const profile = minimalProfile({
    product: {
      name: "Toolkit",
      oneLiner: "",
      features: [],
      quickstart: ["npm install toolkit"],
      useCases: [],
      examples: [],
      contribution: { hasContributionGuide: true, notes: [] }
    }
  });

  const validation = validateProfileForSite(profile);

  assert.equal(validation.valid, false);
  assert.ok(validation.errors.includes("product.contribution.hasContributionGuide requires at least one high/medium sourced contribution fact."));
});

test("rejects local profile assets outside the profile root", async () => {
  const tmp = await mkdtemp(path.join(tmpdir(), "repo-stage-outside-asset-"));
  try {
    const profileDir = path.join(tmp, "profile");
    await mkdir(profileDir, { recursive: true });
    await writeFile(path.join(tmp, "secret.txt"), "do not copy");
    await writeFile(
      path.join(profileDir, "repo-profile.json"),
      `${JSON.stringify(minimalProfile({
        assets: [
          {
            kind: "logo",
            path: "../secret.txt",
            sourceIds: ["src-readme"]
          }
        ]
      }), null, 2)}\n`
    );

    await assert.rejects(
      generateSiteFromProfile({
        profilePath: path.join(profileDir, "repo-profile.json"),
        outDir: path.join(tmp, "out")
      }),
      /outside the profile root/
    );
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});

test("rejects symlinked local profile assets", async () => {
  const tmp = await mkdtemp(path.join(tmpdir(), "repo-stage-symlink-asset-"));
  try {
    const profileDir = path.join(tmp, "profile");
    const assetsDir = path.join(profileDir, "assets");
    await mkdir(assetsDir, { recursive: true });
    await writeFile(path.join(tmp, "secret.svg"), "<svg></svg>");
    await symlink(path.join(tmp, "secret.svg"), path.join(assetsDir, "logo.svg"));
    await writeFile(
      path.join(profileDir, "repo-profile.json"),
      `${JSON.stringify(minimalProfile({
        assets: [
          {
            kind: "logo",
            path: "assets/logo.svg",
            sourceIds: ["src-readme"]
          }
        ]
      }), null, 2)}\n`
    );

    await assert.rejects(
      generateSiteFromProfile({
        profilePath: path.join(profileDir, "repo-profile.json"),
        outDir: path.join(tmp, "out")
      }),
      /cannot be a symlink/
    );
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});

function minimalProfile(overrides = {}) {
  return {
    schemaVersion: "repo-profile.v0",
    repo: {
      url: "https://github.com/example/toolkit",
      owner: "example",
      name: "toolkit",
      description: "Toolkit helps developers.",
      defaultBranch: "main",
      primaryLanguage: "TypeScript",
      license: "MIT",
      topics: []
    },
    sources: [{ id: "src-readme", type: "file", path: "README.md" }],
    facts: [
      {
        id: "fact-quickstart",
        kind: "quickstart",
        value: "npm install toolkit",
        sourceIds: ["src-readme"],
        confidence: "high"
      }
    ],
    product: {
      name: "Toolkit",
      oneLiner: "",
      features: [],
      useCases: [],
      quickstart: ["npm install toolkit"],
      examples: [],
      contribution: { hasContributionGuide: false, notes: [] }
    },
    assets: [],
    gaps: [],
    ...overrides
  };
}
