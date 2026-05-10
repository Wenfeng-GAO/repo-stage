export const SCHEMA_VERSION = "repo-profile.v0";

const CONFIDENCE = new Set(["high", "medium", "low"]);
const SOURCE_TYPES = new Set(["file", "metadata", "url"]);

export function buildRepoProfile(ingestion) {
  const repo = normalizeRepo(ingestion.repo ?? {});
  const sources = normalizeSources(ingestion.sources ?? []);
  const sourceIds = new Set(sources.map((source) => source.id));
  const facts = [];
  const gaps = [];

  const addFact = (fact) => {
    if (!fact.value || !fact.sourceIds?.length) return;
    facts.push({
      id: fact.id,
      kind: fact.kind,
      value: fact.value,
      sourceIds: fact.sourceIds,
      confidence: fact.confidence
    });
  };

  const addGap = (kind, message, severity = "medium") => {
    gaps.push({ kind, message, severity });
  };

  const readmeSource = firstExistingSource(sourceIds, ["src-readme"]);
  const packageSource = firstExistingSource(sourceIds, ["src-package-json", "src-pyproject", "src-cargo", "src-go-mod"]);
  const licenseSource = firstExistingSource(sourceIds, ["src-license"]);
  const docsSource = firstExistingSource(sourceIds, ["src-docs"]);
  const examplesSource = firstExistingSource(sourceIds, ["src-examples"]);

  if (!readmeSource) {
    addGap("missing-readme", "No README source was found.", "high");
  }

  if (repo.description) {
    addFact({
      id: "fact-repo-description",
      kind: "positioning",
      value: repo.description,
      sourceIds: readmeSource ? [readmeSource] : firstSourceIds(sources),
      confidence: readmeSource ? "high" : "medium"
    });
  }

  const product = {
    name: ingestion.product?.name || repo.name || "",
    oneLiner: ingestion.product?.oneLiner || repo.description || "",
    audiences: normalizeList(ingestion.product?.audiences),
    problems: normalizeList(ingestion.product?.problems),
    features: normalizeList(ingestion.product?.features),
    useCases: normalizeList(ingestion.product?.useCases),
    quickstart: normalizeList(ingestion.product?.quickstart),
    examples: normalizeList(ingestion.product?.examples),
    contribution: {
      hasContributionGuide: Boolean(ingestion.product?.contribution?.hasContributionGuide),
      notes: normalizeList(ingestion.product?.contribution?.notes)
    }
  };

  addListFacts(facts, "audience", product.audiences, readmeSource || docsSource, "medium");
  addListFacts(facts, "problem", product.problems, readmeSource || docsSource, "medium");
  addListFacts(facts, "feature", product.features, readmeSource || docsSource, "high");
  addListFacts(facts, "use-case", product.useCases, readmeSource || docsSource, "medium");
  addListFacts(facts, "quickstart", product.quickstart, readmeSource || packageSource || readmeSource, "high");
  addListFacts(facts, "example", product.examples, examplesSource || readmeSource || docsSource, "high");
  addListFacts(facts, "contribution", product.contribution.notes, docsSource || readmeSource, "medium");

  if (product.oneLiner) {
    addFact({
      id: "fact-product-one-liner",
      kind: "positioning",
      value: product.oneLiner,
      sourceIds: readmeSource ? [readmeSource] : firstSourceIds(sources),
      confidence: readmeSource ? "medium" : "low"
    });
  }

  if (repo.license) {
    addFact({
      id: "fact-license",
      kind: "license",
      value: repo.license,
      sourceIds: licenseSource ? [licenseSource] : firstSourceIds(sources),
      confidence: licenseSource ? "high" : "medium"
    });
  } else {
    addGap("missing-license", "No license was detected.", "medium");
  }

  if (product.quickstart.length === 0) {
    addGap("missing-install", "No install command was detected.", "high");
    addGap("missing-quickstart", "No quickstart steps were detected.", "high");
  }

  if (product.examples.length === 0) {
    addGap("missing-example", "No examples or usage snippets were detected.", "medium");
  }

  if (!product.oneLiner) {
    addGap("unclear-positioning", "Product one-liner could not be sourced.", "medium");
  }

  if (product.audiences.length === 0) {
    addGap("unclear-audience", "Target audience could not be sourced.", "low");
  }

  if (!ingestion.assets?.some((asset) => asset.kind === "demo")) {
    addGap("missing-demo", "No demo link found.", "low");
  }

  if (!ingestion.assets?.some((asset) => asset.kind === "screenshot")) {
    addGap("missing-screenshot", "No screenshot found.", "low");
  }

  if (!product.contribution.hasContributionGuide) {
    addGap("missing-contributing", "No contribution guide was detected.", "low");
  }

  const assets = normalizeAssets(ingestion.assets ?? [], sourceIds);
  const sortedFacts = facts.sort((a, b) => a.id.localeCompare(b.id));

  return {
    schemaVersion: SCHEMA_VERSION,
    repo,
    sources,
    facts: sortedFacts,
    product,
    assets,
    gaps: sortByKind(gaps)
  };
}

