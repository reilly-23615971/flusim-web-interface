# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where users can generate tables with infection data

# Imports
import logging
import time
from typing import Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import TwoSlopeNorm, to_hex

from ClientResources.InterfaceFunctions import healthOutcomeStore
from ClientResources.ParameterFunctions import idGet, loadKey, replaceTableNA, saveKey
from ClientResources.SharedResources import (
    ageWithTime,
    mutedCodes,
    presetCommunity,
    presetDataPaths,
    presetScenarioNames,
    tableOutcomes,
    usePresetData,
)
from ClientResources.VisualisationFunctions import formatAsir, generateAsir

# Logging
tableLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state
ageGroups = ageWithTime + ["Total"]


def getSlopeNorm(column: pd.Series) -> TwoSlopeNorm:
    """
    Function to generate the slope norm used for table background gradients.

    Parameters:
        column (Series): A series representing the column to make a slope
            norm for.

    Returns:
        TwoSlopeNorm: The slope norm, with the column's minimum and maximum
            values as the minimum and maximum and correction for columns that
            do not cross zero or are homogenous.
    """
    minVal, maxVal = column.min(), column.max()
    return TwoSlopeNorm(
        vcenter=0,
        vmin=(
            -1e-9
            if minVal >= 0 or pd.isna(minVal)
            else minVal - 1e-9 if minVal == maxVal else minVal
        ),
        vmax=(
            1e-9
            if maxVal <= 0 or pd.isna(maxVal)
            else maxVal + 1e-9 if maxVal == minVal else maxVal
        ),
    )


# Function to choose whether dataframe cells should have white or black text
def selectTextColour(colour: str) -> str:
    """
    Function to decide whether cells in a table have black or white text.

    Parameters:
        colour (str): A string representing a hexadecimal RGB colour.

    Returns:
        str: The hexadecimal code for either black (#000000) or white (#ffffff).
    """
    luminosity = (
        0.299 * int(colour[1:3], 16)  # red
        + 0.587 * int(colour[3:5], 16)  # green
        + 0.114 * int(colour[5:], 16)
    )  # blue
    return "#000000" if luminosity > 135 else "#ffffff"


