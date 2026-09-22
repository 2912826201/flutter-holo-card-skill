#!/usr/bin/env python3
"""Removed unsafe v1 stage. Use the hash-bound asset_pipeline.py workflow."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("height", "medium", "low"), default="height")
    parser.parse_known_args()
    print(
        json.dumps(
            {
                "accepted": False,
                "error": "v1 stage retired: use asset_pipeline.py review-mask then build. No output was written.",
            }
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
