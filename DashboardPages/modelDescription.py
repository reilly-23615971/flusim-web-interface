# Flusim Web Interface Application
# Developed by Reilly Evans
# Page describing the Flusim model and its parameters

# Imports
import streamlit as st

from ParameterTabs.diseaseParams import diseaseDescribe

# Store st.session_state as variable for efficiency
session = st.session_state

# Create page
st.title("Model Description")
st.markdown("""
    This page provides an overview of how the *Flusim* model operates and what parameters it utilises.
""")


st.subheader("Model Overview")
st.markdown("""
    The *Flusim* simulation model is designed to be a lifelike simulation of
    respiratory disease mechanics in Australia. As an individual-based model,
    it simulates each individual in the population as a distinct agent, which
    moves to different locations over the course of the simulation.

    Time in the simulation is separated into intervals called cycles. Each day
    of the simulation involves two cycles, one representing the day and one representing the night. In each cycle, the engine updates the locations of
    each individual in the community, then simulates interactions between people
    in the same location. Additionally, each day cycle is accompanied by the
    background phase, in which individuals across the community are randomly
    paired to interact. These background contacts account for any interactions
    outside of the locations that are built into the simulation, such as those
    that occur on public transport or in shopping centres.
            
    Each individual in the simulation is assigned demographic details determining
    what age group they fall under, whether they are an Indigenous Australian
    and whether they are pregnant. These details affect which locations the
    individual goes to; children will always attend schools while adults go to
    workplaces instead. Demographics also control what interventions apply to
    each person and how susceptible they are to the pathogen.

    Individuals can be infected by the pathogen whenever they interact with another
    individual who is already infected. When an individual is infected by the
    pathogen, the current stage of their infection is tracked alongside their demographic details. As the simulation progresses, the infection will progress
    from a dormant state to being fully infectious and symptomatic before
    eventually disappearing once the individual recovers.

    The *Flusim* model is stochastic, so it will run multiple simulations
    for each parameter set. The results of these simulation will be combined
    to obtain the averaged results for the overall set. In this dashboard,
    all visualisations use medians for averaging.
""")

# TODO: Full parameter templates

st.subheader("Parameter Descriptions")
st.markdown("""
    Below is a description of the different parameters that
    are used to control the behaviour of the simulation.
    To edit the values used for these parameters, visit the
    :primary-badge[:material/variable_insert: Baseline Parameters] page.
""")
errors = session["activeErrors"].get(0, {})
if errors:
    st.warning("""
        There are currently errors present in the parameter values used in the
        simulation. As a result, these descriptions of the parameters may describe
        unintended or invalid behaviour. If you are familiar with the parameters
        on this dashboard, it is recommended that you resolve these errors
        before reading.
    """)
st.page_link(
    "DashboardPages/baselineParameters.py",
    label="Go to Baseline Parameters",
    icon=":material/variable_insert:",
)

# TODO: Engine settings?

showAdvanced = session.get("showAdvanced", False)

# Pathogen Parameters
with st.expander(
    "Pathogen-Related Parameters", expanded=True, icon=":material/coronavirus:"
):
    diseaseDescribe(0, advanced=showAdvanced)

st.markdown("Other parameters coming soon!")
