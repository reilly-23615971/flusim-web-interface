# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the web application interface

# Imports
from io import StringIO
import asyncio
import logging
import threading
from aiohttp import ClientSession
import pandas as pd
import streamlit as st
import altair as alt
from ClientResources.SharedResources import serverUrl, resultQueue

# Logging
functionLog = logging.getLogger(__name__)


"""
Function to send JSON model parameters to the server, awaiting a 
response containing the results of the simulation
"""
async def runModel():
    try:
        # TODO: Convert parameters from Streamlit into valid JSON file
        # TODO: Error handling

        # For testing use this default simulation JSON instead of parameters
        parameterJSON = {
            "name": "Simple Test",
            "output_folder": "./results/",
            "middle_joint": "-coronaV",
            "community_used": ["newcastle"],
            "community_overrides": [{"name": "newcastle","parameters": {}}],
            "shared_overrides": {
                "parameters": {
                    "Command_Argument": {"n_runs": 24,"n_cycles": 720},
                    "Scenario_Strain": [{"StrainId": 0,"Beta": 0.11}]
                }
            },
            "override_templates": [{
                "name": "test_1",
                "parameters": {
                    "Scenario_Parameter": {
                        "seed_rate": 0.125,
                        "school_closure_trigger": "timed",
                        "school_closure_compliance": 0.5,
                        "school_closure_delay": 28,
                        "withdrawal_increase_trigger": "timed",
                        "withdrawal_increase_delay": 28,
                        "work_nonattendance_trigger": "timed",
                        "prob_work_nonattendance": 0.5,
                        "work_nonattendance_delay": 28
                    }
                }
            }],
            "simulation_sets": [{
                "name": "test_set_1",
                "version": 230,
                "simulations": [
                    {"name": "test_sim_1","apply_template": ["test_1"]},
                    {"name": "test_sim_2","apply_template": ["test_1"]}
                ]
            }]
        }
        
        # Send POST request to server with parameters
        # TODO: Return to idea of single client sessions; see if it 
        # improves performance significantly
        functionLog.info(
            f'[runModel] Initialising session with base url {serverUrl}...'
        )
        async with ClientSession(
            raise_for_status = True, base_url = serverUrl
        ) as session:
            functionLog.info(f'[runModel] Sending post request...')
            async with session.post('runModel', json = parameterJSON) as response:
                csvData = await response.text()
            functionLog.info(f'[runModel] Response received! Returning data...')
        # Convert CSV statistics into DataFrame
        formattedData = pd.read_csv(
            StringIO(csvData), header = 0, 
            names = ['Day', 'Base Parameters', 'Surged']
        )
        # TODO: Use JSON parameters to format CSV data with simulation names
        # TODO: Store different data based on the request parameters
        # TODO: Determine if doing all analysis tasks with each model 
        # call is necessary/useful for the user
        return formattedData
    except Exception as e:
        functionLog.error(f'[runModel] Encountered {type(e).__name__}: {e}')
        raise e


"""
Wrapper function for runModel, allowing HTTP requests to be made 
asynchronously without blocking Streamlit operations
"""
def runModelWrapper():
    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def runner():
        try:
            formattedData = asyncio.run(runModel())
            resultQueue.put(formattedData)
        except Exception as e:
            functionLog.error(f'[runner] Encountered {type(e).__name__}: {e}')
            raise e
    st.session_state.simulationInProgress = True
    runModelThread = threading.Thread(target = runner)
    runModelThread.start()


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
    a format more easily used by Altair's charts
"""
def formatEpidemic(
    rawCSV, scenarioNames, outcome = 'Infections', 
    cumulative = False, splitByAge = False
):
    # Validate parameters
    try:
        if not isinstance(scenarioNames, list) or not all(
            isinstance(name, str) for name in scenarioNames
        ): raise ValueError((
            'scenarioNames should be a list of '
            f'strings; was {type(scenarioNames)}.'
        ))
        if outcome not in {
            'Infections', 'Cases', 'Hospitalisations', 
            'ICU Visits', 'GP Visits', 'Deaths'
        }: raise ValueError((
            'outcome should be one of "Infections", "Cases", "Hospitalisations", '
            f'"ICU Visits", "GP Visits", or "Deaths"; was "{outcome}".'
        ))
    except Exception as e:
        functionLog.error(
            f'[formatEpidemic] Encountered {type(e).__name__}: {e}'
        )
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
        if outcome not in {
            'Infections', 'Cases', 'Hospitalisations', 
            'ICU Visits', 'GP Visits', 'Deaths'
        }: raise ValueError((
            'outcome should be one of "Infections", "Cases", "Hospitalisations", '
            f'"ICU Visits", "GP Visits", or "Deaths"; was "{outcome}".'
        ))
    except Exception as e:
        functionLog.error(
            f'[plotEpidemic] Encountered {type(e).__name__}: {e}'
        )
        raise e

    # Define miscellaneous chart components
    plotTitle = (
        f'Cumulative {outcome} Over Time' if cumulative 
        else f'{outcome} per Day Over Time'
    )
    yLabel =  f'Total {outcome}:Q' if cumulative else f'{outcome} per Day:Q'
    xLabel, colourLabel = 'Days Since First Infection:Q', 'Scenario:N'
    tooltipPicker = alt.selection_point(nearest = True, on = 'mouseover')

    # Plot the line graph itself
    epidemicPlot = alt.Chart(data, title = plotTitle).mark_line(
        interpolate = 'natural'
    ).encode(
        x = alt.X(xLabel).scale(
            domain = (0, data['Days Since First Infection'].max())
        ), y = yLabel, color = colourLabel
    )

    # Plot the points used for tooltip display
    epidemicPoints = alt.Chart(data).mark_circle(size = 75).encode(
        x = xLabel, y = yLabel, 
        color = alt.condition(
            tooltipPicker, colourLabel, alt.value('transparent'), empty = False
        ), tooltip = [yLabel, xLabel, colourLabel]
    ).add_params(tooltipPicker)

    # Return both plots combined
    return alt.layer(epidemicPlot, epidemicPoints)