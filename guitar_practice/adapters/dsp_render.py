"""Bounded subprocess adapter to the separately built DSP render host."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path


class DspAudioRenderError(RuntimeError):
    """External audio engine unavailable or rejected the requested render."""


class SubprocessDspAudioRenderer:
    def __init__(self, workspace: Path, *, executable: str = "dsp") -> None:
        self.workspace = workspace.resolve()
        self.executable = executable

    def _path(self, relative: str, *, label: str) -> Path:
        path = (self.workspace / relative).resolve()
        if not path.is_relative_to(self.workspace):
            raise DspAudioRenderError(f"{label} escapes the workspace")
        return path

    def render(
        self,
        source: str,
        output: str,
        *,
        effects: str,
        options: Sequence[str],
        preset_canonical: str | None,
    ) -> str:
        input_path = self._path(source, label="input")
        output_path = self._path(output, label="output")
        if input_path.suffix.casefold() != ".wav" or not input_path.is_file():
            raise DspAudioRenderError("input must be an existing workspace WAV file")
        if output_path.suffix.casefold() != ".wav":
            raise DspAudioRenderError("output must have .wav extension")
        if not output_path.parent.is_dir():
            raise DspAudioRenderError("output directory must exist")
        if output_path.exists() or output_path.is_symlink():
            raise DspAudioRenderError("output already exists; refusing overwrite")

        executable = shutil.which(self.executable)
        if executable is None:
            raise DspAudioRenderError(
                "DSP engine unavailable: build ryjen/dsp and use --engine /path/to/dsp"
            )

        with tempfile.TemporaryDirectory(prefix="guitarctl-dsp-") as directory:
            argv = [
                executable,
                "render", str(input_path),
                "--output", str(output_path),
                "--effects", effects,
                *options,
            ]
            if preset_canonical is not None:
                temp_preset = Path(directory) / "preset.json"
                temp_preset.write_text(preset_canonical, encoding="utf-8")
                argv.extend(["--preset", str(temp_preset)])
            try:
                result = subprocess.run(
                    argv,
                    cwd=self.workspace,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=300,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise DspAudioRenderError(f"DSP invocation failed: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or "unknown DSP engine error"
            raise DspAudioRenderError(f"DSP render failed: {detail[:800]}")
        if not output_path.is_file():
            raise DspAudioRenderError("DSP engine did not produce the output WAV")
        return output
