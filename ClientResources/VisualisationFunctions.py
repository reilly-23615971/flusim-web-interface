# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to generate and format tables and graphs

# Imports
import logging
from collections import defaultdict
from io import BytesIO
from math import ceil
from typing import Any, Literal, Optional, Sequence

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import ColumnConfig

from ClientResources.InterfaceFunctions import ageRangeCombiner
from ClientResources.SharedResources import (  # outcomeAdjectives,
    AnalysisFile,
    ageWithTime,
    communityAgePops,
    mutedCodes,
    roundResults,
    tableOutcomes,
)

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Dictionaries for generating column tooltips
outcomeDescriptions = {
    "Symptomatic Infections": "showing symptoms of the pathogen",
    "Diagnosed Cases": "formally diagnosed as cases of the pathogen",
    "Hospitalisations": "sent to a hospital due to the pathogen",
    "Deaths": "killed as a direct result of the pathogen",
    "ICU Visits": "committed to a hospital's Intensive Care Unit due to the pathogen",
    "GP Visits": (
        "prompted to visit their general practitioner "
        "after noticing the symptoms of the pathogen"
    ),
}
vaccineDescriptions = {
    "All": "",
    "Vaccinated": "vaccinated ",
    "Unvaccinated": "unvaccinated ",
}
ageWithTotal = ["Total"] + ageWithTime


def formatData(data: bytes, settings: AnalysisFile) -> pd.DataFrame:
    """
    Wrapper function to perform the correct formatting process on CSV data.

    Parameters:
        data (bytes): The CSV data to process.

        settings (AnalysisFile): The AnalysisFile containing the settings to use.

    Returns:
        DataFrame: The formatted data.
    """
    if settings.tool == "epidemic":
        return formatEpidemic(
            data,
            settings.names,
            settings.outcome,
            settings.useCumulative,
            settings.splitByAge,
        )
    elif settings.tool == "asir":
        return formatAsir(data, settings.names)
    else:
        raise ValueError(
            "Analysis tool was unrecognised; should be 'epidemic' or 'asir'"
        )


def formatEpidemic(
    rawCSV: bytes,
    scenarioNames: list[str],
    outcomeName: str = "Symptomatic Infections",
    cumulative=False,
    splitByAge=False,
) -> pd.DataFrame:
    """
    Function to convert raw data from the 'epidemic' Flusim analysis tool
    into the desired dataframe format for graphs.

    Parameters:
        rawCSV (bytes): The CSV output of the 'epidemic' analysis function, obtained
            from the server after running the simulation.

        scenarioNames (list of str): A list of strings containing the names of the
            different scenarios that were simulated (since the CSV just uses
            non-descriptive placeholders).

        outcome (str): A string indicating the health outcome the epidemic
            data represents. Can be either 'Symptomatic Infections', 'Diagnosed Cases',
            'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

        cumulative (bool): Set to `True` when the CSV contains cumulative
            data instead of individual data.

        splitByAge: Set to `True` when the CSV data has separate
            columns for each age group.

    Returns:
        formattedData (DataFrame): A dataframe containing the data, reshaped into
            a format more easily used by Altair's charts.

    Raises:
        ValueError: If `scenarioNames` is not a list of strings or `outcome`
            is not one of the recognised health burden outcomes.
    """
    # Validate parameters
    try:
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ):
            raise ValueError(
                f"scenarioNames should be a list of strings; was {type(scenarioNames)}."
            )
        if not scenarioNames:
            raise ValueError("scenarioNames should not be empty.")
        if outcomeName not in tableOutcomes:
            raise ValueError(f"""
                outcome should be either "Symptomatic Infections", "Diagnosed
                Cases", "Hospitalisations", "ICU Visits", "GP Visits", or "Deaths";
                was "{outcomeName}".
            """)
    except Exception as e:
        functionLog.error(
            (
                f"[formatEpidemic] Encountered {type(e).__name__} "
                f"while validating parameters: {e}"
            )
        )
        raise e
    outcome = "Infections"  # TODO: placeholder until other burdens can be graphed
    # Generate and format the dataframe
    if splitByAge:
        # TODO: Complete if desired
        return pd.DataFrame()
    else:
        typeMapping: defaultdict[int, Any] = defaultdict(lambda: np.float64, {0: int})
        framedData = pd.read_csv(
            BytesIO(rawCSV),
            header=0,
            names=["Days Since First Infection"] + scenarioNames,
            dtype=typeMapping,
        )

        # Fill null values
        if cumulative:
            framedData = framedData.ffill()
        else:
            framedData = framedData.fillna(0.0)

        # Reshape data for better Altair usage
        valueLabel = f"Total {outcome}" if cumulative else f"{outcome} per Day"
        meltedData = framedData.melt(
            "Days Since First Infection", var_name="Scenario", value_name=valueLabel
        )

        # Scale the data
        scalingFactor = session.SimParams.get("Scaling Factor", 1.0)
        meltedData[valueLabel] = meltedData[valueLabel] * scalingFactor

        # Round results if necessary
        if roundResults:
            return meltedData.round()
        else:
            return meltedData


