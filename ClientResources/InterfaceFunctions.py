# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
from math import ceil
from io import StringIO
import logging
import pandas as pd
import streamlit as st
import altair as alt
from ClientResources.SharedResources import (
    ageCategories, tableOutcomes, outcomeAdjectives
)

# Logging
functionLog = logging.getLogger(__name__)

"""
Simple function to convert an integer into a string describing a number of days
"""
def dayCount(count): return '1 Day' if count == 1 else f'{count} Days'

"""
Simple function to get a specific session state value with a specific 
ID, checking ID 0 if the specified one doesn't exist before falling 
back on a default

Parameters:
    string: The string component of the session state variable to get.

    id: An integer that will be used to differentiate the parameters in 
    different scenarios by adding numbers to session state variables.

    defaultValue: What to return if neither the specified ID nor 0 give 
    a value in session state.
"""
def idGet(string, id, defaultValue): return st.session_state.get(
    f'{string}{id}', st.session_state.get(f'{string}0', defaultValue)
)

"""
Function to update what parameters are selectable for different 
parts of a form, to avoid duplicates

Parameters:
    groupSets: A dictionary with strings as keys and tuples containing 
    two strings as values, representing the form sections where age 
    groups need to be kept unique. The key strings are the Streamlit 
    session state variables holding the groups that haven't been 
    selected already. The first string of each value tuple is the 
    variable holding the number of rows in the corresponding age 
    selection form. The second string is the prefix used to identify 
    variables holding the groups that have already been used.

    possibleValues: A tuple containing strings representing the 
    possible values that can be selected in the form
"""
def getRemainingGroups(groupSets, possibleValues):
    for set, (rowCount, prefix) in groupSets.items():
        # Calculate age groups that haven't been used yet
        remainingGroups = dict.fromkeys(possibleValues)
        takenGroups = [
            st.session_state.get(f'{prefix}{i}') 
            for i in range(st.session_state[rowCount])
        ]
        for group in takenGroups: 
            if group: remainingGroups.pop(group, None)
        # Save the new age groups
        st.session_state[set] = list(remainingGroups.keys())

"""
Function to add an additional row to a specific variable-length form

Parameters:
    rowCounter: A string representing the Streamlit session state 
    variable storing the current number of rows in the form.

    forceSetParams: A dictionary of strings representing Streamlit 
    state variables and values to assign to them. Used to preload 
    widgets and keep drop-down selections up-to-date.
"""
def addFormRow(rowCounter, forceSetParams = None): 
    st.session_state[rowCounter] += 1
    if forceSetParams: 
        for var, value in forceSetParams.items(): 
            if value: st.session_state[var] = value

"""
Function to remove a row from a specific variable-length form

Parameters:
    deletedRowIndex: An integer representing the index (first is 0) of 
    the row that is to be deleted from the form.

    rowCounter: A string representing the Streamlit session state 
    variable storing the current number of rows in the form.

    inputPrefixes: A set of strings representing the prefixes that 
    denote the input widgets within the rows of the form.

    minRows: An integer representing the minimum number of rows the 
    form can have.
"""
def deleteFormRow(deletedRowIndex, rowCounter, inputPrefixes, minRows = 0):
    numberOfRows = st.session_state[rowCounter]
    # Make sure there's at least 1 row remaining
    if numberOfRows <= minRows: raise ValueError((
        'Tried to delete a row from a form that '
        'already has the minimum number of rows.'
    ))

    # Shift any rows below the deleted one up
    for row in range(deletedRowIndex, numberOfRows - 1):
        for input in inputPrefixes:
            st.session_state[f'{input}{row}'] = st.session_state[
                f'{input}{row+1}'
            ]
    
    # Erase any lingering data
    for input in inputPrefixes: del st.session_state[
        f'{input}{numberOfRows - 1}'
    ]
    st.session_state[rowCounter] -= 1

"""
Function to keep form variables loaded so that users don't have to 
reenter the values when they go to a different page
"""
def preserveFormEntries():
    # Age prefixes



    for row in range(0, st.session_state.outcomeFieldCount):
        for property in {'outcome', 'type', 'delete'}: 
            if f'{property}{row}' in st.session_state:
                st.session_state[f'{property}{row}'] = st.session_state[
                    f'{property}{row}'
                ]

    # Copy this line with xyz replaced with each widget in the form
    if "xyz" in st.session_state: 
        st.session_state.xyz = st.session_state.xyz
    



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
    data represents. Can be either 'Infections', 'Cases', 
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
            'outcome should be either "Infections", "Cases", '
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
        # Complete if necessary; not sure how useful/desirable 
        # age-split time series graphs will be (redundant with asir)
        return pd.DataFrame()
    else:
        framedData = pd.read_csv(
            StringIO(rawCSV), header = 0, 
            names = ['Days Since First Infection'] + scenarioNames
        )

        # Reshape data for better Altair usage
        valueLabel = f'Total {outcome}' if cumulative else f'{outcome} per Day'
        return framedData.melt(
            'Days Since First Infection', var_name = 'Scenario', 
            value_name = valueLabel
        )

