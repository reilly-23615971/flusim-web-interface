# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where users can generate tables with infection data

# Imports
import inspect
import altair as alt
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from ClientResources.InterfaceFunctions import (
    saveKey, loadKey, getRemainingGroups, 
    addFormRow, deleteFormRow, dayCount, idGet
)
from ClientResources.VisualisationFunctions import formatAsir
from ClientResources.SharedResources import outcomeAdjectives, tableOutcomes, tableTypes

# Page Functions
old = """
# Callback for function to add inputs to form
def addFormRow(): st.session_state.outcomeFieldCount += 1

# Callback for function to remove inputs from form
def deleteFormRow(index):
    # Make sure there's at least 1 row remaining
    if st.session_state.outcomeFieldCount < 2: raise ValueError(
        'Cannot remove row from form when only one row remains.'
    )

    # Shift any rows below the deleted one up
    for row in range(index, st.session_state.outcomeFieldCount - 1):
        for property in {'outcome', 'type'}:
            st.session_state[f'{property}{row}'] = st.session_state[
                f'{property}{row+1}'
            ]
    
    # Erase any lingering data
    for property in {'outcome', 'type'}: 
        del st.session_state[
            f'{property}{st.session_state.outcomeFieldCount - 1}'
        ]
    st.session_state.outcomeFieldCount -= 1

# Callback function to generate the table
def generateTable():
    outcomeColumnCount = st.session_state.outcomeFieldCount
    #TODO: Check if any column fields are empty
    columnDetails = [
        (
            st.session_state[f'outcome{colNumber}'], 
            st.session_state[f'type{colNumber}']
        ) for colNumber in range(0, outcomeColumnCount)
    ]
    return
"""

# Initialise session variables needed by the vaccination/NPI forms
sessionParameters = {
    f'healthOutcomeRowCount': 1,
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.get(parameter, default)



st.title('Flusim Disease Model Web Dashboard')

st.write((
    'This page allows for the creation of tables comparing various '
    'health burden outcomes between different scenarios.'
))

# Check if there is data to tabulate
currentDataExists = not (st.session_state.get('modelDataAsir') is None)
if not currentDataExists: st.warning((
    'No simulation data has been generated. Click "Run Simulation" at '
    'the Baseline Parameter Configuration page to run a simulation and '
    'obtain the data necessary to generate a table.'
))

# Data for testing [DEBUG]
with open('./TestData/asirMedianAbsolute.csv', 'rb') as csv:
    st.session_state.modelDataAsir = formatAsir(
        csv.read(), ['Baseline', 'Surged'], 'Cases', False, 'absolute'
    )[0]
st.session_state.scenarios = ['Baseline', 'Surged']

# Form (container) for selecting health outcomes to use for the table


# Save relevant params as variables to avoid lookups
healthOutcomeRowCount = st.session_state[f'healthOutcomeRowCount']
healthOutcomeForm = st.container(border = True)
healthOutcomeErrorContainer = st.container()
healthOutcomeForm.title('Select Health Burden Outcomes')
for i in range(healthOutcomeRowCount): 
    (
        healthOutcomeColumn, outcomeTypeColumn, healthRemoveColumn
    ) = healthOutcomeForm.columns((0.4, 0.4, 0.2))
    currentOutcome = st.session_state.get(f'healthOutcome{i}', 'Infections')
    currentType = st.session_state.get(f'outcomeType{i}', 'Frequency')

    # Health burden outcome column
    loadKey(f'healthOutcome', i, currentOutcome)
    with healthOutcomeColumn: st.selectbox(
        'Health Burden Outcome', key = f'_healthOutcome{i}', 
        # Set health burden options such that only outcomes
        # that haven't been selected yet can be selected
        options = ([currentOutcome] + [
            outcome for outcome in tableOutcomes 
            if outcome != currentOutcome
        ]), 
        on_change = saveKey, args = [f'healthOutcome', id], # type: ignore
        help = '''
            Select the health burden outcome you would like to be 
            included as a column on the table.

            ### Options:
            - Infections: the number of individuals infected with the 
            disease in the simulation.
            - Cases: the number of individuals formally diagnosed with 
            the disease in the simulation.
            - Hospitalisations: the number of individuals who go to the 
            hospital for treatment as a result of the disease in the 
            simulation.
            - Deaths: the number of individuals killed by the disease 
            in the simulation.
            - ICU Visits: the number of individuals who are admitted to 
            an Intensive Care Unit (ICU) as a result of the disease in 
            the simulation.
            - GP Visits: the number of individuals who visit their 
            general practitioner due to symptoms of the disease in the 
            simulation.
        '''
    )
    
    # Initial proportion column
    loadKey(f'outcomeType', id, currentType)
    with outcomeTypeColumn: st.selectbox(
        'Outcome Type', key = f'_outcomeType{i}', 
        options = ([currentType] + [
            type for type in tableTypes if type != currentType
        ]), 
        on_change = saveKey, args = [f'outcomeType', id], # type: ignore
        help = '''
            Select the form in which the desired health burden outcome 
            will be displayed.

            ### Options:
            - Frequency: the median total number of occurrences of this 
            health outcome between all simulation runs within each 
            scenario.
            - Percentage of Population: the median proportion of the 
            total population within the simulation that achieves this 
            health outcome within each scenario, expressed as a 
            percentage.
            - Difference from Baseline (Frequency): The difference 
            between the median occurrences of this health outcome in 
            the baseline scenario and the median occurrences of this 
            health outcome in each other scenario.
            - Difference from Baseline (Percentage): The difference 
            between the median population proportion of this health 
            outcome in the baseline scenario and the median population 
            proportion of this health outcome in each other scenario.
        '''
    )
    # Delete button column
    with healthRemoveColumn: st.button(
        label = 'Remove Column', icon = ':material/delete:',
        key = f'healthOutcomeRemove{i}', on_click = deleteFormRow, args = (
            i, 'healthOutcomeRowCount', {f'healthOutcome', f'outcomeType'}, 1
        ),
        disabled = healthOutcomeRowCount <= 1, help = '''
            Remove this row of the form and do not display this column 
            in the table.
        ''' if healthOutcomeRowCount >= 2 else '''
            The table must have at least one column.
        '''
    )
# Button to add another row for age specific params
healthOutcomeForm.button(
    label = 'Add Burden Column', icon = ':material/add:', 
    on_click = addFormRow, key = f'healthOutcomeAdd', 
    args = (f'healthOutcomeRowCount',), disabled = healthOutcomeRowCount >= 7,
    help = '''
        Add another row to this form, where you can select an 
        additional health burden outcome to be included in the table.
    ''' if healthOutcomeRowCount <= 6 else '''
            The maximum number of columns has been added to this table.
    '''
)

# Button to generate the table itself
#TODO: Build the table
generateTableButton = st.button(
    label = 'Create Table', icon = ':material/backup_table:', 
    key = 'generateTable', type = 'primary'
)

#TODO: Select table units based on what's most appropriate