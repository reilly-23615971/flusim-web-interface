# Flusim Web Interface Application
# Developed by Reilly Evans
# Page describing the Flusim model itself (and potentially other info)

# Imports
import streamlit as st

# Create page
st.title("Flusim Disease Model Dashboard")

st.markdown(
    """
    The SMRG Flusim model, developed by the Software Modelling Research Group
    at the University of Western Australia, implements a high-performance
    agent-based simulation model to simulate the spread of infectious disease
    in a population. This model has been used to aid in deciding effective
    policy for diseases such as influenza [[1](https://doi.org/10.1586/eri.10.136)]
    and COVID-19 [[2](https://doi.org/10.1101/2022.03.09.22272170)]. This website
    allows users to easily run the model with specific parameters and visualise
    the results.
    """
)

st.header("Usage")

st.markdown(
    """
    - Use the sidebar on the left of the screen to navigate between the different
    pages. (If you can't see the sidebar, click the
    :material/keyboard_double_arrow_right: button at the top-left of the page
    to make it visible.)
    - Visit the :grey-badge[:material/variable_insert: Baseline Parameters] page
    to change the parameters used by all simulations, or visit the
    :grey-badge[:material/variable_add: Scenario Parameters] page to specify
    multiple parameter sets to run at the same time.
    """
)

if st.button("Go to Baseline Parameters", icon=":material/variable_insert:"):
    st.switch_page(
        st.Page(
            "DashboardPages/baselineParameters.py",
            title="Baseline Parameters",
            icon=":material/variable_insert:",
        )
    )
if st.button("Go to Scenario Parameters", icon=":material/variable_add:"):
    st.switch_page(
        st.Page(
            "DashboardPages/scenarioParameters.py",
            title="Scenario Parameters",
            icon=":material/variable_add:",
        )
    )

st.markdown(
    """
    - Click the :primary-badge[:material/motion_play: Run Simulation] button in
    the sidebar to run the simulation.
    - Once you've ran a simulation, visit the
    :grey-badge[:material/chart_data: Infection Over Time Graphs] and
    :grey-badge[:material/table_chart_view: Health Burden Tables] pages
    to visualise the results of the simulation.
    """
)

if st.button("Go to Infection Over Time Graphs", icon=":material/chart_data:"):
    st.switch_page(
        st.Page(
            "DashboardPages/infectionOverTimeGraphs.py",
            title="Infection Over Time Graphs",
            icon=":material/chart_data:",
        )
    )
if st.button("Go to Health Burden Tables", icon=":material/table_chart_view:"):
    st.switch_page(
        st.Page(
            "DashboardPages/healthBurdenTables.py",
            title="Health Burden Tables",
            icon=":material/table_chart_view:",
        )
    )

st.header("Model Details")

st.markdown(
    """

    The *Flusim* simulation model is designed to be a lifelike simulation of
    respiratory disease mechanics in Australia. As an individual-based model,
    it simulates each individual in the population as a distinct agent, which
    moves to different locations over the course of the simulation. Individuals
    are assigned demographics such as age and pregnancy status; these affect
    which locations they go to, what interventions apply to them and how
    susceptible they are to the disease.

    When an individual is infected by the disease, the current stage of their
    infection is tracked alongside them. As the simulation progresses, the
    individual will go from dormant to infectious and symptomatic before
    eventually recovering. Individuals who have recovered from the disease
    gain an immunity to being reinfected.

    When an infectious individual is in a given location, there is a chance
    that non-immune uninfected individuals in the same location will catch the
    disease. This probability is dependent on the location as well as the
    demographics of both the infected and healthy individuals in the interaction.
    In addition to these interactions, each individual will interact with other
    randomly selected individuals in each step of the simulation. These
    background contacts account for locations that are not simulated directly
    in the simulation, such as shopping centres or sporting events.

    The *Flusim* model is stochastic, so it will run multiple simulations
    for each parameter set. The results of these simulation will be combined
    to obtain the averaged results for the overall set. In this dashboard,
    all visualisations use medians for averaging.
    """
)
