#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import { buildRepoProfile, validateRepoProfile } from "../src/repo-profile.js";

const args = parseArgs(process.argv.slice(2));

if (!args.input || !args.out) {
  console.error("Usage: repo-stage-generate-profile --input ingestion.json --out repo-profile.json");
  process.exit(2);
}

const ingestion = JSON.parse(await readFile(args.input, "utf8"));
const profile = buildRepoProfile(ingestion);
const validation = validateRepoProfile(profile);

if (!validation.valid) {
  console.error(validation.errors.join("\n"));
  process.exit(1);
}

await writeFile(args.out, `${JSON.stringify(profile, null, 2)}\n`);

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--input") parsed.input = argv[++index];
    if (arg === "--out") parsed.out = argv[++index];
  }
  return parsed;
}
