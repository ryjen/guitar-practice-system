from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "discovery_catalog.py"
SPEC = importlib.util.spec_from_file_location("discovery_catalog", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
discovery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = discovery
SPEC.loader.exec_module(discovery)


class DiscoveryCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = {
            "target_type": "backing-track",
            "goal": "Find a slow blues backing track for slide phrasing",
            "limit": 3,
            "required_constraints": ["genres", "techniques"],
            "constraints": {
                "genres": ["blues"],
                "styles": ["slow-blues"],
                "techniques": ["slide"],
                "tuning": "standard",
                "meter": "4/4",
                "tempo_bpm": {"min": 55, "max": 65},
                "difficulty": "intermediate",
                "roles": ["lead", "improvisation"],
            },
        }
        self.catalog = {
            "version": 1,
            "items": [
                {
                    "id": "slide-slow-blues-a-60",
                    "target_type": "backing-track",
                    "title": "Slow Blues in A for Slide",
                    "summary": "Sparse original backing track for slide phrasing.",
                    "genres": ["blues"],
                    "styles": ["slow-blues", "blues-rock"],
                    "techniques": ["slide", "phrasing"],
                    "tunings": ["standard"],
                    "meters": ["4/4"],
                    "tempo_bpm": 60,
                    "difficulty": "intermediate",
                    "roles": ["lead", "improvisation"],
                    "evidence": [
                        {
                            "state": "verified",
                            "source": "backing-tracks/slide-slow-blues/manifest.json",
                            "kind": "repository",
                        }
                    ],
                    "licensing": "original repository material",
                },
                {
                    "id": "country-clean-100",
                    "target_type": "backing-track",
                    "title": "Country Clean Practice",
                    "genres": ["country"],
                    "styles": ["country-rock"],
                    "techniques": ["hybrid-picking"],
                    "tunings": ["standard"],
                    "meters": ["4/4"],
                    "tempo_bpm": 100,
                    "difficulty": "intermediate",
                    "roles": ["rhythm"],
                    "evidence": [],
                },
            ],
        }

    def test_repository_catalog_and_example_request_are_valid(self) -> None:
        request = discovery.read_json(
            ROOT / "examples" / "discovery" / "slide-backing-track-request.json"
        )
        catalog = discovery.read_json(
            ROOT / "catalogs" / "discovery" / "repository.json"
        )

        result = discovery.search_catalog(request, catalog)

        self.assertEqual("complete", result["status"])
        self.assertEqual("slide-slow-blues-a-60", result["candidates"][0]["source_id"])
        self.assertFalse(any(item["target_type"] == "song" for item in catalog["items"]))

    def test_local_catalog_search_ranks_matching_verified_item(self) -> None:
        result = discovery.search_catalog(self.request, self.catalog)

        self.assertEqual("complete", result["status"])
        self.assertEqual(1, len(result["candidates"]))
        candidate = result["candidates"][0]
        self.assertEqual("slide-slow-blues-a-60", candidate["source_id"])
        self.assertEqual("high", candidate["confidence"])
        self.assertEqual(["blues"], candidate["matched_constraints"]["genres"])
        self.assertEqual([], result["warnings"])

    def test_local_catalog_search_degrades_when_catalog_is_unavailable(self) -> None:
        result = discovery.search_catalog(self.request, None)

        self.assertEqual("degraded", result["status"])
        self.assertEqual([], result["candidates"])
        self.assertIn("unavailable", result["warnings"][0])

    def test_empty_song_catalog_is_valid_and_degrades_without_inventing_candidates(self) -> None:
        request = {
            "target_type": "song",
            "goal": "Find an alt-rock song for texture practice",
            "constraints": {"genres": ["alt-rock"]},
        }
        result = discovery.search_catalog(request, self.catalog)

        self.assertEqual("degraded", result["status"])
        self.assertEqual([], result["candidates"])
        self.assertEqual(["no local catalog candidates matched"], result["warnings"])

    def test_provider_normalizer_drops_mutation_fields_and_caps_confidence(self) -> None:
        payload = {
            "candidates": [
                {
                    "id": "untrusted-1",
                    "target_type": "song",
                    "title": "Unverified suggestion",
                    "rationale": "It may fit.",
                    "confidence": "high",
                    "uncertainty": "Technique usage has not been verified.",
                    "evidence": [],
                    "approved": True,
                    "active": True,
                    "progress": "mastered",
                }
            ]
        }
        result = discovery.normalize_provider_output(
            self.request, payload, provider="test-provider"
        )

        candidate = result["candidates"][0]
        self.assertEqual("backing-track", candidate["target_type"])
        self.assertEqual("low", candidate["confidence"])
        self.assertEqual(
            ["Technique usage has not been verified."], candidate["uncertainty"]
        )
        self.assertNotIn("approved", candidate)
        self.assertNotIn("active", candidate)
        self.assertNotIn("progress", candidate)
        warning = " ".join(result["warnings"])
        self.assertIn("target_type normalized", warning)
        self.assertIn("active, approved, progress", warning)

    def test_provider_normalizer_preserves_verified_confidence_and_sources(self) -> None:
        payload = [
            {
                "source_id": "verified-1",
                "title": "Verified local candidate",
                "rationale": "Repository metadata confirms the match.",
                "confidence": "high",
                "evidence": [
                    {
                        "state": "verified",
                        "source": "docs/discovery/README.md",
                        "kind": "repository",
                    }
                ],
            }
        ]
        result = discovery.normalize_provider_output(
            self.request, payload, provider="local-fixture"
        )

        candidate = result["candidates"][0]
        self.assertEqual("high", candidate["confidence"])
        self.assertEqual("docs/discovery/README.md", candidate["evidence"][0]["source"])

    def test_request_rejects_noncanonical_top_level_genre(self) -> None:
        request = {
            "target_type": "song",
            "goal": "Find something",
            "constraints": {"genres": ["progressive polka"]},
        }
        with self.assertRaises(discovery.DiscoveryError):
            discovery.validate_request(request)

    def test_candidate_ids_are_deterministic_for_same_request(self) -> None:
        first = discovery.search_catalog(self.request, self.catalog)
        second = discovery.search_catalog(self.request, self.catalog)

        self.assertEqual(
            first["candidates"][0]["candidate_id"],
            second["candidates"][0]["candidate_id"],
        )


if __name__ == "__main__":
    unittest.main()
