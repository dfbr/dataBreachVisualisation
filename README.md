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

