# Mutual Fund Analytics — Day 1

## Setup
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Data placement
Copy the 10 provided CSV datasets into `data/raw/`. Keep the original filenames. The inspection script searches recursively under this folder. For automated scheme-code validation, the filenames should contain `fund_master` and `nav_history`.

## Run
```bash
python live_nav_fetch.py
python data_ingestion.py
```

`live_nav_fetch.py` saves the original API JSON responses and one CSV per scheme under `data/raw/`, plus `live_nav_history.csv`.
`data_ingestion.py` prints shape, dtypes, head, and basic anomalies for each CSV and writes inspection/data-quality reports under `reports/`.

## AMFI scheme codes
Treat scheme codes as identifiers, not as numbers for arithmetic. Keep them as strings to avoid accidental formatting changes. A scheme code is an assigned identifier; do not assume its digits encode fund house, category, or risk grade.

## Day 1 deliverables
- `data_ingestion.py`
- `live_nav_fetch.py`
- `requirements.txt`
- `reports/dataset_inspection.csv` and `.json` (generated after running)
- `reports/data_quality_summary.json` and `reports/missing_scheme_codes.csv` (generated when master/history files are found)
