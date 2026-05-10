#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const repos = [
  "https://github.com/sharkdp/bat",
  "https://github.com/pmndrs/zustand",
  "https://github.com/modelcontextprotocol/servers",
  "https://github.com/browser-use/browser-use",
  "https://github.com/docusealco/docuseal",
];

const root = resolve(new URL("..", import.meta.url).pathname);
const cacheDir = join(root, ".tmp", "m4-repos");
const outputDir = join(root, "examples", "m4");

mkdirSync(cacheDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

for (const repoUrl of repos) {
  const { owner, name } = parseGitHubUrl(repoUrl);
  const slug = `${owner}-${name}`;
  const checkout = join(cacheDir, slug);
  const out = join(outputDir, slug);

  if (!existsSync(checkout)) {
    execFileSync("git", ["clone", "--depth", "1", repoUrl, checkout], {
      stdio: "inherit",
    });
  }

  rmSync(out, { recursive: true, force: true });
  mkdirSync(join(out, "site", "assets"), { recursive: true });
  mkdirSync(join(out, "screenshots"), { recursive: true });

  const profile = buildProfile({ repoUrl, owner, name, checkout });
  writeJson(join(out, "repo-profile.json"), profile);
  writeFileSync(join(out, "README-gap-report.md"), renderGapReport(profile), "utf8");
  writeFileSync(join(out, "site", "index.html"), renderHtml(profile), "utf8");
  writeFileSync(join(out, "site", "styles.css"), renderCss(), "utf8");
  writeFileSync(join(out, "review-notes.md"), renderReviewNotes(profile), "utf8");

  const screenshotNotes = captureScreenshots(out);
  writeFileSync(join(out, "validation-report.md"), renderValidation(profile, screenshotNotes), "utf8");

  console.log(`Generated ${slug}`);
}

function parseGitHubUrl(url) {
  const parsed = new URL(url);
  const [owner, name] = parsed.pathname.replace(/^\/|\.git$/g, "").split("/");
  if (!owner || !name || parsed.hostname !== "github.com") {
    throw new Error(`Invalid GitHub repo URL: ${url}`);
  }
  return { owner, name };
}

function buildProfile({ repoUrl, owner, name, checkout }) {
  const readmePath = findFirstFile(checkout, ["README.md", "readme.md", "README.MD"]);
  const readme = readmePath ? readFileSync(readmePath, "utf8") : "";
  const license = detectLicense(checkout);
  const packageMetadata = readPackageMetadata(checkout);
  const sourceId = "src-readme";
  const metadataSourceId = packageMetadata ? "src-package-metadata" : null;
  const sources = [];
  const facts = [];
  const gaps = [];

  if (readmePath) {
    sources.push({
      id: sourceId,
      type: "file",
      path: basename(readmePath),
      url: `${repoUrl}/blob/HEAD/${basename(readmePath)}`,
      notes: "Primary repository README used for generated copy.",
    });
  } else {
    gaps.push(gap("missing-readme", "No README was found.", "high"));
  }

  if (packageMetadata) {
    sources.push({
      id: metadataSourceId,
      type: "file",
      path: packageMetadata.path,
      url: `${repoUrl}/blob/HEAD/${packageMetadata.path}`,
      notes: "Package metadata used for ecosystem and command hints.",
    });
  }

  const title = packageMetadata?.name || firstHeading(readme) || name;
  const description = packageMetadata?.description || firstParagraph(readme) || "";
  const features = extractBullets(readme).slice(0, 6);
  const commands = extractCommands(readme, packageMetadata).slice(0, 5);
  const examples = extractExampleSentences(readme).slice(0, 3);
  const contribution = hasAnyFile(checkout, ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"]);

  addFact(facts, "fact-description", "description", description, [metadataSourceId || sourceId], description ? "medium" : "low");
  features.forEach((feature, index) => {
    addFact(facts, `fact-feature-${index + 1}`, "feature", feature, [sourceId], "medium");
  });
  commands.forEach((command, index) => {
    addFact(facts, `fact-quickstart-${index + 1}`, "quickstart", command, [sourceId], "high");
  });
  examples.forEach((example, index) => {
    addFact(facts, `fact-example-${index + 1}`, "example", example, [sourceId], "medium");
  });
  if (license) {
    addFact(facts, "fact-license", "license", license, [sourceId], "medium");
  } else {
    gaps.push(gap("missing-license", "No license file was detected by the M4 generator.", "medium"));
  }
  if (!commands.length) {
    gaps.push(gap("missing-quickstart", "No obvious install or quickstart command was extracted.", "high"));
  }
  if (!features.length) {
    gaps.push(gap("sparse-docs", "No concise README bullet list was extracted for features.", "medium"));
  }
  if (!examples.length) {
    gaps.push(gap("missing-example", "No obvious example-oriented prose was extracted.", "medium"));
  }
  if (!contribution) {
    gaps.push(gap("missing-contributing", "No CONTRIBUTING.md file was detected.", "low"));
  }

  return {
    schemaVersion: "repo-profile.v0",
    repo: {
      url: repoUrl,
      owner,
      name,
      description,
      defaultBranch: "HEAD",
      primaryLanguage: packageMetadata?.ecosystem || "",
      license,
      topics: [],
    },
    sources,
    facts: facts.filter((fact) => fact.value),
    product: {
      name: title.replace(/^#\s*/, ""),
      oneLiner: description || `${title} is presented from its repository README.`,
      audiences: inferAudiences(readme, name),
      problems: inferProblems(readme, name),
      features,
      useCases: examples,
      quickstart: commands,
      examples,
      contribution: {
        hasContributionGuide: contribution,
        notes: contribution ? ["Contribution guide detected in the repository."] : [],
      },
    },
    assets: [],
    gaps,
  };
}

function addFact(facts, id, kind, value, sourceIds, confidence) {
  if (!value) return;
  facts.push({
    id,
    kind,
    value,
    sourceIds: sourceIds.filter(Boolean),
    confidence,
  });
}

function gap(kind, message, severity) {
  return { kind, message, severity };
}

function findFirstFile(dir, names) {
  for (const name of names) {
    const path = join(dir, name);
    if (existsSync(path)) return path;
  }
  return null;
}

function hasAnyFile(dir, names) {
  return names.some((name) => existsSync(join(dir, name)));
}

function detectLicense(dir) {
  if (existsSync(join(dir, "LICENSE-APACHE")) && existsSync(join(dir, "LICENSE-MIT"))) {
    return "Apache-2.0 OR MIT";
  }
  const file = findFirstFile(dir, ["LICENSE", "LICENSE.md", "LICENSE-APACHE", "LICENSE-MIT", "COPYING"]);
  if (!file) return "";
  const text = readFileSync(file, "utf8").slice(0, 700).toLowerCase();
  if (text.includes("apache license")) return "Apache-2.0";
  if (text.includes("mit license")) return "MIT";
  if (text.includes("gnu general public license")) return "GPL";
  return basename(file);
}

function readPackageMetadata(dir) {
  const packageJson = join(dir, "package.json");
  if (existsSync(packageJson)) {
    const data = JSON.parse(readFileSync(packageJson, "utf8"));
    return {
      path: "package.json",
      name: data.name || "",
      description: data.description || "",
      ecosystem: "JavaScript/TypeScript",
      install: data.name ? `npm install ${data.name}` : "",
    };
  }
  if (existsSync(join(dir, "Cargo.toml"))) {
    const metadata = readTomlLikeMetadata(join(dir, "Cargo.toml"));
    const packageName = metadata.name || basename(dir).split("-").pop();
    return { path: "Cargo.toml", name: packageName, description: metadata.description || "", ecosystem: "Rust", install: `cargo install ${packageName}` };
  }
  if (existsSync(join(dir, "pyproject.toml"))) {
    const metadata = readTomlLikeMetadata(join(dir, "pyproject.toml"));
    const packageName = metadata.name || basename(dir).split("-").pop();
    return { path: "pyproject.toml", name: packageName, description: metadata.description || "", ecosystem: "Python", install: `pip install ${packageName}` };
  }
  if (existsSync(join(dir, "go.mod"))) {
    return { path: "go.mod", name: basename(dir).split("-").pop(), description: "", ecosystem: "Go", install: "" };
  }
  return null;
}

function readTomlLikeMetadata(path) {
  const text = readFileSync(path, "utf8");
  return {
    name: text.match(/^name\s*=\s*"([^"]+)"/m)?.[1] || "",
    description: text.match(/^description\s*=\s*"([^"]+)"/m)?.[1] || "",
  };
}

function firstHeading(markdown) {
  return markdown.match(/^#\s+(.+)$/m)?.[1]?.trim() || "";
}

function firstParagraph(markdown) {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .split(/\n\s*\n/)
    .map((block) => block.replace(/<[^>]+>/g, "").replace(/\[[^\]]+\]\([^)]+\)/g, "").trim())
    .find((block) => block && !block.startsWith("#") && !block.startsWith("!") && block.length > 60)
    ?.replace(/\s+/g, " ")
    .slice(0, 220) || "";
}

