"""Cross-repository contract: guitarctl invokes the *real* native DSP executable.

Skipped unless DSP_RENDER_BINARY points to the pinned DSP binary. Normal
unit tests use the narrower stub; CI separately builds this executable from
the exact upstream DSP commit rather than trusting two independent mocks.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "contracts/dsp/fixtures/jazz-blues-preset-v1.json"
ENGINE = os.environ.get("DSP_RENDER_BINARY")


@unittest.skipUnless(ENGINE, "set DSP_RENDER_BINARY for native bridge test")
class RealDspRenderContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        assert ENGINE is not None
        self.engine = str(Path(ENGINE).resolve(strict=True))
        self.assertTrue(Path(self.engine).is_file())

        # A tiny, real PCM16 guitar-like recording; nothing private and no
        # audio assets to download.
        self.rate = 44_100
        self.frames = 44_100
        samples = bytearray()
        for i in range(self.frames):
            time = i / self.rate
            attack = min(1.0, time * 100.0)
            envelope = math.exp(-2.3 * time) * attack
            mono = round(18000 * envelope * math.sin(2 * math.pi * 220 * time))
            samples.extend(struct.pack("<hh", mono, round(mono * 0.8)))
        with wave.open(str(self.workspace / "guitar.wav"), "wb") as pcm:
            pcm.setnchannels(2)
            pcm.setsampwidth(2)
            pcm.setframerate(self.rate)
            pcm.writeframes(bytes(samples))
        self.original = bytes(samples)

        # Input has the same semantic values as the canonical fixture, but
        # needs canonicalization by the control plane before the native parser.
        document = json.loads(PRESET.read_text(encoding="utf-8"))
        (self.workspace / "preset.json").write_text(
            json.dumps(document, indent=2), encoding="utf-8"
        )

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(
                ["--workspace", str(self.workspace), "render", "guitar.wav",
                 "--engine", self.engine, *args]
            )
        return code, stdout.getvalue(), stderr.getvalue()

    def pcm(self, name: str) -> bytes:
        with wave.open(str(self.workspace / name), "rb") as result:
            self.assertEqual(2, result.getnchannels())
            self.assertEqual(2, result.getsampwidth())
            self.assertEqual(self.rate, result.getframerate())
            self.assertEqual(self.frames, result.getnframes())
            return result.readframes(self.frames)

    def test_preset_chain_produces_real_pcm16_and_preserves_original(self) -> None:
        code, output, error = self.run_cli(
            "--preset", "preset.json", "--effects", "tremolo,delay",
            "--tremolo-rate", "4.5", "--output", "processed.wav"
        )
        self.assertEqual(0, code, error)
        self.assertEqual("", error)
        self.assertEqual(
            {"effects": "tremolo,delay", "output": "processed.wav", "status": "rendered"},
            json.loads(output),
        )
        transformed = self.pcm("processed.wav")
        self.assertNotEqual(self.original, transformed)
        self.assertTrue(any(transformed))
        self.assertEqual(self.original, self.pcm("guitar.wav"))

        # Output must be a new file; never replace the take just produced.
        code, stdout, error = self.run_cli(
            "--preset", "preset.json", "--effects", "tremolo,delay",
            "--output", "processed.wav"
        )
        self.assertEqual(65, code)
        self.assertEqual("", stdout)
        self.assertIn("already exists", error)
        self.assertEqual(transformed, self.pcm("processed.wav"))

    def test_order_is_applied_and_dry_passthrough_is_exact(self) -> None:
        first, _, error = self.run_cli(
            "--effects", "delay,tremolo", "--output", "dt.wav"
        )
        self.assertEqual(0, first, error)
        second, _, error = self.run_cli(
            "--effects", "tremolo,delay", "--output", "td.wav"
        )
        self.assertEqual(0, second, error)
        self.assertNotEqual(self.pcm("dt.wav"), self.pcm("td.wav"))

        dry, _, error = self.run_cli("--effects", "none", "--output", "dry.wav")
        self.assertEqual(0, dry, error)
        self.assertEqual(self.original, self.pcm("dry.wav"))

    def test_rejects_invalid_preset_without_writing_audio(self) -> None:
        document = json.loads((self.workspace / "preset.json").read_text())
        document["parameters"]["delay.mix_milli"] = 1001
        (self.workspace / "preset.json").write_text(json.dumps(document))
        code, stdout, error = self.run_cli(
            "--preset", "preset.json", "--output", "invalid.wav"
        )
        self.assertEqual(65, code)
        self.assertEqual("", stdout)
        self.assertIn("delay.mix_milli", error)
        self.assertFalse((self.workspace / "invalid.wav").exists())


if __name__ == "__main__":
    unittest.main()
