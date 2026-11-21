from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "lua" / "outcome_harness.lua"
LUA = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua5.3")


@unittest.skipUnless(LUA, "lua is not installed")
class ExampleAdapterOutcomeTests(unittest.TestCase):
    """The example adapter must return the typed outcome, never score = 0."""

    scenarios = (
        "graded",
        "previewed",
        "missing-key",
        "missing-input",
        "read-error",
    )

    def test_example_adapter_returns_explicit_outcomes(self) -> None:
        adapter = ROOT / "example" / "adapter.lua"
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(
                    [LUA, str(HARNESS), str(adapter), "example", scenario],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
