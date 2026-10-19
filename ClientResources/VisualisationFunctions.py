# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to generate and format tables and graphs

# Imports
import logging
from collections import defaultdict
from io import BytesIO
from math import ceil
from typing import Any, Literal, Optional, Sequence, cast

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import ColumnConfig

from ClientResources.Constants import MUTED_CODES, ROUND_RESULTS
from ClientResources.InterfaceFunctions import age_range_combiner
from ClientResources.Types import (
    AGE_GROUPS,
    COMMUNITIES,
    HEALTH_OUTCOMES,
    AgeWithTotal,
    AnalysisFile,
    ColumnDetails,
    HealthOutcome,
    SimParams,
)

# Logging
visualisation_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Server data has total at the front, so AGE_WITH_TOTAL must be custom defined
AGE_WITH_TOTAL: list[AgeWithTotal] = ["Total"]
AGE_WITH_TOTAL.extend(AGE_GROUPS)


def format_data(data: bytes, settings: AnalysisFile) -> pd.DataFrame:
    """
    Wrapper function to perform the correct formatting process on CSV data.

    Parameters:
        data (bytes): The CSV data to process.

        settings (AnalysisFile): The AnalysisFile containing the settings to use.

    Returns:
        DataFrame: The formatted data.
    """
    if settings.tool == "epidemic":
        return format_epidemic(
            data,
            settings.names,
            cast(HealthOutcome, settings.outcome),
            settings.use_cumulative,
            settings.split_by_age,
        )
    elif settings.tool == "asir":
        return format_asir(data, settings.names)
    else:
        raise ValueError(
            "Analysis tool was unrecognised; should be 'epidemic' or 'asir'"
        )


