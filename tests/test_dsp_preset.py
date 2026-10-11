from __future__ import annotations

import json
import unittest

from guitar_practice.domain import dsp_preset


FIXTURE = "{\"schema\":\"guitar-dsp.preset\",\"version\":1,\"preset\":\"jazz-blues\",\"tempo_bpm\":92,\"parameters\":{\"delay.feedback_milli\":320,\"delay.free_ms\":375,\"delay.mix_milli\":500,\"delay.subdivision\":\"dotted-eighth\"}}"
DOCUMENT = {
    "schema": "guitar-dsp.preset",
    "version": 1,
    "preset": "jazz-blues",
    "tempo_bpm": 92,
    "parameters": {
        "delay.feedback_milli": 320,
        "delay.free_ms": 375,
        "delay.mix_milli": 500,
        "delay.subdivision": "dotted-eighth",
    },
}


class DspPresetV1Tests(unittest.TestCase):
    def test_canonical_fixture_is_exact_and_round_trips(self) -> None:
        self.assertEqual(FIXTURE, dsp_preset.dumps(DOCUMENT))
        self.assertEqual(DOCUMENT, dsp_preset.loads(FIXTURE))
        self.assertEqual(FIXTURE, dsp_preset.dumps(dsp_preset.loads(FIXTURE)))

    def test_noncanonical_human_json_canonicalizes(self) -> None:
        source = json.dumps(
            {
                "parameters": {
                    "delay.subdivision": "dotted-eighth",
                    "delay.mix_milli": 500,
                    "delay.free_ms": 375,
                    "delay.feedback_milli": 320,
                },
                "tempo_bpm": 92,
                "preset": "jazz-blues",
                "version": 1,
                "schema": "guitar-dsp.preset",
            },
            indent=2,
        )
        self.assertEqual(FIXTURE, dsp_preset.dumps(dsp_preset.loads(source)))

    def test_bounds_are_inclusive(self) -> None:
        minimum = {
            **DOCUMENT,
            "tempo_bpm": 20,
            "parameters": {
                **DOCUMENT["parameters"],
                "delay.feedback_milli": 0,
                "delay.free_ms": 1,
                "delay.mix_milli": 0,
                "delay.subdivision": "free",
            },
        }
        maximum = {
            **DOCUMENT,
            "preset": "a" * 32,
            "tempo_bpm": 300,
            "parameters": {
                **DOCUMENT["parameters"],
                "delay.feedback_milli": 950,
                "delay.free_ms": 2000,
                "delay.mix_milli": 1000,
                "delay.subdivision": "sixteenth",
            },
        }
        dsp_preset.validate(minimum)
        dsp_preset.validate(maximum)

    def test_invalid_documents_fail_closed(self) -> None:
        cases: list[dict[str, object]] = [
            {**DOCUMENT, "version": 2},
            {**DOCUMENT, "schema": "other"},
            {**DOCUMENT, "preset": "Jazz Blues"},
            {**DOCUMENT, "preset": "a" * 33},
            {**DOCUMENT, "tempo_bpm": 19},
            {**DOCUMENT, "tempo_bpm": 301},
            {**DOCUMENT, "tempo_bpm": True},
            {**DOCUMENT, "parameters": {**DOCUMENT["parameters"], "delay.feedback_milli": 951}},
            {**DOCUMENT, "parameters": {**DOCUMENT["parameters"], "delay.free_ms": 0}},
            {**DOCUMENT, "parameters": {**DOCUMENT["parameters"], "delay.free_ms": 2001}},
            {**DOCUMENT, "parameters": {**DOCUMENT["parameters"], "delay.mix_milli": 1001}},
            {**DOCUMENT, "parameters": {**DOCUMENT["parameters"], "delay.subdivision": "triplet"}},
            {**DOCUMENT, "extra": 1},
            {key: value for key, value in DOCUMENT.items() if key != "preset"},
            {
                **DOCUMENT,
                "parameters": {
                    **DOCUMENT["parameters"],
                    "unknown": 1,
                },
            },
            {
                **DOCUMENT,
                "parameters": {
                    key: value
                    for key, value in DOCUMENT["parameters"].items()
                    if key != "delay.mix_milli"
                },
            },
        ]
        for document in cases:
            with self.subTest(document=document):
                with self.assertRaises(dsp_preset.DspPresetError):
                    dsp_preset.validate(document)

    def test_subdivision_enum_is_frozen(self) -> None:
        for subdivision in (
            "free",
            "quarter",
            "dotted-eighth",
            "eighth",
            "eighth-triplet",
            "sixteenth",
        ):
            document = {
                **DOCUMENT,
                "parameters": {
                    **DOCUMENT["parameters"],
                    "delay.subdivision": subdivision,
                },
            }
            dsp_preset.validate(document)


if __name__ == "__main__":
    unittest.main()
