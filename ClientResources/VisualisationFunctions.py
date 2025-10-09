# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by tables and graphs

# Imports
from math import ceil
from io import BytesIO
import logging
from typing import Any
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from ClientResources.SharedResources import (
    AnalysisFile, communityAgePops, tableOutcomes, 
    outcomeAdjectives, ageWithTime, brightCodes
)

# Logging
functionLog = logging.getLogger(__name__)



# Dictionary getting health outcome descriptions
outcomeDescriptions = {
    'Infections': 'infected by the disease', 
    'Diagnosed Cases': 'formally diagnosed as cases of the disease', 
    'Hospitalisations': 'sent to a hospital due to the disease', 
    'Deaths': 'killed as a direct result of the disease', 
    'ICU Visits': 'committed to a hospital\'s Intensive Care Unit due to the disease', 
    'GP Visits': 'prompted to visit their general practitioner after noticing the symptoms of the disease'
}



"""
Wrapper function to perform the correct formatting process on csv data

Parameters:
    data: The CSV data to process.
    settings: The AnalysisFile containing the settings to use.
"""
def formatData(data, settings: AnalysisFile):
    if settings.tool == 'epidemic': 
        typeTag = 'Cumulative' if settings.useCumulative else 'Daily'
        return formatEpidemic(
            data, settings.names, settings.outcome, 
            settings.useCumulative, settings.splitByAge
        ), f'Epidemic{typeTag}'
    # Leave asir alone since it gets formatted when generating the table
    elif settings.tool == 'asir': return data, 'RawAsir'


"""
Function to convert raw data from the 'epidemic' Flusim analysis tool
into the desired DataFrame format for graphs

Parameters:
    rawCSV: The CSV output of the 'epidemic' analysis function, obtained
    from the server after running the simulation.

    scenarioNames: A list of strings containing the names of the 
    different scenarios that were simulated (since the CSV just uses 
    non-descriptive placeholders).

    outcome: A string indicating the health outcome the epidemic 
    data represents. Can be either 'Infections', 'Diagnosed Cases', 
    'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

    cumulative: A Boolean that is True when the CSV contains cumulative 
    data instead of individual data.

    splitByAge: A Boolean that is True when the CSV data has separate 
    columns for each age group.

Output:
    formattedData: A pandas DataFrame containing the data, reshaped into
    a format more easily used by Altair's charts.
"""
def formatEpidemic(
    rawCSV, scenarioNames, outcome = 'Infections', 
    cumulative = False, splitByAge = False
):
    # Validate parameters
    try:
        if (
            not isinstance(scenarioNames, list) 
            or not all(isinstance(name, str) for name in scenarioNames)
        ): raise ValueError((
            'scenarioNames should be a list of '
            f'strings; was {type(scenarioNames)}.'
        ))
        if not scenarioNames: raise ValueError(
            'scenarioNames should not be empty.'
        )
        if outcome not in tableOutcomes: raise ValueError((
            'outcome should be either "Infections", "Diagnosed Cases", '
            '"Hospitalisations", "ICU Visits", "GP Visits", '
            f'or "Deaths"; was "{outcome}".'
        ))
    except Exception as e:
        functionLog.error((
            f'[formatEpidemic] Encountered {type(e).__name__} '
            f'while validating parameters: {e}'
        ))
        raise e

    # Generate and format the dataframe
    if splitByAge:
        # TODO: Complete if desired; not sure how useful/desirable 
        # age-split time series graphs will be (redundant with asir)
        return pd.DataFrame()
    else:
        framedData = pd.read_csv(
            BytesIO(rawCSV), header = 0, 
            names = ['Days Since First Infection'] + scenarioNames
        ).fillna(0.0).round()

        # Reshape data for better Altair usage
        valueLabel = f'Total {outcome}' if cumulative else f'{outcome} per Day'
        
        return framedData.melt(
            'Days Since First Infection', var_name = 'Scenario', 
            value_name = valueLabel
        )





