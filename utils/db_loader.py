from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("data/arvior_validation_golden_v10.sqlite")


WEATHER_COLMAP_DB_TO_API = {
    "date": "Date",
    "Temp_C": "Temp",
    "Tmin_C": "Tmin",
    "Tmax_C": "Tmax",
    "Tdew_C": "Tdew",
    "Rs_MJ_m2_d": "Rs",
    "Pressure_kPa": "Pressure",
    "Wind_m_s": "Wind_(m/s)",
    "P_mm": "P",
    "Rhmin_pct": "Rhmin",
    "Rhmax_pct": "Rhmax",
}


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Could not find database at {DB_PATH}. "
            "Copy arvior_validation_golden V10.sqlite into the data folder first."
        )

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def _json_or_default(value, default):
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def _num(value, default=None) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(value)


def load_trial(con: sqlite3.Connection, trial_id: int) -> dict:
    trial = pd.read_sql_query(
        "SELECT * FROM trials WHERE trial_id=?",
        con,
        params=(trial_id,),
    )

    if trial.empty:
        raise ValueError(f"trial_id not found: {trial_id}")

    return trial.iloc[0].to_dict()


def load_site_display(con: sqlite3.Connection, site_id: int) -> dict:
    site = pd.read_sql_query(
        "SELECT * FROM sites WHERE site_id=?",
        con,
        params=(site_id,),
    )

    if site.empty:
        raise ValueError(f"site_id not found: {site_id}")

    return site.iloc[0].to_dict()


def load_site_for_api(con: sqlite3.Connection, site_id: int, crop_id: str) -> dict:
    site = pd.read_sql_query(
        "SELECT * FROM sites WHERE site_id=?",
        con,
        params=(site_id,),
    )

    if site.empty:
        raise ValueError(f"site_id not found: {site_id}")

    row = site.iloc[0].to_dict()

    return {
        "latitude_deg": _num(row["latitude_deg"]),
        "soil_id": str(row["soil_id"]),
        "crop_id": crop_id,
        "OM_percent": _num(row["OM_percent"]),
        "CN_ratio": _num(row["CN_ratio"]),
        "pH": _num(row["pH"]),
        "sample_depth_cm": _num(row["sample_depth_cm"]),
        "Z_top_cm": _num(row.get("Z_top_cm"), default=30.0),
        "infiltration": {"enabled": True, "routing": "pond"},
        "gw": _json_or_default(row.get("gw_json"), {"enabled": False}),
        "salinity": _json_or_default(row.get("salinity_json"), {"ECe_init": 0.0}),
    }


def load_weather_for_api(
    con: sqlite3.Connection,
    site_id: int,
    start_date: str,
    end_date: str,
) -> list[dict]:
    weather = pd.read_sql_query(
        """
        SELECT *
        FROM weather_daily
        WHERE site_id=?
          AND date>=?
          AND date<=?
        ORDER BY date ASC
        """,
        con,
        params=(site_id, start_date, end_date),
    )

    if weather.empty:
        raise ValueError(
            f"No weather rows found for site_id={site_id} "
            f"between {start_date} and {end_date}."
        )

    weather = weather.rename(columns=WEATHER_COLMAP_DB_TO_API)

    required = [
        "Date",
        "Temp",
        "Tmin",
        "Tmax",
        "Tdew",
        "Rs",
        "Pressure",
        "Wind_(m/s)",
        "P",
    ]

    missing = [col for col in required if col not in weather.columns]
    if missing:
        raise ValueError(f"Weather data missing required columns: {missing}")

    keep = required + [col for col in ["Rhmin", "Rhmax"] if col in weather.columns]
    weather = weather[keep].copy()

    weather["Date"] = pd.to_datetime(weather["Date"]).dt.date.astype(str)

    return weather.to_dict(orient="records")


def load_fertilizer_events_for_api(
    con: sqlite3.Connection,
    trial_id: int,
) -> list[dict]:
    events = pd.read_sql_query(
        """
        SELECT event_type, date, amount, product_id, ignore_in_model
        FROM management_events
        WHERE trial_id=?
          AND event_type='mineral_fertilizer'
          AND (ignore_in_model IS NULL OR ignore_in_model=0)
        ORDER BY date ASC
        """,
        con,
        params=(trial_id,),
    )

    fertilizer = []
    for row in events.to_dict(orient="records"):
        fertilizer.append(
            {
                "date": row["date"],
                "product_id": row["product_id"],
                "kg_product_per_ha": float(row["amount"]),
            }
        )

    return fertilizer