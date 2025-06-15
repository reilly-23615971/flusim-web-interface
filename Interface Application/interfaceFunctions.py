# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the web application interface

# Imports
import io
import urllib
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import streamlit as st

# Constants
SERVER_URL = 'http://127.0.0.1:8000' # change to Azure SWA URL
executor = ThreadPoolExecutor(max_workers = 1)

# Function to create and reuse an asynchronous client session 
# Used for HTTP requests to run the simulation on the server
async def getSession():
    if 'httpSession' not in st.session_state or st.session_state.httpSession.closed:
        st.session_state.httpSession = aiohttp.ClientSession(
            base_url = SERVER_URL, raise_for_status = True
        )
    return st.session_state.httpSession

# Function to send model parameters to the server and receive the resulting data
async def runModel():
    # TODO: Convert parameters into valid JSON file
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

    # Send request to server
    session = await getSession()
    async with session.post('runModel', json = parameterJSON) as response:
        textData = await response.raise_for_status().text
    formattedData = pd.read_csv(io.StringIO(textData))
    st.session_state.modelData = formattedData

    # TODO: Store different data based on the request parameters
    # TODO: Determine if doing all analysis tasks with each model 
    # call is necessary/useful for the user
    st.success('Simulation complete!')

# Wrapper for runModel to be ran on button click
def runModelWrapper():
    # Function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runModel())
        st.session_state.simulationInProgress = False
        loop.close()
    st.session_state.simulationInProgress = True
    executor.submit(runner)