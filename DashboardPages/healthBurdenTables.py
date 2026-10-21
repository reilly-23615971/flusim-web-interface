# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where users can generate tables with infection data

# Imports
import logging
import time
from typing import Literal, Optional, Sequence, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import TwoSlopeNorm, to_hex

from ClientResources.Constants import (
    MUTED_CODES,
    PRESET_COMMUNITY,
    PRESET_DATA_PATHS,
    PRESET_SCENARIO_NAMES,
    SHOW_DEBUG_DOWNLOADS,
    USE_PRESET_DATA,
)
from ClientResources.InterfaceFunctions import health_outcome_store
from ClientResources.ParameterFunctions import (
    id_get,
    load_key,
    replace_table_na,
    save_key,
)
from ClientResources.Types import (
    AGE_GROUPS,
    AGE_WITH_TOTAL,
    HEALTH_OUTCOMES,
    AgeWithTotal,
    ColumnDetails,
    SimParams,
)
from ClientResources.VisualisationFunctions import format_asir, generate_asir

# Logging
table_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


def get_slope_norm(column: pd.Series) -> TwoSlopeNorm:
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
    min_value, max_value = column.min(), column.max()
    return TwoSlopeNorm(
        vcenter=0,
        vmin=(
            -1e-9
            if min_value >= 0 or pd.isna(min_value)
            else min_value - 1e-9 if min_value == max_value else min_value
        ),
        vmax=(
            1e-9
            if max_value <= 0 or pd.isna(max_value)
            else max_value + 1e-9 if max_value == min_value else max_value
        ),
    )


# Function to choose whether dataframe cells should have white or black text
def select_text_colour(colour: str) -> str:
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
        + 0.114 * int(colour[5:], 16)  # blue
    )
    return "#000000" if luminosity > 135 else "#ffffff"


