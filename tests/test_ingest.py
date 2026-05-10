import base64
import tempfile
import unittest
from pathlib import Path

from repo_stage.ingest import (
    GitHubRepo,
    IngestError,
    _fetch_readme,
    _local_paths,
    _local_text_source,
    parse_github_url,
)


class ParseGitHubUrlTest(unittest.TestCase):
    def test_accepts_canonical_url(self) -> None:
        repo = parse_github_url("https://github.com/owner/name")

        self.assertEqual(repo.owner, "owner")
        self.assertEqual(repo.name, "name")
        self.assertEqual(repo.html_url, "https://github.com/owner/name")

    def test_strips_git_suffix(self) -> None:
        repo = parse_github_url("https://github.com/owner/name.git")

        self.assertEqual(repo.name, "name")

    def test_rejects_non_github_url(self) -> None:
        with self.assertRaises(IngestError):
            parse_github_url("https://example.com/owner/name")

    def test_rejects_missing_repo(self) -> None:
        with self.assertRaises(IngestError):
            parse_github_url("https://github.com/owner")

    def test_rejects_nested_repo_paths(self) -> None:
        with self.assertRaises(IngestError):
            parse_github_url("https://github.com/owner/name/issues")


class LocalFallbackSafetyTest(unittest.TestCase):
    def test_local_paths_skip_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            outside = Path(tmp) / "outside.txt"
            docs = root / "docs"
            docs.mkdir(parents=True)
            outside.write_text("secret", encoding="utf-8")
            (docs / "safe.md").write_text("safe", encoding="utf-8")
            (docs / "leak.md").symlink_to(outside)

            self.assertEqual(_local_paths(root), ["docs/safe.md"])

    def test_local_text_source_rejects_symlink_to_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            outside = Path(tmp) / "outside.txt"
            docs = root / "docs"
            docs.mkdir(parents=True)
            outside.write_text("secret", encoding="utf-8")
            (docs / "leak.md").symlink_to(outside)

            source = _local_text_source(GitHubRepo("owner", "repo"), "main", root, "docs/leak.md")

            self.assertIsNone(source)


class GitHubReadmeApiTest(unittest.TestCase):
    def test_fetch_readme_decodes_base64_as_utf8_text(self) -> None:
        class FakeClient:
            def request_json(self, path: str) -> dict[str, str]:
                self.path = path
                return {
                    "content": base64.b64encode("# Hello\n".encode("utf-8")).decode("ascii"),
                    "encoding": "base64",
                    "path": "README.md",
                    "html_url": "https://github.com/owner/repo/blob/main/README.md",
                }

        errors: list[dict[str, str]] = []
        source = _fetch_readme(FakeClient(), GitHubRepo("owner", "repo"), "main", errors)

        self.assertEqual(errors, [])
        self.assertIsNotNone(source)
        self.assertEqual(source["content"], "# Hello\n")


if __name__ == "__main__":
    unittest.main()
