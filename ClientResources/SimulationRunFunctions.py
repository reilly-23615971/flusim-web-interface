# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server for running the simulation

# Imports
from math import ceil
from io import StringIO
import asyncio
import logging
import threading
from aiohttp import ClientSession
import pandas as pd
import streamlit as st
import altair as alt
from ClientResources.ModelSchema import (
    Parameters, modelGuideFile, overrideParams, simulationSet, simulation
)
from ClientResources.InterfaceFunctions import formatEpidemic
from ClientResources.SharedResources import (
    serverUrl, resultQueue, ageCategories, tableOutcomes, outcomeAdjectives
)

# Logging
functionLog = logging.getLogger(__name__)

"""
Function to generate a JSON config file using the parameters set by the user
"""
# Keep in mind that cycles are zero-indexed and each one is only half a 
# day! Double or subtract one from days if necessary
def createConfig():
    # TODO: Properly check how many scenarios there are
    scenarioCount = 0
    scenarioNames = []


    # Set up schema objects
    baselineParams = Parameters()
    scenarioParams = [Parameters() for _ in range(scenarioCount)]

    # TODO: Populate parameters with session_state values

    # Create config object
    return modelGuideFile(
        name = 'Flusim Dashboard Simulation',
        description = (
            'A set of simulations configured using the Flusim Web Dashboard.'
        ),
        community_used = [st.session_state.community], 
        shared_overrides = overrideParams(parameters = baselineParams),
        simulation_sets = [simulationSet(
            name = 'Dashboard Simulation Set', 
            version = st.session_state.sessionID,
            simulations = [simulation(name = 'Baseline')] + [
                simulation(
                    name = scenarioNames[i], override_setting = overrideParams(
                        parameters = scenarioParams[i]
                    )
                ) for i in range(scenarioCount)
            ]
        )]
    )



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
        formattedData = formatEpidemic(csvData, ['Baseline', 'Surged'])
        # TODO: Use JSON parameters to determine how to format CSV data
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