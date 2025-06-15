# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import numpy as np
import pandas as pd
import streamlit as st
from interfaceFunctions import runModelWrapper

# Initialise session variables
if 'modelData' not in st.session_state:
    st.session_state.modelData = None
if 'httpSession' not in st.session_state:
    st.session_state.httpSession = None
if 'simulationInProgress' not in st.session_state:
    st.session_state.simulationInProgress = None

# Define application pages
# TODO: Determine ideal page layout/what goes where
st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')
pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page("modelDescription.py", title="Model Description"),
        st.Page("initialChartPage.py", title="Model Results")
    ]
}

# Define model parameters to adjust in sidebar
# TODO: flesh out selectable options
# TODO: consider allowing for multiple selectable 'profiles' with 
# different parameters to run in parallel
# TODO: Check if server is available and grey out button if not
parameterSidebar = st.sidebar
beta = parameterSidebar.slider('Beta', 0.01, 10.0, 0.11, key = 'beta')
npi = parameterSidebar.selectbox('NPI Presets', ['None', 'Low', 'Medium', 'High'], key = 'npi')
runModelButton = parameterSidebar.button('Run Simulation', on_click = runModelWrapper)

# Initialise and run the application
flusimPages = st.navigation(pages)
flusimPages.run()