def generateTable() -> None:
    """
    Callback function used to generate and format health burden tables.
    """
    # Throw error if no data is present
    fullData = session.get("modelDataAsirFull")
    if not usePresetData and fullData is None:
        raise FileNotFoundError("""
            No simulation ASIR data was available to plot; please run a
            simulation before attempting to generate a table.
        """)
    # TODO: Fix bug where latest column settings aren't stored
    # (add confirmation to generate table button?
    # Rerun page before running generateTable somehow?)

    # Debug code for loading data in testing
    if usePresetData:
        # Set default session_state params
        useAdvanced = session.get("showAdvanced", False)
        scenarioNames = presetScenarioNames
        healthOutcomeRates, mortalityRates = healthOutcomeStore(
            scenarioNames,
            useAges=useAdvanced,
        )
        simParams = {
            "Community": presetCommunity,
            "Scenario Names": scenarioNames,
            "Health Outcome Rates": healthOutcomeRates,
            "Age-Separated Health Outcome Rates": mortalityRates,
            "Scaling Factor": session.get("scalingPopulation", 272407) / 272407,
            "Asymptomatic Rates": (
                [
                    [
                        1 - idGet("asymptomaticChild", scenarioID, 0.35),
                        1 - idGet("asymptomaticAdult", scenarioID, 0.35),
                    ]
                    for scenarioID in range(4)
                ]
                if useAdvanced
                else [
                    [1 - idGet("asymptomaticAdult", scenarioID, 0.35)] * 2
                    for scenarioID in range(4)
                ]
            ),
        }
        session.SimParams = simParams

        # Load test data from files
        with open(presetDataPaths["ASIR"], "rb") as csv:
            fullData = formatAsir(csv.read(), scenarioNames)
        if presetDataPaths.get("ASIR") is not None:
            with open(presetDataPaths["Vaccinated"], "rb") as csv:
                vaccineData = formatAsir(csv.read(), scenarioNames)
        else:
            vaccineData = None

    # Load data from session_state
    else:
        scenarioNames = session.SimParams["Scenario Names"]
        vaccineData = session.get("modelDataAsirVaccinated")

    ageSeparation = session.get("healthOutcomeAgeSeparation", "Combined")

    healthColumnForm = replaceTableNA(
        session.get(
            "healthColumnForm",
            pd.DataFrame(
                {
                    "Health Burden Outcome": [
                        "Symptomatic Infections",
                        "Symptomatic Infections",
                        "Hospitalisations",
                        "Hospitalisations",
                    ],
                    "Age Groups": [[], [], [], []],
                    "Vaccination Status": ["All", "All", "All", "All"],
                    "Options": [
                        [],
                        ["Percentage", "Difference from Baseline"],
                        [],
                        ["Percentage", "Difference from Baseline"],
                    ],
                },
            ),
        ),
        {
            "Age Groups": [],
            "Vaccination Status": "All",
        },
    )
    columnDetails: list[
        tuple[str, list[str], Literal["All", "Vaccinated", "Unvaccinated"], bool, bool]
    ] = [
        (
            outcome,
            ageGroups if ageGroups else ageWithTime,
            vaccineStatus if vaccineData is not None else "All",
            "Percentage" in options,
            "Difference from Baseline" in options,
        )
        for outcome, ageGroups, vaccineStatus, options in zip(
            healthColumnForm["Health Burden Outcome"],
            healthColumnForm["Age Groups"],
            healthColumnForm["Vaccination Status"],
            healthColumnForm["Options"],
        )
        if outcome
    ]

    """outcomeColumnCount = session.get("healthOutcomeRowCount", 1)
    columnDetails = [
        (
            session.get(f"healthOutcome{colNumber}", "Symptomatic Infections"),
            session.get(f"useBaselineDifference{colNumber}", False),
            session.get(f"useProportion{colNumber}", False),
        )
        for colNumber in range(0, outcomeColumnCount)
    ]"""
    scenariosUsed = session.get("healthOutcomeScenariosToUse", scenarioNames)
    agesUsed = (
        session.get("healthOutcomeAgesToUse", ageGroups)
        if ageSeparation == "By Row"
        else []
    )
    useColour = session.get("colourToggle", True)
    tableLog.info(f"""
        [generateTable] Formatting Asir data using the scenarios
        {scenariosUsed} (of {scenarioNames}), the age groups {agesUsed}
        and the following columns: {columnDetails}'
    """)

    assert fullData is not None, "ASIR data was not defined"
    ageData, columnConfig, percSet, diffSet = generateAsir(
        fullData,
        scenarioNames,
        ageSeparation,
        columnDetails,
        includedScenarios=scenariosUsed,
        includedAges=agesUsed,
        vaccinatedData=vaccineData,
    )

    # Format data according to column type
    # TODO: Is + with baseline difference necessary enough to revive this?
    """formatValues: dict[str, Any] = (
        {column: "{:+.5n}" for column in diffSet - percSet}
        | {column: "{:+.3%}" for column in diffSet & percSet}
        | {column: "{:.3%}" for column in percSet - diffSet}
        | {column: "{:.5n}" for column in set(ageData.columns) - (diffSet | percSet)}
    )"""

    # Create fake index columns
    if agesUsed:
        ageData.rename_axis(index=["Scenario Index", "Age Group Index"], inplace=True)
        ageData.insert(
            0, "Scenario Name", ageData.index.get_level_values("Scenario Index").values
        )
        ageData.insert(
            1, "Age Group", ageData.index.get_level_values("Age Group Index").values
        )

    else:
        ageData.rename_axis("Scenario Index", inplace=True)
        ageData.insert(0, "Scenario Name", ageData.index.to_series())

    # Initialise styler
    ageStyle = ageData.style

    # Colour the index cells
    if useColour:
        # Set default cell colours
        ageStyle.set_properties(
            **{"background-color": "#F7F7F7", "color": "black"}, subset=None
        )
        # Generate and map scenario colour palette
        scenarioColourMap = mutedCodes[: len(scenarioNames)]
        scenarioColourDictionary = {
            scenario: to_hex(scenarioColourMap[index])
            for index, scenario in enumerate(scenarioNames)
        }

        # Apply the colours to the scenario column
        def scenarioColourString(name) -> str:
            """
            Simple function to get colours for scenarios in pandas styling format.

            Parameters:
                name (str): The name of the scenario.

            Returns:
                str: A string that can be used in a pandas `Styler` config to
                    colour table cells according to the colour associated
                    with the scenario.
            """
            colour = scenarioColourDictionary[name]
            return f"background-color: {colour}; color: {selectTextColour(colour)}"

        ageStyle = ageStyle.map(scenarioColourString, subset=["Scenario Name"])

        # Colour ages if present
        if agesUsed:
            ageColourMap = plt.get_cmap("viridis_r", 10)
            ageColourList = [ageColourMap(value) for value in np.linspace(0, 1, 10)]
            ageColourDictionary = {
                age: to_hex(ageColourList[index])
                for index, age in enumerate(ageWithTime)
            }
            ageColourDictionary["Total"] = "#000000"

            def ageColourString(value):
                """
                Simple function to get colours for age groups in pandas styling format.

                Parameters:
                    name (str): The name of the age group.

                Returns:
                    str: A string that can be used in a pandas `Styler` config to
                        colour table cells according to the colour associated
                        with the age group.
                """
                colour = ageColourDictionary[value]
                return f"background-color: {colour}; color: {selectTextColour(colour)}"

            ageStyle = ageStyle.map(ageColourString, subset=["Age Group"])

        # Use background gradients on difference from baseline columns
        for column in diffSet:
            colVals = ageData[column]
            gradientMap = np.array(getSlopeNorm(colVals)(colVals))
            ageStyle = ageStyle.background_gradient(
                "RdBu_r",
                vmin=0,
                vmax=1,
                subset=[column],
                gmap=gradientMap,
            )
            # Set white background for NA values to make them readable
            ageStyle = ageStyle.map(
                lambda val: "background-color: #F7F7F7" if pd.isna(val) else "",
                subset=[column],
            )

    # Save the generated table
    session.HealthOutcomeTableData = ageStyle  # .format(formatValues)
    session.HealthOutcomeTableConfig = columnConfig
    session.ChartGenerated = True


