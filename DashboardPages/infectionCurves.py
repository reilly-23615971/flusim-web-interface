# Flusim Web Interface Application
# Developed by Reilly Evans
# Page for displaying line graphs of infection over time

# Imports
import logging
import time
from typing import Optional

import streamlit as st

from ClientResources.ParameterFunctions import loadKey, saveKey
from ClientResources.SharedResources import (
    presetCommunity,
    presetDataPaths,
    presetScenarioNames,
    usePresetData,
)
from ClientResources.VisualisationFunctions import formatEpidemic, plotEpidemic

# Logging
graphLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Function to generate graph
def generateGraph():
    """
    Function to generate an infection curve with simulation data.

    Raises:
        FileNotFoundError: If there is no data to generate a graph with.
    """
    # Throw error if no data is present
    if not usePresetData and session.get("modelDataEpidemicDaily") is None:
        raise FileNotFoundError("""
            No simulation epidemic data was available to plot; please run a
            simulation before attempting to generate a table.
        """)

    chartType = session.get("chartType", "Cumulative")

    # Debug code for loading data in testing
    if usePresetData:
        # Set default session_state params
        scenarioNames = presetScenarioNames
        simParams = {
            "Community": presetCommunity,
            "Scenario Names": scenarioNames,
            "Scaling Factor": session.get("scalingPopulation", 272407) / 272407,
        }
        session.SimParams = simParams
        # Load test data from file
        with open(presetDataPaths[chartType], "rb") as csv:
            epidemicData = formatEpidemic(
                csv.read(),
                scenarioNames,
                cumulative=chartType == "Cumulative",
            )
    # Load data from session_state
    else:
        scenarioNames = session.SimParams["Scenario Names"]
        dataVarName = "Cumulative" if chartType == "Cumulative" else "Daily"
        epidemicData = session.get(f"modelDataEpidemic{dataVarName}")

    scenariosUsed = session.get("chartScenariosToUse", scenarioNames)
    graphLog.info(f"""
        [generateGraph] Formatting epidemic data using the scenarios
        {scenariosUsed} and the data type {chartType}
    """)
    assert epidemicData is not None, "Epidemic data was not defined"
    chartData = plotEpidemic(
        epidemicData,
        includedScenarios=scenariosUsed,
        cumulative=chartType == "Cumulative",
    )

    # Save the generated graph
    session.InfectionChartData = chartData
    session.ChartGenerated = True


st.title("Infection Curves")

st.markdown("""
    Here you can generate line graphs plotting infection rates over
    time for different scenarios in the most recently run simulation.
""")

# Check if there is data to tabulate
chartErrorContainer = st.container()
currentDataExists = usePresetData or session.get("modelDataAsirFull") is not None
if not currentDataExists:
    chartErrorContainer.warning(
        """
        No simulation data has been generated. Click
        :primary-badge[:material/motion_play: Run Simulation] in the
        sidebar to run a simulation and obtain the data necessary to
        generate a graph.
    """,
        icon=":material/science_off:",
    )
if currentDataExists and session.simulationInProgress:
    chartErrorContainer.warning(
        """
        Warning: A new simulation is currently in progress. Since the
        data is not yet ready to process, attempting to create a graph
        now will use the data from the previous simulation. Once the
        in-progress simulation is complete, it will not be possible to
        generate graphs with the previous simulation's data, though the
        current graph will still be available to view and download
        until you generate a new graph.
    """,
        icon=":material/av_timer:",
    )


