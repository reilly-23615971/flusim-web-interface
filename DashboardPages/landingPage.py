# Flusim Web Interface Application
# Developed by Reilly Evans
# Main page for the application

# Imports
import streamlit as st

# Create page
st.title("Flusim Infection Model Dashboard")

st.markdown("""
    The SMRG Flusim model, developed by the Software Modelling Research Group
    at the University of Western Australia, implements a high-performance
    agent-based simulation model to simulate the spread of infectious disease
    in a population. This model has been used to aid in deciding effective
    policy for respiratory viruses such as influenza
    [[1](https://doi.org/10.1586/eri.10.136)]
    and COVID-19 [[2](https://doi.org/10.1101/2022.03.09.22272170)]. This website
    allows users to easily run the model with specific parameters and visualise
    the results.
    """)

st.header("Usage")
# TODO: Update usage instructions (or just refer to manual)
# TODO: Replace buttons with proper st.link_buttons

st.markdown("""
    - Use the sidebar on the left of the screen to navigate between the different
    pages. (If you can't see the sidebar, click the
    :material/keyboard_double_arrow_right: button at the top-left of the page
    to make it visible.)
    - Visit the :grey-badge[:material/variable_insert: Baseline Parameters] page
    to change the parameters used by all simulations, or visit the
    :grey-badge[:material/variable_add: Scenario Parameters] page to specify
    multiple parameter sets to run at the same time.
    """)
st.page_link(
    "DashboardPages/baselineParameters.py",
    label="Go to Baseline Parameters",
    icon=":material/variable_insert:",
)
st.page_link(
    "DashboardPages/scenarioParameters.py",
    label="Go to Scenario Parameters",
    icon=":material/variable_add:",
)

st.markdown("""
    - Click the :primary-badge[:material/motion_play: Run Simulation] button in
    the sidebar to run the simulation.
    - Once you've ran a simulation, visit the
    :grey-badge[:material/chart_data: Infection Over Time Graphs] and
    :grey-badge[:material/table_chart_view: Health Burden Tables] pages
    to visualise the results of the simulation.
    """)

st.page_link(
    "DashboardPages/infectionOverTimeGraphs.py",
    label="Go to Infection Curves",
    icon=":material/chart_data:",
)
st.page_link(
    "DashboardPages/healthBurdenTables.py",
    label="Go to Health Burden Tables",
    icon=":material/table_chart_view:",
)
