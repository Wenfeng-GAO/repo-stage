import json
import tempfile
import unittest
from pathlib import Path

from repo_stage.profile import build_repo_profile, generate_profile_file, validate_repo_profile


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "ingestion"


class ProfileGenerationTest(unittest.TestCase):
    def test_generates_valid_profile_from_m1_ingestion_report(self) -> None:
        profile = build_repo_profile(_fixture("complete-ingestion"))
        validation = validate_repo_profile(profile)

        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(profile["schemaVersion"], "repo-profile.v0")
        self.assertEqual(profile["repo"]["owner"], "example")
        self.assertEqual(profile["repo"]["name"], "toolkit")
        self.assertIn("src-package-1", {source["id"] for source in profile["sources"]})
        self.assertIn("src-example-1", {source["id"] for source in profile["sources"]})
        self.assertTrue(_has_fact(profile, "quickstart", "npm install @example/toolkit"))
        self.assertTrue(_has_fact(profile, "quickstart", "npx toolkit generate openapi.yaml"))
        self.assertTrue(_has_fact(profile, "example", "examples/basic.ts"))
        self.assertNotIn("missing-install", _gap_kinds(profile))
        self.assertNotIn("missing-example", _gap_kinds(profile))
        self.assertTrue(all(fact["sourceIds"] for fact in profile["facts"]))
        self.assertTrue(all(fact["confidence"] in {"high", "medium"} for fact in profile["facts"]))

    def test_missing_information_becomes_warnings_and_gaps(self) -> None:
        profile = build_repo_profile(_fixture("missing-info-ingestion"))
        validation = validate_repo_profile(profile)

        self.assertTrue(validation["valid"], validation["errors"])
        self.assertIn("missing-install", _gap_kinds(profile))
        self.assertIn("missing-license", _gap_kinds(profile))
        self.assertIn("missing-example", _gap_kinds(profile))
        self.assertIn("No install or quickstart command is available.", validation["warnings"])
        self.assertIn("No license is available.", validation["warnings"])
        self.assertIn("No examples are available.", validation["warnings"])

    def test_metadata_facts_use_metadata_source_not_unrelated_file(self) -> None:
        ingestion = _fixture("complete-ingestion")
        ingestion["sources"] = [source for source in ingestion["sources"] if source["id"] != "src-readme"]
        ingestion["readme"] = None

        profile = build_repo_profile(ingestion)
        positioning = [fact for fact in profile["facts"] if fact["kind"] == "positioning"]

        self.assertTrue(positioning)
        self.assertTrue(all(fact["sourceIds"] == ["src-repo-metadata"] for fact in positioning))

    def test_cli_generation_path_writes_valid_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "repo-profile.json"
            profile = generate_profile_file(FIXTURE_DIR / "complete-ingestion.json", out)

            self.assertTrue(out.exists())
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written, profile)
            self.assertTrue(validate_repo_profile(written)["valid"])


class ProfileValidationTest(unittest.TestCase):
    def test_validator_fails_unknown_source_reference(self) -> None:
        profile = build_repo_profile(_fixture("complete-ingestion"))
        profile["facts"][0]["sourceIds"] = ["src-missing"]
        validation = validate_repo_profile(profile)

        self.assertFalse(validation["valid"])
        self.assertTrue(any("unknown source ID: src-missing" in error for error in validation["errors"]))

    def test_validator_fails_missing_repo_fields(self) -> None:
        validation = validate_repo_profile(
            {
                "schemaVersion": "repo-profile.v0",
                "repo": {},
                "sources": [],
                "facts": [],
                "product": {},
                "gaps": [],
            }
        )

        self.assertFalse(validation["valid"])
        self.assertIn("repo.url is required.", validation["errors"])
        self.assertIn("repo.owner is required.", validation["errors"])
        self.assertIn("repo.name is required.", validation["errors"])

    def test_validator_fails_json_parse_errors(self) -> None:
        validation = validate_repo_profile("{not-json")

        self.assertFalse(validation["valid"])
        self.assertTrue(validation["errors"][0].startswith("JSON parse failed:"))

    def test_validator_fails_website_claims_without_facts(self) -> None:
        profile = build_repo_profile(_fixture("complete-ingestion"))
        profile["websiteClaims"] = [{"text": "Used by thousands of teams", "factIds": []}]
        validation = validate_repo_profile(profile)

        self.assertFalse(validation["valid"])
        self.assertIn("websiteClaims[0].factIds must include at least one fact ID.", validation["errors"])


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _has_fact(profile: dict, kind: str, text: str) -> bool:
    return any(fact["kind"] == kind and text in fact["value"] for fact in profile["facts"])


def _gap_kinds(profile: dict) -> set[str]:
    return {gap["kind"] for gap in profile["gaps"]}


if __name__ == "__main__":
    unittest.main()