st.title("Health Burden Tables")

st.markdown("""
    Here you can generate and save tables comparing various health
    burden outcomes (e.g. infections, diagnosed cases, deaths) between
    the different scenarios from the most recently ran simulation.
""")

# Modify CSS to avoid age group names being cut off
st.html("""
    <style>
        .stMultiSelect [data-baseweb=select] span{max-width: 500px;}
    </style>
""")

# Save relevant params as variables to avoid lookups
disableTable = False
tableButtonTooltip = """
Use the data from the most recent simulation to generate a table displaying different
health outcomes on the scenarios in the simulation, with the specific columns
displayed depending on the parameters selected above.
"""
# healthOutcomeRowCount = session["healthOutcomeRowCount"]
healthOutcomeErrorContainer = st.container()

# Check if there is data to tabulate
currentDataExists = usePresetData or session.get("modelDataAsirFull") is not None
currentDataUsesVaccines = (
    usePresetData and presetDataPaths["Vaccinated"] is not None
) or session.get("modelDataAsirVaccinated") is not None
if not currentDataExists:
    healthOutcomeErrorContainer.warning(
        """
        No simulation data has been generated. Click
        :primary-badge[:material/motion_play: Run Simulation] in the
        sidebar to run a simulation and obtain the data necessary to
        generate a table.
    """,
        icon=":material/science_off:",
    )
    disableTable = True
    tableButtonTooltip = """
No simulation experiments have been completed yet, so there is no data to tabulate.
    """
