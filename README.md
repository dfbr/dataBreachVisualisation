# dehashed

Fetches all records from the DeHashed `/data-wells` endpoint (with pagination) into a local JSON file.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python fetch_data_wells.py --output data_wells.json
```

Optionally set `DEHASHED_API_KEY` in the environment to authenticate requests:

```bash
export DEHASHED_API_KEY=your-api-key
python fetch_data_wells.py
```

## Dashboard

`generate_report.py` builds a static HTML dashboard from `data_wells.json` and writes it to
`docs/index.html`, ready for GitHub Pages (configure Pages to publish from the `/docs` folder
on the `main` branch).

```bash
python generate_report.py --input data_wells.json --output docs/index.html
```

The dashboard includes: top breaches by records exposed, breaches/records per year, a
sensitive vs. non-sensitive split, and the most common exposed data types.

Unlike `data_wells.json`, `docs/index.html` is committed to the repo since it's what GitHub
Pages serves.
