#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { validateRepoProfile } from "../src/repo-profile.js";

const file = process.argv[2];

if (!file) {
  console.error("Usage: repo-stage-validate-profile repo-profile.json");
  process.exit(2);
}

const result = validateRepoProfile(await readFile(file, "utf8"));
console.log(JSON.stringify(result, null, 2));
process.exit(result.valid ? 0 : 1);