if currentDataExists and session.simulationInProgress:
    healthOutcomeErrorContainer.warning(
        """
        Warning: A new simulation is currently in progress. Since the
        data is not yet ready to process, attempting to create a table
        now will use the data from the previous simulation. Once the
        in-progress simulation is complete, it will not be possible to
        generate tables with the previous simulation's data, though the
        current table will still be available to view and download
        until you generate a new table.
    """,
        icon=":material/av_timer:",
    )

# Form (container) for selecting table settings
tableSettings = st.expander("Table Settings")
with tableSettings:
    simParams = session.get("SimParams", {})
    st.markdown("""
        Use these parameters to configure how the table will be generated.
        Hover your mouse over the :material/help: help icon next to a
        setting's input field to show an explanation of what that setting
        does. Hover your mouse over any buttons to show an explanation of
        what that button does.
    """)

    # Scenario and age group selection
    st.subheader("Scenario and Age Group Selection")
    scenarioNames = simParams.get("Scenario Names", presetScenarioNames)
    if currentDataExists:
        loadKey("healthOutcomeScenariosToUse", default=scenarioNames)
        scenariosToUse: Optional[list[str]] = st.multiselect(
            "Scenarios to Include in Table",
            scenarioNames,
            default=scenarioNames,
            key="_healthOutcomeScenariosToUse",
            on_change=saveKey,
            args=["healthOutcomeScenariosToUse"],
            placeholder="Please select at least 1 scenario",
            kwargs={"notScenario": True},
            help="""
Select which scenarios should be included in the table.
You may select as many scenarios as you wish, but you
must select at least one. Each scenario will have its
own row in the table, displaying the values of the
specified health burden outcomes in that scenario.
            """,
        )
        if not scenariosToUse:
            st.error(
                """
            Error: No scenarios have been included in the table. If you
            attempt to generate the table now, it will be empty. Please
            select at least one scenario to include with the 'Scenarios
            to Use' setting.
        """,
                icon=":material/tab_unselected:",
            )
            disableTable = True
            tableButtonTooltip = """
No scenarios have been selected in the Table Settings menu. Please select at
least one scenario with the Scenarios to Include in Table setting before
attempting to generate a table.
            """
    else:
        st.info(
            """
            No simulation data has been generated, so there are
            currently no scenarios to select. Click
            :primary-badge[:material/motion_play: Run Simulation] in
            the sidebar to run a simulation and obtain the data
            necessary to generate a table.
        """,
            icon=":material/tab_unselected:",
        )
        scenariosToUse = None

    loadKey("healthOutcomeAgeSeparation", default="Combined")
    ageSeparation = st.radio(
        "Age Group Separation",
        options=["Combined", "By Row", "By Column"],
        captions=[
            "Don't separate data by age groups",
            "Give each age group its own row in the table",
            "Allow columns to display specific age groups",
        ],
        index=0,
        on_change=saveKey,
        args=["healthOutcomeAgeSeparation"],
        kwargs={"notScenario": True},
        key="_healthOutcomeAgeSeparation",
        help="""
Select how the health burdens in different age groups should be displayed
within the table.
### Options:
- Combined: Do not separate health burden data by age groups. The table will
only display the combined health burden data for each scenario.
- By Row: Separate different age groups in the simulation by rows. Each row
of the table will display the health burden data for a specific age group in
a specific simulation.
- By Column: Separate different age groups in the simulation by columns.
When editing the columns that will be generated in the table, you will be
able to select which age groups the health burden data in that column will
be derived from.
        """,
    )

    if ageSeparation == "By Row":
        loadKey("healthOutcomeAgesToUse", default=ageGroups)
        agesToUse: list = st.multiselect(
            "Age Groups to Include in Table",
            options=ageGroups,
            default=ageGroups,
            key="_healthOutcomeAgesToUse",
            on_change=saveKey,
            args=["healthOutcomeAgesToUse"],
            placeholder="Please select at least 1 age group",
            kwargs={"notScenario": True},
            help="""
    Select which age groups should be included in the table.
    You may select as many groups as you wish. Each age group
    will have its own row in the table, displaying the values
    of the specified health burden outcomes for members of the
    population in that age group (or for the entire population
    in the case of the 'Total' group).
            """,
        )
        if not agesToUse:
            st.error(
                """
            Error: No age groups have been included in the table. If you
            attempt to generate the table now, it will be empty. Please
            select at least one age group to include with the 'Age Groups
            to Use' setting.
        """,
                icon=":material/tab_unselected:",
            )
            disableTable = True
            tableButtonTooltip = """
No age groups have been selected in the Table Settings menu. Please select at
least one age group with the Age Groups to Include in Table setting or switch
to a different Age Group Separation mode before attempting to generate a table.
            """
    else:
        agesToUse = []

    # Toggle coloured table cells
    colourToggle = st.toggle(
        "Use Colour in Table",
        value=True,
        on_change=saveKey,
        args=["colourToggle"],
        kwargs={"notScenario": True},
        key="_colourToggle",
        help="""
Toggle whether cells in the table should be coloured based on their value.
When enabled, scenario names (and age group names if Age Group Separation
is set to "By Row") will each have a unique colour, and difference from
baseline columns will use different shades of blue/red to indicate the
magnitude of the difference.
        """,
    )

    # Variable-length form for choosing columns
    # TODO: Either fix or prevent percentage infection >100 due to reinfection
    st.subheader(
        "Select Health Burden Columns",
        help="""
This table specifies health burden outcomes to include as columns in the outcome
table and their format. Each selected outcome will be listed for each age
group in each scenario from the simulation. Note that if multiple columns are
defined with identical parameters, only the first instance of them will be
included in the table.
        """,
    )
    st.markdown("Double-click a cell in this table to edit its value.")

    """
    default=pd.DataFrame(
        {
            "Health Burden Outcome": [None],
            "Age Groups": [[]],
            "Vaccination Status": ["All"],
            "Options": [[]],
        },
    ),
    """

    loadKey(
        "healthColumnForm",
        default=pd.DataFrame(
            {
                "Health Burden Outcome": [
                    "Symptomatic Infections",
                    "Symptomatic Infections",
                    "Hospitalisations",
                    "Hospitalisations",
                ],
                "Age Groups": [[], [], [], []],
                "Vaccination Status": ["All", "All", "All", "All"],
                "Options": [
                    [],
                    ["Percentage", "Difference from Baseline"],
                    [],
                    ["Percentage", "Difference from Baseline"],
                ],
            },
        ),
        dataframe=True,
    )
    baseColumnData = replaceTableNA(
        session["healthColumnForm"],
        {
            "Age Groups": [],
            "Vaccination Status": "All",
        },
    )
    # TODO: Allow manually setting column names
    healthColumnForm = st.data_editor(
        baseColumnData,
        height="content",
        num_rows="dynamic",
        key="_healthColumnForm",
        on_change=saveKey,
        args=["healthColumnForm"],
        kwargs={"dataframe": True},
        placeholder="Select a health burden outcome",
        column_config={
            "Health Burden Outcome": st.column_config.SelectboxColumn(
                "Health Burden Outcome",
                required=True,
                options=tableOutcomes,
                help="""
Select the health burden outcome you would like to be included as a column on the table.
### Options:
- Symptomatic Infections: the number of individuals showing symptoms of the pathogen.
- Diagnosed Cases: the number of individuals formally diagnosed with the pathogen.
- GP Visits: the number of individuals who visit their general practitioner
due to symptoms of the pathogen.
- ICU Visits: the number of individuals who are admitted to an Intensive
Care Unit (ICU) due to the pathogen.
- Hospitalisations: the number of individuals who go to the hospital for
treatment as a result of the pathogen.
- Deaths: the number of individuals killed by the pathogen.
                """,
            ),
            "Age Groups": (
                None
                if ageSeparation != "By Column"
                else st.column_config.MultiselectColumn(
                    "Age Groups",
                    required=bool(ageSeparation == "By Column"),
                    default=[],
                    options=ageWithTime,
                    color="auto",
                    help="""
Select which age groups should be considered for health burdens in this column.
Multiple age groups can be selected; the column will sum the health burden
outcomes from all selected age groups. If no age groups are selected for a column,
all age groups will be considered.
                """,
                )
            ),
            # TODO: Make advanced settings hide this when disabled
            "Vaccination Status": (
                None
                if not currentDataUsesVaccines
                else st.column_config.SelectboxColumn(
                    "Vaccination Status",
                    required=True,
                    default="All",
                    options=["All", "Vaccinated", "Unvaccinated"],
                    help="""
Select what vaccination status should be considered for health burdens in this column.
### Options:
- All: The column will include all health burden outcomes recorded in the
simulation, regardless of vaccination status.
- Vaccinated: The column will only include health burden outcomes recorded in
individuals who had already received vaccines in the simulation.
- Unvaccinated: The column will only include health burden outcomes recorded in
individuals who had not received vaccines in the simulation.
                """,
                )
            ),
            "Options": st.column_config.MultiselectColumn(
                "Options",
                default=[],
                options=["Percentage", "Difference from Baseline"],
                color="auto",
                help="""
Select any number of options here to modify how the column will be displayed.
### Options:
- Percentage: The health burden outcome will be displayed as a percentage
of the total population. Note that this percentage may exceed 100% if infection
waning is present in the simulation, as it is possible for the same individual
to be infected multiple times.
- Difference from Baseline: The column will display the difference in the
selected health burden outcome between the baseline scenario and each other
scenario. If "Percentage" is also selected, this difference will be displayed
as the percentage increase/decrease from the baseline value.
                """,
            ),
        },
    )
    # Display any issues with the current columns
    if healthColumnForm["Health Burden Outcome"].count() < 1:
        # TODO: Specify the columns in question
        st.info(
            """
            At least one column must be configured using this form before a
            table can be generated. Make sure to specify which health burden
            outcome the column will use, as this setting is required for all
            columns.
        """,
            icon=":material/tab_unselected:",
        )
        disableTable = True
        tableButtonTooltip = """
No columns have been configured in the Table Settings menu. Please
add at least one column before attempting to generate a table.
"""
    else:
        if simParams.get("Waning In Simulation"):
            # TODO: Also check for percentage without baseline diff
            st.warning(
                """
                    Warning: Columns that display values as percentages without also
                    displaying differences from baselines may be inaccurate if
                    reinfection is possible within the simulation. Avoid using columns
                    with percentage in tables when the simulation enables immunity waning.
                """,
                icon=":material/heap_snapshot_multiple:",
            )
        # Check for duplicates (lists must be sorted and converted to str)
        dupeColumnForm = healthColumnForm.copy()
        dupeColumnForm["Options"] = dupeColumnForm["Options"].apply(lambda x: sorted(x))
        if ageSeparation == "By Column":
            dupeColumnForm["Age Groups"] = dupeColumnForm["Age Groups"].apply(
                lambda x: sorted(x)
            )
        else:
            dupeColumnForm = dupeColumnForm.drop("Age Groups", errors="ignore")
        if not currentDataUsesVaccines:
            dupeColumnForm = dupeColumnForm.drop("Vaccination Status", errors="ignore")
        if dupeColumnForm.astype(str).duplicated().any():
            st.warning(
                """
                    Warning: Some columns have been given the exact same settings.
                    Since these columns will have the same name, only one column
                    will be included in the final table unless you modify the
                    settings such that they are no longer identical.
                """,
                icon=":material/content_copy:",
            )
        if (
            ageSeparation == "By Column"
            and not healthColumnForm["Age Groups"].fillna(False).all()
        ):
            st.info(
                """
                    Note: Any columns that do not have any age groups selected
                    for them will default to displaying all age groups.
                """,
                icon=":material/tab_unselected:",
            )

    oldVarLengthForm = '''for i in range(healthOutcomeRowCount):
        (
            healthOutcomeColumn,
            healthDifferenceColumn,
            outcomeTypeColumn,
            healthRemoveColumn,
        ) = st.columns((0.25, 0.275, 0.275, 0.2))
        currentOutcome = session.get(f"healthOutcome{i}", "Symptomatic Infections")

        # Health burden outcome column
        loadKey(f"healthOutcome", i, currentOutcome, noZeroDefault=True)
        with healthOutcomeColumn:
            st.selectbox(
                "Health Burden Outcome",
                key=f"_healthOutcome{i}",
                # Set health burden options such that only outcomes
                # that haven't been selected yet can be selected
                options=(
                    [currentOutcome]
                    + [
                        outcome
                        for outcome in tableOutcomes
                        if outcome != currentOutcome
                    ]
                ),
                on_change=saveKey,
                args=[f"healthOutcome", i],
                kwargs={"notScenario": True},
                help="""
                Select the health burden outcome you would like to be
                included as a column on the table.

                ### Options:
                - Symptomatic Infections: the number of individuals infected with
                the pathogen in the simulation.
                - Diagnosed Cases: the number of individuals formally diagnosed
                with the pathogen in the simulation.
                - Hospitalisations: the number of individuals who go to
                the hospital for treatment as a result of the pathogen
                in the simulation.
                - Deaths: the number of individuals killed by the
                pathogen in the simulation.
                - ICU Visits: the number of individuals who are
                admitted to an Intensive Care Unit (ICU) as a result of
                the pathogen in the simulation.
                - GP Visits: the number of individuals who visit their
                general practitioner due to symptoms of the pathogen in
                the simulation.
            """,
            )

        # Difference from baseline column
        # Force set to false if only one scenario is in use
        if not usePresetData and (
            simParams.get("Scenario Count", -1) == 0
            or scenariosToUse == ["Baseline"]
        ):
            session[f"useBaselineDifference{i}"] = False
        loadKey("useBaselineDifference", i, False, noZeroDefault=True)
        with healthDifferenceColumn:
            st.toggle(
                "Difference from Baseline",
                False,
                key=f"_useBaselineDifference{i}",
                on_change=saveKey,
                args=["useBaselineDifference", i],
                disabled=not usePresetData
                and (
                    simParams.get("Scenario Count", -1) == 0
                    or scenariosToUse == ["Baseline"]
                ),
                kwargs={"notScenario": True},
                help=(
                    """
                Toggle whether this column should display the
                difference between the specified health burden
                outcome's result in the baseline simulation and the
                result in the simulation the row is for. For example,
                if the number of infected individuals was 300 in the
                baseline scenario and 400 in Scenario 1, an
                'Symptomatic Infections' column with this setting enabled would
                display +100 in the row for Scenario 1.

                Note that this option will always be set to False if
                only one scenario is included in the table.
            """
                    if (
                        simParams.get("Scenario Count", -1) != 0
                        and scenariosToUse != ["Baseline"]
                    )
                    else """
                There are currently no additional scenarios defined for
                the simulation data, so a difference from baseline
                column would display no useful information.
            """
                ),
            )

        # Proportion column
        loadKey(f"useProportion", i, False, noZeroDefault=True)
        with outcomeTypeColumn:
            st.toggle(
                "Percentage",
                False,
                key=f"_useProportion{i}",
                on_change=saveKey,
                args=[f"useProportion", i],
                kwargs={"notScenario": True},
                help="""
                Toggle whether this column should display its value as
                a percentage rather than as a standard number.

                If 'Difference from Baseline' is disabled, this
                percentage will be relative to the total population of
                each age group in each scenario's community. For
                example, if the number of infected adults was 20,000 in
                a scenario with the Newcastle community (which has
                71,299 adults), an 'Symptomatic Infections' column with
                'Percentage' disabled would display 20,000 while a
                column with it enabled would display 28.051%.

                If 'Difference from Baseline' is enabled, this
                percentage will be relative to the value of the column
                in the baseline scenario for the given age group. For
                example, if the number of infected individuals was 300
                in the baseline scenario and 400 in Scenario 1, an
                'Symptomatic Infections' column with both 'Percentage' and
                'Difference from Baseline' enabled would display
                +33.333% in the row for Scenario 1.
            """,
            )

        # Delete button column
        with healthRemoveColumn:
            st.button(
                label="Remove Column",
                icon=":material/delete:",
                key=f"healthOutcomeRemove{i}",
                on_click=deleteFormRow,
                args=(
                    i,
                    "healthOutcomeRowCount",
                    {"healthOutcome", "useBaselineDifference", "useProportion"},
                    1,
                ),
                disabled=healthOutcomeRowCount <= 1,
                help=(
                    """
                Remove this row of the form and do not display this column
                in the table.
            """
                    if healthOutcomeRowCount >= 2
                    else """
                The table must have at least one column.
            """
                ),
            )
    # Button to add another row for age specific params
    tableSettings.button(
        label="Add Burden Column",
        icon=":material/add:",
        on_click=addFormRow,
        key=f"healthOutcomeAdd",
        args=(
            f"healthOutcomeRowCount",
            {
                f"healthOutcome{healthOutcomeRowCount}": "Symptomatic Infections",
                f"useBaselineDifference{healthOutcomeRowCount}": False,
                f"useProportion{healthOutcomeRowCount}": False,
            },
        ),
        disabled=healthOutcomeRowCount >= 7,
        help=(
            """
            Add another row to this form, where you can select an
            additional health burden outcome to be included in the
            table.
        """
            if healthOutcomeRowCount <= 6
            else """
            The maximum number of columns has been added to this table.
        """
        ),
    )'''

