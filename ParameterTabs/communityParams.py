# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where community parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow, dayCount
)
from ClientResources.SharedResources import ageCategories, kappaLocations

# Logging
communityLog = logging.getLogger(__name__)

"""
Function to generate the parameters for the simulation environment in a 
specified container with scenario differentiation

Parameters:
    container: The Streamlit container (likely a tab or expander) in 
    which the parameters will be generated.

    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables.

    globalErrorContainer: A container outside of the tab where error 
    messages will be placed.
"""
def buildCommunityTab(container, id, globalErrorContainer):
    # Initialise session variables needed by the disease forms
    sessionParameters = {
        f'transRowCount{id}': 0,
        f'kappaRowCount{id}': 0
    }
    for parameter, default in sessionParameters.items(): 
        st.session_state[parameter] = st.session_state.setdefault(
            parameter, default
        )

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    ageGroupSets = {
        f'transRemainingAgeGroups{id}': (
            f'transRowCount{id}', f'transAgeGroup{id}-'
        )
    }
    locationGroupSets = {
        f'kappaRemainingLocations{id}': (
            f'kappaRowCount{id}', f'kappaLocation{id}-'
        )
    }

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories)
    getRemainingGroups(locationGroupSets, kappaLocations)





    # Tab Content
    # TODO: Warn for nonsensical conditions like reduced BCC being 
    # lower than regular BCC
    with container:
        st.header('Community Parameters')
        st.markdown('''
            This tab contains parameters relating to the community that 
            is simulated by the model, including the size of groups in 
            different locations, how individuals react to the disease, 
            and the likelihood of different health outcomes.
        ''')

        # Potential Catchable Errors:
        # - None yet


