# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by tables and graphs

# Imports
from math import ceil
from io import BytesIO
import logging
import pandas as pd
import altair as alt
from ClientResources.SharedResources import (
    AnalysisFile, ageCategories, tableOutcomes, outcomeAdjectives
)

# Logging
functionLog = logging.getLogger(__name__)



"""
Wrapper function to perform the correct formatting process on csv data

Parameters:
    data: The CSV data to process.
    settings: The AnalysisFile containing the settings to use.
"""
def formatData(data, settings: AnalysisFile):
    if settings.tool == 'epidemic': return formatEpidemic(
        data, settings.names, settings.outcome, 
        settings.useCumulative, settings.splitByAge
    )
    elif settings.tool == 'asir': return formatAsir(
        data, settings.names, settings.outcome, 
        settings.useProportion, settings.differenceType
    )


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
            BytesIO(rawCSV), header = 0, 
            names = ['Days Since First Infection'] + scenarioNames
        )

        # Reshape data for better Altair usage
        valueLabel = f'Total {outcome}' if cumulative else f'{outcome} per Day'
        return framedData.melt(
            'Days Since First Infection', var_name = 'Scenario', 
            value_name = valueLabel
        ), 'Epidemic'

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
        BytesIO(rawCSV), header = 0, index_col = 0,
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
    return meltedData, 'Asir'

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