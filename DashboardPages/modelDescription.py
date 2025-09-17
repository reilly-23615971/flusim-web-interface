# Flusim Web Interface Application
# Developed by Reilly Evans
# Page describing the Flusim model itself (and potentially other info)

# Imports
import streamlit as st
from dashboardApp import (
    baselineParameters, scenarioParameters, infectionGraphs, healthTables
)



# Create page
st.title('Flusim Disease Model Dashboard')

st.markdown(
    '''
    The SMRG Flusim model, developed by the Software Modelling Research Group at the University of Western Australia, implements a high-performance agent-based simulation model to simulate the spread of infectious disease in a population. This model has been used to aid in deciding effective policy for diseases such as influenza [[1](https://doi.org/10.1586/eri.10.136)] and COVID-19 [[2](https://doi.org/10.1101/2022.03.09.22272170)]. This website allows users to easily run the model with specific parameters and visualise the results. 
    '''
)

st.header('Usage')

st.markdown(
    '''
    - Use the sidebar on the left of the screen to navigate between the different pages. (If you can't see the sidebar, click the :material/keyboard_double_arrow_right: button at the top-left of the page to make it visible.) 
    - Visit the :grey-badge[:material/variable_insert: Baseline Parameters] page to change the parameters used by all simulations, or visit the :grey-badge[:material/variable_add: Scenario Parameters] page to specify multiple parameter sets to run at the same time. 
    '''
)

if st.button(
    'Go to Baseline Parameters', icon = ':material/variable_insert:'
): st.switch_page(baselineParameters)
if st.button(
    'Go to Scenario Parameters', icon = ':material/variable_add:'
): st.switch_page(scenarioParameters)

st.markdown(
    '''
    - Click the :primary-badge[:material/motion_play: Run Simulation] button in the sidebar to run the simulation.
    - Once you've ran a simulation, visit the :grey-badge[:material/chart_data: Infection Over Time Graphs] and :grey-badge[:material/table_chart_view: Health Burden Tables] pages to visualise the results of the simulation.
    '''
)

if st.button(
    'Go to Infection Over Time Graphs', icon = ':material/chart_data:'
): st.switch_page(infectionGraphs)
if st.button(
    'Go to Health Burden Tables', icon = ':material/table_chart_view:'
): st.switch_page(healthTables)

st.header('Model Details')

st.markdown(
    '''
    TODO
    '''
)