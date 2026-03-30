# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by tables and graphs

# Imports
import logging
from io import BytesIO
from math import ceil
from typing import Any, Literal

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import ColumnConfig

from ClientResources.SharedResources import (
    AnalysisFile,
    ageWithTime,
    brightCodes,
    communityAgePops,
    outcomeAdjectives,
    tableOutcomes,
)

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Dictionary getting health outcome descriptions
outcomeDescriptions = {
    "Symptomatic Infections": "showing symptoms of the disease",
    "Diagnosed Cases": "formally diagnosed as cases of the disease",
    "Hospitalisations": "sent to a hospital due to the disease",
    "Deaths": "killed as a direct result of the disease",
    "ICU Visits": "committed to a hospital's Intensive Care Unit due to the disease",
    "GP Visits": (
        "prompted to visit their general practitioner "
        "after noticing the symptoms of the disease"
    ),
}


def formatData(data: bytes, settings: AnalysisFile) -> tuple[pd.DataFrame | bytes, str]:
    """
    Wrapper function to perform the correct formatting process on csv data

    Parameters:
        data (bytes): The CSV data to process.

        settings (AnalysisFile): The AnalysisFile containing the settings to use.

    Returns:

    """
    if settings.tool == "epidemic":
        typeTag = "Cumulative" if settings.useCumulative else "Daily"
        return (
            formatEpidemic(
                data,
                settings.names,
                settings.outcome,
                settings.useCumulative,
                settings.splitByAge,
            ),
            f"Epidemic{typeTag}",
        )
    # Leave asir alone since it gets formatted when generating the table
    elif settings.tool == "asir":
        return data, "RawAsir"
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
    into the desired DataFrame format for graphs

    Parameters:
        rawCSV (bytes): The CSV output of the 'epidemic' analysis function, obtained
            from the server after running the simulation.

        scenarioNames (list of str): A list of strings containing the names of the
            different scenarios that were simulated (since the CSV just uses
            non-descriptive placeholders).

        outcome (str): A string indicating the health outcome the epidemic
            data represents. Can be either 'Symptomatic Infections', 'Diagnosed Cases',
            'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

        cumulative (bool): Set to True when the CSV contains cumulative
            data instead of individual data.

        splitByAge: Set to True when the CSV data has separate
            columns for each age group.

    Returns:
        formattedData (DataFrame): A pandas DataFrame containing the data, reshaped into
            a format more easily used by Altair's charts.

    Raises:
        ValueError: If scenarioNames is not a list of strings or outcome
            is not one of the recognised health burden outcomes.
    """
    # Validate parameters
    try:
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ):
            raise ValueError(
                (
                    "scenarioNames should be a list of "
                    f"strings; was {type(scenarioNames)}."
                )
            )
        if not scenarioNames:
            raise ValueError("scenarioNames should not be empty.")
        if outcomeName not in tableOutcomes:
            raise ValueError(
                (
                    'outcome should be either "Symptomatic Infections", '
                    "Diagnosed Cases",
                    "Hospitalisations",
                    "ICU Visits",
                    "" f'"GP Visits", or "Deaths"; was "{outcomeName}".',
                )
            )
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
        # TODO: Complete if desired; not sure how useful/desirable
        # age-split time series graphs will be (redundant with asir)
        return pd.DataFrame()
    else:
        framedData = pd.read_csv(
            BytesIO(rawCSV),
            header=0,
            names=["Days Since First Infection"] + scenarioNames,
        )
        if cumulative:
            framedData = framedData.ffill().round()
        else:
            framedData = framedData.fillna(0.0).round()

        # Reshape data for better Altair usage
        valueLabel = f"Total {outcome}" if cumulative else f"{outcome} per Day"

        return framedData.melt(
            "Days Since First Infection", var_name="Scenario", value_name=valueLabel
        )


def plotEpidemic(
    data: pd.DataFrame,
    outcomeName: str = "Symptomatic Infections",
    cumulative=False,
    includedScenarios: list[str] | Literal["all"] = "all",
) -> alt.LayerChart:
    """
    Function to create an Altair line graph of time-series data obtained
    from the 'epidemic' Flusim analysis tool

    Parameters:
        data (DataFrame): A DataFrame containing the epidemic data, processed with
            the formatEpidemic function.

        outcome (str): A string indicating the health outcome the epidemic
            data represents. Can be either 'Symptomatic Infections', 'Diagnosed Cases',
            'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

        cumulative (bool): Boolean that is True when the DataFrame contains
            cumulative data instead of individual data.

        includedScenarios ('all' or list of str): A list of strings containing
            the names of scenarios that will be included in the table. Can
            also be the string 'all' to indicate that all scenarios should
            be included.

    Returns:
        finalPlot (LayerChart): An Altair plot layering a line graph of the infection
            data with a point chart that allows tooltips to appear on the line
            without needing to hover over the line exactly.

    Raises:
        ValueError: If data is not a dataframe or outcome is not one of
            the recognised health burden outcomes.
    """
    # Validate parameters
    try:
        if not isinstance(data, pd.DataFrame):
            raise ValueError(f"data should be a DataFrame, was {type(data)}")
        if outcomeName not in tableOutcomes:
            raise ValueError(
                (
                    'outcome should be either "Symptomatic Infections", '
                    '"Diagnosed Cases", "Hospitalisations", "ICU Visits", '
                    f'"GP Visits", or "Deaths"; was "{outcomeName}".'
                )
            )
    except Exception as e:
        functionLog.error(
            (
                f"[plotEpidemic] Encountered {type(e).__name__} "
                f"while validating parameters: {e}"
            )
        )
        raise e
    outcome = "Infections"  # TODO: placeholder until other burdens can be graphed
    # Define reusable chart components
    plotTitle = (
        f"Cumulative Median {outcome} Over Time"
        if cumulative
        else f"Median {outcome} per Day Over Time"
    )
    yLabel = f"Total {outcome}:Q" if cumulative else f"{outcome} per Day:Q"
    xLabel, colourLabel = "Days Since First Infection:Q", "Scenario:N"
    tooltipPicker = alt.selection_point(
        fields=[xLabel[:-2]], nearest=True, on="pointerover", empty=False
    )
    legendPicker = alt.selection_point(fields=[colourLabel[:-2]], bind="legend")
    tooltipCondition = alt.when(tooltipPicker)
    scenarioNames = data["Scenario"].unique()

    # Remove any scenarios/age groups not specified in the data
    # TODO: Affect the legend as well, preferably without affecting the colours
    if includedScenarios != "all":
        newData = data[data["Scenario"].isin(includedScenarios)]
    else:
        newData = data

    # Plot the line graph itself
    epidemicPlot = (
        alt.Chart(newData, title=plotTitle)
        .mark_line(interpolate="natural")
        .encode(
            x=alt.X(xLabel).scale(
                nice=False,
                domain=(0, ceil(data["Days Since First Infection"].max() / 10) * 10),
            ),
            y=yLabel,
            color=alt.Color(colourLabel).scale(
                domain=list(scenarioNames), range=brightCodes[: len(scenarioNames)]
            ),
            opacity=(
                alt.when(legendPicker).then(alt.value(1)).otherwise(alt.value(0.2))
            ),
        )
        .add_params(legendPicker)
    )

    # Define points for tooltip generation
    epidemicPoints = epidemicPlot.mark_point().encode(
        opacity=tooltipCondition.then(alt.value(1)).otherwise(alt.value(0))
    )

    # Plot vertical lines to display tooltips with data from all scenarios
    epidemicRule = (
        alt.Chart(newData)
        .transform_pivot(colourLabel[:-2], value=yLabel[:-2], groupby=[xLabel[:-2]])
        .mark_rule(color="gray")
        .encode(
            x=xLabel,
            opacity=(tooltipCondition.then(alt.value(0.3)).otherwise(alt.value(0))),
            tooltip=[xLabel]
            + [
                alt.Tooltip(
                    scenario, type="quantitative", title=f"{scenario} {outcome}"
                )
                for scenario in newData["Scenario"].unique()
            ],
        )
        .add_params(tooltipPicker)
    )

    # Return both plots combined
    return alt.layer(epidemicPlot, epidemicPoints, epidemicRule)


# TODO: more options
# TODO: refactor to allow identical columns
def formatAsir(
    rawCSV: bytes,
    scenarioNames: list[str],
    columns: list[tuple[str, bool, bool]] = [("Symptomatic Infections", False, False)],
    includedScenarios: list[str] | Literal["all"] = "all",
    includedAges: list[str] | Literal["all", False] = "all",
) -> tuple[pd.DataFrame, dict[str, ColumnConfig], set[str], set[str]]:
    """
    Function to convert raw data from the age-specific infection rate
    ('asir') Flusim analysis tool into the desired DataFrame format for
    tables and other visualisations

    Parameters:
        rawCSV (bytes): The CSV output of the 'asir' analysis function, obtained
            from the server after running the simulation.

        scenarioNames (list of str): A list of strings containing the names of the
            different scenarios that were simulated (since the CSV just uses
            non-descriptive placeholders). This list should contain the names
            of all scenarios in the simulation, even if not all of them will be
            included in the final table.

        columns (list of tuples (str, bool, bool)): A list of tuples representing
            the health burden outcome and formatting of each column the
            dataframe should have.

        includedScenarios ('all' or list of str): A list of strings
            containing the names of scenarios that will be included in
            the table. Can also be the string 'all' to indicate that all
            scenarios should be included.

        includedAges ('all', False or list of str): A list of strings
            containing the names of age groups that will be included in the
            table. Can also be the string 'all' to indicate that all age
            groups should be included. If this is False, the age group column
            will be omitted entirely.

    Returns:
        formattedData (DataFrame): A pandas DataFrame containing the data,
            reshaped into a format more easily used for table construction.

        columnConfig (dict of str and ColumnConfig): A dictionary storing the
            configuration settings for each column in the table.

        percentCols (set of str): A set of strings holding the names of
            each column that uses percentage formatting.

        differenceCols (set of str): A set of strings holding the names of
            each column that uses difference from baseline formatting.

    Raises:
        ValueError: If scenarioNames is not a list of strings or columns
            are not formatted correctly.
    """
    # Validate parameters
    try:
        if not scenarioNames:
            raise ValueError("scenarioNames should not be empty.")
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ):
            raise ValueError(
                (
                    "scenarioNames should be a list of "
                    f"strings; was {type(scenarioNames)}."
                )
            )
        if not columns:
            raise ValueError("columns should not be empty.")
        if not isinstance(columns, list) or not all(
            isinstance(col, tuple) and len(col) == 3 and col[0] in tableOutcomes
            for col in columns
        ):
            raise ValueError(
                (
                    "columns should be a list of tuples containing health "
                    "outcome strings and proportion/baseline difference "
                    f"booleans; was {columns}."
                )
            )
    except Exception as e:
        functionLog.error(
            f"[formatAsir] Encountered {type(e).__name__} "
            f"while validating parameters: {e}"
        )
        raise e

    # Generate and format the dataframe
    framedData = pd.read_csv(BytesIO(rawCSV), header=0, index_col=0)
    functionLog.info(
        f"Scenario names are {scenarioNames}; current index is {framedData.index}"
    )
    framedData.columns = pd.Index(["Total"] + ageWithTime)

    # Scale the data by symptomatic likelihood
    # TODO: Heed the pandas deprecation warning regarding implicit casting
    asymptomaticChild, asymptomaticAdult = zip(*session.DataAsymptomatic)
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
    meltedData = framedData.round().melt(
        "Scenario", var_name="Age Group", value_name="Base Values"
    )

    # Get base data to use when creating specified columns
    baselineScenario = scenarioNames[0]
    baselineRows = (
        meltedData.loc[meltedData["Scenario"] == baselineScenario]
        .drop("Scenario", axis=1)
        .set_index("Age Group")
    )
    baselineValues = meltedData["Age Group"].map(baselineRows["Base Values"])
    community = session.DataCommunity

    # Generate config data for Streamlit display
    percentCols, differenceCols = set(), set()
    columnConfig = {}

    columnConfig["Scenario"] = st.column_config.TextColumn(
        pinned=True,
        help="""
