#!/usr/bin/env python3
"""Compatibility command for the v2 manifest-based cleanup."""
import sys
from asset_pipeline import main

if __name__ == "__main__":
    sys.argv.insert(1, "cleanup")
    raise SystemExit(main())