"""
Function to create an Altair line graph of time-series data obtained 
from the 'epidemic' Flusim analysis tool

Parameters:
    data: A DataFrame containing the epidemic data, processed with 
    the formatEpidemic function.

    outcome: A string indicating the health outcome the epidemic 
    data represents. Can be either 'Infections', 'Diagnosed Cases', 
    'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

    cumulative: Boolean that is True when the DataFrame contains 
    cumulative data instead of individual data.

Output:
    finalPlot: An Altair plot layering a line graph of the infection 
    data with a point chart that allows tooltips to appear on the line 
    without needing to hover over the line exactly.
"""
def plotEpidemic(
    data, outcome = 'Infections', cumulative = False, 
    includedScenarios: Any = 'all'
):
    # Validate parameters
    try:
        if not isinstance(data, pd.DataFrame): raise ValueError(
            f'data should be a DataFrame, was {type(data)}'
        )
        if outcome not in tableOutcomes: raise ValueError((
            'outcome should be either "Infections", "Diagnosed Cases", '
            '"Hospitalisations", "ICU Visits", "GP Visits", '
            f'or "Deaths"; was "{outcome}".'
        ))
    except Exception as e:
        functionLog.error((
            f'[plotEpidemic] Encountered {type(e).__name__} '
            f'while validating parameters: {e}'
        ))
        raise e

    # Define reusable chart components
    plotTitle = (
        f'Cumulative Median {outcome} Over Time' if cumulative 
        else f'Median {outcome} per Day Over Time'
    )
    yLabel =  f'Total {outcome}:Q' if cumulative else f'{outcome} per Day:Q'
    xLabel, colourLabel = 'Days Since First Infection:Q', 'Scenario:N'
    tooltipPicker = alt.selection_point(
        fields = [xLabel[:-2]], nearest = True, 
        on = 'pointerover', empty = False
    )
    legendPicker = alt.selection_point(
        fields = [colourLabel[:-2]], bind = 'legend'
    )
    tooltipCondition = alt.when(tooltipPicker)
    scenarioNames = data['Scenario'].unique()

    # Remove any scenarios/age groups not specified in the data
    if includedScenarios != 'all': 
        newData = data[data['Scenario'].isin(includedScenarios)]
    else: newData = data

    # Plot the line graph itself
    epidemicPlot = alt.Chart(newData, title = plotTitle).mark_line(
        interpolate = 'natural'
    ).encode(
        x = alt.X(xLabel).scale(nice = False, domain = (
            0, ceil(data['Days Since First Infection'].max() / 10) * 10
        )), 
        y = yLabel, color = alt.Color(colourLabel).scale(
            domain = list(scenarioNames), range = brightCodes[:len(scenarioNames)]
        ), 
        opacity = (
            alt.when(legendPicker).then(alt.value(1)).otherwise(alt.value(0.2))
        )
    ).add_params(legendPicker)

    # Define points for tooltip generation
    epidemicPoints = epidemicPlot.mark_point().encode(
        opacity = tooltipCondition.then(alt.value(1)).otherwise(alt.value(0))
    )

    # Plot vertical lines to display tooltips with data from all scenarios
    epidemicRule = alt.Chart(newData).transform_pivot(
        colourLabel[:-2], value = yLabel[:-2], groupby = [xLabel[:-2]]
    ).mark_rule(color = 'gray').encode(
        x = xLabel, opacity = (
            tooltipCondition.then(alt.value(0.3)).otherwise(alt.value(0))
        ), tooltip = [xLabel] + [
            alt.Tooltip(
                scenario, type = 'quantitative', 
                title = f'{scenario} {outcome}'
            ) for scenario in newData['Scenario'].unique()
        ],
    ).add_params(tooltipPicker)

    # Return both plots combined
    return alt.layer(epidemicPlot, epidemicPoints, epidemicRule)





