from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROFILE_SCHEMA_VERSION = "repo-profile.v0"
INGESTION_SCHEMA_VERSION = "repo-stage-ingestion.v0"
CONFIDENCE_LEVELS = {"high", "medium", "low"}
GAP_KINDS = {
    "missing-readme",
    "missing-install",
    "missing-quickstart",
    "missing-example",
    "missing-demo",
    "missing-screenshot",
    "missing-license",
    "missing-contributing",
    "unclear-audience",
    "unclear-positioning",
    "sparse-docs",
}


class ProfileError(Exception):
    """Readable profile generation or validation failure."""


def build_repo_profile(ingestion: dict[str, Any]) -> dict[str, Any]:
    if ingestion.get("schemaVersion") != INGESTION_SCHEMA_VERSION:
        raise ProfileError(f"Expected ingestion schemaVersion {INGESTION_SCHEMA_VERSION}.")

    sources = _profile_sources(ingestion)
    source_ids = {source["id"] for source in sources}
    metadata_source_id = "src-repo-metadata"
    readme_source_id = "src-readme" if "src-readme" in source_ids else ""
    license_source_id = "src-license" if "src-license" in source_ids else ""
    package_source_ids = _source_ids_by_prefix(source_ids, "src-package-")
    doc_source_ids = _source_ids_by_prefix(source_ids, "src-doc-")
    example_source_ids = _source_ids_by_prefix(source_ids, "src-example-")

    repo = _repo(ingestion.get("repo") or {})
    facts: list[dict[str, Any]] = []

    def add_fact(kind: str, value: str, source_ids: list[str], confidence: str = "high") -> None:
        clean_value = _clean_text(value)
        clean_sources = [source_id for source_id in source_ids if source_id in source_ids_set]
        if not clean_value or not clean_sources:
            return
        facts.append(
            {
                "id": f"fact-{kind}-{len([fact for fact in facts if fact['kind'] == kind]) + 1}",
                "kind": kind,
                "value": clean_value,
                "sourceIds": clean_sources,
                "confidence": confidence,
            }
        )

    source_ids_set = source_ids

    if repo["description"]:
        add_fact("positioning", repo["description"], [metadata_source_id], "high")

    readme = ingestion.get("readme") or {}
    readme_content = readme.get("content") or ""
    readme_paragraph = _first_paragraph(readme_content)
    one_liner = repo["description"] or readme_paragraph
    one_liner_sources = [metadata_source_id] if repo["description"] else [readme_source_id]
    if one_liner and one_liner != repo["description"]:
        add_fact("positioning", one_liner, one_liner_sources, "medium")

    feature_items = _feature_items(readme_content)
    for feature in feature_items:
        add_fact("feature", feature, [readme_source_id], "high")

    quickstart_items = _quickstart_items(readme_content, ingestion.get("packageMetadata") or [])
    for item in quickstart_items:
        add_fact("quickstart", item["value"], [item["sourceId"]], item["confidence"])

    example_items = _example_items(readme_content, ingestion.get("examples") or [])
    for item in example_items:
        add_fact("example", item["value"], [item["sourceId"]], item["confidence"])

    for source_id, doc in zip(doc_source_ids, ingestion.get("docs") or [], strict=False):
        summary = _doc_summary(doc.get("path", ""), doc.get("content", ""))
        add_fact("use-case", summary, [source_id], "medium")

    if repo["license"] and license_source_id:
        add_fact("license", repo["license"], [license_source_id], "high")
    elif repo["license"]:
        add_fact("license", repo["license"], [metadata_source_id], "medium")

    product = {
        "name": _product_name(repo, ingestion.get("packageMetadata") or []),
        "oneLiner": one_liner,
        "audiences": [],
        "problems": [],
        "features": _product_items(facts, "feature"),
        "useCases": _product_items(facts, "use-case"),
        "quickstart": _product_items(facts, "quickstart"),
        "examples": _product_items(facts, "example"),
        "contribution": _contribution(ingestion),
    }

    gaps = _profile_gaps(ingestion, facts, repo, product)

    profile = {
        "schemaVersion": PROFILE_SCHEMA_VERSION,
        "repo": repo,
        "sources": sources,
        "facts": sorted(facts, key=lambda fact: fact["id"]),
        "product": product,
        "assets": _assets(ingestion.get("assets") or []),
        "gaps": sorted(gaps, key=lambda gap: (gap["kind"], gap["message"])),
    }
    return profile


