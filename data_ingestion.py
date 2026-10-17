"""Day 1: inspect provided CSV datasets and validate fund master against NAV history."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def find_csv_by_name(fragment: str):
    matches = [p for p in RAW_DIR.rglob("*.csv") if fragment.lower() in p.stem.lower()]
    if not matches:
        return None
    if len(matches) > 1:
        print(f"Multiple CSVs match '{fragment}'; using {matches[0].name}")
    return matches[0]

def normalized_name(name):
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())

def find_column(df, candidates):
    by_normalized = {normalized_name(c): c for c in df.columns}
    for candidate in candidates:
        if normalized_name(candidate) in by_normalized:
            return by_normalized[normalized_name(candidate)]
    for col in df.columns:
        n = normalized_name(col)
        if any(normalized_name(candidate) in n for candidate in candidates):
            return col
    return None

def main():
    csv_paths = sorted(RAW_DIR.rglob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(
            f"No CSV files found under {RAW_DIR}. Copy the 10 provided CSV datasets into data/raw/ first."
        )

    print(f"Found {len(csv_paths)} CSV file(s) under {RAW_DIR}")
    dataset_summary = []
    loaded = {}

    for path in csv_paths:
        try:
            df = pd.read_csv(path, low_memory=False)
            loaded[path] = df
            print("\n" + "=" * 88)
            print(f"FILE: {path.relative_to(ROOT)}")
            print(f"SHAPE: {df.shape}")
            print("DTYPES:\n", df.dtypes.to_string())
            print("HEAD:\n", df.head().to_string(index=False))
            missing_cells = int(df.isna().sum().sum())
            duplicate_rows = int(df.duplicated().sum())
            dataset_summary.append({
                "file": str(path.relative_to(ROOT)),
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
                "missing_cells": missing_cells,
                "duplicate_rows": duplicate_rows,
                "duplicate_column_names": bool(df.columns.duplicated().any()),
            })
            anomalies = []
            if missing_cells:
                anomalies.append(f"{missing_cells} missing cells")
            if duplicate_rows:
                anomalies.append(f"{duplicate_rows} duplicate rows")
            if df.columns.duplicated().any():
                anomalies.append("duplicate column names")
            if not anomalies:
                anomalies.append("No basic missing/duplicate anomalies detected")
            print("BASIC ANOMALIES:", "; ".join(anomalies))
        except Exception as exc:
            print(f"ERROR reading {path.name}: {exc}")
            dataset_summary.append({"file": str(path.relative_to(ROOT)), "error": str(exc)})

    (REPORT_DIR / "dataset_inspection.json").write_text(
        json.dumps(dataset_summary, indent=2), encoding="utf-8"
    )
    pd.DataFrame(dataset_summary).to_csv(REPORT_DIR / "dataset_inspection.csv", index=False)

    # Validate AMFI scheme codes if the expected master/history files are present.
    master_path = find_csv_by_name("fund_master")
    history_path = find_csv_by_name("nav_history")
    if master_path is None or history_path is None:
        print("\nVALIDATION SKIPPED: couldn't locate both fund_master*.csv and nav_history*.csv in data/raw/.")
        print("Rename or copy the relevant files so their filenames contain 'fund_master' and 'nav_history'.")
        return

    master = pd.read_csv(master_path, low_memory=False)
    history = pd.read_csv(history_path, low_memory=False)
    master_code = find_column(master, ["scheme_code", "scheme code", "amfi_code", "amfi code", "code"])
    history_code = find_column(history, ["scheme_code", "scheme code", "amfi_code", "amfi code", "code"])

    if master_code is None or history_code is None:
        print("\nVALIDATION FAILED: couldn't infer scheme-code columns.")
        print("fund_master columns:", list(master.columns))
        print("nav_history columns:", list(history.columns))
        print("Set the scheme-code column names explicitly in data_ingestion.py.")
        return

    master_codes = set(master[master_code].dropna().astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    history_codes = set(history[history_code].dropna().astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    missing_codes = sorted(master_codes - history_codes)
    matched_codes = sorted(master_codes & history_codes)

    summary = {
        "fund_master_file": master_path.name,
        "nav_history_file": history_path.name,
        "fund_master_rows": int(len(master)),
        "nav_history_rows": int(len(history)),
        "fund_master_unique_non_null_codes": len(master_codes),
        "nav_history_unique_non_null_codes": len(history_codes),
        "matched_codes": len(matched_codes),
        "codes_missing_from_nav_history": missing_codes,
        "validation_passed": len(missing_codes) == 0,
        "fund_master_code_column": master_code,
        "nav_history_code_column": history_code,
    }
    (REPORT_DIR / "data_quality_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame({"scheme_code_missing_from_nav_history": missing_codes}).to_csv(
        REPORT_DIR / "missing_scheme_codes.csv", index=False
    )
    print("\n" + "=" * 88)
    print("DATA QUALITY SUMMARY")
    print(json.dumps(summary, indent=2))

    # Explore common master-data dimensions, printing available matching columns.
    print("\nFUND MASTER EXPLORATION")
    for label, candidates in {
        "fund houses": ["fund_house", "fund house", "fundhouse", "amc"],
        "categories": ["category", "scheme_category", "scheme category"],
        "sub-categories": ["sub_category", "sub category", "scheme_type", "scheme type"],
        "risk grades": ["risk_grade", "risk grade", "riskometer", "risk"],
    }.items():
        col = find_column(master, candidates)
        if col:
            print(f"\nUnique {label} ({col}):")
            print(master[col].dropna().astype(str).str.strip().sort_values().unique().tolist())
        else:
            print(f"\nCould not infer column for {label}. Available columns: {list(master.columns)}")

if __name__ == "__main__":
    main()
