from __future__ import annotations

import ast
import copy
import json
import unittest
from pathlib import Path

from guitar_practice.domain import dsp_preset

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "dsp" / "fixtures" / "jazz-blues-preset-v1.json"
EXPECTED = (
    '{"parameters":{"delay.feedback_milli":320,"delay.free_ms":375,'
    '"delay.mix_milli":500,"delay.subdivision":"dotted-eighth"},'
    '"preset":"jazz-blues","schema":"guitar-dsp.preset",'
    '"tempo_bpm":92,"version":1}\n'
)


def preset() -> dict:
    return {
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


class DspPresetContractTests(unittest.TestCase):
    def test_canonical_fixture_is_exact_and_round_trips(self) -> None:
        fixture = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(EXPECTED, fixture)
        document = dsp_preset.loads(fixture)
        self.assertEqual(preset(), document)
        self.assertEqual(EXPECTED, dsp_preset.dumps(document))
        self.assertEqual(EXPECTED, dsp_preset.canonicalize(fixture))

    def test_canonicalize_normalizes_key_order_and_whitespace(self) -> None:
        source = json.dumps(
            {
                "version": 1,
                "parameters": preset()["parameters"],
                "tempo_bpm": 92,
                "schema": "guitar-dsp.preset",
                "preset": "jazz-blues",
            },
            indent=4,
        )
        self.assertEqual(EXPECTED, dsp_preset.canonicalize(source))

    def test_integer_parameter_bounds_are_inclusive(self) -> None:
        cases = (
            ("tempo_bpm", None, 20, 300),
            ("parameters", "delay.feedback_milli", 0, 950),
            ("parameters", "delay.free_ms", 1, 2000),
            ("parameters", "delay.mix_milli", 0, 1000),
        )
        for field, parameter, minimum, maximum in cases:
            for value in (minimum, maximum):
                with self.subTest(field=field, parameter=parameter, value=value):
                    document = preset()
                    if parameter is None:
                        document[field] = value
                    else:
                        document[field][parameter] = value
                    dsp_preset.validate(document)

            for value in (minimum - 1, maximum + 1, True):
                with self.subTest(
                    field=field,
                    parameter=parameter,
                    invalid=value,
                ):
                    document = preset()
                    if parameter is None:
                        document[field] = value
                    else:
                        document[field][parameter] = value
                    with self.assertRaises(dsp_preset.DspPresetError):
                        dsp_preset.validate(document)

    def test_subdivision_enum_is_bounded(self) -> None:
        for subdivision in sorted(dsp_preset.DELAY_SUBDIVISIONS):
            document = preset()
            document["parameters"]["delay.subdivision"] = subdivision
            dsp_preset.validate(document)

        document = preset()
        document["parameters"]["delay.subdivision"] = "dotted-quarter"
        with self.assertRaisesRegex(
            dsp_preset.DspPresetError,
            "delay.subdivision",
        ):
            dsp_preset.validate(document)

    def test_unknown_and_missing_top_level_fields_fail_closed(self) -> None:
        unknown = preset()
        unknown["device_path"] = "/dev/ttyUSB0"
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "unsupported fields"):
            dsp_preset.validate(unknown)

        for field in dsp_preset.TOP_LEVEL_FIELDS:
            with self.subTest(field=field):
                document = preset()
                del document[field]
                with self.assertRaisesRegex(
                    dsp_preset.DspPresetError,
                    "missing required fields",
                ):
                    dsp_preset.validate(document)

    def test_unknown_and_missing_parameter_ids_fail_closed(self) -> None:
        unknown = preset()
        unknown["parameters"]["shell.command"] = "anything"
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "unsupported IDs"):
            dsp_preset.validate(unknown)

        for parameter in dsp_preset.PARAMETER_IDS:
            with self.subTest(parameter=parameter):
                document = preset()
                del document["parameters"][parameter]
                with self.assertRaisesRegex(
                    dsp_preset.DspPresetError,
                    "missing required IDs",
                ):
                    dsp_preset.validate(document)

    def test_non_string_mapping_keys_fail_closed(self) -> None:
        top_level = preset()
        top_level[1] = "invalid"
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "keys"):
            dsp_preset.validate(top_level)

        parameter = preset()
        parameter["parameters"][1] = 10
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "parameter IDs"):
            dsp_preset.validate(parameter)

    def test_schema_version_and_preset_identity_are_strict(self) -> None:
        for value in (2, 0, True, "1"):
            document = preset()
            document["version"] = value
            with self.assertRaisesRegex(dsp_preset.DspPresetError, "version"):
                dsp_preset.validate(document)

        for value in (
            "Jazz Blues",
            "jazz_blues",
            "jazz-blues-",
            "",
            "a" * 65,
        ):
            document = preset()
            document["preset"] = value
            with self.assertRaisesRegex(dsp_preset.DspPresetError, "preset"):
                dsp_preset.validate(document)

    def test_raw_document_size_is_bounded(self) -> None:
        oversized = EXPECTED + (" " * dsp_preset.MAX_DOCUMENT_CHARS)
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "at most"):
            dsp_preset.loads(oversized)

    def test_duplicate_keys_and_nonfinite_json_fail_closed(self) -> None:
        duplicate = EXPECTED.replace(
            '"version":1}',
            '"version":1,"version":1}',
        )
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "duplicate"):
            dsp_preset.loads(duplicate)

        nonfinite = EXPECTED.replace('"tempo_bpm":92', '"tempo_bpm":NaN')
        with self.assertRaisesRegex(dsp_preset.DspPresetError, "non-finite"):
            dsp_preset.loads(nonfinite)

    def test_portable_schema_matches_domain_contract(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "contracts"
                / "dsp"
                / "guitar-dsp-preset-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            dsp_preset.TOP_LEVEL_FIELDS,
            frozenset(schema["required"]),
        )
        parameter_schema = schema["properties"]["parameters"]
        self.assertEqual(
            dsp_preset.PARAMETER_IDS,
            frozenset(parameter_schema["required"]),
        )
        self.assertEqual(
            dsp_preset.DELAY_SUBDIVISIONS,
            frozenset(
                parameter_schema["properties"]["delay.subdivision"]["enum"]
            ),
        )

    def test_validation_does_not_mutate_input(self) -> None:
        document = preset()
        original = copy.deepcopy(document)
        dsp_preset.validate(document)
        self.assertEqual(original, document)

    def test_domain_contract_imports_only_standard_library(self) -> None:
        source = (
            ROOT / "guitar_practice" / "domain" / "dsp_preset.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        self.assertEqual({"__future__", "json", "re", "typing"}, imports)


if __name__ == "__main__":
    unittest.main()