The scenario that each row's data originates from. 'Baseline'
refers to the scenario using the base parameters at the
Baseline Parameters page, while additional scenarios use the
names given to them at the Scenario Parameters page.
    """,
    )
    columnConfig["Age Group"] = st.column_config.TextColumn(
        pinned=True,
        help="""
The age range of the individuals that each row's data is derived from.
'Total' includes the entire population of the simulation, at all ages;
other age groups list the age range they cover as part of their name.
    """,
    )

    # Prepare burden-scaled columns beforehand for efficiency
    requiredOutcomes = {outcome for outcome, _, _ in columns}
    outcomeColumns: dict[str, pd.Series[Any]] = {}
    outcomeBaselines: dict[str, pd.Series[Any]] = {}
    for outcome in requiredOutcomes:
        match outcome:
            case "Symptomatic Infections":
                scaledColumn = meltedData["Base Values"].copy()
                scaledBaseline = baselineValues.copy()
            case "Deaths":
                # Account for age-specific mortality
                # Convert death rates to DataFrame for efficiency
                deathRates = pd.DataFrame(session.DataMortalityRates).T.stack()
                dataIndexValues = pd.MultiIndex.from_frame(
                    meltedData[["Scenario", "Age Group"]]
                )
                scaledColumn = (
                    meltedData["Base Values"]
                    * pd.Series(
                        dataIndexValues.map(deathRates), index=meltedData.index
                    ).fillna(
                        meltedData["Scenario"].map(
                            session["DataHealthOutcomeRates"]["Deaths"]
                        )
                    )
                ).round()

                # Baseline values
                baselineDeath = session.DataMortalityRates[baselineScenario]
                scaledBaseline = (
                    baselineValues
                    * (
                        meltedData["Age Group"]
                        .map(baselineDeath)
                        .fillna(
                            session["DataHealthOutcomeRates"]["Deaths"][
                                baselineScenario
                            ]
                        )
                    )
                ).round()
            case _:
                scaledColumn = (
                    meltedData["Base Values"]
                    * meltedData["Scenario"].map(
                        session["DataHealthOutcomeRates"][outcome]
                    )
                ).round()
                scaledBaseline = (
                    baselineValues
                    * (session["DataHealthOutcomeRates"][outcome][baselineScenario])
                ).round()
        # Recalculate totals to avoid rounding-induced mismatch
        if not includedAges or (includedAges == "all" or "Total" in includedAges):
            scenarioCount = len(scenarioNames)
            scaledColumn.iloc[:scenarioCount] = (
                scaledColumn.groupby(scaledColumn.index % scenarioCount).sum()
                - scaledColumn.iloc[:scenarioCount]
            )
            scaledBaseline.iloc[:scenarioCount] = scaledColumn.iloc[0]
        outcomeColumns[outcome] = scaledColumn
        outcomeBaselines[outcome] = scaledBaseline

    # Generate columns
    for outcome, proportion, baselineDifference in columns:
        currentColumn = outcomeColumns[outcome]
        columnBaselines = outcomeBaselines[outcome]

        # Apply proportion/difference modifications
        # TODO: Either fix or disable just proportion
        # TODO: See if case matching is better here than elif chains
        if proportion and not baselineDifference:
            currentColumn /= meltedData["Age Group"].map(communityAgePops[community])
            columnName = f"{outcomeAdjectives[outcome]} % of Population"
            columnConfig[columnName] = st.column_config.Column(
                help=f"""
