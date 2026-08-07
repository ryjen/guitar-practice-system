"""Static contract checks for the dependency-free GitHub Pages frontend."""

from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.local_assets: list[str] = []
        self.remote_assets: list[str] = []
        self.csp: str | None = None
        self.toggle_buttons: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.add(element_id)

        if tag == "script" and (source := attributes.get("src")):
            self._record_asset(source)
        if tag == "link" and attributes.get("rel") == "stylesheet":
            if href := attributes.get("href"):
                self._record_asset(href)
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            self.csp = attributes.get("content")

        if tag == "button" and any(
            key in attributes
            for key in ("data-duration", "data-layer", "data-tempo-level")
        ):
            self.toggle_buttons.append(attributes)

    def _record_asset(self, path: str) -> None:
        if path.startswith(("http://", "https://", "//")):
            self.remote_assets.append(path)
        else:
            self.local_assets.append(path)


class PagesFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = (DOCS / "index.html").read_text(encoding="utf-8")
        cls.script = (DOCS / "assets" / "app.js").read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.index)
        cls.parser.close()

    def test_declared_assets_are_local_and_present(self) -> None:
        self.assertFalse(self.parser.remote_assets)
        for asset in self.parser.local_assets:
            relative = asset.removeprefix("./")
            self.assertTrue((DOCS / relative).is_file(), asset)

    def test_required_interaction_targets_are_present(self) -> None:
        required_ids = {
            "shuffle-session",
            "session-stages",
            "session-source",
            "technique-grid",
            "layer-detail",
            "tempo-input",
            "metronome-toggle",
            "metronome-status",
            "review-form",
            "review-output",
            "form-status",
        }
        self.assertTrue(required_ids.issubset(self.parser.ids))

    def test_toggle_controls_expose_pressed_state(self) -> None:
        self.assertGreater(len(self.parser.toggle_buttons), 0)
        for button in self.parser.toggle_buttons:
            self.assertIn(button.get("aria-pressed"), {"true", "false"})

    def test_page_has_restrictive_content_security_policy(self) -> None:
        self.assertIsNotNone(self.parser.csp)
        assert self.parser.csp is not None
        self.assertIn("default-src 'self'", self.parser.csp)
        self.assertIn("object-src 'none'", self.parser.csp)
        self.assertIn("connect-src 'none'", self.parser.csp)

    def test_dynamic_content_avoids_html_string_injection(self) -> None:
        self.assertNotIn("innerHTML", self.script)
        self.assertNotIn("insertAdjacentHTML", self.script)
        self.assertIn("textContent", self.script)

    def test_metronome_and_static_pages_mode_are_configured(self) -> None:
        self.assertIn("AudioContext", self.script)
        self.assertTrue((DOCS / ".nojekyll").is_file())


if __name__ == "__main__":
    unittest.main()
