# Flusim Web Interface Application
# Developed by Reilly Evans
# Page for displaying line graphs of infection over time

# Imports
import logging
import time
from typing import Optional

import streamlit as st

from resources.constants import (
    PRESET_COMMUNITY,
    PRESET_DATA_PATHS,
    PRESET_SCENARIO_NAMES,
    USE_PRESET_DATA,
)
from resources.parameter import load_key, save_key
from resources.types import SimParams
from resources.visualisation import format_epidemic, plot_epidemic

# Logging
graph_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Function to generate graph
def generate_graph():
    """
    Function to generate an infection curve with simulation data.

    Raises:
        FileNotFoundError: If there is no data to generate a graph with.
    """
    # Throw error if no data is present
    if not USE_PRESET_DATA and session.get("model_data_epidemic_daily") is None:
        raise FileNotFoundError(
            "No simulation epidemic data was available to plot; please run a"
            "simulation before attempting to generate a graph."
        )

    chart_type = session.get("chart_type", "Cumulative")

    # Debug code for loading data in testing
    if USE_PRESET_DATA:
        # Set default session_state params
        scenario_names = PRESET_SCENARIO_NAMES
        session.sim_params = SimParams(
            scenario_names=PRESET_SCENARIO_NAMES,
            analysis_formats=[],
            community=PRESET_COMMUNITY,
            scaling_factor=session.get("scaling_population", 272407) / 272407,
        )
        # Load test data from file
        with open(PRESET_DATA_PATHS[chart_type], "rb") as csv:
            epidemic_data = format_epidemic(
                csv.read(),
                scenario_names,
                cumulative=chart_type == "Cumulative",
            )
    # Load data from session_state
    else:
        scenario_names = session.sim_params.scenario_names
        data_categorisation = "cumulative" if chart_type == "Cumulative" else "daily"
        epidemic_data = session.get(f"model_data_epidemic_{data_categorisation}")

    scenarios_used = session.get("chart_scenarios_to_use", scenario_names)
    graph_log.info(
        "[generate_graph] Formatting epidemic data using the scenarios"
        f"{scenarios_used} and the data type {chart_type}"
    )
    assert epidemic_data is not None, "Epidemic data was not defined"
    chart_data = plot_epidemic(
        epidemic_data,
        scenario_names=scenario_names,
        included_scenarios=scenarios_used,
        cumulative=chart_type == "Cumulative",
    )

    # Save the generated graph
    session.infection_chart_data = chart_data
    session.chart_generated = True


st.title("Infection Curves")

st.markdown("""
Here you can generate line graphs plotting infection rates over time for
different scenarios in the most recently run simulation.
""")

# Check if there is data to tabulate
chart_error_container = st.container()
current_data_exists = (
    USE_PRESET_DATA or session.get("model_data_epidemic_daily") is not None
)
if not current_data_exists:
    chart_error_container.warning(
        """
No simulation data has been generated. Click
:primary-badge[:material/motion_play: Run Simulation] in the sidebar to run a
simulation and obtain the data necessary to generate a graph.
        """,
        icon=":material/science_off:",
    )
if current_data_exists and session.simulation_in_progress:
    chart_error_container.warning(
        """
Warning: A new simulation is currently in progress. Since the data is not yet
ready to process, attempting to create a graph now will use the data from the
previous simulation. Once the in-progress simulation is complete, it will not
be possible to generate graphs with the previous simulation's data, though the
current graph will still be available to view and download until you generate a
new graph.
    """,
        icon=":material/av_timer:",
    )