The proportion of the total population (within a given
scenario{' and age group' if includedAges else ''})
that was {outcomeDescriptions[outcome]}, as a
percentage.
            """
            )
            percentCols.add(columnName)
        elif not proportion and baselineDifference:
            currentColumn = currentColumn - columnBaselines
            columnName = f"{outcome} (Difference from Baseline)"
            columnConfig[columnName] = st.column_config.Column(
                help=f"""
The difference between the number of people who were
{outcomeDescriptions[outcome]} within a given
scenario{' (in a given age group)' if includedAges else ''},
and the number of people who were
{outcomeDescriptions[outcome]} within the baseline
scenario{' (in the same age group)' if includedAges else ''}.
            """
            )
            differenceCols.add(columnName)
        elif proportion and baselineDifference:
            currentColumn = currentColumn - columnBaselines
            # Account for potential division by 0
            currentColumn = (currentColumn / columnBaselines).where(
                columnBaselines != 0, other=np.nan
            )
            columnName = f"{outcome} (% Difference from Baseline)"
            columnConfig[columnName] = st.column_config.Column(
                help=f"""
The difference between the number of people who were
{outcomeDescriptions[outcome]} within a given
scenario{' (in a given age group)' if includedAges else ''},
and the number of people who were
{outcomeDescriptions[outcome]} within the baseline
scenario{' (in the same age group)' if includedAges else ''},
as a percentage.
            """
            )
            percentCols.add(columnName)
            differenceCols.add(columnName)
        else:
            columnName = outcome
            columnConfig[columnName] = st.column_config.Column(
                help=f"""