def validate_repo_profile(profile_or_text: dict[str, Any] | str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    profile: Any = profile_or_text

    if isinstance(profile_or_text, str):
        try:
            profile = json.loads(profile_or_text)
        except json.JSONDecodeError as exc:
            return {"valid": False, "errors": [f"JSON parse failed: {exc}"], "warnings": warnings}

    if not isinstance(profile, dict):
        return {"valid": False, "errors": ["Profile must be a JSON object."], "warnings": warnings}

    _require(profile, "schemaVersion", "schemaVersion", errors)
    _require(profile, "repo", "repo", errors, dict)
    _require(profile, "sources", "sources", errors, list)
    _require(profile, "facts", "facts", errors, list)
    _require(profile, "product", "product", errors, dict)
    _require(profile, "gaps", "gaps", errors, list)

    if profile.get("schemaVersion") and profile["schemaVersion"] != PROFILE_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {PROFILE_SCHEMA_VERSION}.")

    repo = profile.get("repo") if isinstance(profile.get("repo"), dict) else {}
    _require(repo, "url", "repo.url", errors)
    _require(repo, "owner", "repo.owner", errors)
    _require(repo, "name", "repo.name", errors)

    source_ids = set()
    for index, source in enumerate(profile.get("sources") or []):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object.")
            continue
        _require(source, "id", f"sources[{index}].id", errors)
        _require(source, "type", f"sources[{index}].type", errors)
        if source.get("id"):
            source_ids.add(source["id"])

    fact_ids = set()
    medium_count = 0
    for index, fact in enumerate(profile.get("facts") or []):
        if not isinstance(fact, dict):
            errors.append(f"facts[{index}] must be an object.")
            continue
        _require(fact, "id", f"facts[{index}].id", errors)
        _require(fact, "kind", f"facts[{index}].kind", errors)
        _require(fact, "value", f"facts[{index}].value", errors)
        _require(fact, "sourceIds", f"facts[{index}].sourceIds", errors, list)
        _require(fact, "confidence", f"facts[{index}].confidence", errors)
        if fact.get("id"):
            fact_ids.add(fact["id"])
        if fact.get("confidence") == "medium":
            medium_count += 1
        if fact.get("confidence") and fact["confidence"] not in CONFIDENCE_LEVELS:
            errors.append(f"facts[{index}].confidence must be high, medium, or low.")
        if isinstance(fact.get("sourceIds"), list):
            if not fact["sourceIds"]:
                errors.append(f"facts[{index}].sourceIds must include at least one source ID.")
            for source_id in fact["sourceIds"]:
                if source_id not in source_ids:
                    errors.append(f"facts[{index}] references unknown source ID: {source_id}.")

    for index, claim in enumerate(profile.get("websiteClaims") or []):
        if not isinstance(claim, dict):
            errors.append(f"websiteClaims[{index}] must be an object.")
            continue
        _require(claim, "text", f"websiteClaims[{index}].text", errors)
        _require(claim, "factIds", f"websiteClaims[{index}].factIds", errors, list)
        if isinstance(claim.get("factIds"), list):
            if not claim["factIds"]:
                errors.append(f"websiteClaims[{index}].factIds must include at least one fact ID.")
            for fact_id in claim["factIds"]:
                if fact_id not in fact_ids:
                    errors.append(f"websiteClaims[{index}] references unknown fact ID: {fact_id}.")

    if not _has_fact_kind(profile, {"quickstart", "install"}):
        warnings.append("No install or quickstart command is available.")
    if not repo.get("license"):
        warnings.append("No license is available.")
    if not _has_fact_kind(profile, {"example"}):
        warnings.append("No examples are available.")
    if not (profile.get("product") or {}).get("oneLiner"):
        warnings.append("Product one-liner is empty.")
    fact_count = len(profile.get("facts") or [])
    if fact_count and medium_count / fact_count > 0.5:
        warnings.append("More than half of page sections depend on medium-confidence facts.")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def generate_profile_file(ingestion_path: Path, output_path: Path) -> dict[str, Any]:
    ingestion = json.loads(ingestion_path.read_text(encoding="utf-8"))
    profile = build_repo_profile(ingestion)
    result = validate_repo_profile(profile)
    if not result["valid"]:
        raise ProfileError("; ".join(result["errors"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return profile


def _profile_sources(ingestion: dict[str, Any]) -> list[dict[str, Any]]:
    repo = ingestion.get("repo") or {}
    sources = [
        {
            "id": "src-repo-metadata",
            "type": "metadata",
            "path": "",
            "url": repo.get("metadataUrl") or repo.get("url") or "",
            "notes": "GitHub repository metadata from ingestion.",
        }
    ]
    for source in ingestion.get("sources") or []:
        sources.append(
            {
                "id": source.get("id") or "",
                "type": "file",
                "path": source.get("path") or "",
                "url": source.get("url") or "",
                "notes": source.get("notes") or f"Ingestion source type: {source.get('type', 'file')}.",
            }
        )
    return sorted((source for source in sources if source["id"]), key=lambda source: source["id"])


def _repo(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": repo.get("url") or "",
        "owner": repo.get("owner") or "",
        "name": repo.get("name") or "",
        "description": repo.get("description") or "",
        "defaultBranch": repo.get("defaultBranch") or "main",
        "primaryLanguage": repo.get("primaryLanguage") or "",
        "license": repo.get("license") or "",
        "topics": sorted(str(topic) for topic in repo.get("topics") or []),
    }


def _product_name(repo: dict[str, Any], packages: list[dict[str, Any]]) -> str:
    for package in packages:
        parsed = package.get("parsed") or {}
        if parsed.get("name"):
            return str(parsed["name"])
    return repo["name"]


def _contribution(ingestion: dict[str, Any]) -> dict[str, Any]:
    paths = [source.get("path", "").lower() for source in ingestion.get("sources") or []]
    has_guide = any("contributing" in path for path in paths)
    return {"hasContributionGuide": has_guide, "notes": []}


def _profile_gaps(
    ingestion: dict[str, Any],
    facts: list[dict[str, Any]],
    repo: dict[str, Any],
    product: dict[str, Any],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    seen = set()
    for gap in ingestion.get("gaps") or []:
        kind = gap.get("kind") if gap.get("kind") in GAP_KINDS else "sparse-docs"
        item = {
            "kind": kind,
            "message": gap.get("message") or "Ingestion reported missing or weak source material.",
            "severity": gap.get("severity") or "medium",
        }
        key = (item["kind"], item["message"])
        if key not in seen:
            gaps.append(item)
            seen.add(key)

    def add(kind: str, message: str, severity: str = "medium") -> None:
        key = (kind, message)
        if key not in seen:
            gaps.append({"kind": kind, "message": message, "severity": severity})
            seen.add(key)

    if not any(fact["kind"] == "quickstart" for fact in facts):
        add("missing-install", "No install command was detected.", "high")
        add("missing-quickstart", "No quickstart steps were detected.", "high")
    if not any(fact["kind"] == "example" for fact in facts):
        add("missing-example", "No examples or usage snippets were detected.", "medium")
    if not repo.get("license"):
        add("missing-license", "No license was detected.", "medium")
    if not product.get("oneLiner"):
        add("unclear-positioning", "Product one-liner could not be sourced.", "medium")
    if not product.get("audiences"):
        add("unclear-audience", "Target audience could not be sourced.", "low")
    if not any(asset.get("kind") == "demo" for asset in ingestion.get("assets") or []):
        add("missing-demo", "No demo link found.", "low")
    if not any(asset.get("kind") == "screenshot" for asset in ingestion.get("assets") or []):
        add("missing-screenshot", "No screenshot found.", "low")
    if not product.get("contribution", {}).get("hasContributionGuide"):
        add("missing-contributing", "No contribution guide was detected.", "low")
    return gaps


def _assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (
            {
                "path": asset.get("path") or asset.get("url") or "",
                "kind": asset.get("kind") or "image",
                "sourceIds": [],
            }
            for asset in assets
            if asset.get("path") or asset.get("url")
        ),
        key=lambda asset: (asset["kind"], asset["path"]),
    )


def _product_items(facts: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [
        {
            "value": fact["value"],
            "sourceIds": fact["sourceIds"],
        }
        for fact in facts
        if fact["kind"] == kind and fact["confidence"] in {"high", "medium"}
    ]


def _feature_items(content: str) -> list[str]:
    features: list[str] = []
    in_feature_section = False
    for line in content.splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,4}\s+(.+)$", stripped)
        if heading:
            title = heading.group(1).lower()
            in_feature_section = any(word in title for word in ("feature", "capabilities", "why"))
            continue
        if in_feature_section and re.match(r"^[-*]\s+\S+", stripped):
            features.append(re.sub(r"^[-*]\s+", "", stripped))
        if len(features) >= 5:
            break
    return _dedupe(features)


def _quickstart_items(content: str, packages: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for command in _commands_from_markdown(content):
        lowered = command.lower()
        if any(token in lowered for token in ("npm install", "pnpm add", "yarn add", "pip install", "cargo install", "go install", "uv add")):
            items.append({"value": command, "sourceId": "src-readme", "confidence": "high"})
        elif lowered.startswith(("npm run ", "pnpm ", "yarn ", "python ", "python3 ", "cargo ", "go run ", "npx ")):
            items.append({"value": command, "sourceId": "src-readme", "confidence": "high"})

    for index, package in enumerate(packages):
        source_id = f"src-package-{index + 1}"
        parsed = package.get("parsed") or {}
        name = parsed.get("name")
        if package.get("path") == "package.json" and name and not any("npm install" in item["value"] for item in items):
            items.append({"value": f"npm install {name}", "sourceId": source_id, "confidence": "medium"})
        if package.get("path") == "pyproject.toml" and name and not any("pip install" in item["value"] for item in items):
            items.append({"value": f"pip install {name}", "sourceId": source_id, "confidence": "medium"})
    return _dedupe_items(items)


def _example_items(content: str, examples: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for command in _commands_from_markdown(_section_text(content, {"example", "examples", "usage", "demo"})):
        if not _is_install_command(command):
            items.append({"value": command, "sourceId": "src-readme", "confidence": "medium"})
    for index, example in enumerate(examples):
        summary = _doc_summary(example.get("path", ""), example.get("content", ""))
        if summary:
            items.append({"value": summary, "sourceId": f"src-example-{index + 1}", "confidence": "high"})
    return _dedupe_items(items)


def _commands_from_markdown(content: str) -> list[str]:
    commands: list[str] = []
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        candidate = stripped[2:].strip() if stripped.startswith("$ ") else stripped
        if in_fence or stripped.startswith("$ "):
            if _looks_like_command(candidate):
                commands.append(candidate)
    return _dedupe(commands)


def _section_text(content: str, heading_words: set[str]) -> str:
    selected: list[str] = []
    include = False
    for line in content.splitlines():
        heading = re.match(r"^#{1,4}\s+(.+)$", line.strip())
        if heading:
            title = heading.group(1).lower()
            include = any(word in title for word in heading_words)
            continue
        if include:
            selected.append(line)
    return "\n".join(selected)


def _is_install_command(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("npm install", "pnpm add", "yarn add", "pip install", "cargo install", "go install", "uv add"))


def _looks_like_command(value: str) -> bool:
    return bool(
        value
        and not value.startswith("#")
        and re.match(r"^(npm|pnpm|yarn|npx|pip|uv|python|python3|cargo|go|repo-stage)\b", value)
    )


def _doc_summary(path: str, content: str) -> str:
    heading = _first_heading(content)
    if heading:
        return f"{path}: {heading}" if path else heading
    paragraph = _first_paragraph(content)
    if paragraph:
        return f"{path}: {paragraph}" if path else paragraph
    return path


def _first_heading(content: str) -> str:
    for line in content.splitlines():
        match = re.match(r"^#{1,4}\s+(.+)$", line.strip())
        if match:
            return _clean_text(match.group(1))
    return ""


def _first_paragraph(content: str) -> str:
    paragraph: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
        if len(" ".join(paragraph)) > 220:
            break
    return _clean_text(" ".join(paragraph))


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _source_ids_by_prefix(source_ids: set[str], prefix: str) -> list[str]:
    return sorted(source_id for source_id in source_ids if source_id.startswith(prefix))


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        clean = _clean_text(value)
        key = clean.lower()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def _dedupe_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for item in items:
        key = item["value"].lower()
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _require(
    obj: dict[str, Any],
    key: str,
    path: str,
    errors: list[str],
    expected_type: type | None = None,
) -> None:
    value = obj.get(key) if isinstance(obj, dict) else None
    if value in (None, "", []):
        errors.append(f"{path} is required.")
    elif expected_type and not isinstance(value, expected_type):
        errors.append(f"{path} must be a {expected_type.__name__}.")


def _has_fact_kind(profile: dict[str, Any], kinds: set[str]) -> bool:
    return any(fact.get("kind") in kinds for fact in profile.get("facts") or [])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or validate a RepoStage repo-profile.json.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    generate = subcommands.add_parser("generate", help="Generate repo-profile.json from an ingestion report.")
    generate.add_argument("ingestion", type=Path, help="Path to repo-stage ingestion JSON.")
    generate.add_argument("--out", type=Path, required=True, help="Path for generated repo-profile.json.")

    validate = subcommands.add_parser("validate", help="Validate a repo-profile.json file.")
    validate.add_argument("profile", type=Path, help="Path to repo-profile.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate_profile_file(args.ingestion, args.out)
            return 0
        result = validate_repo_profile(args.profile.read_text(encoding="utf-8"))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        print(f"repo-stage profile failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
