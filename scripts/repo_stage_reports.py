#!/usr/bin/env python3
"""Write RepoStage gap and validation reports from generated output files."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_TOP_LEVEL_FIELDS = ["schemaVersion", "repo", "sources", "facts", "product", "gaps"]
GAP_KINDS = [
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
]
BANNED_CLAIM_PATTERNS = [
    r"\b\d+[\d,.]*\s+stars?\b",
    r"\b\d+[\d,.]*\s+downloads?\b",
    r"\b\d+[\d,.]*\s+customers?\b",
    r"\bbenchmarks?\b",
    r"\brevenue\b",
    r"\btestimonials?\b",
]


@dataclass
class Check:
    name: str
    status: str
    detail: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_names = ("href", "src")
        for name, value in attrs:
            if name in attr_names and value:
                self.links.append(value)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._skip_depth = 0
        self._current: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "blockquote", "figcaption", "code", "pre"}:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "blockquote", "figcaption", "code", "pre"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self._current.append(text)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        if not self._current:
            return
        text = " ".join(self._current).strip()
        if text:
            self.blocks.append(text)
        self._current = []


def load_profile(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "repo-profile.json is missing."
    except json.JSONDecodeError as exc:
        return None, f"repo-profile.json is invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "repo-profile.json must be a JSON object."
    return data, None


def repo_url(profile: dict[str, Any] | None, fallback: str | None) -> str:
    if fallback:
        return fallback
    if profile:
        repo = profile.get("repo")
        if isinstance(repo, dict):
            value = repo.get("url")
            if isinstance(value, str):
                return value
    return ""


def validate_github_url(url: str) -> Check:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            return Check("URL", "pass", url)
    if not url:
        return Check("URL", "fail", "No repository URL found.")
    return Check("URL", "fail", f"Not a valid GitHub repository URL: {url}")


def validate_schema(profile: dict[str, Any] | None, error: str | None) -> list[Check]:
    if error:
        return [Check("schema", "fail", error)]

    assert profile is not None
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in profile]
    if missing:
        return [Check("schema", "fail", f"Missing top-level fields: {', '.join(missing)}.")]

    repo = profile.get("repo")
    if not isinstance(repo, dict):
        return [Check("schema", "fail", "`repo` must be an object.")]

    missing_repo = [field for field in ["url", "owner", "name"] if not repo.get(field)]
    if missing_repo:
        return [Check("schema", "fail", f"Missing repo fields: {', '.join(missing_repo)}.")]

    return [Check("schema", "pass", "Required profile fields are present.")]


def validate_source_grounding(profile: dict[str, Any] | None, error: str | None) -> list[Check]:
    if error or profile is None:
        return [Check("source grounding", "skipped", "Profile schema failed.")]

    sources = profile.get("sources")
    facts = profile.get("facts")
    if not isinstance(sources, list) or not isinstance(facts, list):
        return [Check("source grounding", "fail", "`sources` and `facts` must be arrays.")]

    source_ids = {source.get("id") for source in sources if isinstance(source, dict)}
    source_ids.discard(None)
    failures: list[str] = []
    warnings: list[str] = []

    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            failures.append(f"fact[{index}] is not an object")
            continue

        fact_id = fact.get("id", f"fact[{index}]")
        source_refs = fact.get("sourceIds")
        confidence = fact.get("confidence")
        if not source_refs:
            failures.append(f"{fact_id} has no sourceIds")
            continue
        if not isinstance(source_refs, list):
            failures.append(f"{fact_id} sourceIds is not an array")
            continue
        unknown = [source_id for source_id in source_refs if source_id not in source_ids]
        if unknown:
            failures.append(f"{fact_id} references unknown source IDs: {', '.join(unknown)}")
        if confidence == "low":
            warnings.append(f"{fact_id} is low confidence and must stay out of the website")

    if failures:
        return [Check("source grounding", "fail", "; ".join(failures))]
    if warnings:
        return [Check("source grounding", "warn", "; ".join(warnings))]
    return [Check("source grounding", "pass", "All facts reference known sources.")]


def validate_output_files(profile_path: Path, site_dir: Path) -> Check:
    expected = [
        profile_path,
        site_dir / "index.html",
        site_dir / "styles.css",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        return Check("output files", "fail", f"Missing files: {', '.join(missing)}.")
    return Check("output files", "pass", "Required generated files exist.")


def validate_gaps(profile: dict[str, Any] | None, error: str | None) -> Check:
    if error or profile is None:
        return Check("gaps", "skipped", "Profile schema failed.")

    gaps = profile.get("gaps")
    if not isinstance(gaps, list):
        return Check("gaps", "fail", "`repo-profile.json.gaps` must be an array.")

    unknown = []
    for index, gap in enumerate(gaps):
        if not isinstance(gap, dict):
            unknown.append(f"gap[{index}] is not an object")
            continue
        kind = gap.get("kind")
        if kind not in GAP_KINDS:
            unknown.append(str(kind or f"gap[{index}]"))

    if unknown:
        return Check("gaps", "warn", f"Unknown gap kinds should be reviewed: {', '.join(unknown)}.")
    return Check("gaps", "pass", "`repo-profile.json.gaps` uses known gap kinds.")


def validate_html(profile: dict[str, Any] | None, profile_error: str | None, site_dir: Path, repo_url_value: str) -> list[Check]:
    index_path = site_dir / "index.html"
    if not index_path.exists():
        return [Check("HTML render", "fail", "site/index.html is missing.")]

    html = index_path.read_text(encoding="utf-8", errors="replace")
    checks: list[Check] = []

    repo_name = ""
    if profile and isinstance(profile.get("repo"), dict):
        repo_name = str(profile["repo"].get("name", ""))

    missing_claims = []
    if repo_name and repo_name not in html:
        missing_claims.append("project name")
    if repo_url_value and repo_url_value not in html:
        missing_claims.append("GitHub URL")
    if missing_claims:
        checks.append(Check("HTML content", "fail", f"Missing {', '.join(missing_claims)} in site/index.html."))
    elif profile_error:
        checks.append(Check("HTML content", "skipped", "Profile schema failed."))
    else:
        checks.append(Check("HTML content", "pass", "Project name and GitHub URL are present."))

    banned_matches = []
    for pattern in BANNED_CLAIM_PATTERNS:
        if re.search(pattern, html, flags=re.IGNORECASE):
            banned_matches.append(pattern)
    if banned_matches:
        checks.append(Check("claim safety", "warn", f"Review potentially unsourced claims: {', '.join(banned_matches)}."))
    else:
        checks.append(Check("claim safety", "pass", "No banned metric or testimonial patterns found."))

    checks.append(validate_html_source_grounding(profile, profile_error, html, repo_url_value))
    return checks


def validate_html_source_grounding(
    profile: dict[str, Any] | None, profile_error: str | None, html: str, repo_url_value: str
) -> Check:
    if profile_error or profile is None:
        return Check("HTML source grounding", "skipped", "Profile schema failed.")

    support_texts = sourced_support_texts(profile, repo_url_value)
    if not support_texts:
        return Check("HTML source grounding", "fail", "No sourced profile text is available to ground page claims.")

    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()

    unsupported = []
    for block in parser.blocks:
        if should_skip_claim_block(block):
            continue
        normalized = normalize_text(block)
        if not any(text_supports_claim(support, normalized) for support in support_texts):
            unsupported.append(block)

    if unsupported:
        examples = "; ".join(unsupported[:3])
        return Check("HTML source grounding", "fail", f"Unsupported visible page claims: {examples}")
    return Check("HTML source grounding", "pass", "Visible page claims are backed by profile facts or sourced fields.")


def sourced_support_texts(profile: dict[str, Any], repo_url_value: str) -> list[str]:
    values: list[str] = []

    repo = profile.get("repo")
    if isinstance(repo, dict):
        values.extend(string_values(repo, ["url", "owner", "name", "description", "primaryLanguage", "license"]))
    if repo_url_value:
        values.append(repo_url_value)

    facts = profile.get("facts")
    if isinstance(facts, list):
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            value = fact.get("value")
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value if item)

    normalized = [normalize_text(value) for value in values if normalize_text(value)]
    return sorted(set(normalized))


def string_values(data: dict[str, Any], fields: list[str]) -> list[str]:
    return [str(data[field]) for field in fields if data.get(field)]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9:/._# +@-]+", " ", value.lower())).strip()


def should_skip_claim_block(block: str) -> bool:
    normalized = normalize_text(block)
    if not normalized:
        return True
    words = normalized.split()
    if len(words) <= 3:
        return True
    if normalized.startswith(("http://", "https://")):
        return True
    if re.fullmatch(r"[\w./:@# +-]+", normalized) and any(token in normalized for token in ["npm ", "python ", "pip ", "cargo ", "go "]):
        return False
    section_labels = {
        "features",
        "quickstart",
        "examples",
        "use cases",
        "license",
        "contributing",
        "get started",
        "view on github",
    }
    return normalized in section_labels


def text_supports_claim(support: str, claim: str) -> bool:
    if not support or not claim:
        return False
    if claim in support or support in claim:
        return True
    support_words = set(support.split())
    claim_words = set(claim.split())
    if len(claim_words) <= 3:
        return True
    overlap = claim_words & support_words
    return len(overlap) / len(claim_words) >= 0.8


def validate_links(site_dir: Path) -> Check:
    index_path = site_dir / "index.html"
    if not index_path.exists():
        return Check("links", "skipped", "site/index.html is missing.")

    parser = LinkParser()
    parser.feed(index_path.read_text(encoding="utf-8", errors="replace"))
    broken: list[str] = []
    for link in parser.links:
        if link.startswith(("#", "mailto:", "tel:", "http://", "https://")):
            continue
        parsed = urlparse(link)
        if parsed.scheme:
            continue
        clean_path = parsed.path
        if not clean_path:
            continue
        target = (site_dir / clean_path).resolve()
        if not target.exists():
            broken.append(link)

    if broken:
        return Check("links", "fail", f"Missing local link targets: {', '.join(sorted(set(broken)))}.")
    return Check("links", "pass", "Local href/src targets resolve.")


def status_counts(checks: list[Check]) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "skipped": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return counts


def normalize_gaps(profile: dict[str, Any] | None) -> list[dict[str, str]]:
    if not profile:
        return []
    gaps = profile.get("gaps")
    if not isinstance(gaps, list):
        return []

    normalized: list[dict[str, str]] = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        normalized.append(
            {
                "kind": str(gap.get("kind", "unknown-gap")),
                "severity": str(gap.get("severity", "medium")),
                "message": str(gap.get("message", "Missing detail.")),
            }
        )
    return normalized


def unsourced_positioning_suggestions(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    suggestions: list[str] = []
    gaps = profile.get("gaps")
    if isinstance(gaps, list):
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            if gap.get("kind") != "unclear-positioning":
                continue
            for field in ["suggestion", "value", "idea"]:
                value = gap.get(field)
                if value:
                    suggestions.append(str(value))
            values = gap.get("suggestions")
            if isinstance(values, list):
                suggestions.extend(str(value) for value in values if value)

    facts = profile.get("facts")
    if isinstance(facts, list):
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            kind = str(fact.get("kind", ""))
            confidence = fact.get("confidence")
            source_ids = fact.get("sourceIds")
            if kind == "positioning" and (confidence == "low" or not source_ids):
                value = fact.get("value")
                if value:
                    suggestions.append(str(value))

    product = profile.get("product")
    if isinstance(product, dict):
        for field in ["audiences", "problems", "useCases"]:
            value = product.get(field)
            if value == []:
                suggestions.append(f"Add clearer {field} to the README so the website can explain positioning.")

    return sorted(set(suggestions))


def gap_report(profile: dict[str, Any] | None, profile_error: str | None, url: str) -> str:
    gaps = normalize_gaps(profile)
    suggestions = unsourced_positioning_suggestions(profile)

    lines = [
        "# README Gap Report",
        "",
        f"- Repository: {url or 'unknown'}",
        f"- Source: `repo-profile.json.gaps`",
        "",
    ]

    if profile_error:
        lines.extend(["## Blocking Issue", "", f"- {profile_error}", ""])

    lines.extend(["## Missing or Weak Source Material", ""])
    if gaps:
        for gap in gaps:
            lines.append(f"- [{gap['severity']}] `{gap['kind']}`: {gap['message']}")
    else:
        lines.append("- No gaps recorded in `repo-profile.json.gaps`.")

    lines.extend(["", "## Positioning Suggestions Kept Out of Website", ""])
    if suggestions:
        for suggestion in suggestions:
            lines.append(f"- {suggestion}")
    else:
        lines.append("- No unsourced positioning suggestions recorded.")

    lines.extend(["", "## Next Maintainer Action", ""])
    if gaps:
        high_or_medium = [gap for gap in gaps if gap["severity"] in {"high", "medium"}]
        focus = high_or_medium[0] if high_or_medium else gaps[0]
        lines.append(f"- Start by adding README/docs material for `{focus['kind']}`.")
    else:
        lines.append("- Review the generated page for tone and accuracy.")

    return "\n".join(lines) + "\n"


def render_checks(html_render: str, desktop: str, mobile: str) -> list[Check]:
    return [
        Check("HTML render", html_render, render_detail(html_render)),
        Check("desktop review", desktop, review_detail(desktop, "desktop")),
        Check("mobile review", mobile, review_detail(mobile, "mobile")),
    ]


def validation_report(checks: list[Check], url: str, output_dir: Path) -> str:
    counts = status_counts(checks)
    lines = [
        "# Validation Report",
        "",
        f"- Repository: {url or 'unknown'}",
        f"- Output directory: `{output_dir}`",
        f"- Summary: {counts['fail']} fail, {counts['warn']} warn, {counts['pass']} pass, {counts['skipped']} skipped",
        "",
        "## Checks",
        "",
    ]
    render_review_names = {"HTML render", "desktop review", "mobile review"}
    for check in checks:
        if check.name in render_review_names:
            continue
        lines.append(f"- [{check.status}] {check.name}: {check.detail}")

    lines.extend(
        [
            "",
            "## Render Review",
            "",
        ]
    )
    for check in checks:
        if check.name not in render_review_names:
            continue
        lines.append(f"- [{check.status}] {check.name}: {check.detail}")
    return "\n".join(lines) + "\n"


def render_detail(status: str) -> str:
    if status == "pass":
        return "Rendered without blocking errors."
    if status == "fail":
        return "Render check failed."
    if status == "warn":
        return "Rendered with issues requiring review."
    return "Skipped because browser/render tooling was not provided."


def review_detail(status: str, viewport: str) -> str:
    if status == "pass":
        return f"{viewport} layout reviewed."
    if status == "fail":
        return f"{viewport} layout failed review."
    if status == "warn":
        return f"{viewport} layout has issues requiring review."
    return f"Skipped because {viewport} screenshot or browser tooling was not provided."


def status_arg(value: str) -> str:
    valid = {"pass", "warn", "fail", "skipped"}
    if value not in valid:
        raise argparse.ArgumentTypeError(f"expected one of: {', '.join(sorted(valid))}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RepoStage README gap and validation reports.")
    parser.add_argument("--profile", default="repo-profile.json", help="Path to repo-profile.json.")
    parser.add_argument("--site", default="site", help="Path to generated site directory.")
    parser.add_argument("--out", default=".", help="Directory for README-gap-report.md and validation-report.md.")
    parser.add_argument("--repo-url", default=None, help="Repository URL override.")
    parser.add_argument("--html-render", type=status_arg, default="skipped", help="Browser render result.")
    parser.add_argument("--desktop-review", type=status_arg, default="skipped", help="Desktop viewport review result.")
    parser.add_argument("--mobile-review", type=status_arg, default="skipped", help="Mobile viewport review result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile)
    site_dir = Path(args.site)
    out_dir = Path(args.out)

    profile, profile_error = load_profile(profile_path)
    url = repo_url(profile, args.repo_url)

    checks = [
        validate_github_url(url),
        validate_output_files(profile_path, site_dir),
        *validate_schema(profile, profile_error),
        validate_gaps(profile, profile_error),
        *validate_source_grounding(profile, profile_error),
        *validate_html(profile, profile_error, site_dir, url),
        validate_links(site_dir),
        *render_checks(args.html_render, args.desktop_review, args.mobile_review),
        Check("README gap report", "pass", "Generated from `repo-profile.json.gaps`."),
        Check("validation report", "pass", "Generated with pass/warn/fail/skipped status values."),
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README-gap-report.md").write_text(gap_report(profile, profile_error, url), encoding="utf-8")
    (out_dir / "validation-report.md").write_text(
        validation_report(checks, url, out_dir),
        encoding="utf-8",
    )

    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
