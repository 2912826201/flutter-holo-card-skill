#!/usr/bin/env python3
"""Compatibility command for the v2 manifest-based check."""
import sys
from asset_pipeline import main

if __name__ == "__main__":
    sys.argv.insert(1, "check")
    raise SystemExit(main())