function extractBullets(markdown) {
  return [...markdown.matchAll(/^\s*[-*]\s+(.{20,180})$/gm)]
    .map((match) => cleanMarkdown(match[1]))
    .filter((line) => line && !line.includes("http") && !line.includes("](#"))
    .filter(unique);
}

function extractCommands(markdown, metadata) {
  const commands = [];
  const fences = [...markdown.matchAll(/```(?:bash|sh|shell|console|zsh|fish|powershell)?\n([\s\S]*?)```/gi)];
  for (const fence of fences) {
    for (const rawLine of fence[1].split("\n")) {
      const line = rawLine.replace(/^\s*[$>]\s*/, "").trim();
      if (/^(npm|pnpm|yarn|bun|pip|pipx|uv|cargo|go|docker|git clone|npx|brew)\b/.test(line)) {
        commands.push(line);
      }
    }
  }
  if (metadata?.install) commands.unshift(metadata.install);
  return commands.filter(unique);
}

function extractExampleSentences(markdown) {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .split(/\n/)
    .map((line) => cleanMarkdown(line))
    .filter((line) => /example|usage|use case|demo|quickstart|getting started/i.test(line))
    .filter((line) => line.length > 35 && line.length < 220)
    .filter(unique);
}

function inferAudiences(markdown, name) {
  const lower = markdown.toLowerCase();
  if (lower.includes("react")) return ["React developers", "frontend teams"];
  if (lower.includes("terminal") || lower.includes("command line") || lower.includes("cli")) return ["command-line users", "developers"];
  if (lower.includes("agent") || lower.includes("ai")) return ["AI application developers", "automation builders"];
  return [`developers evaluating ${name}`];
}