graphSettings = st.expander("Graph Settings")
with graphSettings:
    st.markdown("""
        Use these parameters to configure how the infection curves will be generated.
        Hover your mouse over the :material/help: help icon next to a
        setting's input field to show an explanation of what that setting
        does. Hover your mouse over any buttons to show an explanation of
        what that button does.
    """)

    loadKey("chartType", default="Cumulative")
    chartType = st.selectbox(
        "Chart Type",
        ["Cumulative", "Daily Rate"],
        index=0,
        key="_chartType",
        on_change=saveKey,
        args=["chartType"],
        kwargs={"notScenario": True},
        placeholder="Please select a data format",
        help="""
Select what kind of data should be displayed in the graph.

### Options:
- Cumulative: the chart will plot the total number of
infections that have cumulatively occurred at each point of
the simulation.
- Daily Rate: the chart will plot the number of infections
that occur in each day of the simulation.
        """,
    )

    # Scenario selection
    simParams = session.get("SimParams", {})
    scenarioNames = simParams.get("Scenario Names", presetScenarioNames)
    if currentDataExists:
        loadKey("chartScenariosToUse", default=scenarioNames)
        scenariosToUse: Optional[list[str]] = st.multiselect(
            "Scenarios to Include in Graph",
            scenarioNames,
            default=scenarioNames,
            key="_chartScenariosToUse",
            on_change=saveKey,
            args=["chartScenariosToUse"],
            placeholder="Please select at least 1 scenario",
            kwargs={"notScenario": True},
            help="""
Select which scenarios should be included in the table.
You may select as many scenarios as you wish, but you
must select at least one. Each scenario will be plotted onto the graph
as its own line, showing the infections over time for that scenario.
            """,
        )
        if not scenariosToUse:
            chartErrorContainer.error(
                """
            Error: No scenarios have been included in the graph. If you
            attempt to generate the graph now, it will be empty. Please
            select at least one scenario to include with the 'Scenarios
            to Use' setting.
        """,
                icon=":material/tab_unselected:",
            )
    else:
        st.info(
            """
            No simulation data has been generated, so there are
            currently no scenarios to select. Click
            :primary-badge[:material/motion_play: Run Simulation] in
            the sidebar to run a simulation and obtain the data
            necessary to generate a graph.
        """,
            icon=":material/tab_unselected:",
        )
        scenariosToUse = None


# Button to generate the graph
st.button(
    label="Create Infection Curves",
    icon=":material/chart_data:",
    key="generateGraph",
    type="primary",
    on_click=generateGraph,
    disabled=not (currentDataExists or scenariosToUse),
    help=(
        """
Use the data from the last simulation to generate a graph
displaying the infections in the simulation, formatted using
the settings selected above.
        """
        if currentDataExists
        else """
No simulations have completed yet, so there is no data to plot.
        """
    ),
)

# Display the graph itself
# TODO: Graph is laggy; see if performance can be improved
chartData = session.get("InfectionChartData")
if chartData is not None:
    st.header("Flusim Infection Curves")
    st.altair_chart(chartData)

    @st.fragment()
    def infectionDataDownload():
        """
        Fragment function to show a button that downloads the data in the chart.
        """
        chartTypeTag = "Cumulative" if chartType == "Cumulative" else "Daily"
        dataToDownload = session.get(f"modelDataEpidemic{chartTypeTag}")
        if dataToDownload is not None:
            st.download_button(
                "Download Infection Data",
                dataToDownload.to_csv(index=False),
                f"FlusimInfectionData{chartTypeTag}_{
                    time.strftime('%Y.%m.%d_%I.%M.%S%p')
                }.csv",
                mime="text/csv",
                key="infectionDataDownload",
                icon=":material/download:",
                help="""
Download the infection data from the most recent
simulation (the data used by the above graph) as a CSV
file. Note that all scenarios are included in the
returned file, even if not all were selected for the
graph.
                """,
            )
        elif usePresetData:
            with open(presetDataPaths[chartType], "rb") as csv:
                epidemicData = formatEpidemic(
                    csv.read(), scenarioNames, cumulative=chartType == "Cumulative"
                )
            st.download_button(
                "Download Infection Data",
                epidemicData.to_csv(index=False),
                f"FlusimInfectionData{chartTypeTag}_{
                    time.strftime('%Y.%m.%d_%I.%M.%S%p')
                }.csv",
                mime="text/csv",
                key="infectionDataDownload",
                icon=":material/download:",
                help="""
Download the infection data from the most recent
simulation (the data used by the above graph) as a CSV
file. Note that all scenarios are included in the
returned file, even if not all were selected for the
graph.
                """,
            )
        else:
            st.error(
                """
            Error: The data used by the graph was empty or could not be
            accessed. Please try regenerating the graph or rerunning
            the simulation to fix the issue.
        """,
                icon=":material/error:",
            )

    infectionDataDownload()
