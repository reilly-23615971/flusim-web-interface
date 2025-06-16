# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the web application interface

# Imports
from io import StringIO
import asyncio
from aiohttp import ClientSession
import pandas as pd
import streamlit as st
from sharedResources import serverUrl, threadExecutor, resultQueue, httpSession



# Function to send model parameters to the server and receive the 
# statistics obtained from the server in response
async def runModel():
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

    # Ensure session is initialised
    global httpSession
    if httpSession is None or httpSession.closed:
        httpSession = ClientSession(
            base_url = serverUrl, raise_for_status = True
        )
    
    # Send POST request to server with parameters
    async with httpSession.post('runModel', json = parameterJSON) as response:
        csvData = await response.raise_for_status().text
    
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

    

# Wrapper for runModel to asynchronously send the HTTP requests 
# without blocking Streamlit operations
def runModelWrapper():
    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        formattedData = loop.run_until_complete(runModel())
        loop.close()
        resultQueue.put(formattedData)
    st.session_state.simulationInProgress = True
    threadExecutor.submit(runner)