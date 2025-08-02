# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where basic simulation parameters can be modified

# Imports
import logging
import streamlit as st
from pydantic import ValidationError
from ClientResources.InterfaceFunctions import dayCount
from ClientResources.ModelSchema import (
    Parameters, scenarioParameters, commandArgument
)

# Logging
basicLog = logging.getLogger(__name__)

"""
Function to generate the parameters for the simulation in a specified 
container with scenario differentiation

Parameters:
    container: The Streamlit container (likely a tab or expander) in 
    which the parameters will be generated.

    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables.

    globalErrorContainer: A container outside of the tab where error 
    messages will be placed.
"""
def buildBasicTab(container, id, globalErrorContainer):
    # Tab Content
    with container:
        st.header('Initialisation Parameters')
        st.markdown('''
            This tab contains several key parameters that are 
            fundamental to starting the simulation, including the 
            length it runs for and the number of times to run each 
            scenario.
        ''')

        # Potential Catchable Errors:
        # - Taking Too Long

        # Time Parameters
        runCount = st.slider(
            'Number of Simulation Runs', 1, 24, 24, key = f'runCount{id}', 
            help = f'''
                The number of times that {'each' if id == 0 else 'this'} 
                scenario will be ran. Higher values lead to longer 
                simulations but more accurate results due to averaging.
            '''
        )
        cycleCount = st.select_slider(
            'Length of Simulation (Days)', range(30, 721), 360, 
            format_func = dayCount, key = f'cycleCount{id}', help = '''
                The number of days that will be simulated in each 
                simulation run.
            '''
        )
        st.select_slider(
            'Simulation Starting Day of the Week', (
                'Monday', 'Tuesday', 'Wednesday', 
                'Thursday', 'Friday', 'Saturday', 'Sunday'
            ),
            'Monday', key = f'startDay{id}', help = '''
                The day of the week that the first day of the 
                simulation will be.
            '''
        )





"""
Function to populate the Pydantic model schema with the parameters in 
this tab with scenario differentiation

Parameters:
    schema: The Pydantic model (specifically an object in the 
    Parameters class) that the parameters will be populated into.

    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables. A value of 0 means that this is the 
    baseline scenario and will be treated accordingly.
"""
def basicSchema(schema, id = 0):
    try:
        # Validate parameters
        if not isinstance(schema, Parameters): raise ValueError(
            'schema should be a Parameters object'
        )

        # Command Arguments
        schema.Command_Argument = commandArgument(
            n_runs = st.session_state[f'runCount{id}'], 
            n_cycles = st.session_state[f'cycleCount{id}'] * 2
        )

        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter if schema.Scenario_Parameter 
            else scenarioParameters()
        )
        scenarioParams.start_day_of_week = st.session_state[f'startDay{id}']
        schema.Scenario_Parameter = scenarioParams
    except (ValueError, ValidationError) as e:
        basicLog.error((
            f'[basicParams] Encountered {type(e).__name__} '
            f'while validating parameters for scenario {id}: {e}'
        ))
        raise e