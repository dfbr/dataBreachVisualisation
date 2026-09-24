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

## Dashboard

`docs/index.html` is a static, dependency-free page (Plotly loaded from a CDN) that fetches
`docs/data_wells.json` at page load and renders it client-side — no build step required.
Configure GitHub Pages to publish from the `/docs` folder on the `main` branch.

It includes:
- Summary stats (total data wells, total records exposed, % sensitive)
- Charts: top breaches by records, breaches/records per year, sensitive vs. non-sensitive
  split, most common exposed data types
- A searchable, filterable, sortable, paginated table of every individual breach (name,
  date, records, sensitivity, exposed data types, description)

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


