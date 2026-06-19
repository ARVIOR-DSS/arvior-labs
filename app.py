import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api_client import check_api_health


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

scenario = st.sidebar.selectbox(
    "Scenario",
    [
        "Potato — Changins 2011",
        "Production grassland — 2010",
        "Maize — Gatton 1999",
    ],
)

treatment = st.sidebar.selectbox(
    "Treatment",
    [
        "Default",
        "Low N",
        "Medium N",
        "High N",
    ],
)

run_button = st.sidebar.button("Run ARVIOR", type="primary")

st.sidebar.markdown("---")

if st.sidebar.button("Check API connection"):
    ok, message = check_api_health()

    if ok:
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)

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

    col1, col2, col3 = st.columns(3)

    with col1:
        soil_type = st.selectbox("Soil type", ["Sand", "Loamy", "Clay"])
        om = st.number_input("Organic matter (%)", value=2.3, min_value=0.0, max_value=30.0)

    with col2:
        ph = st.number_input("pH", value=7.4, min_value=3.0, max_value=10.0)
        cn = st.number_input("C/N ratio", value=10.0, min_value=1.0, max_value=50.0)

    with col3:
        sample_depth = st.number_input("Sample depth (cm)", value=20, min_value=1, max_value=100)
        initial_n = st.number_input("Initial mineral N (kg N/ha)", value=60.0, min_value=0.0)


with tab_management:
    st.subheader("Management")

    col1, col2 = st.columns(2)

    with col1:
        sowing_date = st.date_input("Sowing / start date")
    with col2:
        harvest_date = st.date_input("Harvest / end date")

    st.markdown("### Fertilizer events")

    fertilizer_df = pd.DataFrame(
        [
            {"date": "2011-04-12", "product_id": "Ammonium Nitrate", "kg_N_ha_equiv": 80.0},
            {"date": "2011-04-28", "product_id": "Ammonium Nitrate", "kg_N_ha_equiv": 40.0},
        ]
    )

    edited_fertilizer_df = st.data_editor(
        fertilizer_df,
        num_rows="dynamic",
        use_container_width=True,
    )

    st.markdown("### Irrigation events")

    irrigation_df = pd.DataFrame(
        [
            {"date": "2011-04-26", "mm": 30.0},
            {"date": "2011-05-11", "mm": 30.0},
            {"date": "2011-05-30", "mm": 30.0},
            {"date": "2011-07-02", "mm": 30.0},
        ]
    )

    edited_irrigation_df = st.data_editor(
        irrigation_df,
        num_rows="dynamic",
        use_container_width=True,
    )


with tab_advanced:
    st.subheader("Advanced crop parameters")

    enable_advanced = st.checkbox("Enable crop parameter editing")

    if enable_advanced:
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

        st.info("These parameters will later be sent to the API as crop_overrides.")
    else:
        st.info("Advanced crop parameters are hidden. The model will use the default crop catalog values.")


with tab_results:
    st.subheader("Results")

    if run_button:
        st.success("Test run completed. In the next step, this button will call the ARVIOR API.")

        # Temporary fake result data, only to test the interface and plotting.
        demo_df = pd.DataFrame(
            {
                "date": pd.date_range("2011-04-01", periods=120, freq="D"),
                "Biomass_actual_cum": [i * 0.08 for i in range(120)],
                "Biomass_pot_cum": [i * 0.10 for i in range(120)],
            }
        )

        fig = px.line(
            demo_df,
            x="date",
            y=["Biomass_actual_cum", "Biomass_pot_cum"],
            labels={
                "value": "Biomass (t DM/ha)",
                "date": "Date",
                "variable": "Variable",
            },
            title="Biomass development",
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Choose a scenario and click 'Run ARVIOR' in the sidebar.")


with tab_debug:
    st.subheader("Debug information")

    st.write("Selected scenario:", scenario)
    st.write("Selected treatment:", treatment)

    st.markdown("### Edited fertilizer table")
    st.dataframe(edited_fertilizer_df, use_container_width=True)

    st.markdown("### Edited irrigation table")
    st.dataframe(edited_irrigation_df, use_container_width=True)