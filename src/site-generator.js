import { copyFile, lstat, mkdir, readFile, realpath, writeFile } from "node:fs/promises";
import path from "node:path";
import { validateRepoProfile } from "./repo-profile.js";

const ALLOWED_FACT_CONFIDENCE = new Set(["high", "medium"]);
const COPYABLE_ASSET_KINDS = new Set(["logo", "screenshot", "image"]);
const BANNED_CLAIMS = [
  /\b\d+[,.]?\d*\s*(stars?|downloads?|customers?|users?|companies?)\b/i,
  /\bbenchmark(?:ed|s)?\b/i,
  /\btestimonial(?:s)?\b/i,
  /\btrusted by\b/i,
  /\bintegration(?:s)?\b/i,
  /\benterprise[- ]grade\b/i
];

export async function generateSiteFromProfile({ profilePath, outDir }) {
  const rawProfile = await readFile(profilePath, "utf8");
  const profile = JSON.parse(rawProfile);
  const validation = validateProfileForSite(profile);
  if (!validation.valid) {
    throw new Error(`Invalid site profile:\n${validation.errors.join("\n")}`);
  }

  const profileDir = path.dirname(profilePath);
  const siteModel = buildSiteModel(profile);
  const siteDir = path.join(outDir, "site");
  const assetsDir = path.join(siteDir, "assets");
  await mkdir(assetsDir, { recursive: true });

  const copiedAssets = await copyProfileAssets(profile, profileDir, assetsDir);
  const heroAsset = copiedAssets.find((asset) => asset.kind === "logo") || copiedAssets.find((asset) => asset.kind === "screenshot");
  const html = renderHtml(profile, siteModel, heroAsset);
  const bannedMatch = BANNED_CLAIMS.find((pattern) => pattern.test(html));
  if (bannedMatch) {
    throw new Error(`Generated HTML contains banned claim pattern: ${bannedMatch}`);
  }

  await writeFile(path.join(siteDir, "index.html"), html);
  await writeFile(path.join(siteDir, "styles.css"), renderCss());
  if (copiedAssets.length === 0) {
    await writeFile(path.join(assetsDir, ".gitkeep"), "");
  }
  await writeFile(path.join(outDir, "repo-profile.json"), `${JSON.stringify(profile, null, 2)}\n`);
  await writeFile(path.join(outDir, "README-gap-report.md"), renderGapReport(profile));
  await writeFile(path.join(outDir, "validation-report.md"), renderValidationReport(profile, validation, copiedAssets));

  return {
    outDir,
    warnings: validation.warnings
  };
}

