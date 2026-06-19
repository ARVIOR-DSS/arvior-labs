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

    st.info(
        "For this first version, the site properties are loaded from the validation database. "
        "In the next step we will make these values editable."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Site", str(site_display.get("name", "")))
        st.metric("Soil type", str(site_display.get("soil_id", "")))

    with col2:
        st.metric("Organic matter (%)", f"{float(site_display.get('OM_percent')):.2f}")
        st.metric("C/N ratio", f"{float(site_display.get('CN_ratio')):.1f}")

    with col3:
        st.metric("pH", f"{float(site_display.get('pH')):.1f}")
        st.metric("Sample depth (cm)", f"{float(site_display.get('sample_depth_cm')):.0f}")

    st.markdown("### Initial mineral N")
    col4, col5 = st.columns(2)

    with col4:
        initial_n = st.number_input(
            "Initial mineral N at sowing (kg N/ha)",
            value=float(scenario_config["initial_mineral_n_kg_ha"]),
            min_value=0.0,
            step=5.0,
        )

    with col5:
        initial_no3_fraction = st.number_input(
            "NO₃ fraction of initial mineral N",
            value=float(scenario_config["initial_no3_fraction"]),
            min_value=0.0,
            max_value=1.0,
            step=0.05,
        )


with tab_management:
    st.subheader("Management")

    col1, col2 = st.columns(2)

    with col1:
        sowing_date = st.date_input(
            "Sowing / start date",
            value=pd.to_datetime(potato_inputs["sowing_date"]).date(),
        )

    with col2:
        harvest_date = st.date_input(
            "Harvest / end date",
            value=pd.to_datetime(potato_inputs["harvest_date"]).date(),
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
        key=f"fertilizer_{scenario_name}_{treatment_key}",
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
        key=f"irrigation_{scenario_name}_{treatment_key}",
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

            st.success("ARVIOR run completed successfully.")

            # -----------------------------
            # Summary metrics
            # -----------------------------
            final_row = season_df.iloc[-1]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if "Biomass_actual_cum" in season_df.columns:
                    st.metric(
                        "Final biomass",
                        f"{float(final_row['Biomass_actual_cum']):.2f}",
                    )

            with col2:
                if "Yield_dm" in season_df.columns:
                    st.metric(
                        "Yield DM",
                        f"{float(final_row['Yield_dm']):.2f}",
                    )

            with col3:
                if "N_cum_actual" in season_df.columns:
                    st.metric(
                        "N uptake",
                        f"{float(final_row['N_cum_actual']):.1f} kg N/ha",
                    )

            with col4:
                total_irrigation = sum(e["mm"] for e in irrigation_events)
                st.metric(
                    "Total irrigation",
                    f"{total_irrigation:.0f} mm",
                )

            # -----------------------------
            # Plot: biomass
            # -----------------------------
            biomass_cols = [
                col for col in ["Biomass_actual_cum", "Biomass_pot_cum"]
                if col in season_df.columns
            ]

            if biomass_cols:
                fig = px.line(
                    season_df,
                    x="DAS",
                    y=biomass_cols,
                    labels={
                        "DAS": "Days after sowing",
                        "value": "Biomass",
                        "variable": "Variable",
                    },
                    title="Biomass development from sowing to harvest",
                )
                st.plotly_chart(fig, use_container_width=True)

            # -----------------------------
            # Plot: N uptake
            # -----------------------------
            n_cols = [
                col for col in ["N_cum_actual", "N_cum_potential"]
                if col in season_df.columns
            ]

            if n_cols:
                fig_n = px.line(
                    season_df,
                    x="DAS",
                    y=n_cols,
                    labels={
                        "DAS": "Days after sowing",
                        "value": "N uptake (kg N/ha)",
                        "variable": "Variable",
                    },
                    title="Cumulative nitrogen uptake",
                )
                st.plotly_chart(fig_n, use_container_width=True)

            # -----------------------------
            # Plot: water and N stress
            # -----------------------------
            stress_cols = [
                col for col in ["ks", "N_stress_factor", "f_salinity"]
                if col in season_df.columns
            ]

            if stress_cols:
                fig_stress = px.line(
                    season_df,
                    x="DAS",
                    y=stress_cols,
                    labels={
                        "DAS": "Days after sowing",
                        "value": "Stress factor (1 = no stress)",
                        "variable": "Variable",
                    },
                    title="Water, nitrogen and salinity stress factors",
                )
                st.plotly_chart(fig_stress, use_container_width=True)

            # -----------------------------
            # Plot: rain and irrigation
            # -----------------------------
            water_input_cols = [
                col for col in ["P", "Irrigation"]
                if col in season_df.columns
            ]

            if water_input_cols:
                fig_water = px.bar(
                    season_df,
                    x="DAS",
                    y=water_input_cols,
                    labels={
                        "DAS": "Days after sowing",
                        "value": "Water input (mm/day)",
                        "variable": "Variable",
                    },
                    title="Rainfall and irrigation",
                )
                st.plotly_chart(fig_water, use_container_width=True)

            with st.expander("Available output columns"):
                st.write(list(season_df.columns))

            csv = season_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download season output CSV",
                data=csv,
                file_name=f"{scenario_config['crop_id']}_{treatment_key}_season_output.csv",
                mime="text/csv",
            )

        except Exception as exc:
            st.error("The ARVIOR scenario run failed.")
            st.exception(exc)

    else:
        st.info("Choose a scenario and click 'Run ARVIOR' in the sidebar.")


with tab_debug:
    st.subheader("Debug information")

    st.write("Selected scenario:", scenario_name)
    st.write("Selected treatment:", treatment_key)
    st.write("Scenario config:", scenario_config)
    st.write("Treatment config:", treatment_config)

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