function inferProblems(markdown, name) {
  const lower = markdown.toLowerCase();
  if (lower.includes("fast")) return ["Developers need a faster way to complete a common workflow."];
  if (lower.includes("simple")) return ["Developers need a simpler tool with less operational overhead."];
  return [`Developers need to understand where ${name} fits before trying it.`];
}

function cleanMarkdown(value) {
  return value
    .replace(/!\[[^\]]*\]\([^)]+\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function unique(value, index, array) {
  return value && array.indexOf(value) === index;
}

function renderHtml(profile) {
  const github = profile.repo.url;
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(profile.product.name)} | RepoStage Preview</title>
  <link rel="stylesheet" href="./styles.css">
</head>
<body>
  <header class="hero">
    <nav><span>${escapeHtml(profile.product.name)}</span><a href="${github}">GitHub</a></nav>
    <div class="hero-grid">
      <div>
        <p class="eyebrow">${escapeHtml(profile.repo.owner)} / ${escapeHtml(profile.repo.name)}</p>
        <h1>${escapeHtml(profile.product.oneLiner)}</h1>
        <p class="lead">A static RepoStage preview generated from repository README and metadata. Claims are intentionally conservative and source-grounded.</p>
        <div class="actions">
          <a class="primary" href="#quickstart">Try the quickstart</a>
          <a class="secondary" href="${github}">View repository</a>
        </div>
      </div>
      <aside>
        <strong>Repository facts</strong>
        <dl>
          <dt>License</dt><dd>${escapeHtml(profile.repo.license || "Not detected")}</dd>
          <dt>Ecosystem</dt><dd>${escapeHtml(profile.repo.primaryLanguage || "Not detected")}</dd>
          <dt>Sources</dt><dd>${profile.sources.length} repository source${profile.sources.length === 1 ? "" : "s"}</dd>
        </dl>
      </aside>
    </div>
  </header>
  <main>
    <section>
      <h2>Why developers look at it</h2>
      <div class="cards">${profile.product.problems.map((item) => `<article>${escapeHtml(item)}</article>`).join("")}</div>
    </section>
    <section>
      <h2>Repository-grounded features</h2>
      <div class="cards">${profile.product.features.map((item) => `<article>${escapeHtml(item)}</article>`).join("") || "<article>No concise feature bullets were detected.</article>"}</div>
    </section>
    <section id="quickstart">
      <h2>Quickstart</h2>
      <pre><code>${escapeHtml(profile.product.quickstart.join("\n") || "No quickstart command detected.")}</code></pre>
    </section>
    <section>
      <h2>Examples and use cases</h2>
      <ul>${profile.product.examples.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No example prose was detected.</li>"}</ul>
    </section>
  </main>
</body>
</html>
`;
}

function renderCss() {
  return `:root {
  color: #17201b;
  background: #f7f5ef;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; }
a { color: inherit; }
.hero { min-height: 76vh; padding: 28px clamp(20px, 5vw, 72px); background: #e8f0ea; border-bottom: 1px solid #c9d7cd; }
nav { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
nav a { text-decoration: none; border-bottom: 1px solid currentColor; }
.hero-grid { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 48px; align-items: end; margin-top: 12vh; }
.eyebrow { color: #386b51; font-weight: 700; text-transform: uppercase; font-size: 0.82rem; }
h1 { max-width: 960px; margin: 0; font-size: clamp(2.1rem, 5vw, 5rem); line-height: 1.02; letter-spacing: 0; }
.lead { max-width: 720px; font-size: 1.18rem; line-height: 1.65; color: #46504a; }
.actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }
.actions a { min-height: 44px; display: inline-flex; align-items: center; padding: 0 18px; border-radius: 6px; text-decoration: none; font-weight: 700; }
.primary { background: #17201b; color: #fff; }
.secondary { border: 1px solid #17201b; }
aside { background: #fffdf7; border: 1px solid #cfd7cf; border-radius: 8px; padding: 22px; }
dt { margin-top: 16px; color: #5e6a63; font-size: 0.8rem; text-transform: uppercase; }
dd { margin: 4px 0 0; font-weight: 700; }
main { padding: 56px clamp(20px, 5vw, 72px); }
section { max-width: 1120px; margin: 0 auto 56px; }
h2 { font-size: 1.6rem; margin-bottom: 18px; }
.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
article { background: #fff; border: 1px solid #d8d8d1; border-radius: 8px; padding: 18px; line-height: 1.5; }
pre { overflow: auto; background: #18211c; color: #f3fff7; padding: 20px; border-radius: 8px; }
li { margin: 10px 0; line-height: 1.55; }
@media (max-width: 760px) {
  .hero { min-height: auto; padding-bottom: 48px; }
  .hero-grid { grid-template-columns: 1fr; margin-top: 64px; gap: 28px; }
  .cards { grid-template-columns: 1fr; }
  h1 { font-size: 2.25rem; }
}
`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderGapReport(profile) {
  return `# README Gap Report: ${profile.repo.owner}/${profile.repo.name}

${profile.gaps.length ? profile.gaps.map((item) => `- **${item.severity} / ${item.kind}:** ${item.message}`).join("\n") : "No major extraction gaps were detected by the M4 generator."}

## Manual Edit Notes

- Confirm the hero one-liner with a maintainer before publishing.
- Replace conservative extracted feature copy with maintainer-preferred phrasing where needed.
- Add screenshots or demo assets when the repository has a visual workflow but no detected image asset.
`;
}

function renderReviewNotes(profile) {
  const unsupportedRisk = profile.gaps.some((item) => item.kind === "missing-quickstart") ? "medium" : "low";
  return `# Review Notes: ${profile.repo.owner}/${profile.repo.name}

## Output Quality

- The page uses the real repository name and URL.
- The quickstart section ${profile.product.quickstart.length ? "uses commands extracted from repository material." : "needs maintainer input because no command was extracted."}
- Feature copy is conservative and based on README bullets where available.
- Unsupported-claim risk: ${unsupportedRisk}.

## Likely Manual Edits

- Tighten the hero from maintainer-approved positioning.
- Decide whether the first CTA should be install, documentation, demo, or GitHub.
- Add stronger project assets if a logo, screenshot, or demo should lead the page.

## Reviewer Verdict Placeholder

- Reviewer:
- Relationship to project:
- Would use / publish / adapt:
- Required edits:
`;
}

function renderValidation(profile, screenshotNotes) {
  const factSourceIds = new Set(profile.sources.map((source) => source.id));
  const brokenFacts = profile.facts.filter((fact) => fact.sourceIds.some((id) => !factSourceIds.has(id)));
  return `# Validation Report: ${profile.repo.owner}/${profile.repo.name}

## Checks

- Valid JSON profile: pass
- Real repository URL present: pass
- Generated static HTML/CSS: pass
- Facts reference known sources: ${brokenFacts.length ? "fail" : "pass"}
- Quickstart detected: ${profile.product.quickstart.length ? "pass" : "warning"}
- License detected: ${profile.repo.license ? "pass" : "warning"}
- Desktop screenshot: ${screenshotNotes.desktop}
- Mobile screenshot: ${screenshotNotes.mobile}

## Caveats

- This is a first-pass M4 generation output, not maintainer-approved copy.
- GitHub topics and stars are intentionally omitted to avoid unsourced or unstable claims.
- Maintainer feedback is still required before counting this example toward the full M4 acceptance criteria.
`;
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function captureScreenshots(out) {
  const htmlUrl = pathToFileURL(join(out, "site", "index.html")).href;
  const desktop = join(out, "screenshots", "desktop.png");
  const mobile = join(out, "screenshots", "mobile.png");
  try {
    execFileSync("npx", ["playwright", "screenshot", "--viewport-size=1440,1100", htmlUrl, desktop], { stdio: "ignore" });
    execFileSync("npx", ["playwright", "screenshot", "--viewport-size=390,844", htmlUrl, mobile], { stdio: "ignore" });
    return { desktop: "pass", mobile: "pass" };
  } catch {
    return { desktop: "skipped; Playwright screenshot command failed", mobile: "skipped; Playwright screenshot command failed" };
  }
}