"""
Function to convert raw data from the age-specific infection rate 
('asir') Flusim analysis tool into the desired DataFrame format for 
tables and other visualisations

Parameters:
    rawCSV: The CSV output of the 'asir' analysis function, obtained
    from the server after running the simulation.

    scenarioNames: A list of strings containing the names of the 
    different scenarios that were simulated (since the CSV just uses 
    non-descriptive placeholders).

    outcome: A string indicating the health outcome the asir
    data represents. Can be either 'Infections', 'Cases', 
    'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

    proportion: A Boolean that is True when the CSV contains 
    proportional/fractional results instead of the direct number of 
    infections per category.

    difference: A string that is not empty when the outputted DataFrame 
    should contain a column indicating the difference between the 
    baseline scenario (assumed to be the first in the CSV file) and 
    the other scenarios. Can be either 'absolute', 'percentage' or an 
    empty string/False.

Output:
    formattedData: A pandas DataFrame containing the data, reshaped into
    a format more easily used for table construction.
"""
def formatAsir(
    rawCSV, scenarioNames, outcome = 'Infections', 
    proportion = False, difference = ''
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
            'outcome should be either "Infections", "Cases", '
            '"Hospitalisations", "ICU Visits", "GP Visits", '
            f'or "Deaths"; was "{outcome}".'
        ))
        if difference and difference not in {'absolute', 'percentage'}: 
            raise ValueError((
                'difference should be either "absolute", "percentage", '
                f'or an empty string; was "{difference}".'
            ))
    except Exception as e:
        functionLog.error(
            f'[formatAsir] Encountered {type(e).__name__} '
            f'while validating parameters: {e}'
        )
        raise e

    # Generate and format the dataframe
    framedData = pd.read_csv(
        StringIO(rawCSV), header = 0, index_col = 0,
        names = ['Total'].extend(ageCategories.keys())
    )
    framedData.index = pd.Index(scenarioNames)
    framedData.reset_index(names = 'Scenario', inplace = True)

    # Reshape data for better Altair usage
    valueLabel = (
        f'{outcomeAdjectives[outcome]} Proportion of Population' if proportion 
        else f'Number of {outcome}'
    )
    meltedData = framedData.melt(
        'Scenario', var_name = 'Age Group', value_name = valueLabel
    )
    if not difference: return meltedData
    
    # Generate difference column if specified
    baselineScenario = scenarioNames[0]
    baselineRows = (meltedData.loc[
        meltedData['Scenario'] == baselineScenario
    ].set_index('Age Group')[valueLabel])
    
    if difference == 'absolute': diffFromBaseline = (
        meltedData[valueLabel] - meltedData['Age Group'].map(baselineRows)
    ).abs()
    else: diffFromBaseline = (
        meltedData[valueLabel] - meltedData['Age Group'].map(baselineRows)
    ).abs() / meltedData['Age Group'].map(baselineRows)
    
    meltedData['Difference from Baseline'] = diffFromBaseline
    return meltedData

"""
Function to create an Altair line graph of time-series data obtained 
from the 'epidemic' Flusim analysis tool

Parameters:
    data: A DataFrame containing the epidemic data, processed with 
    the formatEpidemic function.

    outcome: A string indicating the health outcome the epidemic 
    data represents. Can be either 'Infections', 'Cases', 
    'Hospitalisations', 'ICU Visits', 'GP Visits' or 'Deaths'.

    cumulative: Boolean that is True when the DataFrame contains 
    cumulative data instead of individual data.

Output:
    finalPlot: An Altair plot layering a line graph of the infection 
    data with a point chart that allows tooltips to appear on the line 
    without needing to hover over the line exactly.
"""
def plotEpidemic(data, outcome = 'Infections', cumulative = False):
    # Validate parameters
    try:
        if not isinstance(data, pd.DataFrame): raise ValueError(
            f'data should be a DataFrame, was {type(data)}'
        )
        if outcome not in tableOutcomes: raise ValueError((
            'outcome should be either "Infections", "Cases", '
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

    # Plot the line graph itself
    epidemicPlot = alt.Chart(data, title = plotTitle).mark_line(
        interpolate = 'natural'
    ).encode(
        x = alt.X(xLabel).scale(nice = False, domain = (
            0, ceil(data['Days Since First Infection'].max() / 10) * 10
        )), 
        y = yLabel, color = colourLabel, opacity = (
            alt.when(legendPicker).then(alt.value(1)).otherwise(alt.value(0.2))
        )
    ).add_params(legendPicker)

    # Define points for tooltip generation
    epidemicPoints = epidemicPlot.mark_point().encode(
        opacity = tooltipCondition.then(alt.value(1)).otherwise(alt.value(0))
    )

    # Plot vertical lines to display tooltips with data from all scenarios
    epidemicRule = alt.Chart(data).transform_pivot(
        colourLabel[:-2], value = yLabel[:-2], groupby = [xLabel[:-2]]
    ).mark_rule(color = 'gray').encode(
        x = xLabel, opacity = (
            tooltipCondition.then(alt.value(0.3)).otherwise(alt.value(0))
        ), tooltip = [xLabel] + [
            alt.Tooltip(
                scenario, type = 'quantitative', 
                title = f'{scenario} {outcome}'
            ) for scenario in data['Scenario'].unique()
        ],
    ).add_params(tooltipPicker)

    # Return both plots combined
    return alt.layer(epidemicPlot, epidemicPoints, epidemicRule)