def generate_table() -> None:
    """
    Callback function used to generate and format health burden tables.
    """
    # Throw error if no data is present
    full_data = session.get("model_data_asir_full")
    if not USE_PRESET_DATA and full_data is None:
        raise FileNotFoundError(
            "No simulation ASIR data was available to plot; please run a"
            "simulation before attempting to generate a table."
        )
    # TODO: Fix bug where latest column settings aren't stored
    # (add confirmation to generate table button?
    # Rerun page before running generate_table somehow?)

    # Debug code for loading data in testing
    if USE_PRESET_DATA:
        # Set default session_state parameters
        use_advanced = session.get("show_advanced", False)
        scenario_names = PRESET_SCENARIO_NAMES
        basic_rates, age_rates = health_outcome_store(
            scenario_names,
            use_ages=use_advanced,
        )
        session.sim_params = SimParams(
            scenario_names=scenario_names,
            analysis_formats=[],
            community=PRESET_COMMUNITY,
            health_outcome_rates=basic_rates,
            age_health_outcome_rates=age_rates,
            scaling_factor=session.get("scaling_population", 272407) / 272407,
            symptomatic_rates=(
                [
                    [
                        1 - id_get("asymptomatic_child", scenario_id, 0.35),
                        1 - id_get("asymptomatic_adult", scenario_id, 0.35),
                    ]
                    for scenario_id in range(4)
                ]
                if use_advanced
                else [
                    [1 - id_get("asymptomatic_adult", scenario_id, 0.35)] * 2
                    for scenario_id in range(4)
                ]
            ),
        )

        # Load test data from files
        with open(PRESET_DATA_PATHS["ASIR"], "rb") as csv:
            full_data = format_asir(csv.read(), scenario_names)
        if PRESET_DATA_PATHS.get("ASIR") is not None:
            with open(PRESET_DATA_PATHS["Vaccinated"], "rb") as csv:
                vaccine_data = format_asir(csv.read(), scenario_names)
        else:
            vaccine_data = None

    # Load data from session_state
    else:
        scenario_names = session.sim_params.scenario_names
        vaccine_data = session.get("model_data_asir_vaccinated")

    age_separation = session.get("health_outcome_age_separation", "Combined")

    health_column_form = replace_table_na(
        session.get(
            "health_column_form",
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
    column_details = cast(
        list[ColumnDetails],
        [
            (
                outcome,
                ages if ages else AGE_WITH_TOTAL,
                vaccine_status if vaccine_data is not None else "All",
                "Percentage" in options,
                "Difference from Baseline" in options,
            )
            for outcome, ages, vaccine_status, options in zip(
                health_column_form["Health Burden Outcome"],
                health_column_form["Age Groups"],
                health_column_form["Vaccination Status"],
                health_column_form["Options"],
            )
            if outcome
        ],
    )
    scenarios_used = session.get("health_outcome_scenarios_to_use", scenario_names)
    ages_used = (
        session.get("health_outcome_ages_to_use", AGE_WITH_TOTAL)
        if age_separation == "By Row"
        else []
    )
    use_colour = session.get("colour_health_burden_tables", True)
    table_log.info(f"""
[generate_table] Formatting Asir data using the scenarios {scenarios_used} (of
{scenario_names}), the age groups {ages_used} and the following columns:
{column_details}
    """)

    assert full_data is not None, "ASIR data was not defined"
    age_data, column_config, percentage_columns, difference_columns = generate_asir(
        full_data,
        scenario_names,
        age_separation,
        column_details,
        included_scenarios=scenarios_used,
        included_ages=ages_used,
        vaccinated_data=vaccine_data,
    )

    # Format data according to column type
    # TODO: Is + with baseline difference necessary enough to revive this?
    """format_values: dict[str, Any] = (
        {column: "{:+.5n}" for column in difference_columns - percentage_columns}
        | {column: "{:+.3%}" for column in difference_columns & percentage_columns}
        | {column: "{:.3%}" for column in percentage_columns - difference_columns}
        | {column: "{:.5n}" for column in set(age_data.columns) - (difference_columns | percentage_columns)}
    )"""

    # Create fake index columns
    if ages_used:
        age_data.rename_axis(index=["Scenario Index", "Age Group Index"], inplace=True)
        age_data.insert(
            0,
            ("", "Scenario Name"),
            age_data.index.get_level_values("Scenario Index").values,
        )
        age_data.insert(
            1,
            ("", "Age Group"),
            age_data.index.get_level_values("Age Group Index").values,
        )

    else:
        age_data.rename_axis("Scenario Index", inplace=True)
        age_data.insert(0, ("", "Scenario Name"), age_data.index.to_series())

    # Initialise styler
    age_style = age_data.style

    # Colour the index cells
    if use_colour:
        # Set default cell colours
        age_style.set_properties(
            **{"background-color": "#F7F7F7", "color": "black"}, subset=None
        )
        # Generate and map scenario colour palette
        scenario_colour_map = MUTED_CODES[: len(scenario_names)]
        scenario_colour_dictionary = {
            scenario: to_hex(scenario_colour_map[index])
            for index, scenario in enumerate(scenario_names)
        }

        # Apply the colours to the scenario column
        def scenario_colour_string(name) -> str:
            """
            Simple function to get colours for scenarios in pandas styling
            format.

            Parameters:
                name (str): The name of the scenario.

            Returns:
                str: A string that can be used in a pandas `Styler` config to
                    colour table cells according to the colour associated with
                    the scenario.
            """
            colour = scenario_colour_dictionary[name]
            return f"background-color: {colour}; color: {select_text_colour(colour)}"

        age_style = age_style.map(
            scenario_colour_string, subset=[("", "Scenario Name")]
        )

        # Colour ages if present
        if ages_used:
            age_colour_map = plt.get_cmap("viridis_r", 10)
            age_colour_list = [age_colour_map(value) for value in np.linspace(0, 1, 10)]
            age_colour_dictionary = {
                age: to_hex(age_colour_list[index])
                for index, age in enumerate(AGE_GROUPS)
            }
            age_colour_dictionary["Total"] = "#000000"

            def age_colour_string(value):
                """
                Simple function to get colours for age groups in pandas styling
                format.

                Parameters:
                    name (str): The name of the age group.

                Returns:
                    str: A string that can be used in a pandas `Styler` config
                        to colour table cells according to the colour
                        associated with the age group.
                """
                colour = age_colour_dictionary[value]
                return (
                    f"background-color: {colour}; color: {select_text_colour(colour)}"
                )

            age_style = age_style.map(age_colour_string, subset=[("", "Age Group")])

        # Use background gradients on difference from baseline columns
        for column in difference_columns:
            column_values = age_data[column]
            gradient_map = np.array(get_slope_norm(column_values)(column_values))
            age_style = age_style.background_gradient(
                "RdBu",
                vmin=0,
                vmax=1,
                subset=[column],
                gmap=gradient_map,
            )
            # Set white background for NA values to make them readable
            age_style = age_style.map(
                lambda val: "background-color: #F7F7F7" if pd.isna(val) else "",
                subset=[column],
            )

    # Format column config to match Streamlit requirements with MultiIndex
    formatted_config = {
        cast(int, age_data.columns.get_loc(column)) + age_data.index.nlevels: value
        for column, value in column_config.items()
        if column in age_data.columns
    }

    # Save the generated table
    session.health_outcome_table_data = age_style  # .format(format_values)
    session.health_outcome_table_config = formatted_config
    session.chart_generated = True


def download_preset_table(
    name: str,
    columns: Sequence[ColumnDetails] = [
        ("Symptomatic Infections", [], "All", False, False)
    ],
    age_separation: Literal["Combined", "By Row", "By Column"] = "Combined",
    included_scenarios: Optional[list[str]] = None,
    included_ages: Optional[list[AgeWithTotal]] = None,
) -> None:
    """
    Function to create a button downloading specific table presets.

    Parameters:
        name (str): The name of the file to download.

        columns (sequence of tuples (str, list of str, str, bool, bool)): A
            list of tuples representing the settings each column should have.
            The values in each tuple are as follows:
             - the health burden outcome to display
             - which age groups the column should represent (ignored if
            `age_separation` is `Combined` or `By Row`)
             - what vaccination status the column should represent
             - whether or not the column should display percentages
             - whether or not the column should display the difference from
            the baseline scenario's values

        age_separation (str): A string indicating whether different age groups
            should be represented with additional rows or columns. Can be
            either `Combined` (do not separate values by age group at all), `By
            Row` (include extra rows for each age group), or `By Column` (use
            different age groups for each column).

        included_scenarios (list of str, optional): A list of strings
            containing the names of scenarios that will be included in
            the table. If this is `None`, all scenarios will be included.

        included_ages (list of str, optional): A list of strings
            containing the names of age groups that will be included in the
            table. If this is `None`, all age groups will be included. However,
            if this is an empty list, the age group column will be omitted
            entirely. Ignored if `age_separation` is `Combined` or `By Column`.
    """
    # TODO: Reduce redundancy with generate_table

    # Throw error if no data is present
    full_data = session.get("model_data_asir_full")
    if not USE_PRESET_DATA and full_data is None:
        raise FileNotFoundError(
            "No simulation ASIR data was available to plot; please run a"
            "simulation before attempting to download a table."
        )

    # Debug code for loading data in testing
    if USE_PRESET_DATA:
        # Set default session_state params
        use_advanced = session.get("show_advanced", False)
        scenario_names = PRESET_SCENARIO_NAMES
        basic_rates, age_rates = health_outcome_store(
            scenario_names,
            use_ages=use_advanced,
        )
        session.sim_params = SimParams(
            scenario_names=scenario_names,
            analysis_formats=[],
            community=PRESET_COMMUNITY,
            health_outcome_rates=basic_rates,
            age_health_outcome_rates=age_rates,
            symptomatic_rates=(
                [
                    [
                        1 - id_get("asymptomatic_child", scenario_id, 0.35),
                        1 - id_get("asymptomatic_adult", scenario_id, 0.35),
                    ]
                    for scenario_id in range(4)
                ]
                if use_advanced
                else [
                    [1 - id_get("asymptomatic_adult", scenario_id, 0.35)] * 2
                    for scenario_id in range(4)
                ]
            ),
            scaling_factor=session.get("scaling_population", 272407) / 272407,
        )

        # Load test data from files
        with open(PRESET_DATA_PATHS["ASIR"], "rb") as csv:
            full_data = format_asir(csv.read(), scenario_names)
        if PRESET_DATA_PATHS.get("ASIR") is not None:
            with open(PRESET_DATA_PATHS["Vaccinated"], "rb") as csv:
                vaccine_data = format_asir(csv.read(), scenario_names)
        else:
            vaccine_data = None

    # Load data from session_state
    else:
        scenario_names = session.sim_params.scenario_names
        vaccine_data = session.get("model_data_asir_vaccinated")

    table_log.info(f"""
[download_preset_table] Formatting Asir data for the preset {name}, using the
scenarios {included_scenarios} (of {scenario_names}), the age groups
{included_ages} and the following columns: {columns}
    """)

    assert full_data is not None, "ASIR data was not defined"
    age_data, _, _, _ = generate_asir(
        full_data,
        scenario_names,
        age_separation,
        columns,
        included_scenarios=included_scenarios,
        included_ages=included_ages,
        vaccinated_data=vaccine_data,
    )

    # Create fake index columns
    if age_separation == "By Row":
        age_data.rename_axis(index=["Scenario Index", "Age Group Index"], inplace=True)
        age_data.insert(
            0,
            ("", "Scenario Name"),
            age_data.index.get_level_values("Scenario Index").values,
        )
        age_data.insert(
            1,
            ("", "Age Group"),
            age_data.index.get_level_values("Age Group Index").values,
        )

    else:
        age_data.rename_axis("Scenario Index", inplace=True)
        age_data.insert(0, ("", "Scenario Name"), age_data.index.to_series())

    st.download_button(
        f"Download {name}",
        age_data.to_csv(index=False),
        f"{name}.csv",
        mime="text/csv",
        icon=":material/download:",
        help="Download a preset table as a CSV file.",
    )


st.title("Health Burden Tables")

st.markdown("""
Here you can generate and save tables comparing various health burden outcomes
(e.g. infections, diagnosed cases, deaths) between the different scenarios from
the most recently ran simulation.
""")

# Modify CSS to avoid age group names being cut off
st.html("""
    <style>
        .stMultiSelect [data-baseweb=select] span{max-width: 500px;}
    </style>
""")

# Save relevant params as variables to avoid lookups
disable_table = False
table_button_tooltip = """
Use the data from the most recent simulation to generate a table displaying
different health outcomes on the scenarios in the simulation, with the specific
columns displayed depending on the parameters selected above.
"""
health_outcome_error_container = st.container()

# Check if there is data to tabulate
current_data_exists = USE_PRESET_DATA or session.get("model_data_asir_full") is not None
current_data_uses_vaccines = (
    USE_PRESET_DATA and PRESET_DATA_PATHS["Vaccinated"] is not None
) or session.get("model_data_asir_vaccinated") is not None
if not current_data_exists:
    health_outcome_error_container.warning(
        """
No simulation data has been generated. Click
:primary-badge[:material/motion_play: Run Simulation] in the sidebar to run a
simulation and obtain the data necessary to generate a table.
        """,
        icon=":material/science_off:",
    )
    disable_table = True
    table_button_tooltip = """
No simulation experiments have been completed yet, so there is no data to tabulate.
    """
if current_data_exists and session.simulation_in_progress:
    health_outcome_error_container.warning(
        """
Warning: A new simulation is currently in progress. Since the data is not yet
ready to process, attempting to create a table now will use the data from the
previous simulation. Once the in-progress simulation is complete, it will not
be possible to generate tables with the previous simulation's data, though the
current table will still be available to view and download until you generate a
new table.
    """,
        icon=":material/av_timer:",
    )

# Form (container) for selecting table settings
table_settings = st.expander("Table Settings")
with table_settings:
    sim_params: SimParams = session.get(
        "sim_params",
        SimParams(
            scenario_names=PRESET_SCENARIO_NAMES,
            analysis_formats=[],
            community=PRESET_COMMUNITY,
        ),
    )
    st.markdown("""
Use these parameters to configure how the table will be generated. Hover your
mouse over the :material/help: help icon next to a setting's input field to
show an explanation of what that setting does. Hover your mouse over any
buttons to show an explanation of what that button does.
    """)

    # Scenario and age group selection
    st.subheader("Scenario and Age Group Selection")
    scenario_names = sim_params.scenario_names
    if current_data_exists:
        load_key("health_outcome_scenarios_to_use", default=scenario_names)
        scenarios_to_use: Optional[list[str]] = st.multiselect(
            "Scenarios to Include in Table",
            scenario_names,
            default=scenario_names,
            key="_health_outcome_scenarios_to_use",
            on_change=save_key,
            args=["health_outcome_scenarios_to_use"],
            placeholder="Please select at least 1 scenario",
            kwargs={"not_scenario": True},
            help="""
Select which scenarios should be included in the table. You may select as many
scenarios as you wish, but you must select at least one. Each scenario will
have its own row in the table, displaying the values of the specified health
burden outcomes in that scenario.
            """,
        )
        if not scenarios_to_use:
            st.error(
                """
Error: No scenarios have been included in the table. If you attempt to generate
the table now, it will be empty. Please select at least one scenario to include
with the 'Scenarios to Use' setting.
                """,
                icon=":material/tab_unselected:",
            )
            disable_table = True
            table_button_tooltip = """
No scenarios have been selected in the Table Settings menu. Please select at
least one scenario with the Scenarios to Include in Table setting before
attempting to generate a table.
            """
    else:
        st.info(
            """
No simulation data has been generated, so there are currently no scenarios to
select. Click :primary-badge[:material/motion_play: Run Simulation] in the
sidebar to run a simulation and obtain the data necessary to generate a table.
            """,
            icon=":material/tab_unselected:",
        )
        scenarios_to_use = None

    load_key("health_outcome_age_separation", default="Combined")
    age_separation = st.radio(
        "Age Group Separation",
        options=["Combined", "By Row", "By Column"],
        captions=[
            "Don't separate data by age groups",
            "Give each age group its own row in the table",
            "Allow columns to display specific age groups",
        ],
        index=0,
        on_change=save_key,
        args=["health_outcome_age_separation"],
        kwargs={"not_scenario": True},
        key="_health_outcome_age_separation",
        help="""
Select how the health burdens in different age groups should be displayed
within the table.
### Options:
- Combined: Do not separate health burden data by age groups. The table will
only display the combined health burden data for each scenario.
- By Row: Separate different age groups in the simulation by rows. Each row of
the table will display the health burden data for a specific age group in a
specific simulation.
- By Column: Separate different age groups in the simulation by columns. When
editing the columns that will be generated in the table, you will be able to
select which age groups the health burden data in that column will be derived
from.
        """,
    )

    if age_separation == "By Row":
        load_key("health_outcome_ages_to_use", default=AGE_WITH_TOTAL)
        ages_to_use = st.multiselect(
            "Age Groups to Include in Table",
            options=AGE_WITH_TOTAL,
            default=AGE_WITH_TOTAL,
            key="_health_outcome_ages_to_use",
            on_change=save_key,
            args=["health_outcome_ages_to_use"],
            placeholder="Please select at least 1 age group",
            kwargs={"not_scenario": True},
            help="""
Select which age groups should be included in the table. You may select as many
groups as you wish. Each age group will have its own row in the table,
displaying the values of the specified health burden outcomes for members of
the population in that age group (or for the entire population in the case of
the 'Total' group).
            """,
        )
        if not ages_to_use:
            st.error(
                """
Error: No age groups have been included in the table. If you attempt to
generate the table now, it will be empty. Please select at least one age group
to include with the 'Age Groups to Use' setting.
                """,
                icon=":material/tab_unselected:",
            )
            disable_table = True
            table_button_tooltip = """
No age groups have been selected in the Table Settings menu. Please select at
least one age group with the Age Groups to Include in Table setting or switch
to a different Age Group Separation mode before attempting to generate a table.
            """
    else:
        ages_to_use = []

    # Toggle coloured table cells
    colour_health_burden_tables = st.toggle(
        "Use Colour in Table",
        value=True,
        on_change=save_key,
        args=["colour_health_burden_tables"],
        kwargs={"not_scenario": True},
        key="_colour_health_burden_tables",
        help="""
Toggle whether cells in the table should be coloured based on their value. When
enabled, scenario names (and age group names if Age Group Separation is set to
"By Row") will each have a unique colour, and difference from baseline columns
will use different shades of blue/red to indicate the magnitude of the difference.
        """,
    )

    # Variable-length form for choosing columns
    # TODO: Either fix or prevent percentage infection >100 due to reinfection
    st.subheader(
        "Select Health Burden Columns",
        help="""
This table specifies health burden outcomes to include as columns in the
outcome table and their format. Each selected outcome will be listed for each
age group in each scenario from the simulation. Note that if multiple columns
are defined with identical parameters, only the first instance of them will be
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

    load_key(
        "health_column_form",
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
    base_column_data = replace_table_na(
        session["health_column_form"],
        {
            "Age Groups": [],
            "Vaccination Status": "All",
        },
    )
    # TODO: Allow manually setting column names
    health_column_form = st.data_editor(
        base_column_data,
        height="content",
        num_rows="dynamic",
        key="_health_column_form",
        on_change=save_key,
        args=["health_column_form"],
        kwargs={"dataframe": True},
        placeholder="Select a health burden outcome",
        column_config={
            "Health Burden Outcome": st.column_config.SelectboxColumn(
                "Health Burden Outcome",
                required=True,
                options=HEALTH_OUTCOMES,
                help="""
Select the health burden outcome you would like to be included as a column on
the table.
### Options:
- Symptomatic Infections: the number of individuals showing symptoms of the
pathogen.
- Diagnosed Cases: the number of individuals formally diagnosed with the
pathogen.
- GP Visits: the number of individuals who visit their general practitioner due
to symptoms of the pathogen.
- ICU Visits: the number of individuals who are admitted to an Intensive Care
Unit (ICU) due to the pathogen.
- Hospitalisations: the number of individuals who go to the hospital for
treatment as a result of the pathogen.
- Deaths: the number of individuals killed by the pathogen.
                """,
            ),
            "Age Groups": (
                None
                if age_separation != "By Column"
                else st.column_config.MultiselectColumn(
                    "Age Groups",
                    required=bool(age_separation == "By Column"),
                    default=[],
                    options=AGE_GROUPS,
                    color="auto",
                    help="""
Select which age groups should be considered for health burdens in this column.
Multiple age groups can be selected; the column will sum the health burden
outcomes from all selected age groups. If no age groups are selected for a
column, all age groups will be considered.
                """,
                )
            ),
            # TODO: Make advanced settings hide this when disabled
            "Vaccination Status": (
                None
                if not current_data_uses_vaccines
                else st.column_config.SelectboxColumn(
                    "Vaccination Status",
                    required=True,
                    default="All",
                    options=["All", "Vaccinated", "Unvaccinated"],
                    help="""
Select what vaccination status should be considered for health burdens in this
column.
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
            # TODO: Rename baseline difference to averted burdens?
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
    if health_column_form["Health Burden Outcome"].count() < 1:
        # TODO: Specify the columns in question
        st.info(
            """
At least one column must be configured using this form before a table can be
generated. Make sure to specify which health burden outcome the column will
use, as this setting is required for all columns.
            """,
            icon=":material/tab_unselected:",
        )
        disable_table = True
        table_button_tooltip = """
No columns have been configured in the Table Settings menu. Please add at least
one column before attempting to generate a table.
        """
    else:
        if sim_params.waning:
            # TODO: Also check for percentage without baseline diff
            # TODO: Account for baseline diff change to averted burdens
            st.warning(
                """
Warning: Columns that display values as percentages without also displaying
differences from baselines may be inaccurate if reinfection is possible within
the simulation. Avoid using columns with percentage in tables when the
simulation enables immunity waning.
                """,
                icon=":material/heap_snapshot_multiple:",
            )
        # Check for duplicates (lists must be sorted and converted to str)
        duplicate_form = health_column_form.copy()
        duplicate_form["Options"] = duplicate_form["Options"].apply(lambda x: sorted(x))
        if age_separation == "By Column":
            duplicate_form["Age Groups"] = duplicate_form["Age Groups"].apply(
                lambda x: sorted(x)
            )
        else:
            duplicate_form = duplicate_form.drop("Age Groups", errors="ignore")
        if not current_data_uses_vaccines:
            duplicate_form = duplicate_form.drop("Vaccination Status", errors="ignore")
        if duplicate_form.astype(str).duplicated().any():
            st.warning(
                """
Warning: Some columns have been given the exact same settings. Since these
columns will have the same name, only one column will be included in the final
table unless you modify the settings such that they are no longer identical.
                """,
                icon=":material/content_copy:",
            )
        if (
            age_separation == "By Column"
            and not health_column_form["Age Groups"].fillna(False).all()
        ):
            st.info(
                """
Note: Any columns that do not have any age groups selected for them will
default to displaying all age groups.
                """,
                icon=":material/tab_unselected:",
            )

# Button to generate the table itself
st.button(
    label="Create Table",
    icon=":material/backup_table:",
    key="generate_table",
    type="primary",
    on_click=generate_table,
    disabled=disable_table,
    help=table_button_tooltip,
)
# Display the table itself
table_data = session.get("health_outcome_table_data")
table_config = session.get("health_outcome_table_config")
if table_data is not None:
    st.header("Health Burden Outcome Table")
    # TODO: Fix columns being deselected when changing column settings
    # TODO: Consider increasing the default height (you'll need to measure in pixels)
    st.dataframe(
        table_data,
        height="auto",
        width="stretch",
        column_config=table_config,
        hide_index=True,
        placeholder="N/A",
    )

    @st.fragment()
    def burden_data_download():
        """
        Fragment function to show a button that downloads the data in the table.
        """
        # TODO: Reflect changes made to the table by the user (reordered cols etc.)
        # Or just remove this since there's a built-in download button now
        assert table_data is not None, "Table data was not defined"
        st.download_button(
            "Download Table Data",
            table_data.data.to_csv(index=False),
            f"FlusimHealthBurdenData_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.csv",
            mime="text/csv",
            key="infection_data_download",
            icon=":material/download:",
            help="Download the above table as a CSV file.",
        )

    burden_data_download()

# Debug buttons for common table downloads
if SHOW_DEBUG_DOWNLOADS and current_data_exists:
    st.divider()
    download_preset_table(
        "AllBurdens",
        columns=[
            ("Symptomatic Infections", AGE_WITH_TOTAL, "All", False, False),
            ("Symptomatic Infections", AGE_WITH_TOTAL, "All", False, True),
            ("Symptomatic Infections", AGE_WITH_TOTAL, "All", True, True),
            ("GP Visits", AGE_WITH_TOTAL, "All", False, False),
            ("GP Visits", AGE_WITH_TOTAL, "All", False, True),
            ("GP Visits", AGE_WITH_TOTAL, "All", True, True),
            ("Hospitalisations", AGE_WITH_TOTAL, "All", False, False),
            ("Hospitalisations", AGE_WITH_TOTAL, "All", False, True),
            ("Hospitalisations", AGE_WITH_TOTAL, "All", True, True),
            ("Deaths", AGE_WITH_TOTAL, "All", False, False),
            ("Deaths", AGE_WITH_TOTAL, "All", False, True),
            ("Deaths", AGE_WITH_TOTAL, "All", True, True),
        ],
    )
    download_preset_table(
        "AgesByRow",
        columns=[
            ("Symptomatic Infections", AGE_GROUPS, "All", False, False),
            ("Symptomatic Infections", AGE_GROUPS, "All", False, True),
            ("Symptomatic Infections", AGE_GROUPS, "All", True, True),
            ("GP Visits", AGE_GROUPS, "All", False, False),
            ("GP Visits", AGE_GROUPS, "All", False, True),
            ("GP Visits", AGE_GROUPS, "All", True, True),
            ("Hospitalisations", AGE_GROUPS, "All", False, False),
            ("Hospitalisations", AGE_GROUPS, "All", False, True),
            ("Hospitalisations", AGE_GROUPS, "All", True, True),
            ("Deaths", AGE_GROUPS, "All", False, False),
            ("Deaths", AGE_GROUPS, "All", False, True),
            ("Deaths", AGE_GROUPS, "All", True, True),
        ],
        age_separation="By Row",
    )
    download_preset_table(
        "AgesByColumn",
        columns=[
            (
                "Symptomatic Infections",
                ["Infant (7-24 Months)", "Young Child (3-5 Years)"],
                "All",
                False,
                True,
            ),
            (
                "Symptomatic Infections",
                ["Child (6-12 Years)", "Adolescent (13-17 Years)"],
                "All",
                False,
                True,
            ),
            ("Symptomatic Infections", AGE_GROUPS, "All", False, True),
            (
                "GP Visits",
                ["Infant (7-24 Months)", "Young Child (3-5 Years)"],
                "All",
                False,
                True,
            ),
            (
                "GP Visits",
                ["Child (6-12 Years)", "Adolescent (13-17 Years)"],
                "All",
                False,
                True,
            ),
            ("GP Visits", AGE_GROUPS, "All", False, True),
            (
                "Hospitalisations",
                ["Infant (7-24 Months)", "Young Child (3-5 Years)"],
                "All",
                False,
                True,
            ),
            (
                "Hospitalisations",
                ["Child (6-12 Years)", "Adolescent (13-17 Years)"],
                "All",
                False,
                True,
            ),
            ("Hospitalisations", AGE_GROUPS, "All", False, True),
            (
                "Deaths",
                ["Infant (7-24 Months)", "Young Child (3-5 Years)"],
                "All",
                False,
                True,
            ),
            (
                "Deaths",
                ["Child (6-12 Years)", "Adolescent (13-17 Years)"],
                "All",
                False,
                True,
            ),
            ("Deaths", AGE_GROUPS, "All", False, True),
        ],
        age_separation="By Column",
    )
