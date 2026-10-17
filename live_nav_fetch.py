"""Fetch current/latest available NAV history from MFAPI and save raw CSV files."""
from pathlib import Path
from datetime import datetime, timezone
import json
import time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://api.mfapi.in/mf/"

SCHEMES = {
    "125497": "HDFC_Top_100_Direct",
    "119551": "SBI_Bluechip",
    "120503": "ICICI_Bluechip",
    "118632": "Nippon_Large_Cap",
    "119092": "Axis_Bluechip",
    "120841": "Kotak_Bluechip",
}

def fetch_scheme(session: requests.Session, code: str, label: str) -> pd.DataFrame:
    url = f"{BASE_URL}{code}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    # Preserve the unmodified API response for traceability.
    raw_json_path = RAW_DIR / f"mfapi_{code}_{label}.json"
    raw_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    data = payload.get("data", [])
    if not isinstance(data, list) or not data:
        raise ValueError(f"No NAV records returned for scheme {code} ({label}). Response keys: {list(payload)}")

    meta = payload.get("meta", {})
    df = pd.DataFrame(data)
    df["scheme_code"] = str(code)
    df["scheme_name"] = meta.get("scheme_name") or label.replace("_", " ")
    df["fund_house"] = meta.get("fund_house")
    df["scheme_category"] = meta.get("scheme_category")
    df["scheme_type"] = meta.get("scheme_type")
    df["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    if "nav" in df.columns:
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["source_url"] = url

    csv_path = RAW_DIR / f"nav_{code}_{label}.csv"
    df.to_csv(csv_path, index=False)
    print(f"{label} ({code}): {len(df):,} NAV rows -> {csv_path.relative_to(ROOT)}")
    if "date" in df.columns and df["date"].notna().any():
        latest_idx = df["date"].idxmax()
        print(f"  Latest date in response: {df.loc[latest_idx, 'date'].date()}, NAV: {df.loc[latest_idx, 'nav']}")
    return df

def main():
    all_frames = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "MutualFundAnalyticsInternship/1.0"})
        for code, label in SCHEMES.items():
            try:
                all_frames.append(fetch_scheme(session, code, label))
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                print(f"FAILED {label} ({code}): {exc}")
            time.sleep(0.25)  # be polite to the public API

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True, sort=False)
        combined_path = RAW_DIR / "live_nav_history.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\nCombined NAV history: {len(combined):,} rows -> {combined_path.relative_to(ROOT)}")
    else:
        raise RuntimeError("No scheme data could be fetched. Check internet access and scheme codes.")

if __name__ == "__main__":
    main()
