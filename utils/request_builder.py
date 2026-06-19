from __future__ import annotations

from datetime import timedelta

import pandas as pd

from utils.db_loader import (
    load_fertilizer_events_for_api,
    load_site_for_api,
    load_trial,
    load_weather_for_api,
)


def inject_initial_mineral_n(
    prev_state: dict | None,
    nmin_kg_ha: float,
    no3_fraction: float,
) -> tuple[dict, dict]:
    """
    Inject mineral N into the checkpoint state at sowing.

    This follows the validation logic:
    - run warm-up first
    - then add initial mineral N to nitrogen.NO3_pool and nitrogen.NH4_pool
    - then run the crop season
    """
    state = dict(prev_state or {})

    nitrogen = state.get("nitrogen")
    nitrogen = dict(nitrogen) if isinstance(nitrogen, dict) else {}

    no3_add = float(nmin_kg_ha) * float(no3_fraction)
    nh4_add = float(nmin_kg_ha) * (1.0 - float(no3_fraction))

    no3_before = float(nitrogen.get("NO3_pool", 0.0) or 0.0)
    nh4_before = float(nitrogen.get("NH4_pool", 0.0) or 0.0)

    nitrogen["NO3_pool"] = no3_before + no3_add
    nitrogen["NH4_pool"] = nh4_before + nh4_add
    nitrogen["NO3_mobile_share"] = float(
        nitrogen.get("NO3_mobile_share", 1.0) or 1.0
    )

    state["nitrogen"] = nitrogen

    debug = {
        "nmin_kg_ha": float(nmin_kg_ha),
        "no3_fraction": float(no3_fraction),
        "NO3_before": no3_before,
        "NH4_before": nh4_before,
        "NO3_added": no3_add,
        "NH4_added": nh4_add,
        "NO3_after": nitrogen["NO3_pool"],
        "NH4_after": nitrogen["NH4_pool"],
    }

    return state, debug


def build_management(
    sowing_date: str,
    harvest_date: str,
    fertilizer_events: list[dict],
    irrigation_events: list[dict],
) -> dict:
    return {
        "sowing": {"date": sowing_date},
        "harvest": {"date": harvest_date},
        "irrigation": irrigation_events,
        "organic_fertilizer": [],
        "mineral_fertilizer": fertilizer_events,
    }


def build_run_request(
    con,
    site_id: int,
    crop_id: str,
    sowing_date: str,
    harvest_date: str,
    window_start: str,
    window_end: str,
    fertilizer_events: list[dict],
    irrigation_events: list[dict],
    prev_state: dict | None = None,
    site_overrides: dict | None = None,
) -> dict:
    site = load_site_for_api(con, site_id=site_id, crop_id=crop_id)

    if site_overrides:
        site.update(site_overrides)

    weather = load_weather_for_api(
        con,
        site_id=site_id,
        start_date=window_start,
        end_date=window_end,
    )

    management = build_management(
        sowing_date=sowing_date,
        harvest_date=harvest_date,
        fertilizer_events=fertilizer_events,
        irrigation_events=irrigation_events,
    )

    return {
        "weather": weather,
        "site": site,
        "management": management,
        "crop_id": crop_id,
        "prev_state": prev_state,
        "dss_config": {},
    }


def build_scenario_inputs(con, scenario: dict, treatment_key: str) -> dict:
    treatment = scenario["treatments"][treatment_key]
    trial = load_trial(con, treatment["trial_id"])

    crop_id = scenario["crop_id"]

    raw_sowing_date = trial.get("sowing_date")
    raw_harvest_date = trial.get("harvest_date")

    harvest_date = pd.to_datetime(raw_harvest_date).date()

    # Production grassland is treated as perennial-like:
    # effective start is Jan 1 of the trial/harvest year.
    if scenario.get("effective_start_mode") == "jan1_of_harvest_year":
        sowing_date = pd.Timestamp(
            year=harvest_date.year,
            month=1,
            day=1,
        ).date()
    else:
        sowing_date = pd.to_datetime(raw_sowing_date).date()

    warmup_days = int(scenario.get("warmup_days", 0) or 0)

    if warmup_days > 0:
        warmup_start = sowing_date - timedelta(days=warmup_days)
        warmup_end = sowing_date - timedelta(days=1)
    else:
        warmup_start = None
        warmup_end = None

    fertilizer_events = load_fertilizer_events_for_api(
        con,
        treatment["trial_id"],
    )

    irrigation_events = treatment.get("default_irrigation", [])

    return {
        "trial": trial,
        "crop_id": crop_id,
        "sowing_date": sowing_date.isoformat(),
        "harvest_date": harvest_date.isoformat(),
        "warmup_start": warmup_start.isoformat() if warmup_start else None,
        "warmup_end": warmup_end.isoformat() if warmup_end else None,
        "fertilizer_events": fertilizer_events,
        "irrigation_events": irrigation_events,
    }


def add_days_after_sowing(df: pd.DataFrame, sowing_date: str) -> pd.DataFrame:
    out = df.copy()

    if "Date" not in out.columns:
        return out

    out["Date"] = pd.to_datetime(out["Date"])
    sow = pd.to_datetime(sowing_date)

    out["DAS"] = (out["Date"] - sow).dt.days
    return out