The number of people (within a given
scenario{' and age group' if includedAges else ''})
who were {outcomeDescriptions[outcome]}.
            """
            )

        # Formally create the column
        meltedData[columnName] = currentColumn

    # Remove the base values column once it's redundant
    meltedData.drop("Base Values", axis=1, inplace=True)

    # Remove any scenarios/age groups not specified in the data
    if includedScenarios != "all" and (set(scenarioNames) != set(includedScenarios)):
        meltedData = meltedData[meltedData["Scenario"].isin(includedScenarios)]
    if not includedAges:
        meltedData = meltedData[meltedData["Age Group"] == "Total"]
        meltedData.drop("Age Group", axis=1, inplace=True)
    elif includedAges != "all" and (set(includedAges) != set(framedData.columns)):
        meltedData = meltedData[meltedData["Age Group"].isin(includedAges)]

    # Set index for data
    meltedData["Scenario"] = pd.Categorical(
        meltedData["Scenario"], categories=scenarioNames, ordered=True
    )
    if includedAges:
        meltedData["Age Group"] = pd.Categorical(
            meltedData["Age Group"], categories=ageWithTime + ["Total"], ordered=True
        )
    meltedData = (
        meltedData.set_index(["Scenario", "Age Group"])
        if includedAges
        else meltedData.set_index("Scenario")
    ).sort_index()

    return meltedData, columnConfig, percentCols, differenceCols
