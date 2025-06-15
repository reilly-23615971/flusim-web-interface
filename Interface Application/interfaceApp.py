# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import io
import urllib
import requests
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.logger import get_logger

# Initialise session variables
if 'modelData' not in st.session_state:
    st.session_state.modelData = None

# Define application pages
# TODO: Determine ideal page layout/what goes where
st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')
pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page("modelDescription.py", title="Model Description"),
        st.Page("initialChartPage.py", title="Model Results")
    ]
}

# Function to run the model when sidebar button is pressed
async def runModel():
    # TODO: Check if server is available and grey out button if not
    # TODO: Convert parameters into valid JSON file

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

    # Contact the server to run the model
    try:
        modelURL = urllib.parse.urljoin('https://placeholder.url', '/runModel')
        response = requests.post(modelURL, json = parameterJSON)
        # TODO: Add spinner or progress bar while awaiting results
        data = pd.read_csv(io.StringIO(response.raise_for_status().text))
        st.session_state.modelData = data
        # TODO: Store different models based on the request parameters
        # TODO: Determine if doing all analysis tasks with each model 
        # call is necessary/useful for the user
        st.success('Simulation complete!')
    except requests.RequestException as e:
            # TODO: More comprehensive errors
            st.error(f'Failed to access the model server: {e}')


# Define model parameters to adjust in sidebar
# TODO: flesh out selectable options
# TODO: consider allowing for multiple selectable 'profiles' with 
# different parameters to run in parallel
parameterSidebar = st.sidebar
beta = parameterSidebar.slider('Beta', 0.01, 10.0, 0.11, key = 'beta')
npi = parameterSidebar.selectbox('NPI Presets', ['None', 'Low', 'Medium', 'High'], key = 'npi')
runModelButton = parameterSidebar.button('Run Simulation', on_click = runModel)

# Initialise and run the application
flusimPages = st.navigation(pages)
flusimPages.run()