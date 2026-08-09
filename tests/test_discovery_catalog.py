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
        self.assertEqual("repository", result["catalog"])
        self.assertEqual(1, result["catalog_version"])
        self.assertEqual("slide-slow-blues-a-60", result["candidates"][0]["source_id"])
        self.assertFalse(any(item["target_type"] == "song" for item in catalog["items"]))

    def test_local_catalog_search_ranks_matching_item(self) -> None:
        result = discovery.search_catalog(self.request, self.catalog)

        self.assertEqual("complete", result["status"])
        self.assertEqual(1, len(result["candidates"]))
        candidate = result["candidates"][0]
        self.assertEqual("slide-slow-blues-a-60", candidate["source_id"])
        self.assertGreater(candidate["score"], 0)
        self.assertEqual(["blues"], candidate["matched_constraints"]["genres"])
        self.assertEqual(
            "backing-tracks/slide-slow-blues/manifest.json",
            candidate["evidence"][0]["source"],
        )
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

    def test_stable_tie_break_uses_source_id(self) -> None:
        catalog = {
            "version": 1,
            "items": [
                {
                    "id": "z-track",
                    "target_type": "backing-track",
                    "title": "Z",
                    "genres": ["blues"],
                    "styles": [],
                    "techniques": ["slide"],
                    "gear_ids": [],
                    "roles": [],
                    "tunings": [],
                    "meters": [],
                },
                {
                    "id": "a-track",
                    "target_type": "backing-track",
                    "title": "A",
                    "genres": ["blues"],
                    "styles": [],
                    "techniques": ["slide"],
                    "gear_ids": [],
                    "roles": [],
                    "tunings": [],
                    "meters": [],
                },
            ],
        }
        request = {
            "target_type": "backing-track",
            "goal": "Find blues slide material",
            "constraints": {"genres": ["blues"], "techniques": ["slide"]},
        }

        result = discovery.search_catalog(request, catalog)

        self.assertEqual(["a-track", "z-track"], [c["source_id"] for c in result["candidates"]])


if __name__ == "__main__":
    unittest.main()
