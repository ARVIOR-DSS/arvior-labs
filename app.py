import json

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.api_client import check_api_health, run_arvior
from utils.db_loader import connect, load_site_display
from utils.request_builder import (
    add_days_after_sowing,
    build_potato_inputs,
    build_run_request,
    inject_initial_mineral_n,
)
from utils.scenarios import SCENARIOS

def available_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Return only columns that exist in the dataframe."""
    return [col for col in cols if col in df.columns]


def plot_line(df: pd.DataFrame, y_cols: list[str], title: str, y_label: str):
    cols = available_cols(df, y_cols)

    if not cols:
        return

    fig = px.line(
        df,
        x="DAS",
        y=cols,
        labels={
            "DAS": "Days after sowing",
            "value": y_label,
            "variable": "Variable",
        },
        title=title,
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_bar(df: pd.DataFrame, y_cols: list[str], title: str, y_label: str):
    cols = available_cols(df, y_cols)

    if not cols:
        return

    fig = px.bar(
        df,
        x="DAS",
        y=cols,
        labels={
            "DAS": "Days after sowing",
            "value": y_label,
            "variable": "Variable",
        },
        title=title,
    )
    st.plotly_chart(fig, use_container_width=True)

def render_model_results(
    season_df: pd.DataFrame,
    irrigation_events: list[dict],
    crop_id: str,
    treatment_key: str,
):
    """Render summary metrics, graphs and CSV download for the latest model run."""

    st.markdown("## Summary")

    final_row = season_df.iloc[-1]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if "Biomass_actual_cum" in season_df.columns:
            st.metric(
                "Final biomass",
                f"{float(final_row['Biomass_actual_cum']):.2f} t DM/ha",
            )

    with col2:
        if "Yield_dm" in season_df.columns:
            st.metric(
                "Yield DM",
                f"{float(final_row['Yield_dm']):.2f}",
            )

    with col3:
        if "Yield_fresh" in season_df.columns:
            st.metric(
                "Fresh yield",
                f"{float(final_row['Yield_fresh']):.2f}",
            )

    with col4:
        if "N_cum_actual" in season_df.columns:
            st.metric(
                "N uptake",
                f"{float(final_row['N_cum_actual']):.1f} kg N/ha",
            )

    with col5:
        total_irrigation = sum(float(e["mm"]) for e in irrigation_events)
        st.metric(
            "Total irrigation",
            f"{total_irrigation:.0f} mm",
        )

    col6, col7, col8, col9, col10 = st.columns(5)

    with col6:
        if "NO3_leached" in season_df.columns:
            st.metric(
                "Total NO₃ leached",
                f"{float(season_df['NO3_leached'].sum()):.1f} kg N/ha",
            )

    with col7:
        if "N_denitrified" in season_df.columns:
            st.metric(
                "Denitrified N",
                f"{float(season_df['N_denitrified'].sum()):.1f} kg N/ha",
            )

    with col8:
        if "NH3_volatilized" in season_df.columns:
            st.metric(
                "NH₃ volatilized",
                f"{float(season_df['NH3_volatilized'].sum()):.1f} kg N/ha",
            )

    with col9:
        if "ks" in season_df.columns:
            water_stress_days = int((season_df["ks"] < 0.99).sum())
            st.metric(
                "Water-stress days",
                f"{water_stress_days}",
            )

    with col10:
        if "N_stress_factor" in season_df.columns:
            n_stress_days = int((season_df["N_stress_factor"] < 0.99).sum())
            st.metric(
                "N-stress days",
                f"{n_stress_days}",
            )

    st.markdown("## Model outputs")

    results_tab1, results_tab2, results_tab3, results_tab4 = st.tabs(
        [
            "Growth and yield",
            "Nitrogen",
            "Water balance",
            "Stress and DSS",
        ]
    )

    with results_tab1:
        plot_line(
            season_df,
            ["Biomass_actual_cum", "Biomass_pot_cum"],
            "Biomass development",
            "Biomass (t DM/ha)",
        )

        plot_line(
            season_df,
            ["dBiomass_actual", "dBiomass_pot"],
            "Daily biomass growth",
            "Daily biomass growth (t DM/ha/day)",
        )

        plot_line(
            season_df,
            ["Yield_dm", "Yield_dm_pot"],
            "Dry matter yield",
            "Yield DM",
        )

        plot_line(
            season_df,
            ["Yield_fresh", "Yield_fresh_pot"],
            "Fresh yield",
            "Fresh yield",
        )

    with results_tab2:
        plot_line(
            season_df,
            ["N_cum_actual"],
            "Cumulative nitrogen uptake",
            "N uptake (kg N/ha)",
        )

        plot_line(
            season_df,
            ["N_actual_daily", "N_potential_daily"],
            "Daily nitrogen uptake",
            "Daily N uptake/demand (kg N/ha/day)",
        )

        plot_line(
            season_df,
            ["NO3_pool", "NH4_pool"],
            "Mineral nitrogen pools",
            "Mineral N pool (kg N/ha)",
        )

        plot_bar(
            season_df,
            ["N_fert_added_today"],
            "Fertilizer N additions",
            "N added (kg N/ha/day)",
        )

        plot_line(
            season_df,
            ["NO3_leached", "N_denitrified", "NH3_volatilized"],
            "Daily nitrogen losses",
            "N loss (kg N/ha/day)",
        )

    with results_tab3:
        plot_line(
            season_df,
            ["VWC"],
            "Volumetric water content",
            "VWC (%)",
        )

        plot_line(
            season_df,
            ["wb_D_end_mm", "RAW", "TAW"],
            "Root-zone depletion, RAW and TAW",
            "Water depth (mm)",
        )

        plot_bar(
            season_df,
            ["P", "Irrigation"],
            "Rainfall and irrigation",
            "Water input (mm/day)",
        )

        plot_line(
            season_df,
            ["ET0", "ETa"],
            "Reference and actual evapotranspiration",
            "ET (mm/day)",
        )

        plot_line(
            season_df,
            ["DP", "Runoff"],
            "Drainage and runoff",
            "Water loss (mm/day)",
        )

    with results_tab4:
        plot_line(
            season_df,
            ["ks", "N_stress_factor", "f_salinity"],
            "Stress factors",
            "Stress factor (1 = no stress)",
        )

        plot_line(
            season_df,
            ["Irrig_rec_mm"],
            "DSS irrigation recommendation",
            "Recommended irrigation (mm)",
        )

        plot_line(
            season_df,
            ["Fert_rec_kgN_ha"],
            "DSS fertilizer recommendation",
            "Recommended N (kg N/ha)",
        )

        plot_line(
            season_df,
            ["Leach_risk_index", "Drive_risk_index"],
            "Operational risk indices",
            "Risk index",
        )

    with st.expander("Available output columns"):
        st.write(list(season_df.columns))

    csv = season_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download season output CSV",
        data=csv,
        file_name=f"{crop_id}_{treatment_key}_season_output.csv",
        mime="text/csv",
    )

st.set_page_config(
    page_title="ARVIOR Education Demo",
    page_icon="🌱",
    layout="wide",
)


# -----------------------------
# Header
# -----------------------------
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.markdown("### 🌱")

with col_title:
    st.title("ARVIOR Education Demo")
    st.caption(
        "Interactive crop–soil–water–nitrogen model demo for education and scenario exploration."
    )


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Scenario settings")

scenario_name = st.sidebar.selectbox(
    "Scenario",
    list(SCENARIOS.keys()),
)

scenario_config = SCENARIOS[scenario_name]

treatment_key = st.sidebar.selectbox(
    "Treatment",
    list(scenario_config["treatments"].keys()),
)

treatment_config = scenario_config["treatments"][treatment_key]

run_button = st.sidebar.button("Run ARVIOR", type="primary")

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0

selection_id = f"{scenario_name}_{treatment_key}"
previous_selection_id = st.session_state.get("selection_id")

if previous_selection_id != selection_id:
    st.session_state["selection_id"] = selection_id
    st.session_state["reset_counter"] += 1

reset_button = st.sidebar.button("Reset scenario defaults")

if reset_button:
    st.session_state["reset_counter"] += 1

    # Clear previous model results.
    for key in list(st.session_state.keys()):
        if key.startswith("last_"):
            del st.session_state[key]

    st.rerun()

widget_key = f"{selection_id}_{st.session_state['reset_counter']}"

st.sidebar.markdown("---")

if st.sidebar.button("Check API connection"):
    ok, message = check_api_health()

    if ok:
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)


# -----------------------------
# Load database defaults
# -----------------------------
con = connect()

potato_inputs = build_potato_inputs(
    con=con,
    scenario=scenario_config,
    treatment_key=treatment_key,
)

site_display = load_site_display(
    con=con,
    site_id=scenario_config["site_id"],
)


# -----------------------------
# Main tabs
# -----------------------------
tab_site, tab_management, tab_advanced, tab_results, tab_debug = st.tabs(
    [
        "Site",
        "Management",
        "Advanced crop parameters",
        "Results",
        "Debug",
    ]
)


with tab_site:
    st.subheader("Site properties")

    st.caption(
        "These values are loaded from the validation database, but can be changed "
        "for educational scenario exploration."
    )

    current_soil_id = str(site_display.get("soil_id", "Loamy"))

    soil_options = ["Sand", "Loamy", "Clay"]
    if current_soil_id not in soil_options:
        soil_options.insert(0, current_soil_id)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Location")
        st.write(str(site_display.get("name", "")))

        soil_id = st.selectbox(
            "Soil type",
            soil_options,
            index=soil_options.index(current_soil_id),
            key=f"soil_id_{widget_key}",
        )

        sample_depth_cm = st.number_input(
            "Sample depth (cm)",
            value=float(site_display.get("sample_depth_cm")),
            min_value=1.0,
            max_value=100.0,
            step=1.0,
            key=f"sample_depth_{widget_key}",
        )

    with col2:
        st.markdown("### Soil chemistry")

        om_percent = st.number_input(
            "Organic matter (%)",
            value=float(site_display.get("OM_percent")),
            min_value=0.0,
            max_value=30.0,
            step=0.1,
            key=f"om_{widget_key}",
        )

        ph = st.number_input(
            "pH",
            value=float(site_display.get("pH")),
            min_value=3.0,
            max_value=10.0,
            step=0.1,
            key=f"ph_{widget_key}",
        )

    with col3:
        st.markdown("### Nitrogen initialisation")

        cn_ratio = st.number_input(
            "C/N ratio",
            value=float(site_display.get("CN_ratio")),
            min_value=1.0,
            max_value=50.0,
            step=0.5,
            key=f"cn_{widget_key}",
        )

        initial_n = st.number_input(
            "Initial mineral N at sowing (kg N/ha)",
            value=float(scenario_config["initial_mineral_n_kg_ha"]),
            min_value=0.0,
            step=5.0,
            key=f"initial_n_{widget_key}",
        )

        initial_no3_fraction = st.number_input(
            "NO₃ fraction of initial mineral N",
            value=float(scenario_config["initial_no3_fraction"]),
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=f"initial_no3_fraction_{widget_key}",
        )

    site_overrides = {
        "soil_id": soil_id,
        "OM_percent": float(om_percent),
        "CN_ratio": float(cn_ratio),
        "pH": float(ph),
        "sample_depth_cm": float(sample_depth_cm),
    }

    with st.expander("Site values sent to the API"):
        st.json(site_overrides)


with tab_management:
    st.subheader("Management")

    col1, col2 = st.columns(2)

    with col1:
        sowing_date = st.date_input(
            "Sowing / start date",
            value=pd.to_datetime(potato_inputs["sowing_date"]).date(),
            key=f"sowing_date_{widget_key}",
        )

    with col2:
        harvest_date = st.date_input(
            "Harvest / end date",
            value=pd.to_datetime(potato_inputs["harvest_date"]).date(),
            key=f"harvest_date_{widget_key}",
        )

    st.markdown("### Fertilizer events")

    fertilizer_df = pd.DataFrame(potato_inputs["fertilizer_events"])

    if fertilizer_df.empty:
        fertilizer_df = pd.DataFrame(
            columns=["date", "product_id", "kg_product_per_ha"]
        )

    edited_fertilizer_df = st.data_editor(
        fertilizer_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"fertilizer_{widget_key}",
    )

    st.markdown("### Irrigation events")

    st.caption(
        "These are the irrigation events generated in the validation output. "
        "For the education demo they are fixed editable events."
    )

    irrigation_df = pd.DataFrame(potato_inputs["irrigation_events"])

    if irrigation_df.empty:
        irrigation_df = pd.DataFrame(columns=["date", "mm"])

    edited_irrigation_df = st.data_editor(
        irrigation_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"irrigation_{widget_key}",
    )


with tab_advanced:
    st.subheader("Advanced crop parameters")

    enable_advanced = st.checkbox("Enable crop parameter editing")

    if enable_advanced:
        st.warning(
            "The UI can already collect these crop parameters, but the deployed API "
            "must still support crop_overrides before they can affect the model run."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            tbase = st.number_input("Tbase", value=4.0)
            tsum = st.number_input("Tsum", value=1300.0)

        with col2:
            i50a = st.number_input("I50a", value=300.0)
            i50b = st.number_input("I50b", value=500.0)

        with col3:
            rue = st.number_input("RUE", value=1.6)
            n_uptake_a = st.number_input("N_uptake_a", value=61.0)

        with col4:
            n_uptake_b = st.number_input("N_uptake_b", value=0.44)
            n_dilution_fmin = st.number_input("N_dilution_fmin", value=0.35)

    else:
        st.info("Advanced crop parameters are hidden. The model uses default crop catalog values.")


with tab_results:
    st.subheader("Results")

    if run_button:
        st.info(
            "Running ARVIOR with validation-style warm-up: "
            "30 days before sowing → inject initial mineral N → sowing-to-harvest run."
        )

        try:
            sowing_date_str = sowing_date.isoformat()
            harvest_date_str = harvest_date.isoformat()

            warmup_start = (
                pd.to_datetime(sowing_date_str)
                - pd.Timedelta(days=int(scenario_config["warmup_days"]))
            ).date().isoformat()

            warmup_end = (
                pd.to_datetime(sowing_date_str)
                - pd.Timedelta(days=1)
            ).date().isoformat()

            fertilizer_events_raw = edited_fertilizer_df.to_dict(orient="records")
            irrigation_events_raw = edited_irrigation_df.to_dict(orient="records")

            fertilizer_events = [
                {
                    "date": str(e["date"]),
                    "product_id": str(e["product_id"]),
                    "kg_product_per_ha": float(e["kg_product_per_ha"]),
                }
                for e in fertilizer_events_raw
                if pd.notna(e.get("date"))
                and pd.notna(e.get("product_id"))
                and pd.notna(e.get("kg_product_per_ha"))
            ]

            irrigation_events = [
                {
                    "date": str(e["date"]),
                    "mm": float(e["mm"]),
                }
                for e in irrigation_events_raw
                if pd.notna(e.get("date"))
                and pd.notna(e.get("mm"))
            ]

            # -----------------------------
            # API call 1: warm-up
            # -----------------------------
            warmup_request = build_run_request(
                con=con,
                site_id=scenario_config["site_id"],
                crop_id=scenario_config["crop_id"],
                sowing_date=sowing_date_str,
                harvest_date=harvest_date_str,
                window_start=warmup_start,
                window_end=warmup_end,
                fertilizer_events=fertilizer_events,
                irrigation_events=irrigation_events,
                prev_state=None,
                site_overrides=site_overrides,
            )

            warmup_response = run_arvior(warmup_request)
            warmup_state = warmup_response["next_state"]

            # -----------------------------
            # Inject initial N at sowing
            # -----------------------------
            season_prev_state, init_n_debug = inject_initial_mineral_n(
                prev_state=warmup_state,
                nmin_kg_ha=float(initial_n),
                no3_fraction=float(initial_no3_fraction),
            )

            # -----------------------------
            # API call 2: sowing to harvest
            # -----------------------------
            season_request = build_run_request(
                con=con,
                site_id=scenario_config["site_id"],
                crop_id=scenario_config["crop_id"],
                sowing_date=sowing_date_str,
                harvest_date=harvest_date_str,
                window_start=sowing_date_str,
                window_end=harvest_date_str,
                fertilizer_events=fertilizer_events,
                irrigation_events=irrigation_events,
                prev_state=season_prev_state,
                site_overrides=site_overrides,
            )

            season_response = run_arvior(season_request)

            season_df = pd.DataFrame(season_response["df"])
            season_df = add_days_after_sowing(
                season_df,
                sowing_date=sowing_date_str,
            )

            st.session_state["last_warmup_request"] = warmup_request
            st.session_state["last_warmup_response"] = warmup_response
            st.session_state["last_season_request"] = season_request
            st.session_state["last_season_response"] = season_response
            st.session_state["last_season_df"] = season_df
            st.session_state["last_init_n_debug"] = init_n_debug

            st.session_state["last_irrigation_events"] = irrigation_events
            st.session_state["last_crop_id"] = scenario_config["crop_id"]
            st.session_state["last_treatment_key"] = treatment_key
            st.session_state["last_run_label"] = f"{scenario_name} — {treatment_key}"

            st.success("ARVIOR run completed successfully.")

        except Exception as exc:
            st.error("The ARVIOR scenario run failed.")
            st.exception(exc)

    if "last_season_df" in st.session_state:
        st.caption(
            f"Showing latest completed run: "
            f"{st.session_state.get('last_run_label', '')}"
        )

        render_model_results(
            season_df=st.session_state["last_season_df"],
            irrigation_events=st.session_state.get("last_irrigation_events", []),
            crop_id=st.session_state.get("last_crop_id", scenario_config["crop_id"]),
            treatment_key=st.session_state.get("last_treatment_key", treatment_key),
        )
    else:
        st.info("Choose a scenario and click 'Run ARVIOR' in the sidebar.")


with tab_debug:
    st.subheader("Debug information")

    st.write("Selected scenario:", scenario_name)
    st.write("Selected treatment:", treatment_key)
    st.write("Scenario config:", scenario_config)
    st.write("Treatment config:", treatment_config)
    st.markdown("### Site overrides")
    st.json(site_overrides)

    st.markdown("### Edited fertilizer table")
    st.dataframe(edited_fertilizer_df, use_container_width=True)

    st.markdown("### Edited irrigation table")
    st.dataframe(edited_irrigation_df, use_container_width=True)

    if "last_init_n_debug" in st.session_state:
        with st.expander("Initial N injection debug"):
            st.json(st.session_state["last_init_n_debug"])

    if "last_warmup_request" in st.session_state:
        with st.expander("Last warm-up request"):
            st.json(st.session_state["last_warmup_request"])

    if "last_warmup_response" in st.session_state:
        with st.expander("Last warm-up response"):
            st.json(st.session_state["last_warmup_response"])

    if "last_season_request" in st.session_state:
        with st.expander("Last season request"):
            st.json(st.session_state["last_season_request"])

    if "last_season_response" in st.session_state:
        with st.expander("Last season response"):
            st.json(st.session_state["last_season_response"])