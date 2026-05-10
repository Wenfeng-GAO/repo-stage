from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from repo_stage.ingest import IngestError, GitHubRepo, ingest_repo, parse_github_url


BANNED_CLAIM_PATTERNS = [
    r"\b\d[\d,\.]*\s*(stars?|downloads?|users?|customers?|companies|teams)\b",
    r"\b\d+x\b",
    r"\bbenchmarks?\b",
    r"\btestimonials?\b",
    r"\btrusted by\b",
    r"\bused by\b",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-stage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate RepoStage output for a public GitHub repo.")
    generate.add_argument("repo_url", help="GitHub repository URL, e.g. https://github.com/owner/repo")
    generate.add_argument("--out", default=None, help="Output directory. Defaults to ./generated/<owner>-<repo>.")
    generate.add_argument("--token", help="GitHub API token. Defaults to GITHUB_TOKEN when present.")

    args = parser.parse_args(argv)
    if args.command == "generate":
        return generate_command(args)
    return 1


def generate_command(args: argparse.Namespace) -> int:
    try:
        repo_ref = parse_github_url(args.repo_url)
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out or Path("generated") / f"{repo_ref.owner}-{repo_ref.name}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        ingestion = ingest_repo(args.repo_url, token=args.token or os.environ.get("GITHUB_TOKEN"))
        profile = build_profile_from_ingestion(ingestion)
        write_json(out_dir / "repo-profile.json", profile)
        write_site(out_dir / "site", profile)
        write_gap_report(out_dir / "README-gap-report.md", profile)
        validation = validate_output(out_dir, profile)
        write_validation_report(out_dir / "validation-report.md", validation)

        status = "complete" if validation["status"] == "passed" else "complete_with_warnings"
        print(json.dumps({"status": status, "out": str(out_dir), "validation": validation["status"]}, indent=2))
        return 0 if validation["status"] in {"passed", "warnings"} else 1
    except Exception as exc:  # noqa: BLE001 - CLI should degrade into a report.
        profile = minimal_failed_profile(repo_ref, str(exc))
        failure = {"status": "failed", "error": str(exc), "outputs": expected_outputs()}
        write_json(out_dir / "repo-profile.json", profile)
        write_gap_report(out_dir / "README-gap-report.md", profile)
        write_validation_report(out_dir / "validation-report.md", failure)
        print(json.dumps({"status": "failed", "out": str(out_dir), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def build_profile_from_ingestion(ingestion: dict[str, Any]) -> dict[str, Any]:
    repo = ingestion.get("repo") or {}
    repo_url = repo.get("url") or ""
    sources = normalize_sources(ingestion)
    source_id_by_path = {source.get("path"): source.get("id") for source in sources if source.get("path")}
    facts: list[dict[str, Any]] = []
    gaps = list(ingestion.get("gaps") or [])
    gaps.extend(warning_gap(message) for message in ingestion.get("warnings") or [])
    gaps.extend(error_gap(error) for error in ingestion.get("errors") or [])

    readme = ingestion.get("readme")
    readme_text = source_content(readme)
    text_pool = "\n\n".join(
        source_content(item)
        for item in [readme, *(ingestion.get("docs") or []), *(ingestion.get("examples") or [])]
        if source_content(item)
    )
    package_items = ingestion.get("packageMetadata") or []
    package = package_items[0] if package_items else None
    source_items = [
        item
        for item in [readme, *(ingestion.get("docs") or []), *(ingestion.get("examples") or [])]
        if source_content(item)
    ]

    description = clean_sentence(repo.get("description") or package_description(package) or first_paragraph(readme_text))
    one_liner = description or f"{repo.get('name', 'This repository')} is a public GitHub project."
    add_fact(facts, "description", one_liner, source_id_for_item(source_id_by_path, readme) or "src-github", "medium" if readme else "high")

    sourced_commands: list[tuple[str, str]] = []
    for item in source_items:
        source_id = source_id_for_item(source_id_by_path, item)
        if source_id:
            sourced_commands.extend((command, source_id) for command in extract_commands(source_content(item)))
    sourced_commands.extend(package_commands_with_sources(package_items, source_id_by_path))
    sourced_commands = unique_pairs(sourced_commands)[:6]
    commands = [command for command, _source_id in sourced_commands]
    for command, source_id in sourced_commands:
        add_fact(facts, "quickstart", command, source_id, "high")

    sourced_features: list[tuple[str, str]] = []
    for item in source_items:
        source_id = source_id_for_item(source_id_by_path, item)
        if source_id:
            sourced_features.extend((feature, source_id) for feature in extract_features(source_content(item)))
    sourced_features = unique_pairs(sourced_features)
    features = [feature for feature, _source_id in sourced_features]
    if features:
        for feature, source_id in sourced_features[:6]:
            add_fact(facts, "feature", feature, source_id, "medium")
    else:
        features = [one_liner]
        gaps.append({"kind": "unclear-positioning", "message": "Repository sources did not expose clear feature bullets.", "severity": "medium"})

    sourced_examples: list[tuple[str, str]] = []
    for item in source_items:
        source_id = source_id_for_item(source_id_by_path, item)
        if source_id:
            sourced_examples.extend((example, source_id) for example in extract_examples(source_content(item)))
    sourced_examples = unique_pairs(sourced_examples)
    examples = [example for example, _source_id in sourced_examples]
    for example, source_id in sourced_examples[:3]:
        add_fact(facts, "example", example, source_id, "high")

    contribution = any("contributing" in str(source.get("path", "")).lower() for source in sources)
    use_cases: list[str] = []
    gaps.append({
        "kind": "unclear-use-cases",
        "message": "Heuristic use-case suggestions are kept out of the generated site until they can be tied to exact source facts.",
        "severity": "low",
    })

    return {
        "schemaVersion": "repo-profile.v0",
        "repo": {
            "url": repo_url,
            "owner": repo.get("owner", ""),
            "name": repo.get("name", ""),
            "description": description,
            "defaultBranch": repo.get("defaultBranch", ""),
            "primaryLanguage": repo.get("primaryLanguage", ""),
            "license": repo.get("license", ""),
            "topics": repo.get("topics") or [],
        },
        "sources": sources,
        "facts": facts,
        "product": {
            "name": display_name(repo.get("name", ""), package),
            "oneLiner": one_liner,
            "audiences": infer_audiences(text_pool),
            "problems": [],
            "features": features[:6],
            "useCases": use_cases,
            "quickstart": commands,
            "examples": examples[:3],
            "contribution": {
                "hasContributionGuide": contribution,
                "notes": ["Contribution guide found in repository."] if contribution else [],
            },
        },
        "assets": normalize_profile_assets(ingestion.get("assets") or [], source_id_by_path),
        "gaps": gaps,
    }


def normalize_sources(ingestion: dict[str, Any]) -> list[dict[str, Any]]:
    repo = ingestion.get("repo") or {}
    sources = [{
        "id": "src-github",
        "type": "github-metadata",
        "path": "",
        "url": repo.get("metadataUrl") or repo.get("url", ""),
        "notes": "GitHub repository metadata from ingestion",
    }]
    for idx, item in enumerate(ingestion.get("sources") or [], 1):
        sources.append({
            "id": item.get("id") or f"src-{idx}",
            "type": item.get("type") or "file",
            "path": item.get("path", ""),
            "url": item.get("url", ""),
            "notes": item.get("notes", ""),
        })
    existing_paths = {source["path"] for source in sources if source.get("path")}
    for idx, item in enumerate(ingestion.get("assets") or [], 1):
        asset_path = item.get("path", "")
        if not asset_path or asset_path in existing_paths:
            continue
        sources.append({
            "id": f"src-asset-{idx}",
            "type": "file",
            "path": asset_path,
            "url": item.get("url", ""),
            "notes": f"Repository asset detected as {item.get('kind', 'image')}",
        })
    return sources


def source_content(source: dict[str, Any] | None) -> str:
    return str((source or {}).get("content") or "")


def source_id_for_item(source_id_by_path: dict[str, str], item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    return source_id_by_path.get(item.get("path"))


def add_fact(facts: list[dict[str, Any]], kind: str, value: str, source_id: str | None, confidence: str) -> None:
    if value and source_id:
        facts.append({
            "id": f"fact-{len(facts) + 1}",
            "kind": kind,
            "value": value,
            "sourceIds": [source_id],
            "confidence": confidence,
        })


def first_paragraph(text: str) -> str:
    stripped = strip_markdown_noise(text)
    for para in re.split(r"\n\s*\n", stripped):
        para = " ".join(line.strip() for line in para.splitlines() if line.strip() and not line.strip().startswith(("#", "[!", "<")))
        if len(para) > 30:
            return para
    return ""


def clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", strip_markdown_noise(str(text))).strip(" -")
    return text[:220].strip()


def strip_markdown_noise(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


def extract_commands(text: str) -> list[str]:
    commands: list[str] = []
    for block in re.findall(r"```(?:bash|sh|shell|console|zsh|terminal)?\n(.*?)```", text, flags=re.S | re.I):
        for line in block.splitlines():
            line = line.strip()
            line = re.sub(r"^\$ ", "", line)
            if is_command(line):
                commands.append(line)
    for line in text.splitlines():
        line = line.strip("` ")
        if is_command(line):
            commands.append(line)
    return commands


def is_command(line: str) -> bool:
    if not line or len(line) > 160 or line.startswith(("#", "//", ">>>")):
        return False
    return bool(re.match(r"^(npm|pnpm|yarn|bun|npx|pipx?|uv|cargo|go|git clone|docker|make|cmake|brew|curl|repo-stage)\b", line))


def package_description(package: dict[str, Any] | None) -> str:
    parsed = (package or {}).get("parsed") or {}
    return str(parsed.get("description") or "")


def package_commands_with_sources(package_items: list[dict[str, Any]], source_id_by_path: dict[str, str]) -> list[tuple[str, str]]:
    commands: list[tuple[str, str]] = []
    for package in package_items:
        path = str(package.get("path") or "")
        source_id = source_id_by_path.get(path)
        if not source_id:
            continue
        parsed = package.get("parsed") or {}
        name = parsed.get("name") or parsed.get("module")
        if path.endswith("package.json") and name:
            commands.append((f"npm install {name}", source_id))
            scripts = parsed.get("scripts") or {}
            for script in ("dev", "build", "test", "start"):
                if script in scripts:
                    commands.append((f"npm run {script}", source_id))
        elif path.endswith("pyproject.toml") and name:
            commands.append((f"pip install {name}", source_id))
        elif path.endswith("Cargo.toml") and name:
            commands.append((f"cargo install {name}", source_id))
        elif path.endswith("go.mod") and name:
            commands.append((f"go install {name}@latest", source_id))
    return commands


def extract_features(text: str) -> list[str]:
    features: list[str] = []
    in_section = False
    for line in strip_markdown_noise(text).splitlines():
        lower = line.lower().strip()
        if re.match(r"^#{1,3}\s+(features|why|highlights|capabilities|what)", lower):
            in_section = True
            continue
        if in_section and lower.startswith("#"):
            break
        if in_section and re.match(r"^[-*]\s+\S", line.strip()):
            features.append(clean_sentence(re.sub(r"^[-*]\s+", "", line.strip())))
    if not features:
        for line in strip_markdown_noise(text).splitlines():
            if re.match(r"^[-*]\s+\S", line.strip()):
                item = clean_sentence(re.sub(r"^[-*]\s+", "", line.strip()))
                if 20 <= len(item) <= 180 and not looks_like_navigation_item(item):
                    features.append(item)
    return unique([feature for feature in features if feature])


def looks_like_navigation_item(item: str) -> bool:
    lower = item.lower()
    if lower.startswith(("http", "npm ", "pip ")):
        return True
    return bool(re.fullmatch(r"[\w./-]+\.(md|mdx|rst|txt)", item, re.I))


def extract_examples(text: str) -> list[str]:
    examples = []
    for block in re.findall(r"```(?:\w+)?\n(.*?)```", text, flags=re.S):
        cleaned = block.strip()
        if 20 <= len(cleaned) <= 600 and not cleaned.startswith("{"):
            examples.append(cleaned)
    return examples


def extract_use_cases(text: str, repo_name: str) -> list[str]:
    use_cases = []
    lower = text.lower()
    if "cli" in lower or "command line" in lower:
        use_cases.append("Use from the command line in local development workflows.")
    if "react" in lower or "component" in lower:
        use_cases.append("Build application interfaces with reusable components.")
    if "api" in lower or "sdk" in lower:
        use_cases.append("Integrate repository capabilities into developer applications.")
    if not use_cases:
        use_cases.append(f"Evaluate {repo_name} from the generated quickstart and repository documentation.")
    return use_cases[:3]


def infer_audiences(text: str) -> list[str]:
    lower = text.lower()
    audiences = []
    if any(term in lower for term in ("developer", "cli", "api", "sdk", "library")):
        audiences.append("Developers")
    if any(term in lower for term in ("react", "component", "ui", "design")):
        audiences.append("Frontend teams")
    if any(term in lower for term in ("agent", "ai", "llm", "model")):
        audiences.append("AI builders")
    if not audiences:
        audiences.append("Open-source users")
    return audiences[:3]


def display_name(repo_name: str, package: dict[str, Any] | None) -> str:
    name = ((package or {}).get("parsed") or {}).get("name")
    if name:
        return str(name).split("/")[-1]
    return repo_name


def unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def unique_pairs(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    result = []
    for value, source_id in items:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append((value, source_id))
    return result


def normalize_profile_assets(assets: list[dict[str, Any]], source_id_by_path: dict[str, str]) -> list[dict[str, Any]]:
    normalized = []
    for item in assets:
        asset_path = item.get("path", "")
        source_id = source_id_by_path.get(asset_path)
        if not asset_path or not source_id:
            continue
        normalized.append({
            "path": asset_path,
            "kind": item.get("kind", "image"),
            "sourceIds": [source_id],
        })
    return normalized


def warning_gap(message: str) -> dict[str, str]:
    return {"kind": "ingestion-warning", "message": message, "severity": "low"}


def error_gap(error: dict[str, Any]) -> dict[str, str]:
    message = error.get("message") if isinstance(error, dict) else str(error)
    return {"kind": "ingestion-error", "message": str(message), "severity": "medium"}


def gap(kind: str, message: str, severity: str) -> dict[str, str]:
    return {"kind": kind, "message": message, "severity": severity}


def write_site(site_dir: Path, profile: dict[str, Any]) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "assets").mkdir(exist_ok=True)
    (site_dir / "index.html").write_text(render_html(profile), encoding="utf-8")
    (site_dir / "styles.css").write_text(render_css(), encoding="utf-8")


def render_html(profile: dict[str, Any]) -> str:
    repo = profile["repo"]
    product = profile["product"]
    name = html.escape(product["name"] or repo["name"])
    one_liner = html.escape(product["oneLiner"] or repo["description"] or "Open-source project")
    features = product["features"] or []
    quickstart = product["quickstart"] or []
    use_cases = product["useCases"] or []
    facts = [
        ("Language", repo.get("primaryLanguage") or "Not detected"),
        ("License", repo.get("license") or "Not declared"),
        ("Repository", f"{repo['owner']}/{repo['name']}"),
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name} | RepoStage</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <section class="hero">
      <p class="eyebrow">Generated from repository sources</p>
      <h1>{name}</h1>
      <p class="lead">{one_liner}</p>
      <div class="actions">
        <a class="button primary" href="{html.escape(repo['url'])}">View on GitHub</a>
        {quickstart_link(quickstart)}
      </div>
    </section>

    <section id="quickstart" class="band">
      <div>
        <p class="eyebrow">Quickstart</p>
        <h2>Start from commands found in the repo</h2>
      </div>
      {render_commands(quickstart)}
    </section>

    <section class="grid-section">
      <div>
        <p class="eyebrow">What it offers</p>
        <h2>Source-grounded project highlights</h2>
      </div>
      <div class="cards">{render_cards(features)}</div>
    </section>

    <section class="grid-section muted">
      <div>
        <p class="eyebrow">Use cases</p>
        <h2>Where this project fits</h2>
      </div>
      <div class="cards">{render_cards(use_cases)}</div>
    </section>

    <section class="facts">
      {''.join(f'<div><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>' for label, value in facts)}
    </section>
  </main>
</body>
</html>
"""


def quickstart_link(commands: list[str]) -> str:
    if commands:
        return '<a class="button" href="#quickstart">Copy quickstart</a>'
    return ""


def render_commands(commands: list[str]) -> str:
    if not commands:
        return '<p class="empty">No install or usage command was found. See README-gap-report.md for the missing source material.</p>'
    escaped = "\n".join(html.escape(command) for command in commands[:6])
    return f"<pre><code>{escaped}</code></pre>"


def render_cards(items: list[str]) -> str:
    if not items:
        return '<article><p>Not enough sourced detail was available for this section.</p></article>'
    return "".join(f"<article><p>{html.escape(item)}</p></article>" for item in items[:6])


def render_css() -> str:
    return """* { box-sizing: border-box; }
:root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #5f6c78;
  --line: #d9e0e7;
  --paper: #fbfcfd;
  --band: #eef4f8;
  --accent: #0f766e;
  --accent-ink: #ffffff;
}
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
}
main { max-width: 1120px; margin: 0 auto; padding: 40px 24px 64px; }
.hero { min-height: 54vh; display: grid; align-content: center; border-bottom: 1px solid var(--line); padding: 40px 0 56px; }
.eyebrow { color: var(--accent); font-size: 0.78rem; font-weight: 800; letter-spacing: 0; text-transform: uppercase; margin: 0 0 12px; }
h1 { font-size: clamp(3rem, 8vw, 6.5rem); line-height: 0.94; margin: 0; max-width: 900px; }
h2 { font-size: clamp(1.75rem, 4vw, 3rem); line-height: 1; margin: 0; max-width: 720px; }
.lead { font-size: clamp(1.15rem, 2.5vw, 1.55rem); color: var(--muted); max-width: 780px; margin: 24px 0 0; }
.actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 32px; }
.button { min-height: 44px; display: inline-flex; align-items: center; justify-content: center; padding: 10px 16px; border: 1px solid var(--line); color: var(--ink); text-decoration: none; font-weight: 700; border-radius: 6px; }
.button.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
section { margin-top: 48px; }
.band { background: var(--band); padding: 28px; border-radius: 8px; display: grid; grid-template-columns: 0.8fr 1.2fr; gap: 28px; align-items: start; }
pre { margin: 0; overflow: auto; padding: 20px; background: #111827; color: #e5edf4; border-radius: 8px; font-size: 0.95rem; }
.grid-section { display: grid; grid-template-columns: 0.8fr 1.2fr; gap: 28px; align-items: start; }
.cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
article { border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 18px; min-height: 112px; }
article p { margin: 0; color: var(--muted); }
.muted article { background: #f7fafb; }
.facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); }
.facts div { background: #fff; padding: 18px; min-width: 0; }
.facts span { display: block; color: var(--muted); font-size: 0.85rem; }
.facts strong { display: block; margin-top: 6px; overflow-wrap: anywhere; }
.empty { color: var(--muted); margin: 0; }
@media (max-width: 760px) {
  main { padding: 24px 16px 44px; }
  .hero { min-height: auto; padding-top: 36px; }
  .band, .grid-section { grid-template-columns: 1fr; }
  .cards, .facts { grid-template-columns: 1fr; }
}
"""


def write_gap_report(path: Path, profile: dict[str, Any]) -> None:
    gaps = profile.get("gaps", [])
    lines = [
        f"# README Gap Report: {profile.get('repo', {}).get('owner', '')}/{profile.get('repo', {}).get('name', '')}",
        "",
        "RepoStage only uses sourced repository facts. The items below explain what was missing or weak.",
        "",
    ]
    if not gaps:
        lines.append("No blocking README gaps were detected.")
    else:
        for item in gaps:
            lines.append(f"- **{item.get('severity', 'medium')} / {item.get('kind', 'gap')}**: {item.get('message', '')}")
    lines.extend(["", "## Output Contract", "", *[f"- `{item}`" for item in expected_outputs()]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_output(out_dir: Path, profile: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    for rel in expected_outputs(include_validation_report=False):
        if not (out_dir / rel).exists():
            errors.append(f"Missing required output: {rel}")
    try:
        parsed = json.loads((out_dir / "repo-profile.json").read_text(encoding="utf-8"))
        validate_profile(parsed, errors, warnings)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"repo-profile.json did not parse: {exc}")
    html_text = (out_dir / "site" / "index.html").read_text(encoding="utf-8") if (out_dir / "site" / "index.html").exists() else ""
    sourced_fact_text = "\n".join(str(fact.get("value", "")) for fact in profile.get("facts", []))
    if profile["repo"]["name"] not in html_text and profile["product"]["name"] not in html_text:
        errors.append("Generated HTML does not include the project name.")
    if profile["repo"]["url"] not in html_text:
        errors.append("Generated HTML does not include the GitHub repository URL.")
    plain_html = html.unescape(re.sub(r"<[^>]+>", " ", html_text))
    for pattern in BANNED_CLAIM_PATTERNS:
        for match in re.finditer(pattern, plain_html, re.I):
            if match.group(0).lower() not in sourced_fact_text.lower():
                errors.append(f"Generated HTML may contain an unsourced banned claim: {match.group(0)}")
    if not profile["product"].get("quickstart"):
        warnings.append("No quickstart commands were available.")
    if not profile["repo"].get("license"):
        warnings.append("No license was available.")
    status = "failed" if errors else "warnings" if warnings else "passed"
    return {"status": status, "errors": errors, "warnings": warnings, "outputs": expected_outputs()}


def validate_profile(profile: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    required = ["schemaVersion", "repo", "sources", "facts", "product", "gaps"]
    for key in required:
        if key not in profile:
            errors.append(f"Profile missing top-level field: {key}")
    if profile.get("schemaVersion") != "repo-profile.v0":
        errors.append("Profile schemaVersion must be repo-profile.v0")
    repo = profile.get("repo", {})
    for key in ("url", "owner", "name"):
        if not repo.get(key):
            errors.append(f"Profile repo.{key} is required")
    source_ids = {item.get("id") for item in profile.get("sources", [])}
    for fact in profile.get("facts", []):
        if not fact.get("sourceIds"):
            errors.append(f"Fact {fact.get('id')} must include at least one source")
        for source_id in fact.get("sourceIds", []):
            if source_id not in source_ids:
                errors.append(f"Fact {fact.get('id')} references unknown source {source_id}")
    for index, asset in enumerate(profile.get("assets", [])):
        if not asset.get("path"):
            errors.append(f"Asset {index} path is required")
        asset_source_ids = asset.get("sourceIds") or []
        if not asset_source_ids:
            errors.append(f"Asset {asset.get('path') or index} must include at least one source")
        for source_id in asset_source_ids:
            if source_id not in source_ids:
                errors.append(f"Asset {asset.get('path') or index} references unknown source {source_id}")
    sourced_values = {
        str(fact.get("value"))
        for fact in profile.get("facts", [])
        if fact.get("confidence") in {"high", "medium"} and fact.get("sourceIds")
    }
    product = profile.get("product", {})
    validate_sourced_product_value(product.get("oneLiner"), "product.oneLiner", sourced_values, errors)
    for field in ("features", "useCases", "quickstart", "examples"):
        for index, value in enumerate(product.get(field) or []):
            validate_sourced_product_value(value, f"product.{field}[{index}]", sourced_values, errors)
    if not profile.get("product", {}).get("oneLiner"):
        warnings.append("Product oneLiner is empty.")


def validate_sourced_product_value(value: str | None, path_name: str, sourced_values: set[str], errors: list[str]) -> None:
    if value and value not in sourced_values:
        errors.append(f"{path_name} must match a high/medium sourced fact")


def write_validation_report(path: Path, validation: dict[str, Any]) -> None:
    lines = ["# Validation Report", "", f"Status: **{validation.get('status', 'unknown')}**", ""]
    if validation.get("error"):
        lines.extend(["## Error", "", validation["error"], ""])
    for title, key in (("Errors", "errors"), ("Warnings", "warnings")):
        lines.extend([f"## {title}", ""])
        items = validation.get(key) or []
        lines.extend([f"- {item}" for item in items] or ["None."])
        lines.append("")
    lines.extend(["## Required Outputs", "", *[f"- `{item}`" for item in validation.get("outputs", expected_outputs())]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expected_outputs(include_validation_report: bool = True) -> list[str]:
    outputs = ["site/index.html", "site/styles.css", "repo-profile.json", "README-gap-report.md"]
    if include_validation_report:
        outputs.append("validation-report.md")
    return outputs


def minimal_failed_profile(repo_ref: GitHubRepo, error: str) -> dict[str, Any]:
    return {
        "schemaVersion": "repo-profile.v0",
        "repo": {
            "url": repo_ref.html_url,
            "owner": repo_ref.owner,
            "name": repo_ref.name,
            "description": "",
            "defaultBranch": "",
            "primaryLanguage": "",
            "license": "",
            "topics": [],
        },
        "sources": [],
        "facts": [],
        "product": {
            "name": repo_ref.name,
            "oneLiner": "",
            "audiences": [],
            "problems": [],
            "features": [],
            "useCases": [],
            "quickstart": [],
            "examples": [],
            "contribution": {"hasContributionGuide": False, "notes": []},
        },
        "assets": [],
        "gaps": [gap("generation-failed", error, "high")],
    }


if __name__ == "__main__":
    raise SystemExit(main())
