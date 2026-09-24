# dehashed

Fetches all records from the DeHashed `/data-wells` endpoint (with pagination) into
`docs/data_wells.json`, and serves them via a static dashboard at `docs/index.html` for
GitHub Pages.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python fetch_data_wells.py --output docs/data_wells.json
```

Optionally set `DEHASHED_API_KEY` in the environment to authenticate requests:

```bash
export DEHASHED_API_KEY=your-api-key
python fetch_data_wells.py
```

### Rate limiting

DeHashed doesn't publish a concrete numeric rate limit for the public, unauthenticated
`/data-wells` endpoint, so the script is conservative by default: it waits at least
`--min-interval` seconds (default `3.0`) between requests, and if it does get rate limited
(HTTP 429) it honors the `Retry-After` header, falling back to exponential backoff, rather
than failing. It's slow by design but should be reliable. Tune with `--min-interval` if
needed.

### Incremental fetching

Walking all ~1,200 pages every run isn't necessary (and isn't rate-limit-friendly) once the
local `docs/data_wells.json` is up to date. Before doing a full walk, the script fetches only
page 1 and compares its `total` count and entries against the existing local file. If they
match, nothing has changed upstream, so it skips the full re-fetch and leaves the file
untouched. Otherwise it performs a full walk and rewrites the file. Pass `--force-full` to
always do a complete walk regardless.

## Dashboard

`docs/index.html` is a static, dependency-free page that fetches `docs/data_wells.json` at
page load and renders it client-side — no build step, no external libraries. Configure
GitHub Pages to publish from the `/docs` folder on the `main` branch.

It's a single searchable, filterable, sortable, paginated table of every individual breach
(name, date, records, sensitivity, exposed data types, description), with:
- Free-text search by name
- A multi-select data-type filter (e.g. show breaches exposing `email` and/or `password`)
- A sensitive-only toggle
- Live totals (breach count and total records) for whatever is currently filtered

Since the dashboard loads `data_wells.json` over `fetch()`, both `docs/index.html` and
`docs/data_wells.json` are committed to the repo — refreshing the data is just a matter of
re-running `fetch_data_wells.py` and committing the updated JSON.

To preview locally (fetch() requires http:// rather than file://):

```bash
cd docs && python3 -m http.server 8000
```

Then open http://localhost:8000.

## Automated daily updates & new-breach notifications

`.github/workflows/update-data.yml` runs on a daily schedule (and can be triggered manually
via "Run workflow"):

1. Fetches the latest `data_wells` and overwrites `docs/data_wells.json`.
2. Diffs it against the previous version (`scripts/detect_new_wells.py`, matched on the
   `insights` slug, falling back to name+date) to find newly added breaches.
3. Commits and pushes the updated JSON if it changed.
4. If any new breaches were found, opens a GitHub Issue labeled `new-breach` summarizing them.

Notifications are handled natively through GitHub Issues rather than a separate service:
anyone **watching** the repository (Watch → All Activity, or "Custom" → Issues) gets a
GitHub notification (web/email/mobile) whenever that issue is opened — no extra
infrastructure required. To opt in, watch the repo at
https://github.com/dfbr/dataBreachVisualisation.

If you have a DeHashed API key and want to use it (avoids rate limiting on the daily run),
set it as a repo secret named `DEHASHED_API_KEY` (Settings → Secrets and variables →
Actions).


