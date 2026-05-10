#!/usr/bin/env node
import path from "node:path";
import { readdir } from "node:fs/promises";
import { generateSiteFromProfile } from "../src/site-generator.js";

const args = parseArgs(process.argv.slice(2));

if (args.fixtures) {
  const fixturesRoot = path.resolve(args.fixtures);
  const outRoot = path.resolve(args.out || "examples/outputs");
  const entries = await readdir(fixturesRoot, { withFileTypes: true });
  for (const entry of entries.filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
    const result = await generateSiteFromProfile({
      profilePath: path.join(fixturesRoot, entry.name, "repo-profile.json"),
      outDir: path.join(outRoot, entry.name)
    });
    console.log(`Generated ${result.outDir}`);
  }
  process.exit(0);
}

if (!args.profile || !args.out) {
  console.error("Usage: repo-stage-generate-site --profile repo-profile.json --out output-dir");
  console.error("   or: repo-stage-generate-site --fixtures fixtures/profiles --out examples/outputs");
  process.exit(2);
}

const result = await generateSiteFromProfile({
  profilePath: path.resolve(args.profile),
  outDir: path.resolve(args.out)
});

console.log(`Generated ${result.outDir}`);
for (const warning of result.warnings) {
  console.warn(`Warning: ${warning}`);
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--profile") parsed.profile = argv[++index];
    if (arg === "--out") parsed.out = argv[++index];
    if (arg === "--fixtures") parsed.fixtures = argv[++index];
  }
  return parsed;
}
