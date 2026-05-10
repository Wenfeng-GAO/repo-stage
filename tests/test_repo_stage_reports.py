from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repo_stage_reports.py"


class RepoStageReportsTest(unittest.TestCase):
    def run_report(
        self,
        tmpdir: Path,
        *,
        profile: dict | None = None,
        html: str | None = None,
        args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if profile is not None:
            (tmpdir / "repo-profile.json").write_text(json.dumps(profile), encoding="utf-8")
        site = tmpdir / "site"
        site.mkdir(exist_ok=True)
        if html is not None:
            (site / "index.html").write_text(html, encoding="utf-8")
        (site / "styles.css").write_text("", encoding="utf-8")

        cmd = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--profile",
            str(tmpdir / "repo-profile.json"),
            "--site",
            str(site),
            "--out",
            str(tmpdir),
            *(args or []),
        ]
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def profile(self, **updates: object) -> dict:
        data = {
            "schemaVersion": "repo-profile.v0",
            "repo": {
                "url": "https://github.com/example/tool",
                "owner": "example",
                "name": "tool",
                "description": "A command line helper for repository reports",
                "defaultBranch": "main",
                "primaryLanguage": "Python",
                "license": "MIT",
                "topics": [],
            },
            "sources": [{"id": "src-readme", "type": "file", "path": "README.md", "url": "", "notes": ""}],
            "facts": [
                {
                    "id": "fact-one-liner",
                    "kind": "summary",
                    "value": "A command line helper for repository reports",
                    "sourceIds": ["src-readme"],
                    "confidence": "high",
                },
                {
                    "id": "fact-quickstart",
                    "kind": "quickstart",
                    "value": "python tool.py",
                    "sourceIds": ["src-readme"],
                    "confidence": "high",
                },
            ],
            "product": {
                "name": "tool",
                "oneLiner": "A command line helper for repository reports",
                "audiences": ["open-source maintainers"],
                "problems": ["repository reports"],
                "features": ["repository reports"],
                "useCases": ["repository reports"],
                "quickstart": ["python tool.py"],
                "examples": [],
                "contribution": {"hasContributionGuide": False, "notes": []},
            },
            "assets": [],
            "gaps": [{"kind": "missing-demo", "message": "No demo link found.", "severity": "medium"}],
        }
        data.update(updates)
        return data

    def test_generates_gap_and_validation_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            result = self.run_report(
                tmpdir,
                profile=self.profile(),
                html=(
                    '<!doctype html><html><body><h1>tool</h1>'
                    '<p>A command line helper for repository reports</p>'
                    '<a href="https://github.com/example/tool">GitHub</a></body></html>'
                ),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("`missing-demo`: No demo link found.", (tmpdir / "README-gap-report.md").read_text())
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[pass] HTML source grounding", validation)
            self.assertIn("0 fail", validation)
            self.assertIn("3 skipped", validation)

    def test_render_failure_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            result = self.run_report(
                tmpdir,
                profile=self.profile(),
                html=(
                    '<html><body><h1>tool</h1>'
                    '<p>A command line helper for repository reports</p>'
                    '<a href="https://github.com/example/tool">GitHub</a></body></html>'
                ),
                args=["--html-render", "fail"],
            )

            self.assertNotEqual(result.returncode, 0)
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[fail] HTML render", validation)
            self.assertIn("1 fail", validation)

    def test_unsupported_html_claim_fails_source_grounding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            result = self.run_report(
                tmpdir,
                profile=self.profile(),
                html=(
                    '<html><body><h1>tool</h1>'
                    '<p>Enterprise grade SOC2 ready platform with zero setup</p>'
                    '<a href="https://github.com/example/tool">GitHub</a></body></html>'
                ),
            )

            self.assertNotEqual(result.returncode, 0)
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[fail] HTML source grounding", validation)
            self.assertIn("Enterprise grade SOC2 ready platform with zero setup", validation)

    def test_short_repo_name_does_not_ground_substring_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            profile = self.profile(
                repo={
                    "url": "https://github.com/example/r",
                    "owner": "example",
                    "name": "r",
                    "description": "",
                    "defaultBranch": "main",
                    "primaryLanguage": "Python",
                    "license": "MIT",
                    "topics": [],
                }
            )

            result = self.run_report(
                tmpdir,
                profile=profile,
                html=(
                    '<html><body><h1>r</h1>'
                    '<p>Enterprise grade SOC2 ready platform with zero setup</p>'
                    '<a href="https://github.com/example/r">GitHub</a></body></html>'
                ),
            )

            self.assertNotEqual(result.returncode, 0)
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[fail] HTML source grounding", validation)
            self.assertIn("Enterprise grade SOC2 ready platform with zero setup", validation)

    def test_missing_files_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            site = tmpdir / "site"
            site.mkdir()
            (tmpdir / "repo-profile.json").write_text(json.dumps(self.profile()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--profile",
                    str(tmpdir / "repo-profile.json"),
                    "--site",
                    str(site),
                    "--out",
                    str(tmpdir),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[fail] output files", validation)
            self.assertIn("site/index.html", validation)

    def test_unknown_source_id_fails_grounding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            profile = self.profile()
            profile["facts"][0]["sourceIds"] = ["missing-source"]

            result = self.run_report(
                tmpdir,
                profile=profile,
                html='<html><body><h1>tool</h1><p>A command line helper for repository reports</p></body></html>',
            )

            self.assertNotEqual(result.returncode, 0)
            validation = (tmpdir / "validation-report.md").read_text()
            self.assertIn("[fail] source grounding", validation)
            self.assertIn("missing-source", validation)


if __name__ == "__main__":
    unittest.main()
