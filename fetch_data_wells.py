#!/usr/bin/env python3
"""Fetch all records from the DeHashed /data-wells endpoint and save them locally.

The endpoint is paginated: each response includes a `next_page` boolean and a
`data_wells` list. This script walks pages starting at 1 until `next_page` is
false (or the page comes back empty), then writes every collected record to a
single local JSON file.

Usage:
    python fetch_data_wells.py [--output docs/data_wells.json]

The default output path lives under docs/ so the file is served directly by
GitHub Pages alongside docs/index.html, which loads it via fetch().

Optional auth:
    If DEHASHED_API_KEY is set in the environment, it is sent as the
    Dehashed-Api-Key header. The endpoint has been observed to work without
    an API key, but supplying one avoids rate limiting.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.dehashed.com/data-wells"
DEFAULT_OUTPUT = "docs/data_wells.json"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def build_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("DEHASHED_API_KEY")
    if api_key:
        headers["Dehashed-Api-Key"] = api_key
    return headers


def fetch_page(session: requests.Session, headers: dict[str, str], page: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                API_URL,
                params={"page": page},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    assert last_error is not None
    raise last_error


def fetch_all_data_wells() -> list[dict[str, Any]]:
    headers = build_headers()
    all_wells: list[dict[str, Any]] = []

    with requests.Session() as session:
        page = 1
        while True:
            payload = fetch_page(session, headers, page)
            wells = payload.get("data_wells") or []
            if not wells:
                break

            all_wells.extend(wells)
            total = payload.get("total")
            print(f"Fetched page {page}: {len(wells)} records (running total: {len(all_wells)}"
                  f"{f'/{total}' if total is not None else ''})")

            if not payload.get("next_page"):
                break
            page += 1

    return all_wells


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Path to write the collected JSON data to (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    data_wells = fetch_all_data_wells()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_wells, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(data_wells)} records to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