export function validateProfileForSite(profile) {
  const base = validateRepoProfile(profile);
  const errors = [...base.errors];
  const warnings = [...base.warnings];
  const sourceIds = new Set((profile.sources || []).map((source) => source.id));
  const allowedFacts = sourcedFacts(profile);
  const allowedFactValues = new Set(allowedFacts.map((fact) => normalizeClaim(fact.value)));

  requireSourcedProductValue(profile.product?.oneLiner, "product.oneLiner", allowedFactValues, errors);
  validateProductList(profile.product?.problems, "product.problems", allowedFactValues, errors);
  validateProductList(profile.product?.features, "product.features", allowedFactValues, errors);
  validateProductList(profile.product?.useCases, "product.useCases", allowedFactValues, errors);
  validateProductList(profile.product?.examples, "product.examples", allowedFactValues, errors);
  validateProductList(profile.product?.quickstart, "product.quickstart", allowedFactValues, errors);
  validateProductList(profile.product?.contribution?.notes, "product.contribution.notes", allowedFactValues, errors);

  for (const [index, asset] of (profile.assets || []).entries()) {
    if (!asset.path) {
      errors.push(`assets[${index}].path is required.`);
    }
    if (!Array.isArray(asset.sourceIds) || asset.sourceIds.length === 0) {
      errors.push(`assets[${index}].sourceIds must include at least one source ID.`);
      continue;
    }
    for (const sourceId of asset.sourceIds) {
      if (!sourceIds.has(sourceId)) {
        errors.push(`assets[${index}] references unknown source ID: ${sourceId}.`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

function buildSiteModel(profile) {
  const facts = sourcedFacts(profile);
  const byKind = (kind) => facts.filter((fact) => fact.kind === kind);
  const firstValue = (...kinds) => {
    for (const kind of kinds) {
      const fact = facts.find((item) => item.kind === kind);
      if (fact?.value) return fact.value;
    }
    return "";
  };

  return {
    projectName: profile.product?.name || profile.repo.name,
    oneLiner: firstValue("positioning", "solution") || profile.repo.description || profile.repo.name,
    problem: firstValue("problem"),
    solution: firstValue("solution", "positioning"),
    features: byKind("feature"),
    quickstart: byKind("quickstart"),
    examples: [...byKind("example"), ...byKind("use-case")],
    contribution: byKind("contribution")
  };
}

function sourcedFacts(profile) {
  const sourceIds = new Set((profile.sources || []).map((source) => source.id));
  return (profile.facts || []).filter((fact) => {
    return ALLOWED_FACT_CONFIDENCE.has(fact.confidence) && fact.sourceIds?.length && fact.sourceIds.every((sourceId) => sourceIds.has(sourceId));
  });
}

function requireSourcedProductValue(value, pathName, allowedFactValues, errors) {
  if (!value) return;
  if (!allowedFactValues.has(normalizeClaim(value))) {
    errors.push(`${pathName} must match a high/medium sourced fact before it can be rendered.`);
  }
}

function validateProductList(items, pathName, allowedFactValues, errors) {
  for (const [index, item] of normalizeList(items).entries()) {
    if (!allowedFactValues.has(normalizeClaim(item))) {
      errors.push(`${pathName}[${index}] must match a high/medium sourced fact before it can be rendered.`);
    }
  }
}

async function copyProfileAssets(profile, profileDir, assetsDir) {
  const copied = [];
  const profileRoot = await realpath(profileDir);
  for (const asset of profile.assets || []) {
    if (!COPYABLE_ASSET_KINDS.has(asset.kind) || isRemoteUrl(asset.path)) continue;
    const sourcePath = await resolveProfileAssetPath(profileRoot, asset.path);
    const fileName = `${asset.kind}-${path.basename(asset.path)}`;
    await copyFile(sourcePath, path.join(assetsDir, fileName));
    copied.push({
      ...asset,
      outputPath: `./assets/${fileName}`
    });
  }
  return copied;
}

async function resolveProfileAssetPath(profileRoot, assetPath) {
  const resolvedPath = path.resolve(profileRoot, assetPath);
  const stats = await lstat(resolvedPath);
  if (stats.isSymbolicLink()) {
    throw new Error(`Profile asset cannot be a symlink: ${assetPath}`);
  }
  if (!stats.isFile()) {
    throw new Error(`Profile asset must be a regular file: ${assetPath}`);
  }

  const realAssetPath = await realpath(resolvedPath);
  const relativePath = path.relative(profileRoot, realAssetPath);
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    throw new Error(`Profile asset is outside the profile root: ${assetPath}`);
  }

  return realAssetPath;
}

function renderHtml(profile, model, heroAsset) {
  const repo = profile.repo;
  const ctaHref = model.quickstart.length ? "#quickstart" : repo.url;
  const ctaText = model.quickstart.length ? "Start with the quickstart" : "Open the repository";
  const exampleItems = model.examples.length ? model.examples : [];

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${escapeHtml(model.projectName)} - Project Website</title>
    <meta name="description" content="${escapeHtml(model.oneLiner)}">
    <link rel="stylesheet" href="./styles.css">
  </head>
  <body>
    <header class="hero">
      <nav class="nav">
        <a class="brand" href="${escapeHtml(repo.url)}">${escapeHtml(model.projectName)}</a>
        <div class="nav-links">
          <a href="#features">Features</a>
          <a href="#quickstart">Quickstart</a>
          <a href="${escapeHtml(repo.url)}">GitHub</a>
        </div>
      </nav>
      <div class="hero-grid">
        <div>
          <p class="eyebrow">${escapeHtml(repo.owner)} / ${escapeHtml(repo.name)}</p>
          <h1>${escapeHtml(model.projectName)}</h1>
          <p class="hero-copy">${escapeHtml(model.oneLiner)}</p>
          <div class="actions">
            <a class="button" href="${escapeHtml(ctaHref)}">${escapeHtml(ctaText)}</a>
            <a class="button secondary" href="${escapeHtml(repo.url)}">View on GitHub</a>
          </div>
        </div>
        ${renderHeroPanel(repo, heroAsset)}
      </div>
    </header>

    <main>
      <section class="section problem-solution">
        <div>
          <p class="eyebrow">Problem</p>
          <h2>${escapeHtml(model.problem || "What the repository helps with")}</h2>
        </div>
        <div>
          <p class="eyebrow">Solution</p>
          <p>${escapeHtml(model.solution || model.oneLiner)}</p>
        </div>
      </section>

      ${renderFactCards("Features", "features", model.features, "No sourced features were found in the profile.")}
      ${renderQuickstart(model.quickstart)}
      ${renderFactCards("Examples and use cases", "examples", exampleItems, "No sourced examples or use cases were found in the profile.")}
      ${renderTrust(profile)}
      ${renderContribution(profile, model.contribution)}
    </main>

    <footer class="footer">
      <p>Generated from sourced repository facts. Review the profile and gap report before publishing.</p>
    </footer>
  </body>
</html>
`;
}

function renderHeroPanel(repo, heroAsset) {
  if (heroAsset) {
    return `<aside class="repo-panel asset-panel"><img src="${escapeHtml(heroAsset.outputPath)}" alt="${escapeHtml(heroAsset.kind)} for ${escapeHtml(repo.name)}"></aside>`;
  }
  return `<aside class="repo-panel">
    <span>Repository</span>
    <strong>${escapeHtml(repo.owner)}/${escapeHtml(repo.name)}</strong>
    <p>${escapeHtml(repo.description || repo.url)}</p>
  </aside>`;
}

function renderFactCards(label, id, facts, emptyText) {
  if (!facts.length) {
    return `<section class="section" id="${id}"><div class="section-heading"><p class="eyebrow">${escapeHtml(label)}</p></div><p class="muted">${escapeHtml(emptyText)}</p></section>`;
  }
  return `<section class="section" id="${id}">
    <div class="section-heading"><p class="eyebrow">${escapeHtml(label)}</p></div>
    <div class="card-grid">
      ${facts.map((fact) => `<article class="info-card" data-sources="${escapeHtml(fact.sourceIds.join(","))}"><h3>${escapeHtml(fact.value)}</h3></article>`).join("")}
    </div>
  </section>`;
}

function renderQuickstart(facts) {
  if (!facts.length) {
    return `<section class="section" id="quickstart"><div class="section-heading"><p class="eyebrow">Quickstart</p><h2>Start from the repository</h2></div><p class="muted">No sourced install or quickstart command was found in the profile.</p></section>`;
  }
  return `<section class="section" id="quickstart">
    <div class="section-heading">
      <p class="eyebrow">Quickstart</p>
      <h2>Use the commands documented by the project</h2>
    </div>
    <div class="code-stack">
      ${facts.map((fact, index) => `<div class="command" data-sources="${escapeHtml(fact.sourceIds.join(","))}"><span>Step ${index + 1}</span><pre><code>${escapeHtml(fact.value)}</code></pre></div>`).join("")}
    </div>
  </section>`;
}

function renderTrust(profile) {
  const repo = profile.repo;
  const items = [
    repo.primaryLanguage ? ["Language", repo.primaryLanguage] : null,
    repo.license ? ["License", repo.license] : null,
    repo.defaultBranch ? ["Default branch", repo.defaultBranch] : null,
    repo.topics?.length ? ["Topics", repo.topics.join(", ")] : null,
    ["Repository", repo.url]
  ].filter(Boolean);
  return `<section class="section trust">
    <div class="section-heading"><p class="eyebrow">Project facts</p><h2>Grounded in repository metadata</h2></div>
    <dl class="fact-grid">
      ${items.map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${key === "Repository" ? `<a href="${escapeHtml(value)}">${escapeHtml(value)}</a>` : escapeHtml(value)}</dd></div>`).join("")}
    </dl>
  </section>`;
}

function renderContribution(profile, facts) {
  if (!profile.product?.contribution?.hasContributionGuide && !facts.length) return "";
  return `<section class="section contributor">
    <div><p class="eyebrow">Contribute</p><h2>Help improve ${escapeHtml(profile.product?.name || profile.repo.name)}</h2></div>
    ${facts.length ? `<ul>${facts.map((fact) => `<li data-sources="${escapeHtml(fact.sourceIds.join(","))}">${escapeHtml(fact.value)}</li>`).join("")}</ul>` : "<p>The profile indicates contribution material is available in the repository.</p>"}
    <a class="button secondary" href="${escapeHtml(profile.repo.url)}">Review the repo</a>
  </section>`;
}

function renderCss() {
  return `:root {
  color-scheme: light;
  --bg: #f7f8fb;
  --ink: #15171c;
  --muted: #626a73;
  --line: #d9dee7;
  --panel: #ffffff;
  --accent: #0f766e;
  --accent-strong: #115e59;
  --code: #10141f;
  --code-text: #e9edf5;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--bg);
  line-height: 1.6;
}
a { color: inherit; }
.hero, .section, .footer { padding: 32px clamp(20px, 5vw, 72px); }
.hero {
  min-height: 88vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #eef2f3;
  border-bottom: 1px solid var(--line);
}
.nav {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  margin-bottom: 56px;
}
.brand { font-weight: 800; text-decoration: none; }
.nav-links { display: flex; gap: 18px; color: var(--muted); font-size: 0.95rem; }
.nav-links a { text-decoration: none; }
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.75fr);
  gap: clamp(28px, 5vw, 72px);
  align-items: end;
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, h3, p { overflow-wrap: anywhere; }
h1 { margin: 0; font-size: clamp(3rem, 8vw, 6.5rem); line-height: 0.95; letter-spacing: 0; }
h2 { margin: 0; font-size: clamp(1.75rem, 4vw, 3rem); line-height: 1.1; letter-spacing: 0; }
h3 { margin: 0; font-size: 1.08rem; }
.hero-copy { max-width: 760px; margin: 24px 0 0; color: #39414c; font-size: clamp(1.15rem, 2.2vw, 1.55rem); }
.actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }
.button {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: white;
  font-weight: 750;
  text-decoration: none;
}
.button.secondary { background: transparent; color: var(--accent-strong); }
.repo-panel, .info-card, .command, .fact-grid div, .contributor {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}
.repo-panel { padding: 24px; }
.asset-panel { display: flex; align-items: center; justify-content: center; min-height: 220px; }
.asset-panel img { display: block; max-width: 100%; max-height: 280px; object-fit: contain; }
.repo-panel span, .command span, dt { display: block; color: var(--muted); font-size: 0.82rem; font-weight: 750; }
.repo-panel strong { display: block; margin: 8px 0; font-size: 1.15rem; }
.section { max-width: 1180px; margin: 0 auto; }
.section-heading { max-width: 760px; margin-bottom: 24px; }
.problem-solution { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: 32px; align-items: start; }
.problem-solution p:last-child { margin-top: 0; color: #39414c; font-size: 1.12rem; }
.card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.info-card { padding: 22px; }
.muted { color: var(--muted); }
.code-stack { display: grid; gap: 14px; }
.command { padding: 16px; overflow: hidden; }
pre { margin: 10px 0 0; padding: 16px; overflow-x: auto; border-radius: 6px; background: var(--code); color: var(--code-text); }
code { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 0.94rem; }
.fact-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 0; }
.fact-grid div { padding: 18px; }
dd { margin: 6px 0 0; font-weight: 750; overflow-wrap: anywhere; }
.contributor { display: grid; grid-template-columns: minmax(0, 0.7fr) minmax(0, 1fr) auto; gap: 20px; align-items: center; }
.footer { color: var(--muted); border-top: 1px solid var(--line); }
@media (max-width: 820px) {
  .hero { min-height: auto; }
  .nav, .hero-grid, .problem-solution, .contributor { grid-template-columns: 1fr; flex-direction: column; align-items: flex-start; }
  .nav-links { flex-wrap: wrap; }
  .card-grid, .fact-grid { grid-template-columns: 1fr; }
  h1 { font-size: clamp(2.5rem, 16vw, 4.25rem); }
}
`;
}

function renderGapReport(profile) {
  const gaps = profile.gaps || [];
  const rows = gaps.length ? gaps.map((gap) => `- **${gap.kind}** (${gap.severity || "unknown"}): ${gap.message}`).join("\n") : "- No gaps were recorded in the profile.";
  return `# README Gap Report

Generated for ${profile.repo.owner}/${profile.repo.name}.

${rows}
`;
}

function renderValidationReport(profile, validation, copiedAssets) {
  const warnings = validation.warnings.length ? validation.warnings.map((warning) => `- ${warning}`).join("\n") : "- None";
  const assets = copiedAssets.length ? copiedAssets.map((asset) => `- ${asset.kind}: ${asset.outputPath}`).join("\n") : "- None";
  return `# Validation Report

## Checks

- PASS: repo-profile.json parsed and validated.
- PASS: website copy is limited to high/medium sourced facts and repository metadata.
- PASS: generated HTML includes ${profile.product?.name || profile.repo.name}.
- PASS: generated HTML includes ${profile.repo.url}.

## Warnings

${warnings}

## Copied Assets

${assets}
`;
}

function normalizeList(items) {
  if (!Array.isArray(items)) return [];
  return items.map((item) => String(item ?? "").trim()).filter(Boolean);
}

function normalizeClaim(value) {
  return String(value || "").trim().replace(/\s+/g, " ").toLowerCase();
}

function isRemoteUrl(value) {
  return /^https?:\/\//i.test(String(value || ""));
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
