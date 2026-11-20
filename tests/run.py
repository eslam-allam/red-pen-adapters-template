#!/usr/bin/env python3
"""Run the registry template test suite."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from registry import RegistryToolError, find_minisign  # noqa: E402


def main() -> int:
    try:
        print(f"minisign: {find_minisign()}")
    except RegistryToolError as exc:
        print(f"minisign: unavailable ({exc}); signing tests will be skipped")
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
