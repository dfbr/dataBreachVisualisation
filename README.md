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