def plotEpidemic(
    data: pd.DataFrame,
    scenarioNames: list[str],
    includedScenarios: list[str],
    outcomeName: str = "Symptomatic Infections",
    cumulative=False,
) -> alt.LayerChart:
    """
    Function to create an Altair line graph of time-series data obtained
    from the 'epidemic' Flusim analysis tool.

    Parameters:
        data (DataFrame): A dataframe containing the epidemic data, processed with
            the formatEpidemic function.

        scenarioNames (list of str): An ordered list of all scenarios in
            the data, included or otherwise.

        includedScenarios (list of str): A list of strings containing
            the names of scenarios that will be included in the table.

        outcomeName (str): A string indicating the health outcome the epidemic
            data represents. Accepts any of the following values:
             - Symptomatic Infections
             - Diagnosed Cases
             - Hospitalisations
             - ICU Visits
             - GP Visits
             - Deaths

        cumulative (bool): Set to `True` when the DataFrame contains
            cumulative data instead of individual data.

    Returns:
        finalPlot (LayerChart): An Altair plot layering a line graph of the infection
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
        if outcomeName not in tableOutcomes:
            raise ValueError(f"""
                outcome should be either "Symptomatic Infections", "Diagnosed
                Cases", "Hospitalisations", "ICU Visits", "GP Visits", or "Deaths";
                was "{outcomeName}".
            """)
    except Exception as e:
        functionLog.error(
            (
                f"[plotEpidemic] Encountered {type(e).__name__} "
                f"while validating parameters: {e}"
            )
        )
        raise e
    assert set(includedScenarios).issubset(
        scenarioNames
    ), "Included scenarios not in data"
    outcome = "Infections"  # TODO: placeholder until other burdens can be graphed

    # Remove any scenarios/age groups not specified in the data
    filteredData = data[data["Scenario"].isin(includedScenarios)]
    filteredData["Scenario Index"] = filteredData["Scenario"].map(
        includedScenarios.index
    )

    # Reusable chart components
    yLabel = f"Total {outcome}" if cumulative else f"{outcome} per Day"
    scenarioColours = [
        mutedCodes[scenarioNames.index(scenario)] for scenario in includedScenarios
    ]
    tooltipSelection = alt.selection_point(
        fields=["Days Since First Infection"],
        nearest=True,
        on="pointerover",
        empty=False,
        clear="pointerout",
    )

    # Define the chart itself
    chartBase = alt.Chart(
        filteredData,
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
    chartLines = chartBase.mark_line(interpolate="natural").encode(
        y=f"{yLabel}:Q",
        color=alt.Color("Scenario:N").scale(
            domain=includedScenarios, range=scenarioColours
        ),
    )

    # Highlight x-value at mouse with vertical rule
    chartPoints = chartLines.mark_point().transform_filter(tooltipSelection)
    chartRule = (
        chartBase.transform_pivot(
            "Scenario Index", value=yLabel, groupby=["Days Since First Infection"]
        )
        .mark_rule(color="grey")
        .encode(
            opacity=alt.when(tooltipSelection)
            .then(alt.value(0.3))
            .otherwise(alt.value(0)),
            tooltip=["Days Since First Infection:Q"]
            + [
                alt.Tooltip(str(index), type="quantitative", title=scenario)
                for index, scenario in enumerate(includedScenarios)
            ],
        )
        .add_params(tooltipSelection)
    )

    # Return all plots combined
    return chartLines + chartPoints + chartRule


def formatAsir(rawCSV: bytes, scenarioNames: list[str]) -> pd.DataFrame:
    """
    Function to convert raw data from the age-specific infection rate
    ('asir') Flusim analysis tool into the desired dataframe format for
    tables and other visualisations.

    Parameters:
        rawCSV (bytes): The CSV output of the 'asir' analysis function, obtained
            from the server after running the simulation.

        scenarioNames (list of str): A list of strings containing the names of the
            different scenarios that were simulated (since the CSV just uses
            non-descriptive placeholders). This list should contain the names
            of all scenarios in the simulation, even if not all of them will be
            included in the final table.
    """
    # Validate parameters
    try:
        if not scenarioNames:
            raise ValueError("scenarioNames should not be empty.")
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ):
            raise ValueError(
                f"scenarioNames should be a list of strings; was {type(scenarioNames)}."
            )
    except Exception as e:
        functionLog.error(
            f"[generateAsir] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e

    # Generate and format the dataframe
    typeMapping: defaultdict[int, Any] = defaultdict(lambda: np.float64, {0: str})
    framedData = pd.read_csv(
        BytesIO(rawCSV),
        header=0,
        index_col=0,
        dtype=typeMapping,
    )
    functionLog.info(
        f"Scenario names are {scenarioNames}; current index is {framedData.index}"
    )
    framedData.columns = pd.Index(ageWithTotal)

    # Scale the data by population and symptomatic likelihood
    simParams = session.SimParams
    populationScale = simParams["Scaling Factor"]
    framedData.iloc[:, 0:] *= populationScale
    asymptomaticChild, asymptomaticAdult = zip(*simParams["Asymptomatic Rates"])
    framedData.loc[:, ageWithTime[:6]] = framedData.loc[:, ageWithTime[:6]].mul(
        asymptomaticChild, axis=0
    )
    framedData.loc[:, ageWithTime[6:]] = framedData.loc[:, ageWithTime[6:]].mul(
        asymptomaticAdult, axis=0
    )

    # Reset indices
    framedData.index = pd.Index(scenarioNames)
    framedData.reset_index(names="Scenario", inplace=True)

    # Reshape data for better Streamlit usage with placeholder infections
    return framedData.melt("Scenario", var_name="Age Group", value_name="Base Values")


def scaleAsirColumn(
    data: pd.DataFrame, outcome: str, baselineData: pd.Series, baselineScenario: str
) -> tuple[pd.Series, pd.Series]:
    """
    Function to scale the values of ASIR data based on the occurrence rates
    for a given health burden outcome.

    Parameters:
        data (DataFrame): The ASIR data to be scaled.

        outcome (str): The outcome the data must be scaled by.

        baselineData (Series): A version of the data with the baseline
            scenario's infection rates copied over all other scenarios,
            used for calculating difference-from-baseline columns.

        baselineScenario (str): The name of the baseline scenario.

    Returns:
        (tuple with 2 Series): The ASIR values scaled based on the required
            health burdens, and the baseline data scaled based on the required
            health burdens.
    """
    # TODO: see if making rates parameters is more efficient
    healthRates = session.SimParams["Health Outcome Rates"]
    mortDict = session.SimParams["Age-Separated Health Outcome Rates"]
    match outcome:
        case "Symptomatic Infections":
            # No scaling necessary
            scaledColumn = data["Base Values"].copy()
            scaledBaseline = baselineData.copy()
        case "Deaths":
            # TODO: Update for any other outcomes that become age-specific
            deathRates = pd.DataFrame(mortDict).T.stack()
            dataIndexValues = pd.MultiIndex.from_frame(data[["Scenario", "Age Group"]])
            scaledColumn = data["Base Values"] * pd.Series(
                dataIndexValues.map(deathRates), index=data.index
            ).fillna(data["Scenario"].map(healthRates["Deaths"]))

            baselineDeath = mortDict[baselineScenario]
            scaledBaseline = baselineData * (
                data["Age Group"]
                .map(baselineDeath)
                .fillna(healthRates["Deaths"][baselineScenario])
            )

        case _:
            scaledColumn = data["Base Values"] * data["Scenario"].map(
                healthRates[outcome]
            )
            scaledBaseline = baselineData * healthRates[outcome][baselineScenario]
    if roundResults:
        return scaledColumn.round(), scaledBaseline.round()
    else:
        return scaledColumn, scaledBaseline


def recalculateTotals(
    data: pd.Series, baselineData: pd.Series, scenarioCount: int
) -> tuple[pd.Series, pd.Series]:
    """
    Recalculates the first few total cells in ASIR data to account for
    rounding differences.

    Parameters:
        data (Series): The ASIR data to have new totals calculated.

        baselineData (Series): A version of the data with the baseline
            scenario's infection rates copied over all other scenarios,
            used for calculating difference-from-baseline columns.

        scenarioCount (str): The number of scenarios represented in the columns.

    Returns:
        (tuple with 2 Series): The two column inputs with their total cells
            recalculated to be accurate to the sum of the rest of the cells in
            the column.
    """
    totalData, totalBaseline = data.copy(), baselineData.copy()
    totalData.iloc[:scenarioCount] = (
        data.groupby(data.index % scenarioCount).sum() - data.iloc[:scenarioCount]
    )
    totalBaseline.iloc[:scenarioCount] = totalData.iloc[0]
    return totalData, totalBaseline


def generateAsir(
    baseData: pd.DataFrame,
    scenarioNames: list[str],
    ageSeparation: Literal["Combined", "By Row", "By Column"] = "Combined",
    columns: Sequence[
        tuple[str, list[str], Literal["All", "Vaccinated", "Unvaccinated"], bool, bool]
    ] = [("Symptomatic Infections", [], "All", False, False)],
    includedScenarios: Optional[list[str]] = None,
    includedAges: Optional[list[str]] = None,
    vaccinatedData: Optional[pd.DataFrame] = None,
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
        baseData (DataFrame): A DataFrame containing the asir data, processed with
            the formatAsir function.

        scenarioNames (list of str): A list of strings containing the names of the
            different scenarios that were simulated (since the CSV just uses
            non-descriptive placeholders). This list should contain the names
            of all scenarios in the simulation, even if not all of them will be
            included in the final table.

        ageSeparation (str): A string indicating whether different age groups
            should be represented with additional rows or columns. Can be either
            `Combined` (do not separate values by age group at all), `By Row`
            (include extra rows for each age group), or `By Column` (use different
            age groups for each column).

        columns (sequence of tuples (str, list of str, str, bool, bool)): A list
            of tuples representing the settings each column should have. The
            values in each tuple are as follows:
             - the health burden outcome to display
             - which age groups the column should represent (ignored if
            `ageSeparation` is `Combined` or `By Row`)
             - what vaccination status the column should represent
             - whether or not the column should display percentages
             - whether or not the column should display the difference from
            the baseline scenario's values

        includedScenarios (list of str, optional): A list of strings
            containing the names of scenarios that will be included in
            the table. If this is `None`, all scenarios will be included.

        includedAges (list of str, optional): A list of strings
            containing the names of age groups that will be included in the
            table. If this is `None`, all age groups will be included. However,
            if this is an empty list, the age group column will be omitted entirely.
            Ignored if `ageSeparation` is `Combined` or `By Column`.

        vaccinatedData (Dataframe, optional): A DataFrame containing asir data
            specifically for vaccinated individuals in the simulation.

    Returns:
        formattedData (DataFrame): A dataframe containing the data,
            reshaped into a format more easily used for table construction.

        columnConfig (dict of str tuples and ColumnConfig): A dictionary storing
            the configuration settings for each column in the table.

        percentCols (set of str tuples): A set of strings holding the names of
            each column that uses percentage formatting.

        differenceCols (set of str tuples): A set of strings holding the names of
            each column that uses difference from baseline formatting.

    Raises:
        ValueError: If `scenarioNames` is not a list of strings or columns
            are not formatted correctly.
    """
    # TODO: Improve efficiency (don't calculate age rows if ageSeparation isn't By Row)

    # Validate parameters
    try:
        if not scenarioNames:
            raise ValueError("scenarioNames should not be empty.")
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ):
            raise ValueError(
                f"scenarioNames should be a list of strings; was {type(scenarioNames)}."
            )
        if not columns:
            raise ValueError("columns should not be empty.")
        if not isinstance(columns, list) or not all(
            isinstance(col, tuple)
            and len(col) == 5
            and col[0] in tableOutcomes
            and set(col[1]).issubset(ageWithTotal)
            and col[2] in {"All", "Vaccinated", "Unvaccinated"}
            for col in columns
        ):
            raise ValueError(f"columns was not correctly formatted; was {columns}.")
    except Exception as e:
        functionLog.error(
            f"[generateAsir] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e
    # Convert None values for includedScenarios/Ages to refer to all values
    if includedScenarios is None:
        includedScenarios = scenarioNames
    if includedAges is None:
        includedAges = ageWithTime + ["Total"]

    # Empty includedAges if not doing age rows
    if ageSeparation != "By Row":
        includedAges = []

    # Useful constants
    fullData = baseData.copy()
    agePops = communityAgePops[session.SimParams["Community"]]
    scenarioCount = len(scenarioNames)
    ageIndices = {
        age: range(index * scenarioCount, (index * scenarioCount) + scenarioCount)
        for index, age in enumerate(ageWithTotal)
    }

    # Generate baseline data for columns that need it
    baselineScenario = scenarioNames[0]
    baselineRows = (
        fullData.loc[fullData["Scenario"] == baselineScenario]
        .drop("Scenario", axis=1)
        .set_index("Age Group")
    )
    fullBaselines = fullData["Age Group"].map(baselineRows["Base Values"])

    # Generate vaccinated baseline data if needed
    vaccinatedBaselines = pd.Series()
    if vaccinatedData is not None:
        vaccinatedData = vaccinatedData.copy()
        vaccinatedBaselineRows = (
            vaccinatedData.loc[vaccinatedData["Scenario"] == baselineScenario]
            .drop("Scenario", axis=1)
            .set_index("Age Group")
        )
        vaccinatedBaselines = vaccinatedData["Age Group"].map(
            vaccinatedBaselineRows["Base Values"]
        )

    # Prepare burden-scaled columns beforehand for efficiency
    requiredOutcomes = {outcome for outcome, _, _, _, _ in columns}
    outcomeColumns: dict[tuple[str, str], pd.Series[Any]] = {}
    outcomeBaselines: dict[tuple[str, str], pd.Series[Any]] = {}
    for outcome in requiredOutcomes:
        # Scale data and generate vaccinated/unvaccinated splits
        scaledColumn, scaledBaseColumn = scaleAsirColumn(
            fullData, outcome, fullBaselines, baselineScenario
        )
        scaledColumn, scaledBaseColumn = recalculateTotals(
            scaledColumn, scaledBaseColumn, scenarioCount
        )
        outcomeColumns[(outcome, "All")] = scaledColumn
        outcomeBaselines[(outcome, "All")] = scaledBaseColumn
        if vaccinatedData is not None:
            vaccinatedColumn, vaccinatedBaseColumn = scaleAsirColumn(
                vaccinatedData,
                outcome,
                vaccinatedBaselines,
                baselineScenario,
            )
            vaccinatedColumn, vaccinatedBaseColumn = recalculateTotals(
                vaccinatedColumn, vaccinatedBaseColumn, scenarioCount
            )
            outcomeColumns[(outcome, "Vaccinated")] = vaccinatedColumn
            outcomeBaselines[(outcome, "Vaccinated")] = vaccinatedBaseColumn

            unvaccinatedColumn = scaledColumn - vaccinatedColumn
            unvaccinatedBaseColumn = scaledBaseColumn - vaccinatedBaseColumn
            unvaccinatedColumn, unvaccinatedBaseColumn = recalculateTotals(
                unvaccinatedColumn, unvaccinatedBaseColumn, scenarioCount
            )
            outcomeColumns[(outcome, "Unvaccinated")] = unvaccinatedColumn
            outcomeBaselines[(outcome, "Unvaccinated")] = unvaccinatedBaseColumn

    # Remove the base values column once it's redundant
    fullData.drop("Base Values", axis=1, inplace=True)

    # Format as MultiIndex
    fullData.columns = pd.MultiIndex.from_product(([""], fullData.columns))

    # Generate config data for Streamlit display
    percentCols, differenceCols = set(), set()
    columnConfig = {}
    columnConfig[("", "Scenario Name")] = st.column_config.TextColumn(pinned=True)
    columnConfig[("", "Age Group")] = st.column_config.TextColumn(pinned=True)

    # Generate columns
    for outcome, ageGroups, vaccineStatus, proportion, baselineDifference in columns:
        currentColumn = outcomeColumns[(outcome, vaccineStatus)].copy()
        columnBaselines = outcomeBaselines[(outcome, vaccineStatus)].copy()
        columnName = f"{"" if vaccineStatus == "All" else vaccineStatus} {outcome}"
        columnSuffix = ""

        # Replace values with those of summed age groups
        if ageSeparation == "By Column":
            if set(ageGroups) == set(ageWithTime):
                ageGroups = ["Total"]
            filteredColumn = currentColumn.iloc[
                np.array([index for age in ageGroups for index in ageIndices[age]])
            ]
            columnSums = filteredColumn.groupby(
                filteredColumn.index % scenarioCount
            ).sum()
            currentColumn = pd.concat([columnSums] * 11, ignore_index=True)
            columnBaselines = pd.Series(columnSums[0], index=range(11 * scenarioCount))
            columnSuffix += f"{ageRangeCombiner(ageGroups)} "

        # Apply proportion/difference modifications
        # TODO: Either fix or disable just proportion
        if proportion and not baselineDifference:
            # Get required total population
            scalingFactor = session.SimParams.get("Scaling Factor", 1.0)
            if ageSeparation == "By Column":
                populationColumn: int | pd.Series = scalingFactor * sum(
                    agePops[age] for age in ageGroups
                )
            else:
                populationColumn = (
                    fullData[("", "Age Group")].map(agePops) * scalingFactor
                )
            currentColumn /= populationColumn
            columnSuffix += "%"
            percentCols.add((columnName, columnSuffix))
        elif not proportion and baselineDifference:
            currentColumn = currentColumn - columnBaselines
            columnSuffix = "Difference from Baseline"
            differenceCols.add((columnName, columnSuffix))
        elif proportion and baselineDifference:
            currentColumn = currentColumn - columnBaselines
            # Account for potential division by 0
            currentColumn = (currentColumn / columnBaselines).where(
                columnBaselines != 0, other=np.nan
            )
            columnSuffix = "% Difference from Baseline"
            percentCols.add((columnName, columnSuffix))
            differenceCols.add((columnName, columnSuffix))
        else:
            columnSuffix += "Total"

        # Formally create the column and add config details
        fullData[(columnName, columnSuffix)] = currentColumn
        columnConfig[(columnName, columnSuffix)] = st.column_config.NumberColumn(
            format="percent" if proportion else "localized"
        )

    # Remove any scenarios/age groups not specified in the data
    if set(scenarioNames) != set(includedScenarios):
        fullData = fullData[fullData[("", "Scenario")].isin(includedScenarios)]
    if not includedAges:
        fullData = fullData[fullData[("", "Age Group")] == "Total"]
        fullData = fullData.drop(("", "Age Group"), axis=1)
    elif set(includedAges) != set(ageWithTotal):
        fullData = fullData[fullData[("", "Age Group")].isin(includedAges)]

    # Make index columns categorical
    fullData.loc[:, ("", "Scenario")] = pd.Categorical(
        fullData[("", "Scenario")],
        categories=scenarioNames,
        ordered=True,
    )
    if includedAges:
        fullData.loc[:, ("", "Age Group")] = pd.Categorical(
            fullData[("", "Age Group")],
            categories=ageWithTotal,
            ordered=True,
        )

    # Order index using order of includedScenarios/includedAges
    if includedAges:
        fullData = (
            fullData.set_index([("", "Scenario"), ("", "Age Group")])
            .reindex(includedScenarios, level=0)
            .reindex(includedAges, level=1)
        )
    else:
        fullData = fullData.set_index(("", "Scenario")).reindex(includedScenarios)

    return fullData, columnConfig, percentCols, differenceCols