# Button to generate the table itself
st.button(
    label="Create Table",
    icon=":material/backup_table:",
    key="generateTable",
    type="primary",
    on_click=generateTable,
    disabled=disableTable,
    help=tableButtonTooltip,
)
# Display the table itself
tableData = session.get("HealthOutcomeTableData")
tableConfig = session.get("HealthOutcomeTableConfig")
if tableData is not None:
    st.header("Health Burden Outcome Table")
    # TODO: Fix columns being deselected when changing column settings
    st.dataframe(
        tableData,
        height="auto",
        width="content",
        column_config=tableConfig,
        hide_index=True,
        placeholder="N/A",
    )

    @st.fragment()
    def burdenDataDownload():
        """
        Fragment function to show a button that downloads the data in the table.
        """
        # TODO: Reflect changes made to the table by the user (reordered cols etc.)
        # Or just remove this since there's a built-in download button now
        assert tableData is not None, "Table data was not defined"
        st.download_button(
            "Download Table Data",
            tableData.data.to_csv(index=False),
            f"FlusimHealthBurdenData_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.csv",
            mime="text/csv",
            key="infectionDataDownload",
            icon=":material/download:",
            help="""
Download the above table as a CSV file.
        """,
        )

    burdenDataDownload()

    st.subheader("Using the Table")
    st.markdown("""
        - Use the scroll bars on the right and bottom edges of the
        table to scroll and view rows/columns that are not immediately
        visible.
        - Double-click on a cell in the table to view its exact value.
        - Click on one of the column headers to sort the table using
        the values of that column.
        - Adjust column widths by clicking and dragging the lines
        between each column in the header row.
        - Click the :material/more_vert: menu button that appears when
        hovering your mouse over a column header to view more
        formatting options for that column.

        Hovering your mouse over the table will display icons for
        additional icons on the top-right corner, which can be used for
        the following actions:

        - Click the :material/download: download symbol to download the
        table as a CSV file. Note that the
        :grey-badge[:material/download: Download Table Data] button
        above can also be used.
        - Click the :material/search: magnifying glass symbol to search
        for a specific scenario, age group or value in the table.
        - Click the :material/fullscreen: fullscreen symbol to put the
        table in fullscreen; click it again to return to viewing the
        whole dashboard.
    """)
