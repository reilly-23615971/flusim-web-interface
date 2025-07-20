# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where basic simulation parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow, dayCount
)
from ClientResources.SharedResources import (
    ageCategories, kappaLocations, communityPopulation
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
        st.header('Basic Parameters')
        st.markdown('''
            This tab contains several key parameters that are 
            fundamental to the simulation, including the length it runs 
            for and the community it simulates.
        ''')

        # Potential Catchable Errors:
        # - Taking Too Long

        # Time Parameters
        runCount = st.slider(
            'Number of Simulation Runs', 1, 24, 24,
            key = f'runCount{id}', help = f'''
                The number of times that {
                    'the baseline scenario' if id == 0 else 'this scenario'
                } will be ran. Higher values lead to longer simulations 
                but more accurate results due to averaging.
            '''
        )
        cycleCount = st.select_slider(
            'Length of Simulation (Days)', range(30, 721), 720, 
            format_func = dayCount, 
            key = f'cycleCount{id}', help = '''
                The number of days that will be simulated in each 
                simulation run.
            '''
        )



        # Community Selection
        community = st.selectbox(
            'Simulated Community', key = f'community{id}', 
            options = communityPopulation.keys(), help = '''
                The Australian city whose community data will be used 
                as the basis for the population and demographic 
                distribution in the simulation. Note that the data used 
                for these communities comes from 2011.

                ##### Options:
                - Newcastle: A metropolitan area in New South Wales, 
                Australia. It has a population of 272407, the 
                second-largest in the state, and has a demographic 
                distribution that more closely matches that of 
                Australia as a whole compared to Cairns.
                - Cairns: A major city in Queensland, Australia. It has 
                a population of 140402 (as of 2011 when this data was 
                collected) and has a higher Indigenous population 
                compared to Newcastle.
            '''
        )
        # TODO: Consider displaying more comprehensive community info 
        # regarding the one the user selects



        