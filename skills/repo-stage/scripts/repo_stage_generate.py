#!/usr/bin/env python3
"""Generate a conservative RepoStage static site from a public repo or local fixture."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates" / "site"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RepoStage output files.")
    parser.add_argument("repo", nargs="?", help="Public GitHub repo URL.")
    parser.add_argument("--repo-path", help="Use an existing local repository path instead of cloning.")
    parser.add_argument("--repo-url", help="Source GitHub URL to record when using --repo-path.")
    parser.add_argument("--out", required=True, help="Output directory.")
    parser.add_argument("--style", default="technical", help="Optional visual direction note.")
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(f"repo-stage: {message}")


def parse_github_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        fail("repo URL must be in https://github.com/owner/repo form")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        fail("repo URL must include owner and repository name")
    owner, name = parts[0], re.sub(r"\.git$", "", parts[1])
    return owner, name


def clone_repo(repo_url: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="repo-stage-"))
    target = temp_dir / "repo"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        fail("git is not installed; provide --repo-path for a local checkout")
    except subprocess.CalledProcessError as exc:
        fail(f"could not clone repository: {exc.stderr.strip() or exc.stdout.strip()}")
    return target


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def find_first(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def first_paragraph(markdown: str) -> str:
    in_code = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line or line.startswith("#") or line.startswith("- "):
            continue
        return re.sub(r"\s+", " ", line)
    return ""


def fenced_commands(markdown: str) -> list[str]:
    commands: list[str] = []
    in_code = False
    block: list[str] = []
    for raw in markdown.splitlines():
        if raw.strip().startswith("```"):
            if in_code and block:
                text = "\n".join(block).strip()
                if looks_like_command(text):
                    commands.append(text)
            in_code = not in_code
            block = []
            continue
        if in_code:
            block.append(raw.rstrip())
    return commands[:3]


def looks_like_command(text: str) -> bool:
    first = text.strip().splitlines()[0] if text.strip() else ""
    prefixes = ("npm ", "npx ", "pnpm ", "yarn ", "pip ", "uv ", "cargo ", "go ", "git ", "python ", "python3 ", "./")
    return first.startswith(prefixes) or bool(re.match(r"^[a-z0-9._-]+\s+[a-z0-9._/-]+", first, re.I))


def list_items_after_heading(markdown: str, heading_name: str) -> list[str]:
    lines = markdown.splitlines()
    items: list[str] = []
    capture = False
    for raw in lines:
        line = raw.strip()
        if re.match(r"^#{2,6}\s+", line):
            capture = heading_name.lower() in line.lower()
            continue
        if capture and line.startswith("- "):
            items.append(line[2:].strip())
        elif capture and line and not line.startswith("- "):
            if items:
                break
    return items[:6]


def package_metadata(repo_path: Path) -> dict[str, str]:
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(read_text(package_json))
        except json.JSONDecodeError:
            return {}
        return {
            "name": str(data.get("name") or ""),
            "description": str(data.get("description") or ""),
            "license": str(data.get("license") or ""),
            "language": "JavaScript",
        }
    if (repo_path / "pyproject.toml").exists():
        return {"language": "Python"}
    if (repo_path / "Cargo.toml").exists():
        return {"language": "Rust"}
    if (repo_path / "go.mod").exists():
        return {"language": "Go"}
    return {}


def detect_license(repo_path: Path, metadata: dict[str, str], readme: str) -> tuple[str, str]:
    if metadata.get("license"):
        return metadata["license"], "src-package-json"
    for name in ("LICENSE", "LICENSE.md", "COPYING"):
        if (repo_path / name).exists():
            text = read_text(repo_path / name).lower()
            if "mit license" in text:
                return "MIT", "src-license"
            if "apache license" in text:
                return "Apache-2.0", "src-license"
            return name, "src-license"
    match = re.search(r"(?im)^##\s+license\s*\n+([^\n]+)", readme)
    return (match.group(1).strip(), "src-readme") if match else ("", "")


def build_profile(repo_path: Path, repo_url: str, owner: str, repo_name: str) -> dict:
    readme_path = find_first([repo_path / "README.md", repo_path / "readme.md", repo_path / "README"])
    readme = read_text(readme_path) if readme_path else ""
    metadata = package_metadata(repo_path)
    project_name = first_heading(readme) or metadata.get("name") or repo_name
    one_liner = first_paragraph(readme) or metadata.get("description") or ""
    features = list_items_after_heading(readme, "features")
    quickstart = fenced_commands(readme)
    license_name, license_source = detect_license(repo_path, metadata, readme)
    language = metadata.get("language", "")

    sources = [{"id": "src-repo-url", "type": "metadata", "path": "", "url": repo_url, "notes": "Repository URL provided as input."}]
    if readme_path:
        sources.append({"id": "src-readme", "type": "file", "path": str(readme_path.relative_to(repo_path)), "url": "", "notes": "Primary README source."})
    if (repo_path / "package.json").exists():
        sources.append({"id": "src-package-json", "type": "file", "path": "package.json", "url": "", "notes": "Package metadata."})
    if license_name and license_source == "src-license":
        sources.append({"id": "src-license", "type": "file", "path": "LICENSE", "url": "", "notes": "License source."})

    readme_source = "src-readme" if readme_path else ""
    project_name_source = readme_source or ("src-package-json" if metadata.get("name") else "src-repo-url")
    one_liner_source = readme_source or ("src-package-json" if metadata.get("description") else "")

    facts = [
        {"id": "fact-project-name", "kind": "identity", "value": project_name, "sourceIds": [project_name_source], "confidence": "high"},
        {"id": "fact-repo-url", "kind": "identity", "value": repo_url, "sourceIds": ["src-repo-url"], "confidence": "high"},
        {"id": "fact-repo-owner", "kind": "identity", "value": owner, "sourceIds": ["src-repo-url"], "confidence": "high"},
        {"id": "fact-repo-name", "kind": "identity", "value": repo_name, "sourceIds": ["src-repo-url"], "confidence": "high"},
    ]
    if one_liner:
        facts.append({"id": "fact-one-liner", "kind": "positioning", "value": one_liner, "sourceIds": [one_liner_source], "confidence": "medium"})
    for index, feature in enumerate(features, start=1):
        facts.append({"id": f"fact-feature-{index}", "kind": "feature", "value": feature, "sourceIds": [readme_source], "confidence": "high"})
    for index, command in enumerate(quickstart, start=1):
        facts.append({"id": f"fact-quickstart-{index}", "kind": "quickstart", "value": command, "sourceIds": [readme_source], "confidence": "high"})
    if license_name:
        facts.append({"id": "fact-license", "kind": "license", "value": license_name, "sourceIds": [license_source], "confidence": "high"})

    gaps = []
    if not readme:
        gaps.append({"kind": "missing-readme", "message": "No README file found.", "severity": "high"})
    if not quickstart:
        gaps.append({"kind": "missing-quickstart", "message": "No fenced quickstart or install command found.", "severity": "medium"})
    if not features:
        gaps.append({"kind": "sparse-docs", "message": "No explicit feature list found.", "severity": "medium"})
    if not license_name:
        gaps.append({"kind": "missing-license", "message": "No license detected.", "severity": "medium"})
    gaps.append({"kind": "missing-screenshot", "message": "No screenshot or demo asset was detected by the lightweight helper.", "severity": "low"})

    return {
        "schemaVersion": "repo-profile.v0",
        "repo": {
            "url": repo_url,
            "owner": owner,
            "name": repo_name,
            "description": metadata.get("description", one_liner),
            "defaultBranch": "",
            "primaryLanguage": language,
            "license": license_name,
            "topics": [],
        },
        "sources": sources,
        "facts": facts,
        "product": {
            "name": project_name,
            "oneLiner": one_liner,
            "audiences": ["Developers"] if one_liner else [],
            "problems": [],
            "features": features,
            "useCases": infer_use_cases(one_liner, features),
            "quickstart": quickstart,
            "examples": [],
            "contribution": {"hasContributionGuide": (repo_path / "CONTRIBUTING.md").exists(), "notes": []},
        },
        "assets": [],
        "gaps": gaps,
    }


def infer_use_cases(one_liner: str, features: list[str]) -> list[str]:
    cases = []
    if one_liner:
        cases.append(one_liner)
    for feature in features[:2]:
        cases.append(feature)
    return cases[:3]


def escape_block(text: str) -> str:
    return html.escape(text or "See the repository README for setup details.")


def render_site(profile: dict, out_dir: Path) -> None:
    site_dir = out_dir / "site"
    assets_dir = site_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    index_template = read_text(TEMPLATE_DIR / "index.html")
    css_template = read_text(TEMPLATE_DIR / "styles.css")
    product = profile["product"]
    repo = profile["repo"]
    features = product.get("features") or ["Repository facts were extracted; add a stronger feature list to the README for a sharper page."]
    use_cases = product.get("useCases") or ["Developers can evaluate the project from its README and source files."]
    quickstart = "\n\n".join(product.get("quickstart") or [])

    replacements = {
        "{{PROJECT_NAME}}": html.escape(product.get("name") or repo["name"]),
        "{{ONE_LINER}}": html.escape(product.get("oneLiner") or repo.get("description") or "A public open-source project page generated from repository facts."),
        "{{OWNER}}": html.escape(repo["owner"]),
        "{{REPO_NAME}}": html.escape(repo["name"]),
        "{{GITHUB_URL}}": html.escape(repo["url"]),
        "{{PRIMARY_LANGUAGE}}": html.escape(repo.get("primaryLanguage") or "Not detected"),
        "{{LICENSE}}": html.escape(repo.get("license") or "Not detected"),
        "{{FEATURE_CARDS}}": "\n".join(
            f'          <article class="feature-card"><h3>{html.escape(feature.split(".")[0][:80])}</h3><p>{html.escape(feature)}</p></article>'
            for feature in features[:3]
        ),
        "{{QUICKSTART}}": escape_block(quickstart),
        "{{USE_CASES}}": "\n".join(f"          <li>{html.escape(item)}</li>" for item in use_cases[:4]),
        "{{TRUST_COPY}}": html.escape(
            f"This page is generated from repository files for {repo['owner']}/{repo['name']}. "
            f"License: {repo.get('license') or 'not detected'}. "
            "Review repo-profile.json for source references before publishing."
        ),
    }
    html_out = index_template
    for key, value in replacements.items():
        html_out = html_out.replace(key, value)

    (site_dir / "index.html").write_text(html_out, encoding="utf-8")
    (site_dir / "styles.css").write_text(css_template, encoding="utf-8")


def write_gap_report(profile: dict, out_dir: Path) -> None:
    lines = ["# README Gap Report", ""]
    if profile["gaps"]:
        for gap in profile["gaps"]:
            lines.append(f"- **{gap['severity']} / {gap['kind']}**: {gap['message']}")
    else:
        lines.append("No major gaps detected by the lightweight helper.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "This report separates missing or weak source material from website claims. Add facts to the README or docs before promoting them on the page.",
        ]
    )
    (out_dir / "README-gap-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_report(profile: dict, out_dir: Path, style: str) -> None:
    lines = [
        "# Validation Report",
        "",
        "Status: generated; run `validate_output.py` for strict checks.",
        "",
        "## Checks Recorded",
        "",
        "- Required files were written by the generator.",
        "- `repo-profile.json` was serialized as JSON.",
        "- Website copy was generated from profile fields only.",
        f"- Style direction recorded: {style}.",
        "",
        "## Skipped Checks",
        "",
        "- Desktop browser screenshot: skipped by the lightweight helper.",
        "- Mobile browser screenshot: skipped by the lightweight helper.",
        "- Console error inspection: skipped by the lightweight helper.",
        "",
        "## Review Notes",
        "",
        "- Desktop: review the generated `site/index.html` in a browser before publishing.",
        "- Mobile: verify that headings, buttons, and code blocks fit narrow screens before publishing.",
    ]
    if profile["gaps"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {gap['kind']}: {gap['message']}" for gap in profile["gaps"])
    (out_dir / "validation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_url = args.repo_url or args.repo
    if not repo_url:
        fail("provide a repo URL or --repo-url")
    owner, repo_name = parse_github_url(repo_url)

    repo_path = Path(args.repo_path).resolve() if args.repo_path else clone_repo(repo_url)
    if not repo_path.exists():
        fail(f"repo path does not exist: {repo_path}")

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    profile = build_profile(repo_path, repo_url, owner, repo_name)
    (out_dir / "repo-profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    render_site(profile, out_dir)
    write_gap_report(profile, out_dir)
    write_validation_report(profile, out_dir, args.style)

    print(f"Wrote RepoStage output to {out_dir}")


if __name__ == "__main__":
    main()