def format_epidemic(
    raw_csv: bytes,
    scenario_names: list[str],
    outcome_name: HealthOutcome = "Symptomatic Infections",
    cumulative=False,
    split_by_age=False,
) -> pd.DataFrame:
    """
    Function to convert raw data from the 'epidemic' Flusim analysis tool
    into the desired dataframe format for graphs.

    Parameters:
        raw_csv (bytes): The CSV output of the 'epidemic' analysis function,
            obtained from the server after running the simulation.

        scenario_names (list of str): A list of strings containing the names of
            the different scenarios that were simulated (since the CSV just
            uses non-descriptive placeholders).

        outcome_name (str): A string indicating the health outcome the epidemic
            data represents. Currently unused. Accepts any of the following values:
             - Symptomatic Infections (default)
             - Diagnosed Cases
             - Hospitalisations
             - ICU Visits
             - GP Visits
             - Deaths

        cumulative (bool): Set to `True` when the CSV contains cumulative
            data instead of individual data.

        split_by_age: Set to `True` when the CSV data has separate
            columns for each age group. Currently unimplemented.

    Returns:
        formatted_data (DataFrame): A dataframe containing the data, reshaped
            into a format more easily used by Altair's charts.

    Raises:
        ValueError: If `scenario_names` is not a list of strings or `outcome`
            is not one of the recognised health burden outcomes.

        NotImplementedError: If `split_by_age` is enabled before it is
            implemented.
    """

    # Validate parameters
    try:
        if not isinstance(scenario_names, list) or not all(
            isinstance(name, str) for name in scenario_names
        ):
            raise ValueError(
                "scenario_names should be a list of "
                f"strings; was {type(scenario_names)}."
            )
        if not scenario_names:
            raise ValueError("scenario_names should not be empty.")
        if outcome_name not in HEALTH_OUTCOMES:
            raise ValueError(
                'outcome should be either "Symptomatic Infections", "Diagnosed'
                ' Cases", "Hospitalisations", "ICU Visits", "GP Visits", or '
                f'"Deaths"; was "{outcome_name}".'
            )
    except Exception as e:
        visualisation_log.error(
            f"[format_epidemic] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e
    outcome = "Infections"  # TODO: placeholder until other burdens can be graphed
    # Generate and format the dataframe
    if split_by_age:
        # TODO: Complete if desired
        raise NotImplementedError(
            "Separating epidemic data by age is not "
            "currently supported by the dashboard."
        )
    else:
        type_mapping: defaultdict[int, Any] = defaultdict(lambda: np.float64, {0: int})
        framed_data = pd.read_csv(
            BytesIO(raw_csv),
            header=0,
            names=["Days Since First Infection"] + scenario_names,
            dtype=type_mapping,
        )

        # Fill null values
        if cumulative:
            framed_data = framed_data.ffill()
        else:
            framed_data = framed_data.fillna(0.0)

        # Reshape data for better Altair usage
        value_label = f"Total {outcome}" if cumulative else f"{outcome} per Day"
        melted_data = framed_data.melt(
            "Days Since First Infection", var_name="Scenario", value_name=value_label
        )

        # Scale the data
        scaling_factor = session.sim_params.scaling_factor
        melted_data[value_label] = melted_data[value_label] * scaling_factor

        # Round results if necessary
        if ROUND_RESULTS:
            return melted_data.round()
        else:
            return melted_data


def plot_epidemic(
    data: pd.DataFrame,
    scenario_names: list[str],
    included_scenarios: list[str],
    outcome_name: HealthOutcome = "Symptomatic Infections",
    cumulative=False,
) -> alt.LayerChart:
    """
    Function to create an Altair line graph of time-series data obtained
    from the 'epidemic' Flusim analysis tool.

    Parameters:
        data (DataFrame): A dataframe containing the epidemic data, processed
            with the format_epidemic function.

        scenario_names (list of str): An ordered list of all scenarios in
            the data, included or otherwise.

        included_scenarios (list of str): A list of strings containing
            the names of scenarios that will be included in the table.

        outcome_name (str): A string indicating the health outcome the epidemic
            data represents. Currently unused. Accepts any of the following values:
             - Symptomatic Infections (default)
             - Diagnosed Cases
             - Hospitalisations
             - ICU Visits
             - GP Visits
             - Deaths

        cumulative (bool): Set to `True` when the DataFrame contains
            cumulative data instead of individual data.

    Returns:
        LayerChart: An Altair plot layering a line graph of the infection
            data with a point chart that allows tooltips to appear on the line
            without needing to hover over the line exactly.

    Raises:
        ValueError: If `data` is not a `DataFrame` or `outcome` is not one of
            the recognised health burden outcomes.
    """

    # Validate parameters
    try:
        if not isinstance(data, pd.DataFrame):
            raise ValueError(f"data should be a DataFrame, was {type(data)}")
    except Exception as e:
        visualisation_log.error(
            f"[plot_epidemic] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e
    assert set(included_scenarios).issubset(
        scenario_names
    ), "Included scenarios not in data"
    outcome = "Infections"  # TODO: placeholder until other burdens can be graphed

    # Remove any scenarios/age groups not specified in the data
    filtered_data = data[data["Scenario"].isin(included_scenarios)]
    filtered_data["Scenario Index"] = filtered_data["Scenario"].map(
        included_scenarios.index
    )

    # Reusable chart components
    y_label = f"Total {outcome}" if cumulative else f"{outcome} per Day"
    scenario_colours = [
        MUTED_CODES[scenario_names.index(scenario)] for scenario in included_scenarios
    ]
    tooltip_selection = alt.selection_point(
        fields=["Days Since First Infection"],
        nearest=True,
        on="pointerover",
        empty=False,
        clear="pointerout",
    )

    # Define the chart itself
    chart_base = alt.Chart(
        filtered_data,
        title=(
            f"Cumulative Median {outcome} Over Time"
            if cumulative
            else f"Median {outcome} per Day Over Time"
        ),
    ).encode(
        x=alt.X("Days Since First Infection:Q").scale(
            nice=False,
            domain=(0, ceil(data["Days Since First Infection"].max() / 10) * 10),
        )
    )

    # Plot the lines
    chart_lines = chart_base.mark_line(interpolate="natural").encode(
        y=f"{y_label}:Q",
        color=alt.Color("Scenario:N").scale(
            domain=included_scenarios, range=scenario_colours
        ),
    )

    # Highlight x-value at mouse with vertical rule
    chart_points = chart_lines.mark_point().transform_filter(tooltip_selection)
    chart_rule = (
        chart_base.transform_pivot(
            "Scenario Index", value=y_label, groupby=["Days Since First Infection"]
        )
        .mark_rule(color="grey")
        .encode(
            opacity=alt.when(tooltip_selection)
            .then(alt.value(0.3))
            .otherwise(alt.value(0)),
            tooltip=["Days Since First Infection:Q"]
            + [
                alt.Tooltip(str(index), type="quantitative", title=scenario)
                for index, scenario in enumerate(included_scenarios)
            ],
        )
        .add_params(tooltip_selection)
    )

    # Return all plots combined
    return chart_lines + chart_points + chart_rule


def format_asir(raw_csv: bytes, scenario_names: list[str]) -> pd.DataFrame:
    """
    Function to convert raw data from the age-specific infection rate
    ('asir') Flusim analysis tool into the desired dataframe format for
    tables and other visualisations.

    Parameters:
        raw_csv (bytes): The CSV output of the 'asir' analysis function,
            obtained from the server after running the simulation.

        scenario_names (list of str): A list of strings containing the names of
            the different scenarios that were simulated (since the CSV just
            uses non-descriptive placeholders). This list should contain the
            names of all scenarios in the simulation, even if not all of them
            will be included in the final table.
    """
    # Validate parameters
    try:
        if not scenario_names:
            raise ValueError("scenario_names should not be empty.")
        if not isinstance(scenario_names, list) or not all(
            isinstance(name, str) for name in scenario_names
        ):
            raise ValueError(
                "scenario_names should be a list of "
                f"strings; was {type(scenario_names)}."
            )
    except Exception as e:
        visualisation_log.error(
            f"[format_asir] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e

    # Generate and format the dataframe
    type_mapping: defaultdict[int, Any] = defaultdict(lambda: np.float64, {0: str})
    framed_data = pd.read_csv(
        BytesIO(raw_csv),
        header=0,
        index_col=0,
        dtype=type_mapping,
    )
    visualisation_log.info(
        f"Scenario names are {scenario_names}; current index is {framed_data.index}"
    )
    framed_data.columns = pd.Index(AGE_WITH_TOTAL)

    # Scale the data by population and symptomatic likelihood
    sim_params: SimParams = session.sim_params
    population_scale = sim_params.scaling_factor
    framed_data.iloc[:, 0:] *= population_scale
    asymptomatic_child, asymptomatic_adult = zip(*sim_params.symptomatic_rates)
    framed_data.loc[:, AGE_GROUPS[:6]] = framed_data.loc[:, list(AGE_GROUPS[:6])].mul(
        asymptomatic_child, axis=0
    )
    framed_data.loc[:, AGE_GROUPS[6:]] = framed_data.loc[:, list(AGE_GROUPS[6:])].mul(
        asymptomatic_adult, axis=0
    )

    # Reset indices
    framed_data.index = pd.Index(scenario_names)
    framed_data.reset_index(names="Scenario", inplace=True)

    # Reshape data for better Streamlit usage with placeholder infections
    return framed_data.melt("Scenario", var_name="Age Group", value_name="Base Values")


def scale_asir_column(
    data: pd.DataFrame,
    outcome: HealthOutcome,
    baseline_data: pd.Series,
    baseline_scenario_name: str,
) -> tuple[pd.Series, pd.Series]:
    """
    Function to scale the values of ASIR data based on the occurrence rates
    for a given health burden outcome.

    Parameters:
        data (DataFrame): The ASIR data to be scaled.

        outcome (str): The outcome the data must be scaled by.

        baseline_data (Series): A version of the data with the baseline
            scenario's infection rates copied over all other scenarios,
            used for calculating difference-from-baseline columns.

        baseline_scenario_name (str): The name of the baseline scenario.

    Returns:
        (tuple with 2 Series): The ASIR values scaled based on the required
            health burdens, and the baseline data scaled based on the required
            health burdens.
    """
    # TODO: see if making rates parameters is more efficient
    health_rates = session.sim_params.health_outcome_rates
    age_rates = session.sim_params.age_health_outcome_rates
    match outcome:
        case "Symptomatic Infections":
            # No scaling necessary
            scaled_column = data["Base Values"].copy()
            scaled_baseline = baseline_data.copy()
        case "Hospitalisations" | "ICU Visits" | "Deaths":
            # Get age-specific rates
            burden_rates = pd.DataFrame(age_rates[outcome]).T.stack()
            data_index_values = pd.MultiIndex.from_frame(
                data[["Scenario", "Age Group"]]
            )
            scaled_column = data["Base Values"] * pd.Series(
                data_index_values.map(burden_rates), index=data.index
            ).fillna(data["Scenario"].map(health_rates[outcome]))

            baseline_rates = age_rates[outcome][baseline_scenario_name]
            scaled_baseline = baseline_data * (
                data["Age Group"]
                .map(baseline_rates)
                .fillna(health_rates[outcome][baseline_scenario_name])
            )

        case _:
            scaled_column = data["Base Values"] * data["Scenario"].map(
                health_rates[outcome]
            )
            scaled_baseline = (
                baseline_data * health_rates[outcome][baseline_scenario_name]
            )
    if ROUND_RESULTS:
        return scaled_column.round(), scaled_baseline.round()
    else:
        return scaled_column, scaled_baseline


def recalculate_totals(
    data: pd.Series, baseline_data: pd.Series, scenario_count: int
) -> tuple[pd.Series, pd.Series]:
    """
    Recalculates the first few total cells in ASIR data to account for
    rounding differences.

    Parameters:
        data (Series): The ASIR data to have new totals calculated.

        baseline_data (Series): A version of the data with the baseline
            scenario's infection rates copied over all other scenarios,
            used for calculating difference-from-baseline columns.

        scenario_count (str): The number of scenarios represented in the
            columns.

    Returns:
        (tuple with 2 Series): The two column inputs with their total cells
            recalculated to be accurate to the sum of the rest of the cells in
            the column.
    """
    total_data, total_baseline = data.copy(), baseline_data.copy()
    total_data.iloc[:scenario_count] = (
        data.groupby(data.index % scenario_count).sum() - data.iloc[:scenario_count]
    )
    total_baseline.iloc[:scenario_count] = total_data.iloc[0]
    return total_data, total_baseline


def generate_asir(
    base_data: pd.DataFrame,
    scenario_names: list[str],
    age_separation: Literal["Combined", "By Row", "By Column"] = "Combined",
    columns: Sequence[ColumnDetails] = [
        ("Symptomatic Infections", [], "All", False, False)
    ],
    included_scenarios: Optional[list[str]] = None,
    included_ages: Optional[list[AgeWithTotal]] = None,
    vaccinated_data: Optional[pd.DataFrame] = None,
) -> tuple[
    pd.DataFrame,
    dict[tuple[str, str], ColumnConfig],
    set[tuple[str, str]],
    set[tuple[str, str]],
]:
    """
    Function to create a table of health burden data obtained
    from the 'asir' Flusim analysis tool.

    Parameters:
        base_data (DataFrame): A DataFrame containing the asir data, processed
            with the format_asir function.

        scenario_names (list of str): A list of strings containing the names of
            the different scenarios that were simulated (since the CSV just
            uses non-descriptive placeholders). This list should contain the
            names of all scenarios in the simulation, even if not all of them
            will be included in the final table.

        age_separation (str): A string indicating whether different age groups
            should be represented with additional rows or columns. Can be
            either `Combined` (do not separate values by age group at all),
            `By Row` (include extra rows for each age group), or `By Column`
            (use different age groups for each column).

        columns (sequence of tuples): A list
            of tuples representing the settings each column should have. The
            values in each tuple are as follows:
             - the health burden outcome to display
             - which age groups the column should represent (ignored if
            `age_separation` is `Combined` or `By Row`)
             - what vaccination status the column should represent
             - whether or not the column should display percentages
             - whether or not the column should display the difference from
            the baseline scenario's values

        included_scenarios (list of str, optional): A list of strings
            containing the names of scenarios that will be included in
            the table. If this is `None`, all scenarios will be included.

        included_ages (list of str, optional): A list of strings
            containing the names of age groups that will be included in the
            table. If this is `None`, all age groups will be included. However,
            if this is an empty list, the age group column will be omitted
            entirely. Ignored if `age_separation` is `Combined` or `By Column`.

        vaccinated_data (Dataframe, optional): A DataFrame containing asir data
            specifically for vaccinated individuals in the simulation.

    Returns:
        formatted_data (DataFrame): A dataframe containing the data,
            reshaped into a format more easily used for table construction.

        column_config (dict of str tuples and ColumnConfig): A dictionary
            storing the configuration settings for each column in the table.

        percent_columns (set of str tuples): A set of strings holding the names
            of each column that uses percentage formatting.

        difference_columns (set of str tuples): A set of strings holding the
            names of each column that uses difference from baseline formatting.

    Raises:
        ValueError: If `scenario_names` is not a list of strings or columns
            are not formatted correctly.
    """
    # TODO: Improve efficiency (don't calculate age rows if age_separation isn't By Row)

    # Validate parameters
    try:
        if not scenario_names:
            raise ValueError("scenario_names should not be empty.")
        if not isinstance(scenario_names, list) or not all(
            isinstance(name, str) for name in scenario_names
        ):
            raise ValueError(
                "scenario_names should be a list of "
                f"strings; was {type(scenario_names)}."
            )
        if not columns:
            raise ValueError("columns should not be empty.")
        if not all(
            isinstance(col, tuple)
            and len(col) == 5
            and col[0] in HEALTH_OUTCOMES
            and set(col[1]).issubset(AGE_WITH_TOTAL)
            and col[2] in {"All", "Vaccinated", "Unvaccinated"}
            for col in columns
        ):
            raise ValueError(f"columns was not correctly formatted; was {columns}.")
    except Exception as e:
        visualisation_log.error(
            f"[generate_asir] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e
    # Convert None values for included_scenarios/Ages to refer to all values
    if included_scenarios is None:
        included_scenarios = scenario_names
    if included_ages is None:
        included_ages = AGE_WITH_TOTAL

    # Empty included_ages if not doing age rows
    if age_separation != "By Row":
        included_ages = []

    # Useful constants
    full_data = base_data.copy()
    age_pops = COMMUNITIES[session.sim_params.community].age_pops
    scenario_count = len(scenario_names)
    age_indices = {
        age: range(index * scenario_count, (index * scenario_count) + scenario_count)
        for index, age in enumerate(AGE_WITH_TOTAL)
    }

    # Generate baseline data for columns that need it
    baseline_scenario_name = scenario_names[0]
    baseline_rows = (
        full_data.loc[full_data["Scenario"] == baseline_scenario_name]
        .drop("Scenario", axis=1)
        .set_index("Age Group")
    )
    full_baselines = full_data["Age Group"].map(baseline_rows["Base Values"])

    # Generate vaccinated baseline data if needed
    vaccinated_baselines = pd.Series()
    if vaccinated_data is not None:
        vaccinated_data = vaccinated_data.copy()
        vaccinated_baseline_rows = (
            vaccinated_data.loc[vaccinated_data["Scenario"] == baseline_scenario_name]
            .drop("Scenario", axis=1)
            .set_index("Age Group")
        )
        vaccinated_baselines = vaccinated_data["Age Group"].map(
            vaccinated_baseline_rows["Base Values"]
        )

    # Prepare burden-scaled columns beforehand for efficiency
    required_outcomes: set[HealthOutcome] = {outcome for outcome, _, _, _, _ in columns}
    outcome_columns: dict[tuple[str, str], pd.Series[Any]] = {}
    outcome_baselines: dict[tuple[str, str], pd.Series[Any]] = {}
    for outcome in required_outcomes:
        # Scale data and generate vaccinated/unvaccinated splits
        scaled_column, scaled_baseline = scale_asir_column(
            full_data, outcome, full_baselines, baseline_scenario_name
        )
        scaled_column, scaled_baseline = recalculate_totals(
            scaled_column, scaled_baseline, scenario_count
        )
        outcome_columns[(outcome, "All")] = scaled_column
        outcome_baselines[(outcome, "All")] = scaled_baseline
        if vaccinated_data is not None:
            vaccinated_column, vaccinated_baseline = scale_asir_column(
                vaccinated_data,
                outcome,
                vaccinated_baselines,
                baseline_scenario_name,
            )
            vaccinated_column, vaccinated_baseline = recalculate_totals(
                vaccinated_column, vaccinated_baseline, scenario_count
            )
            outcome_columns[(outcome, "Vaccinated")] = vaccinated_column
            outcome_baselines[(outcome, "Vaccinated")] = vaccinated_baseline

            unvaccinated_column = scaled_column - vaccinated_column
            unvaccinated_baseline = scaled_baseline - vaccinated_baseline
            unvaccinated_column, unvaccinated_baseline = recalculate_totals(
                unvaccinated_column, unvaccinated_baseline, scenario_count
            )
            outcome_columns[(outcome, "Unvaccinated")] = unvaccinated_column
            outcome_baselines[(outcome, "Unvaccinated")] = unvaccinated_baseline

    # Remove the base values column once it's redundant
    full_data.drop("Base Values", axis=1, inplace=True)

    # Format as MultiIndex
    full_data.columns = pd.MultiIndex.from_product(([""], full_data.columns))

    # Generate config data for Streamlit display
    percent_columns, difference_columns = set(), set()
    column_config = {}
    column_config[("", "Scenario Name")] = st.column_config.TextColumn(pinned=True)
    column_config[("", "Age Group")] = st.column_config.TextColumn(pinned=True)

    # Generate columns
    for outcome, age_groups, vaccine_status, use_proportion, use_difference in columns:
        current_column = outcome_columns[(outcome, vaccine_status)].copy()
        current_baseline = outcome_baselines[(outcome, vaccine_status)].copy()
        column_name = f"{"" if vaccine_status == "All" else vaccine_status} {outcome}"
        column_suffix = ""

        # Replace values with those of summed age groups
        if age_separation == "By Column":
            if set(age_groups) == set(AGE_GROUPS):
                age_groups = cast(Sequence[AgeWithTotal], ["Total"])
            filtered_column = current_column.iloc[
                np.array([index for age in age_groups for index in age_indices[age]])
            ]
            column_sums = filtered_column.groupby(
                filtered_column.index % scenario_count
            ).sum()
            current_column = pd.concat([column_sums] * 11, ignore_index=True)
            current_baseline = pd.Series(
                column_sums[0], index=range(11 * scenario_count)
            )
            column_suffix += f"{age_range_combiner(list(age_groups))} "

        # Apply proportion/difference modifications
        if use_proportion and not use_difference:
            # Get required total population
            scaling_factor = session.sim_params.scaling_factor
            if age_separation == "By Column":
                population_column: int | pd.Series = scaling_factor * sum(
                    age_pops[age] for age in age_groups
                )
            else:
                population_column = (
                    full_data[("", "Age Group")].map(age_pops) * scaling_factor
                )
            current_column /= population_column
            column_suffix += "%"
            percent_columns.add((column_name, column_suffix))
        elif not use_proportion and use_difference:
            current_column = current_baseline - current_column
            column_suffix += "Averted"
            difference_columns.add((column_name, column_suffix))
        elif use_proportion and use_difference:
            current_column = current_baseline - current_column
            # Account for potential division by 0
            current_column = (current_column / current_baseline).where(
                current_baseline != 0, other=np.nan
            )
            column_suffix += "% Averted"
            percent_columns.add((column_name, column_suffix))
            difference_columns.add((column_name, column_suffix))
        else:
            column_suffix += "Total"

        # Formally create the column and add config details
        full_data[(column_name, column_suffix)] = current_column
        column_config[(column_name, column_suffix)] = st.column_config.NumberColumn(
            format="percent" if use_proportion else "localized"
        )

    # Remove any scenarios/age groups not specified in the data
    if set(scenario_names) != set(included_scenarios):
        full_data = full_data[full_data[("", "Scenario")].isin(included_scenarios)]
    if not included_ages:
        full_data = full_data[full_data[("", "Age Group")] == "Total"]
        full_data = full_data.drop(("", "Age Group"), axis=1)
    elif set(included_ages) != set(AGE_WITH_TOTAL):
        full_data = full_data[full_data[("", "Age Group")].isin(included_ages)]

    # Make index columns categorical
    full_data.loc[:, ("", "Scenario")] = pd.Categorical(
        full_data[("", "Scenario")],
        categories=scenario_names,
        ordered=True,
    )
    if included_ages:
        full_data.loc[:, ("", "Age Group")] = pd.Categorical(
            full_data[("", "Age Group")],
            categories=AGE_WITH_TOTAL,
            ordered=True,
        )

    # Order index using order of included_scenarios/included_ages
    if included_ages:
        full_data = (
            full_data.set_index([("", "Scenario"), ("", "Age Group")])
            .reindex(included_scenarios, level=0)
            .reindex(included_ages, level=1)
        )
    else:
        full_data = full_data.set_index(("", "Scenario")).reindex(included_scenarios)

    return full_data, column_config, percent_columns, difference_columns
