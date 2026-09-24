#!/usr/bin/env python3
"""Diff two data_wells JSON snapshots and report newly added breaches.

Used by the daily-update GitHub Action to decide whether to open a
notification issue. A breach is identified by its `insights` slug when
present, otherwise by its `name` + `date` pair.

Usage:
    python scripts/detect_new_wells.py --old old.json --new new.json --output new_wells.json
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def load(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def key_for(well: dict[str, Any]) -> str:
    insights = well.get("insights")
    if insights:
        return f"insights:{insights}"
    return f"name-date:{well.get('name')}|{well.get('date')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="Path to the previous JSON snapshot")
    parser.add_argument("--new", required=True, help="Path to the freshly fetched JSON snapshot")
    parser.add_argument("--output", required=True, help="Where to write the list of newly added breaches")
    args = parser.parse_args()

    old_keys = {key_for(w) for w in load(args.old)}
    new_wells = load(args.new)

    added = [w for w in new_wells if key_for(w) not in old_keys]
    added.sort(key=lambda w: w.get("records") or 0, reverse=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(added, f, ensure_ascii=False, indent=2)

    print(f"Found {len(added)} new breach(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
