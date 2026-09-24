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

Rate limiting:
    DeHashed does not publish a concrete numeric rate limit for the public,
    unauthenticated /data-wells endpoint, so this script errs on the side of
    caution: a configurable minimum delay is enforced between requests
    (--min-interval, default 3s), and HTTP 429 responses are honored via the
    Retry-After header (falling back to exponential backoff) rather than
    treated as a hard failure. This is deliberately slow but reliable.

Incremental fetching:
    Walking all ~1,200 pages every run is unnecessary (and rate-limit-unfriendly)
    when nothing has changed upstream. Before doing a full walk, the script
    fetches only page 1 and compares its `total` count and entries against the
    existing local output file. If they match, it assumes nothing changed and
    exits without re-fetching or rewriting the file. Otherwise it performs a
    full walk and rewrites the file with the authoritative full list. Pass
    --force-full to always do a complete walk.

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
DEFAULT_MIN_INTERVAL = 3.0
MAX_429_RETRIES = 6
BACKOFF_429_START_SECONDS = 10
BACKOFF_429_CAP_SECONDS = 180


def build_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("DEHASHED_API_KEY")
    if api_key:
        headers["Dehashed-Api-Key"] = api_key
    return headers


def key_for(well: dict[str, Any]) -> str:
    """Identify a breach for change-detection. Kept in sync with scripts/detect_new_wells.py."""
    insights = well.get("insights")
    if insights:
        return f"insights:{insights}"
    return f"name-date:{well.get('name')}|{well.get('date')}"


def load_existing(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


class RateLimiter:
    """Enforces a minimum delay between requests and backs off on HTTP 429."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def mark(self) -> None:
        self._last_request_at = time.monotonic()


def fetch_page_once(
    session: requests.Session,
    headers: dict[str, str],
    page: int,
    limiter: RateLimiter,
) -> dict[str, Any]:
    """Fetch a single page, transparently retrying on HTTP 429 until it succeeds or gives up."""
    backoff_429 = BACKOFF_429_START_SECONDS

    for retry_429 in range(MAX_429_RETRIES + 1):
        limiter.wait()
        response = session.get(
            API_URL,
            params={"page": page},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        limiter.mark()

        if response.status_code != 429:
            response.raise_for_status()
            return response.json()

        if retry_429 == MAX_429_RETRIES:
            raise requests.HTTPError("Rate limited (429) after max retries", response=response)

        retry_after = response.headers.get("Retry-After")
        delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff_429
        print(f"Rate limited on page {page}; waiting {delay:.0f}s before retrying...")
        time.sleep(delay)
        backoff_429 = min(backoff_429 * 2, BACKOFF_429_CAP_SECONDS)

    raise AssertionError("unreachable")


def fetch_page(
    session: requests.Session,
    headers: dict[str, str],
    page: int,
    limiter: RateLimiter,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_page_once(session, headers, page, limiter)
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    assert last_error is not None
    raise last_error


def fetch_all_data_wells(
    limiter: RateLimiter,
    existing: list[dict[str, Any]],
    force_full: bool,
) -> tuple[list[dict[str, Any]], bool]:
    """Returns (data_wells, changed). If unchanged, data_wells is the existing list untouched."""
    headers = build_headers()
    existing_keys = {key_for(w) for w in existing}

    with requests.Session() as session:
        first_payload = fetch_page(session, headers, 1, limiter)
        first_page_wells = first_payload.get("data_wells") or []
        total = first_payload.get("total")

        if (
            not force_full
            and existing
            and total == len(existing)
            and all(key_for(w) in existing_keys for w in first_page_wells)
        ):
            print(
                f"No changes detected (total={total} matches existing, page 1 unchanged); "
                "skipping full refetch."
            )
            return existing, False

        print("Change detected (or first run) — performing full paginated fetch...")
        all_wells: list[dict[str, Any]] = list(first_page_wells)
        print(f"Fetched page 1: {len(first_page_wells)} records (running total: {len(all_wells)}"
              f"{f'/{total}' if total is not None else ''})")

        page = 1
        next_page = first_payload.get("next_page")
        while next_page:
            page += 1
            payload = fetch_page(session, headers, page, limiter)
            wells = payload.get("data_wells") or []
            if not wells:
                break
            all_wells.extend(wells)
            total = payload.get("total")
            print(f"Fetched page {page}: {len(wells)} records (running total: {len(all_wells)}"
                  f"{f'/{total}' if total is not None else ''})")
            next_page = payload.get("next_page")

    return all_wells, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Path to write the collected JSON data to (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=DEFAULT_MIN_INTERVAL,
        help=f"Minimum seconds between requests (default: {DEFAULT_MIN_INTERVAL})",
    )
    parser.add_argument(
        "--force-full",
        action="store_true",
        help="Always perform a full paginated walk, skipping the incremental fast path",
    )
    args = parser.parse_args()

    existing = load_existing(args.output)
    limiter = RateLimiter(args.min_interval)

    data_wells, changed = fetch_all_data_wells(limiter, existing, args.force_full)

    if not changed:
        print(f"{args.output} is already up to date ({len(data_wells)} records).")
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_wells, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(data_wells)} records to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