"""
Function to convert raw data from the age-specific infection rate 
('asir') Flusim analysis tool into the desired DataFrame format for 
tables and other visualisations

Parameters:
    rawCSV: The CSV output of the 'asir' analysis function, obtained
    from the server after running the simulation.

    scenarioNames: A list of strings containing the names of the 
    different scenarios that were simulated (since the CSV just uses 
    non-descriptive placeholders). This list should contain the names 
    of all scenarios in the simulation, even if not all of them will be 
    included in the final table.

    columns: A list of tuples representing the health burden outcome 
    and formatting of each column the dataframe should have.

    includedScenarios: A list of strings containing the names of 
    scenarios that will be included in the table. Can also be the 
    string 'all' to indicate that all scenarios should be included.

    includedAges: A list of strings containing the names of 
    age groups that will be included in the table. Can also be the 
    string 'all' to indicate that all age groups should be included. 
    If this is False, the age group column will be omitted entirely.

Output:
    formattedData: A pandas DataFrame containing the data, reshaped into
    a format more easily used for table construction.
"""
# TODO: more options if time permits
def formatAsir(
    rawCSV, scenarioNames, columns = [('Infections', False, False)], 
    includedScenarios: Any = 'all', includedAges: Any = 'all'
):
    # Validate parameters
    try:
        if not scenarioNames: raise ValueError(
            'scenarioNames should not be empty.'
        )
        if (
            not isinstance(scenarioNames, list) 
            or not all(isinstance(name, str) for name in scenarioNames)
        ): raise ValueError((
            'scenarioNames should be a list of '
            f'strings; was {type(scenarioNames)}.'
        ))
        if not columns: raise ValueError(
            'columns should not be empty.'
        )
        if not isinstance(columns, list) or not all(
            isinstance(col, tuple) and len(col) == 3 
            and col[0] in tableOutcomes for col in columns
        ): raise ValueError((
            'columns should be a list of tuples containing health '
            'outcome strings and proportion/baseline difference '
            f'booleans; was {columns}.'
        ))
    except Exception as e:
        functionLog.error(
            f'[formatAsir] Encountered {type(e).__name__} '
            f'while validating parameters: {e}'
        )
        raise e

    # Generate and format the dataframe
    framedData = pd.read_csv(
        BytesIO(rawCSV), header = 0, index_col = 0
    )
    functionLog.info(f'Scenario names are {scenarioNames}; current index is {framedData.index}')
    framedData.columns = ['Total'] + ageWithTime
    framedData.index = pd.Index(scenarioNames)
    framedData.reset_index(names = 'Scenario', inplace = True)

    # Reshape data for better Streamlit usage with placeholder infections
    meltedData = framedData.melt(
        'Scenario', var_name = 'Age Group', value_name = 'Base Values'
    )
    
    # Get base data to use when creating specified columns
    baselineScenario = scenarioNames[0]
    baselineRows = meltedData.loc[
        meltedData['Scenario'] == baselineScenario
    ].drop('Scenario', axis = 1).set_index('Age Group')
    baselineValues = meltedData['Age Group'].map(baselineRows['Base Values'])
    community = st.session_state.DataCommunity

    # Generate config data for Streamlit display
    percentCols = []
    differenceCols = []
    columnConfig = {}

    columnConfig['Scenario'] = st.column_config.TextColumn(help = '''
The scenario that each row's data originates from. 'Baseline' 
refers to the scenario using the base parameters at the 
Baseline Parameters page, while additional scenarios use the 
names given to them at the Scenario Parameters page.
    ''')
    columnConfig['Age Group'] = st.column_config.TextColumn(help = '''
The age range of the individuals that each row's data is derived from. 
'Total' includes the entire population of the simulation, at all ages; 
other age groups list the age range they cover as part of their name.
    ''')

    # Generate columns
    for outcome, baselineDifference, proportion in columns:
        # Multiply base infection rate with corresponding outcome rate
        if outcome not in {'Infections', 'Deaths'}: 
            currentColumn = (
                meltedData['Base Values'] * meltedData['Scenario'].map(
                    st.session_state['DataHealthOutcomeRates'][outcome]
                )
            )
            columnBaselines = baselineValues * (
                st.session_state['DataHealthOutcomeRates'][outcome]['Baseline']
            )
        elif outcome == 'Deaths':
            # Account for age-specific mortality
            # Convert death rates to DataFrame for efficiency
            deathRates = pd.DataFrame(
                st.session_state.DataMortalityRates
            ).T.stack()
            dataIndexValues = pd.MultiIndex.from_frame(
                meltedData[['Scenario', 'Age Group']]
            )
            currentColumn = meltedData['Base Values'] * pd.Series(
                dataIndexValues.map(deathRates), index = meltedData.index
            ).fillna(meltedData['Scenario'].map(
                st.session_state['DataHealthOutcomeRates']['Deaths']
            ))

            # Baseline values
            baselineDeath = st.session_state.DataMortalityRates['Baseline']
            columnBaselines = baselineValues * (
                meltedData['Age Group'].map(baselineDeath).fillna(
                    st.session_state['DataHealthOutcomeRates']['Deaths']['Baseline']
                )
            )

        else: 
            currentColumn = meltedData['Base Values'].copy()
            columnBaselines = baselineValues.copy()

        # Apply proportion/difference modifications
        if proportion and not baselineDifference: 
            currentColumn /= meltedData['Age Group'].map(
                communityAgePops[community]
            )
            columnName = (
                f'{outcomeAdjectives[outcome]} % of Population'
            )
            columnConfig[columnName] = st.column_config.Column(help = f'''
The proportion of the total population (within a given 
scenario{' and age group' if includedAges else ''}) 
that was {outcomeDescriptions[outcome]}, as a 
percentage.
            ''')
            percentCols.append(columnName)
        elif not proportion and baselineDifference:
            currentColumn = (currentColumn - columnBaselines).round()
            columnName = f'{outcome} (Difference from Baseline)'
            columnConfig[columnName] = st.column_config.Column(
                help = f'''
The difference between the number of people who were 
{outcomeDescriptions[outcome]} within a given 
scenario{' (in a given age group)' if includedAges else ''}, 
and the number of people who were 
{outcomeDescriptions[outcome]} within the baseline 
scenario{' (in the same age group)' if includedAges else ''}.
            ''')
            differenceCols.append(columnName)
        elif proportion and baselineDifference:
            currentColumn -= columnBaselines
            # Account for potential division by 0
            currentColumn = (currentColumn / columnBaselines).where(
                columnBaselines != 0, other = np.nan
            )
            columnName = f'{outcome} (% Difference from Baseline)'
            columnConfig[columnName] = st.column_config.Column(help = f'''
The difference between the number of people who were 
{outcomeDescriptions[outcome]} within a given 
scenario{' (in a given age group)' if includedAges else ''}, 
and the number of people who were 
{outcomeDescriptions[outcome]} within the baseline 
scenario{' (in the same age group)' if includedAges else ''}, 
as a percentage.
            ''')
            percentCols.append(columnName)
            differenceCols.append(columnName)
        else: 
            currentColumn = currentColumn.round()
            columnName = outcome
            columnConfig[columnName] = st.column_config.Column(help = f'''
The number of people (within a given 
scenario{' and age group' if includedAges else ''}) 
who were {outcomeDescriptions[outcome]}.
            ''')
        
        # Formally create the column
        meltedData[columnName] = currentColumn

    # Remove the base values column once it's redundant
    meltedData.drop('Base Values', axis = 1, inplace = True)

    # Remove any scenarios/age groups not specified in the data
    if includedScenarios != 'all' and (
        set(scenarioNames) != set(includedScenarios)
    ): meltedData = meltedData[meltedData['Scenario'].isin(includedScenarios)]
    if not includedAges:
        meltedData = meltedData[meltedData['Age Group'] == 'Total']
        meltedData.drop('Age Group', axis = 1, inplace = True)
    elif includedAges != 'all' and (
        set(includedAges) != set(framedData.columns)
    ): meltedData = meltedData[meltedData['Age Group'].isin(includedAges)]

    # Set index for data
    meltedData['Scenario'] = pd.Categorical(
        meltedData['Scenario'], categories = scenarioNames, ordered = True
    )
    if includedAges: meltedData['Age Group'] = pd.Categorical(
        meltedData['Age Group'], categories = ageWithTime + ['Total'], 
        ordered = True
    )
    meltedData = (
        meltedData.set_index(['Scenario', 'Age Group']) 
        if includedAges else meltedData.set_index('Scenario')
    ).sort_index()

    return meltedData, columnConfig, percentCols, differenceCols