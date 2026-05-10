from __future__ import annotations

import argparse
import base64
import json
import os
import re
import stat
import subprocess
import tempfile
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_ROOT = "https://api.github.com"
RAW_ROOT = "https://raw.githubusercontent.com"
USER_AGENT = "RepoStage-ingest/0.1"

README_NAMES = {"readme", "readme.md", "readme.rst", "readme.txt", "readme.markdown"}
LICENSE_NAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}
PACKAGE_FILES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
    "Gemfile",
}
DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
ASSET_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".avif",
}
MAX_TEXT_BYTES = 256_000
MAX_DOC_FILES = 20
MAX_EXAMPLE_FILES = 20
MAX_ASSETS = 40


class IngestError(Exception):
    """Readable ingestion failure for CLI users."""


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"


def parse_github_url(value: str) -> GitHubRepo:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise IngestError("Invalid GitHub URL. Expected https://github.com/owner/repo")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise IngestError("Invalid GitHub URL. Expected https://github.com/owner/repo")

    owner, repo = parts[0], parts[1]
    repo = repo[:-4] if repo.endswith(".git") else repo
    safe = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not safe.match(owner) or not safe.match(repo):
        raise IngestError("Invalid GitHub URL. Owner and repo may contain only letters, numbers, dots, underscores, and hyphens.")

    return GitHubRepo(owner=owner, name=repo)


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.rate_limit: dict[str, Any] = {
            "usedToken": bool(token),
            "limit": None,
            "remaining": None,
            "resetEpoch": None,
            "degraded": False,
            "notes": [],
        }

    def request_json(self, path_or_url: str) -> Any:
        url = path_or_url if path_or_url.startswith("http") else f"{API_ROOT}{path_or_url}"
        req = urllib.request.Request(url, headers=self._headers(accept="application/vnd.github+json"))
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                self._capture_rate_limit(response.headers)
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._capture_rate_limit(exc.headers)
            message = self._error_message(exc)
            if exc.code == 403 and self.rate_limit.get("remaining") == 0:
                self.rate_limit["degraded"] = True
                self.rate_limit["notes"].append("GitHub API rate limit reached; retry later or set GITHUB_TOKEN.")
            raise IngestError(message) from exc
        except urllib.error.URLError as exc:
            raise IngestError(f"Network error while contacting GitHub: {exc.reason}") from exc

    def request_text(self, url: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
        req = urllib.request.Request(url, headers=self._headers(accept="text/plain"))
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                self._capture_rate_limit(response.headers)
                data = response.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            self._capture_rate_limit(exc.headers)
            raise IngestError(self._error_message(exc)) from exc
        except urllib.error.URLError as exc:
            raise IngestError(f"Network error while reading {url}: {exc.reason}") from exc

        if len(data) > max_bytes:
            raise IngestError(f"File is larger than the {max_bytes} byte ingestion limit: {url}")
        return data.decode("utf-8", errors="replace")

    def _headers(self, accept: str) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _capture_rate_limit(self, headers: Any) -> None:
        for key, target in (
            ("X-RateLimit-Limit", "limit"),
            ("X-RateLimit-Remaining", "remaining"),
            ("X-RateLimit-Reset", "resetEpoch"),
        ):
            value = headers.get(key) if headers else None
            if value is not None:
                try:
                    self.rate_limit[target] = int(value)
                except ValueError:
                    self.rate_limit[target] = value

    def _error_message(self, exc: urllib.error.HTTPError) -> str:
        if exc.code == 404:
            return "Repository is private, unavailable, or does not exist."
        if exc.code == 403:
            return "GitHub API request was forbidden or rate limited. Set GITHUB_TOKEN if the public API limit is exhausted."
        return f"GitHub API request failed with HTTP {exc.code}: {exc.reason}"


def ingest_repo(url: str, token: str | None = None) -> dict[str, Any]:
    repo_ref = parse_github_url(url)
    client = GitHubClient(token=token)
    try:
        return _ingest_repo_with_api(repo_ref, client)
    except IngestError as exc:
        if token:
            raise
        return _ingest_repo_with_git_fallback(repo_ref, str(exc))


def _ingest_repo_with_api(repo_ref: GitHubRepo, client: GitHubClient) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[str] = []

    repo_meta = client.request_json(f"/repos/{repo_ref.owner}/{repo_ref.name}")
    if repo_meta.get("private"):
        raise IngestError("Repository is private and cannot be ingested as a public repo.")

    default_branch = repo_meta.get("default_branch") or "main"
    tree = _fetch_tree(client, repo_ref, default_branch)
    paths = [item["path"] for item in tree if item.get("type") == "blob" and item.get("path")]

    readme = _fetch_readme(client, repo_ref, default_branch, errors)
    license_source = _fetch_license(client, repo_ref, default_branch, paths, errors)
    package_metadata = _fetch_package_metadata(client, repo_ref, default_branch, paths, errors)
    docs = _fetch_text_group(client, repo_ref, default_branch, paths, _is_doc_path, MAX_DOC_FILES, "docs", errors)
    examples = _fetch_text_group(client, repo_ref, default_branch, paths, _is_example_path, MAX_EXAMPLE_FILES, "examples", errors)
    assets = _asset_entries(repo_ref, default_branch, paths)

    gaps = _derive_gaps(readme, license_source, package_metadata, docs, examples, assets, repo_meta)
    if readme is None:
        warnings.append("README was not found; profile generation will be sparse.")
    if not package_metadata:
        warnings.append("No recognized package metadata file was found.")

    sources = []
    if readme:
        sources.append(_source_summary("src-readme", "readme", readme))
    if license_source:
        sources.append(_source_summary("src-license", "license", license_source))
    sources.extend(_source_summary(f"src-package-{idx + 1}", "package", item) for idx, item in enumerate(package_metadata))
    sources.extend(_source_summary(f"src-doc-{idx + 1}", "docs", item) for idx, item in enumerate(docs))
    sources.extend(_source_summary(f"src-example-{idx + 1}", "example", item) for idx, item in enumerate(examples))

    return {
        "schemaVersion": "repo-stage-ingestion.v0",
        "ingestedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": {
            "url": repo_ref.html_url,
            "owner": repo_ref.owner,
            "name": repo_ref.name,
            "description": repo_meta.get("description") or "",
            "defaultBranch": default_branch,
            "primaryLanguage": repo_meta.get("language") or "",
            "license": _license_name(repo_meta, license_source),
            "topics": repo_meta.get("topics") or [],
            "homepage": repo_meta.get("homepage") or "",
            "visibility": repo_meta.get("visibility") or "public",
            "metadataUrl": repo_meta.get("html_url") or repo_ref.html_url,
        },
        "rateLimit": client.rate_limit,
        "sources": sources,
        "readme": readme,
        "license": license_source,
        "packageMetadata": package_metadata,
        "docs": docs,
        "examples": examples,
        "assets": assets[:MAX_ASSETS],
        "gaps": gaps,
        "warnings": warnings,
        "errors": errors,
    }


def _ingest_repo_with_git_fallback(repo_ref: GitHubRepo, api_error: str) -> dict[str, Any]:
    errors: list[dict[str, str]] = [{"source": "github-api", "message": api_error}]
    warnings = ["GitHub API metadata was unavailable; used shallow git clone fallback with reduced metadata."]
    with tempfile.TemporaryDirectory(prefix="repo-stage-") as tmp:
        checkout = Path(tmp) / repo_ref.name
        clone = subprocess.run(
            ["git", "clone", "--depth", "1", repo_ref.html_url, str(checkout)],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if clone.returncode != 0:
            detail = clone.stderr.strip() or clone.stdout.strip()
            raise IngestError(f"Repository is private, unavailable, or could not be cloned. {detail}".strip())

        branch = subprocess.run(
            ["git", "-C", str(checkout), "branch", "--show-current"],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        default_branch = branch.stdout.strip() or "HEAD"
        paths = _local_paths(checkout)

        readme = _local_first_text(repo_ref, default_branch, checkout, paths, lambda path: Path(path).name.lower() in README_NAMES)
        license_source = _local_first_text(repo_ref, default_branch, checkout, paths, lambda path: path.lower() in LICENSE_NAMES)
        package_metadata = _local_package_metadata(repo_ref, default_branch, checkout, paths)
        docs = _local_text_group(repo_ref, default_branch, checkout, paths, _is_doc_path, MAX_DOC_FILES)
        examples = _local_text_group(repo_ref, default_branch, checkout, paths, _is_example_path, MAX_EXAMPLE_FILES)
        assets = _asset_entries(repo_ref, default_branch, paths)
        gaps = _derive_gaps(readme, license_source, package_metadata, docs, examples, assets, {})

        if not readme:
            warnings.append("README was not found; profile generation will be sparse.")
        if not package_metadata:
            warnings.append("No recognized package metadata file was found.")

        sources = []
        if readme:
            sources.append(_source_summary("src-readme", "readme", readme))
        if license_source:
            sources.append(_source_summary("src-license", "license", license_source))
        sources.extend(_source_summary(f"src-package-{idx + 1}", "package", item) for idx, item in enumerate(package_metadata))
        sources.extend(_source_summary(f"src-doc-{idx + 1}", "docs", item) for idx, item in enumerate(docs))
        sources.extend(_source_summary(f"src-example-{idx + 1}", "example", item) for idx, item in enumerate(examples))

        return {
            "schemaVersion": "repo-stage-ingestion.v0",
            "ingestedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repo": {
                "url": repo_ref.html_url,
                "owner": repo_ref.owner,
                "name": repo_ref.name,
                "description": "",
                "defaultBranch": default_branch,
                "primaryLanguage": "",
                "license": _license_name({}, license_source),
                "topics": [],
                "homepage": "",
                "visibility": "public",
                "metadataUrl": repo_ref.html_url,
            },
            "rateLimit": {
                "usedToken": False,
                "limit": None,
                "remaining": None,
                "resetEpoch": None,
                "degraded": True,
                "notes": ["GitHub API unavailable without token; report was built from shallow git clone fallback."],
            },
            "sources": sources,
            "readme": readme,
            "license": license_source,
            "packageMetadata": package_metadata,
            "docs": docs,
            "examples": examples,
            "assets": assets[:MAX_ASSETS],
            "gaps": gaps,
            "warnings": warnings,
            "errors": errors,
        }


def _fetch_tree(client: GitHubClient, repo: GitHubRepo, branch: str) -> list[dict[str, Any]]:
    data = client.request_json(f"/repos/{repo.owner}/{repo.name}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    if data.get("truncated"):
        client.rate_limit["degraded"] = True
        client.rate_limit["notes"].append("Repository tree was truncated by GitHub; some files may be missing from ingestion.")
    return data.get("tree") or []


def _local_paths(root: Path) -> list[str]:
    paths = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        try:
            mode = path.lstat().st_mode
        except OSError:
            continue
        if stat.S_ISREG(mode):
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _local_first_text(repo: GitHubRepo, branch: str, root: Path, paths: list[str], predicate: Any) -> dict[str, Any] | None:
    for path in paths:
        if predicate(path):
            return _local_text_source(repo, branch, root, path)
    return None


def _local_package_metadata(repo: GitHubRepo, branch: str, root: Path, paths: list[str]) -> list[dict[str, Any]]:
    found = []
    for path in paths:
        if Path(path).name in PACKAGE_FILES:
            source = _local_text_source(repo, branch, root, path)
            if source:
                source["parsed"] = _parse_package_file(path, source["content"])
                found.append(source)
    return found


def _local_text_group(repo: GitHubRepo, branch: str, root: Path, paths: list[str], predicate: Any, limit: int) -> list[dict[str, Any]]:
    found = []
    for path in paths:
        if len(found) >= limit:
            break
        if predicate(path):
            source = _local_text_source(repo, branch, root, path)
            if source:
                found.append(source)
    return found


def _local_text_source(repo: GitHubRepo, branch: str, root: Path, path: str) -> dict[str, Any] | None:
    file_path = root / path
    try:
        root_resolved = root.resolve(strict=True)
        file_resolved = file_path.resolve(strict=True)
        if os.path.commonpath([root_resolved, file_resolved]) != str(root_resolved):
            return None
        mode = file_path.lstat().st_mode
        if not stat.S_ISREG(mode) or file_path.stat().st_size > MAX_TEXT_BYTES:
            return None
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return _text_source(path, _html_url(repo, branch, path), content)


def _fetch_readme(
    client: GitHubClient, repo: GitHubRepo, branch: str, errors: list[dict[str, str]]
) -> dict[str, Any] | None:
    try:
        data = client.request_json(f"/repos/{repo.owner}/{repo.name}/readme")
        content = _decode_github_content(data)
        return _text_source(data.get("path") or "README.md", data.get("html_url") or _html_url(repo, branch, "README.md"), content)
    except IngestError as exc:
        errors.append({"source": "readme", "message": str(exc)})
        return None


def _decode_github_content(data: dict[str, Any]) -> str:
    encoding = data.get("encoding") or "base64"
    if encoding != "base64":
        raise IngestError(f"Unsupported GitHub contents encoding for README: {encoding}")
    try:
        raw = base64.b64decode(data.get("content", ""), validate=False)
    except Exception as exc:  # noqa: BLE001 - decode errors should become readable ingestion errors.
        raise IngestError(f"Could not decode GitHub README content: {exc}") from exc
    return raw.decode("utf-8", errors="replace")


def _fetch_license(
    client: GitHubClient,
    repo: GitHubRepo,
    branch: str,
    paths: list[str],
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    for path in paths:
        if path.lower() in LICENSE_NAMES:
            return _fetch_text_source(client, repo, branch, path, errors, "license")
    return None


def _fetch_package_metadata(
    client: GitHubClient,
    repo: GitHubRepo,
    branch: str,
    paths: list[str],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    found = []
    for path in paths:
        if Path(path).name in PACKAGE_FILES:
            source = _fetch_text_source(client, repo, branch, path, errors, "package")
            if source:
                source["parsed"] = _parse_package_file(path, source["content"])
                found.append(source)
    return found


def _fetch_text_group(
    client: GitHubClient,
    repo: GitHubRepo,
    branch: str,
    paths: list[str],
    predicate: Any,
    limit: int,
    source_name: str,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    found = []
    for path in sorted(paths):
        if len(found) >= limit:
            break
        if predicate(path):
            source = _fetch_text_source(client, repo, branch, path, errors, source_name)
            if source:
                found.append(source)
    return found


def _fetch_text_source(
    client: GitHubClient,
    repo: GitHubRepo,
    branch: str,
    path: str,
    errors: list[dict[str, str]],
    source_name: str,
) -> dict[str, Any] | None:
    try:
        content = client.request_text(_raw_url(repo, branch, path))
        return _text_source(path, _html_url(repo, branch, path), content)
    except IngestError as exc:
        errors.append({"source": source_name, "path": path, "message": str(exc)})
        return None


def _parse_package_file(path: str, content: str) -> dict[str, Any]:
    name = Path(path).name
    try:
        if name == "package.json":
            data = json.loads(content)
            return {
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "scripts": data.get("scripts", {}),
                "dependencies": sorted((data.get("dependencies") or {}).keys())[:30],
                "devDependencies": sorted((data.get("devDependencies") or {}).keys())[:30],
            }
        if name == "pyproject.toml":
            data = tomllib.loads(content)
            project = data.get("project") or {}
            poetry = (data.get("tool") or {}).get("poetry") or {}
            return {
                "name": project.get("name") or poetry.get("name", ""),
                "version": project.get("version") or poetry.get("version", ""),
                "description": project.get("description") or poetry.get("description", ""),
                "dependencies": project.get("dependencies") or poetry.get("dependencies", {}),
            }
        if name == "Cargo.toml":
            data = tomllib.loads(content)
            package = data.get("package") or {}
            return {
                "name": package.get("name", ""),
                "version": package.get("version", ""),
                "description": package.get("description", ""),
                "dependencies": sorted((data.get("dependencies") or {}).keys())[:30],
            }
        if name == "go.mod":
            first = content.splitlines()[0] if content.splitlines() else ""
            return {"module": first.removeprefix("module ").strip() if first.startswith("module ") else ""}
    except Exception as exc:  # noqa: BLE001 - parser errors should not fail ingestion.
        return {"parseError": str(exc)}
    return {}


def _derive_gaps(
    readme: dict[str, Any] | None,
    license_source: dict[str, Any] | None,
    package_metadata: list[dict[str, Any]],
    docs: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    repo_meta: dict[str, Any],
) -> list[dict[str, str]]:
    text = "\n".join(
        item.get("content", "")
        for item in [readme, *docs, *examples]
        if item
    ).lower()
    gaps: list[dict[str, str]] = []
    if not readme:
        gaps.append({"kind": "missing-readme", "message": "No README was available from the repository.", "severity": "high"})
    if not any(word in text for word in ("install", "installation", "npm install", "pip install", "cargo install", "go install")):
        gaps.append({"kind": "missing-install", "message": "No obvious installation command was found.", "severity": "medium"})
    if not any(word in text for word in ("quickstart", "quick start", "getting started", "usage", "example")):
        gaps.append({"kind": "missing-quickstart", "message": "No clear quickstart or usage section was found.", "severity": "medium"})
    if not examples and "example" not in text:
        gaps.append({"kind": "missing-example", "message": "No examples directory or obvious example text was found.", "severity": "medium"})
    if not assets:
        gaps.append({"kind": "missing-screenshot", "message": "No reusable image assets or screenshots were found.", "severity": "low"})
    if not license_source and not repo_meta.get("license"):
        gaps.append({"kind": "missing-license", "message": "No license file or GitHub license metadata was found.", "severity": "high"})
    if not package_metadata:
        gaps.append({"kind": "sparse-docs", "message": "No recognized package metadata was found.", "severity": "low"})
    return gaps


def _source_summary(source_id: str, source_type: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": source_id,
        "type": source_type,
        "path": item["path"],
        "url": item["url"],
        "bytes": item["bytes"],
        "notes": item.get("notes", ""),
    }


def _text_source(path: str, url: str, content: str) -> dict[str, Any]:
    return {
        "path": path,
        "url": url,
        "bytes": len(content.encode("utf-8")),
        "content": content,
    }


def _asset_entries(repo: GitHubRepo, branch: str, paths: list[str]) -> list[dict[str, Any]]:
    assets = []
    for path in sorted(paths):
        suffix = Path(path).suffix.lower()
        if suffix in ASSET_EXTENSIONS:
            kind = "logo" if "logo" in path.lower() else "screenshot" if "screenshot" in path.lower() else "image"
            assets.append({"path": path, "kind": kind, "url": _html_url(repo, branch, path), "rawUrl": _raw_url(repo, branch, path)})
    return assets


def _is_doc_path(path: str) -> bool:
    lower = path.lower()
    return lower.startswith("docs/") and Path(lower).suffix in DOC_EXTENSIONS


def _is_example_path(path: str) -> bool:
    lower = path.lower()
    return lower.startswith(("examples/", "example/", "samples/", "sample/")) and Path(lower).suffix in DOC_EXTENSIONS | {".js", ".ts", ".py", ".go", ".rs", ".java", ".rb"}


def _license_name(repo_meta: dict[str, Any], license_source: dict[str, Any] | None) -> str:
    license_meta = repo_meta.get("license") or {}
    if license_meta.get("spdx_id") and license_meta.get("spdx_id") != "NOASSERTION":
        return license_meta["spdx_id"]
    return Path(license_source["path"]).name if license_source else ""


def _raw_url(repo: GitHubRepo, branch: str, path: str) -> str:
    return f"{RAW_ROOT}/{repo.owner}/{repo.name}/{urllib.parse.quote(branch, safe='')}/{urllib.parse.quote(path)}"


def _html_url(repo: GitHubRepo, branch: str, path: str) -> str:
    return f"{repo.html_url}/blob/{urllib.parse.quote(branch, safe='')}/{urllib.parse.quote(path)}"


def write_report(report: dict[str, Any], output: Path | None) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a public GitHub repository into a structured RepoStage JSON report.")
    parser.add_argument("url", help="Public GitHub repository URL, e.g. https://github.com/owner/repo")
    parser.add_argument("--out", type=Path, help="Write report JSON to this path. Defaults to stdout.")
    parser.add_argument("--token", help="GitHub API token. Defaults to GITHUB_TOKEN when present.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = ingest_repo(args.url, token=args.token or os.environ.get("GITHUB_TOKEN"))
        write_report(report, args.out)
    except IngestError as exc:
        print(f"repo-stage ingest failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