graph_settings = st.expander("Graph Settings")
with graph_settings:
    st.markdown("""
Use these parameters to configure how the infection curves will be generated.
Hover your mouse over the :material/help: help icon next to a setting's input
field to show an explanation of what that setting does. Hover your mouse over
any buttons to show an explanation of what that button does.
    """)

    load_key("chart_type", default="Cumulative")
    chart_type = st.selectbox(
        "Chart Type",
        ["Cumulative", "Daily Rate"],
        index=0,
        key="_chart_type",
        on_change=save_key,
        args=["chart_type"],
        kwargs={"not_scenario": True},
        placeholder="Please select a data format",
        help="""
Select what kind of data should be displayed in the graph.

### Options:
- Cumulative: the chart will plot the total number of infections that have
cumulatively occurred at each point of the simulation.
- Daily Rate: the chart will plot the number of infections that occur in each
day of the simulation.
        """,
    )

    # Scenario selection
    sim_params: SimParams = session.get(
        "sim_params",
        SimParams(
            scenario_names=PRESET_SCENARIO_NAMES,
            analysis_formats=[],
            community=PRESET_COMMUNITY,
        ),
    )
    scenario_names = sim_params.scenario_names
    if current_data_exists:
        load_key("chart_scenarios_to_use", default=scenario_names)
        scenarios_to_use: Optional[list[str]] = st.multiselect(
            "Scenarios to Include in Graph",
            scenario_names,
            default=scenario_names,
            key="_chart_scenarios_to_use",
            on_change=save_key,
            args=["chart_scenarios_to_use"],
            placeholder="Please select at least 1 scenario",
            kwargs={"not_scenario": True},
            help="""
Select which scenarios should be included in the table. You may select as many
scenarios as you wish, but you must select at least one. Each scenario will be
plotted onto the graph as its own line, showing the infections over time for
that scenario.
            """,
        )
        if not scenarios_to_use:
            chart_error_container.error(
                """
Error: No scenarios have been included in the graph. If you attempt to generate
the graph now, it will be empty. Please select at least one scenario to include
with the 'Scenarios to Use' setting.
                """,
                icon=":material/tab_unselected:",
            )
    else:
        st.info(
            """
No simulation data has been generated, so there are currently no scenarios to
select. Click :primary-badge[:material/motion_play: Run Simulation] in the
sidebar to run a simulation and obtain the data necessary to generate a graph.
        """,
            icon=":material/tab_unselected:",
        )
        scenarios_to_use = None


# Button to generate the graph
st.button(
    label="Create Infection Curves",
    icon=":material/chart_data:",
    key="generate_graph",
    type="primary",
    on_click=generate_graph,
    disabled=not (current_data_exists or scenarios_to_use),
    help=(
        """
Use the data from the last simulation to generate a graph displaying the
infections in the simulation, formatted using the settings selected above.
        """
        if current_data_exists
        else "No simulations have completed yet, so there is no data to plot."
    ),
)

# Display the graph itself
# TODO: Clicking on the legend is no longer a thing; update the manual
chart_data = session.get("infection_chart_data")
if chart_data is not None:
    st.header("Flusim Infection Curves")
    st.altair_chart(chart_data)

    @st.fragment()
    def infection_data_download():
        """
        Fragment function to show a button that downloads the data in the chart.
        """
        chart_type_tag = "cumulative" if chart_type == "Cumulative" else "daily"
        data_to_download = session.get(f"model_data_epidemic_{chart_type_tag}")
        if data_to_download is not None:
            st.download_button(
                "Download Infection Data",
                data_to_download.to_csv(index=False),
                f"FlusimInfectionData{chart_type_tag}_{
                    time.strftime('%Y.%m.%d_%I.%M.%S%p')
                }.csv",
                mime="text/csv",
                key="infection_data_download",
                icon=":material/download:",
                help="""
Download the infection data from the most recent simulation (the data used by
the above graph) as a CSV file. Note that all scenarios are included in the
returned file, even if not all were selected for the graph.
                """,
            )
        elif USE_PRESET_DATA:
            with open(PRESET_DATA_PATHS[chart_type], "rb") as csv:
                epidemic_data = format_epidemic(
                    csv.read(), scenario_names, cumulative=chart_type == "Cumulative"
                )
            st.download_button(
                "Download Infection Data",
                epidemic_data.to_csv(index=False),
                f"FlusimInfectionData{chart_type_tag}_{
                    time.strftime('%Y.%m.%d_%I.%M.%S%p')
                }.csv",
                mime="text/csv",
                key="infection_data_download",
                icon=":material/download:",
                help="""
Download the infection data from the most recent simulation (the data used by
the above graph) as a CSV file. Note that all scenarios are included in the
returned file, even if not all were selected for the graph.
                """,
            )
        else:
            st.error(
                """
Error: The data used by the graph was empty or could not be accessed. Please
try regenerating the graph or rerunning the simulation to fix the issue.
                """,
                icon=":material/error:",
            )

    infection_data_download()
