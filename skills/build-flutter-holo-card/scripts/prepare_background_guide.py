#!/usr/bin/env python3
"""Retired: send the full original card directly to image generation."""
import json

if __name__ == "__main__":
    print(json.dumps({"accepted": False, "error":
        "Background guide stage retired. Generate a complete extended background from the original card; no output was written."}))
    raise SystemExit(2)
