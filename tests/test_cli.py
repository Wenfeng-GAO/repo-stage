from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from repo_stage import cli
from repo_stage.cli import build_profile_from_ingestion, validate_output, write_gap_report, write_json, write_site
from repo_stage.ingest import IngestError, _local_paths, _local_text_source, parse_github_url


def sample_ingestion() -> dict[str, object]:
    readme = {
        "path": "README.md",
        "url": "https://github.com/owner/repo/blob/main/README.md",
        "bytes": 180,
        "content": """# Repo

A tool for developers.

## Features

- 10-100x faster than alternatives.

## Usage

```bash
pip install repo
```
""",
    }
    return {
        "schemaVersion": "repo-stage-ingestion.v0",
        "repo": {
            "url": "https://github.com/owner/repo",
            "owner": "owner",
            "name": "repo",
            "description": "A tool.",
            "defaultBranch": "main",
            "primaryLanguage": "Python",
            "license": "MIT",
            "topics": [],
            "metadataUrl": "https://github.com/owner/repo",
        },
        "sources": [{"id": "src-readme", "type": "readme", "path": "README.md", "url": readme["url"], "notes": ""}],
        "readme": readme,
        "license": None,
        "packageMetadata": [],
        "docs": [],
        "examples": [],
        "assets": [],
        "gaps": [],
        "warnings": [],
        "errors": [],
    }


class RepoStageCliTests(unittest.TestCase):
    def test_generate_writes_required_outputs_from_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cli, "ingest_repo", return_value=sample_ingestion()):
                with redirect_stdout(StringIO()):
                    code = cli.main(["generate", "https://github.com/owner/repo", "--out", tmp])

            self.assertEqual(code, 0)
            for rel in ("site/index.html", "site/styles.css", "repo-profile.json", "README-gap-report.md", "validation-report.md"):
                self.assertTrue((Path(tmp) / rel).exists(), rel)

    def test_generate_failure_writes_contract_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cli, "ingest_repo", side_effect=IngestError("rate limited")):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    code = cli.main(["generate", "https://github.com/owner/repo", "--out", tmp])

            self.assertEqual(code, 1)
            profile = json.loads((Path(tmp) / "repo-profile.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["gaps"][0]["kind"], "generation-failed")
            self.assertTrue((Path(tmp) / "README-gap-report.md").exists())
            self.assertTrue((Path(tmp) / "validation-report.md").exists())

    def test_profile_builder_uses_ingestion_symlink_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            docs = root / "docs"
            outside = Path(tmp) / "outside.md"
            docs.mkdir(parents=True)
            (root / "README.md").write_text("# Safe\n\nA safe README for developers.\n", encoding="utf-8")
            (docs / "safe.md").write_text("safe docs", encoding="utf-8")
            outside.write_text("secret from outside root", encoding="utf-8")
            (docs / "leak.md").symlink_to(outside)

            paths = _local_paths(root)
            sources = [
                _local_text_source(parse_github_url("https://github.com/owner/repo"), "main", root, path)
                for path in paths
            ]
            sources = [source for source in sources if source]
            ingestion = {
                **sample_ingestion(),
                "sources": [{"id": f"src-{idx}", "type": "file", "path": source["path"], "url": source["url"], "notes": ""} for idx, source in enumerate(sources, 1)],
                "readme": next(source for source in sources if source["path"] == "README.md"),
                "docs": [source for source in sources if source["path"].startswith("docs/")],
            }
            profile = build_profile_from_ingestion(ingestion)

            self.assertNotIn("docs/leak.md", json.dumps(profile))
            self.assertNotIn("secret from outside root", json.dumps(profile))

    def test_validate_accepts_sourced_metric_claim(self) -> None:
        profile = build_profile_from_ingestion(sample_ingestion())
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_json(out_dir / "repo-profile.json", profile)
            write_site(out_dir / "site", profile)
            write_gap_report(out_dir / "README-gap-report.md", profile)
            result = validate_output(out_dir, profile)
        self.assertEqual(result["status"], "passed")


if __name__ == "__main__":
    unittest.main()