export function validateRepoProfile(input) {
  let profile = input;
  const errors = [];
  const warnings = [];

  if (typeof input === "string") {
    try {
      profile = JSON.parse(input);
    } catch (error) {
      return {
        valid: false,
        errors: [`JSON parse failed: ${error.message}`],
        warnings
      };
    }
  }

  if (!isObject(profile)) {
    return {
      valid: false,
      errors: ["Profile must be a JSON object."],
      warnings
    };
  }

  requireField(profile, "schemaVersion", "schemaVersion", errors);
  requireField(profile, "repo", "repo", errors, isObject);
  requireField(profile, "sources", "sources", errors, Array.isArray);
  requireField(profile, "facts", "facts", errors, Array.isArray);
  requireField(profile, "product", "product", errors, isObject);
  requireField(profile, "gaps", "gaps", errors, Array.isArray);

  if (profile.schemaVersion && profile.schemaVersion !== SCHEMA_VERSION) {
    errors.push(`schemaVersion must be ${SCHEMA_VERSION}.`);
  }

  if (isObject(profile.repo)) {
    requireField(profile.repo, "url", "repo.url", errors);
    requireField(profile.repo, "owner", "repo.owner", errors);
    requireField(profile.repo, "name", "repo.name", errors);
  }

  const sourceIds = new Set();
  const factIds = new Set();
  if (Array.isArray(profile.sources)) {
    for (const [index, source] of profile.sources.entries()) {
      if (!isObject(source)) {
        errors.push(`sources[${index}] must be an object.`);
        continue;
      }
      requireField(source, "id", `sources[${index}].id`, errors);
      requireField(source, "type", `sources[${index}].type`, errors);
      if (source.id) sourceIds.add(source.id);
      if (source.type && !SOURCE_TYPES.has(source.type)) {
        warnings.push(`sources[${index}].type is not a known source type: ${source.type}.`);
      }
    }
  }

  if (Array.isArray(profile.facts)) {
    for (const [index, fact] of profile.facts.entries()) {
      if (!isObject(fact)) {
        errors.push(`facts[${index}] must be an object.`);
        continue;
      }
      requireField(fact, "id", `facts[${index}].id`, errors);
      requireField(fact, "kind", `facts[${index}].kind`, errors);
      requireField(fact, "value", `facts[${index}].value`, errors);
      requireField(fact, "sourceIds", `facts[${index}].sourceIds`, errors, Array.isArray);
      requireField(fact, "confidence", `facts[${index}].confidence`, errors);
      if (fact.id) factIds.add(fact.id);

      if (fact.confidence && !CONFIDENCE.has(fact.confidence)) {
        errors.push(`facts[${index}].confidence must be high, medium, or low.`);
      }
      if (Array.isArray(fact.sourceIds)) {
        if (fact.sourceIds.length === 0) {
          errors.push(`facts[${index}].sourceIds must include at least one source ID.`);
        }
        for (const sourceId of fact.sourceIds) {
          if (!sourceIds.has(sourceId)) {
            errors.push(`facts[${index}] references unknown source ID: ${sourceId}.`);
          }
        }
      }
    }
  }

  if (Array.isArray(profile.websiteClaims)) {
    for (const [index, claim] of profile.websiteClaims.entries()) {
      if (!isObject(claim)) {
        errors.push(`websiteClaims[${index}] must be an object.`);
        continue;
      }
      requireField(claim, "text", `websiteClaims[${index}].text`, errors);
      requireField(claim, "factIds", `websiteClaims[${index}].factIds`, errors, Array.isArray);
      if (Array.isArray(claim.factIds)) {
        if (claim.factIds.length === 0) {
          errors.push(`websiteClaims[${index}].factIds must include at least one fact ID.`);
        }
        for (const factId of claim.factIds) {
          if (!factIds.has(factId)) {
            errors.push(`websiteClaims[${index}] references unknown fact ID: ${factId}.`);
          }
        }
      }
    }
  }

  if (!hasFactKind(profile, "quickstart")) {
    warnings.push("No install or quickstart command is available.");
  }
  if (!profile.repo?.license) {
    warnings.push("No license is available.");
  }
  if (!hasFactKind(profile, "example")) {
    warnings.push("No examples are available.");
  }
  if (!profile.product?.oneLiner) {
    warnings.push("Product one-liner is empty.");
  }
  if (Array.isArray(profile.facts) && profile.facts.length > 0) {
    const mediumCount = profile.facts.filter((fact) => fact.confidence === "medium").length;
    if (mediumCount / profile.facts.length > 0.5) {
      warnings.push("More than half of facts are medium confidence.");
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

function normalizeRepo(repo) {
  const fromUrl = parseGitHubUrl(repo.url);
  return {
    url: repo.url || "",
    owner: repo.owner || fromUrl.owner || "",
    name: repo.name || fromUrl.name || "",
    description: repo.description || "",
    defaultBranch: repo.defaultBranch || "main",
    primaryLanguage: repo.primaryLanguage || "",
    license: repo.license || "",
    topics: normalizeList(repo.topics)
  };
}

function normalizeSources(sources) {
  return sources
    .map((source) => ({
      id: source.id,
      type: source.type || "file",
      path: source.path || "",
      url: source.url || "",
      notes: source.notes || ""
    }))
    .filter((source) => source.id)
    .sort((a, b) => a.id.localeCompare(b.id));
}

function normalizeAssets(assets, sourceIds) {
  return assets
    .map((asset) => ({
      path: asset.path || asset.url || "",
      kind: asset.kind || "asset",
      sourceIds: normalizeList(asset.sourceIds).filter((sourceId) => sourceIds.has(sourceId))
    }))
    .filter((asset) => asset.path)
    .sort((a, b) => `${a.kind}:${a.path}`.localeCompare(`${b.kind}:${b.path}`));
}

function addListFacts(facts, kind, values, sourceId, confidence) {
  if (!sourceId) return;
  for (const [index, value] of values.entries()) {
    facts.push({
      id: `fact-${kind}-${index + 1}`,
      kind,
      value,
      sourceIds: [sourceId],
      confidence
    });
  }
}

function normalizeList(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item ?? "").trim())
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));
}

function firstExistingSource(sourceIds, candidates) {
  return candidates.find((id) => sourceIds.has(id)) || "";
}

function firstSourceIds(sources) {
  return sources[0]?.id ? [sources[0].id] : [];
}

function sortByKind(gaps) {
  return gaps.sort((a, b) => `${a.kind}:${a.message}`.localeCompare(`${b.kind}:${b.message}`));
}

function parseGitHubUrl(url) {
  const match = String(url || "").match(/^https:\/\/github\.com\/([^/]+)\/([^/#?]+)(?:[/#?].*)?$/);
  if (!match) return {};
  return { owner: match[1], name: match[2].replace(/\.git$/, "") };
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireField(object, key, path, errors, predicate = Boolean) {
  if (!predicate(object?.[key])) {
    errors.push(`${path} is required.`);
  }
}

function hasFactKind(profile, kind) {
  return Array.isArray(profile.facts) && profile.facts.some((fact) => fact.kind === kind);
}
