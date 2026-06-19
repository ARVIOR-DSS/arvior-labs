from __future__ import annotations


SCENARIOS = {
    "Potato — Changins 2011": {
        "description": "Bintje potato validation trial at Agroscope-Changins, Switzerland.",
        "crop_id": "potato_table",
        "site_id": 5,
        "run_mode": "warmup_then_season",
        "warmup_days": 30,
        "initial_mineral_n_kg_ha": 60.0,
        "initial_no3_fraction": 0.90,
        "treatments": {
            "N0": {
                "trial_id": 11,
                "label": "No fertilizer",
                "default_irrigation": [
                    {"date": "2011-04-26", "mm": 30.0},
                    {"date": "2011-05-11", "mm": 30.0},
                    {"date": "2011-05-30", "mm": 30.0},
                    {"date": "2011-07-02", "mm": 30.0},
                ],
            },
            "N120": {
                "trial_id": 12,
                "label": "120 kg N/ha",
                "default_irrigation": [
                    {"date": "2011-04-26", "mm": 30.0},
                    {"date": "2011-05-11", "mm": 30.0},
                    {"date": "2011-05-30", "mm": 30.0},
                    {"date": "2011-07-02", "mm": 30.0},
                ],
            },
            "N200": {
                "trial_id": 13,
                "label": "200 kg N/ha",
                "default_irrigation": [
                    {"date": "2011-04-26", "mm": 30.0},
                    {"date": "2011-05-11", "mm": 30.0},
                    {"date": "2011-05-30", "mm": 30.0},
                    {"date": "2011-07-02", "mm": 30.0},
                ],
            },
        },
    },
    "Production grassland — Netherlands 2010": {
        "description": "Production grassland validation trial on sandy soil near the Loonse and Drunense Duinen.",
        "crop_id": "production_grassland",
        "site_id": 13,
        "run_mode": "season_only",
        "warmup_days": 0,
        "effective_start_mode": "jan1_of_harvest_year",
        "initial_mineral_n_kg_ha": 60.0,
        "initial_no3_fraction": 0.90,
        "treatments": {
            "N200": {
                "trial_id": 35,
                "label": "200 kg N/ha/year",
                "default_irrigation": [],
            },
            "N400": {
                "trial_id": 36,
                "label": "400 kg N/ha/year",
                "default_irrigation": [],
            },
        },
    },
}