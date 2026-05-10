#!/usr/bin/env python3
"""Validate the minimum RepoStage output contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


BANNED_PATTERNS = [
    r"\b\d+[,.]?\d*\+?\s+stars\b",
    r"\b\d+[,.]?\d*\+?\s+downloads\b",
    r"\b\d+[,.]?\d*\+?\s+customers\b",
    r"\btrusted by\b",
    r"\bindustry-leading\b",
    r"\bbenchmark(?:ed|s)?\b",
    r"\brevenue\b",
]


def add(lines: list[str], text: str = "") -> None:
    lines.append(text)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_output.py <out_dir>", file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1]).resolve()
    report_lines = ["# Validation Report", ""]
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    required = [
        out_dir / "repo-profile.json",
        out_dir / "README-gap-report.md",
        out_dir / "validation-report.md",
        out_dir / "site" / "index.html",
        out_dir / "site" / "styles.css",
    ]
    for path in required:
        if path.exists():
            checks.append(f"Found `{path.relative_to(out_dir)}`.")
        else:
            errors.append(f"Missing `{path.relative_to(out_dir)}`.")

    profile = None
    profile_path = out_dir / "repo-profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            checks.append("Parsed `repo-profile.json` as JSON.")
        except json.JSONDecodeError as exc:
            errors.append(f"`repo-profile.json` does not parse: {exc}.")

    if profile:
        for field in ("schemaVersion", "repo", "sources", "facts", "product", "gaps"):
            if field not in profile:
                errors.append(f"`repo-profile.json` missing top-level field `{field}`.")
        repo = profile.get("repo", {})
        for field in ("url", "owner", "name"):
            if not repo.get(field):
                errors.append(f"`repo-profile.json` missing `repo.{field}`.")
        source_ids = {source.get("id") for source in profile.get("sources", [])}
        for fact in profile.get("facts", []):
            refs = fact.get("sourceIds") or []
            if not refs:
                errors.append(f"Fact `{fact.get('id', '<unknown>')}` has no source IDs.")
            for ref in refs:
                if ref not in source_ids:
                    errors.append(f"Fact `{fact.get('id', '<unknown>')}` references unknown source `{ref}`.")
        if not profile.get("product", {}).get("quickstart"):
            warnings.append("No quickstart command is available.")
        if not repo.get("license"):
            warnings.append("No license is available.")
        if not profile.get("product", {}).get("examples"):
            warnings.append("No examples are available.")
        if not profile.get("product", {}).get("oneLiner"):
            warnings.append("Product one-liner is empty.")

    html_path = out_dir / "site" / "index.html"
    if profile and html_path.exists():
        html_text = html_path.read_text(encoding="utf-8")
        project_name = profile.get("product", {}).get("name") or profile.get("repo", {}).get("name")
        repo_url = profile.get("repo", {}).get("url")
        if project_name and project_name in html_text:
            checks.append("HTML contains the project name.")
        else:
            errors.append("HTML does not contain the project name.")
        if repo_url and repo_url in html_text:
            checks.append("HTML contains the GitHub URL.")
        else:
            errors.append("HTML does not contain the GitHub URL.")
        for pattern in BANNED_PATTERNS:
            if re.search(pattern, html_text, re.I):
                errors.append(f"HTML contains blocked unsourced claim pattern: `{pattern}`.")

    add(report_lines, f"Status: {'failed' if errors else 'passed'}")
    add(report_lines)
    add(report_lines, "## Checks")
    add(report_lines)
    report_lines.extend(f"- {check}" for check in checks)

    add(report_lines)
    add(report_lines, "## Warnings")
    add(report_lines)
    report_lines.extend(f"- {warning}" for warning in warnings) if warnings else add(report_lines, "- None.")

    add(report_lines)
    add(report_lines, "## Errors")
    add(report_lines)
    report_lines.extend(f"- {error}" for error in errors) if errors else add(report_lines, "- None.")

    add(report_lines)
    add(report_lines, "## Skipped Checks")
    add(report_lines)
    add(report_lines, "- Desktop browser screenshot: not run by this validator.")
    add(report_lines, "- Mobile browser screenshot: not run by this validator.")
    add(report_lines, "- Console error inspection: not run by this validator.")

    add(report_lines)
    add(report_lines, "## Review Notes")
    add(report_lines)
    add(report_lines, "- Desktop: open `site/index.html` and verify content does not overlap.")
    add(report_lines, "- Mobile: test a narrow viewport and verify code blocks scroll cleanly.")

    (out_dir / "validation-report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"RepoStage validation passed for {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
