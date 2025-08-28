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
from ClientResources.InterfaceFunctions import saveKey, loadKey
from ClientResources.VisualisationFunctions import formatAsir
from ClientResources.SharedResources import outcomeAdjectives, tableOutcomes

# Page Functions

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



st.title('Flusim Disease Model Web Dashboard')

st.write((
    'This page allows for the creation of tables comparing various '
    'health outcomes between different scenarios.'
))

# Check if there is data to tabulate
if st.session_state.asirData is None: st.write((
    'No simulation data has been generated. Click "Run Simulation" on '
    'the sidebar to run a simulation to obtain the data necessary '
    'to generate a table.'
))

# Data for testing [DEBUG]
with open('./TestData/asirMedianAbsolute.csv', 'r') as csv:
    st.session_state.asirData = formatAsir(
        csv.read(), ['Baseline', 'Surged'], 'Cases', False, 'absolute'
    )[0]
st.session_state.scenarios = ['Baseline', 'Surged']

# Form (container) for selecting health outcomes to use for the table
tableForm = st.container()

# Construct the form for selecting table columns
#TODO: Ask supervisors if there's a better word than 'numeric' or 
# 'absolute' or 'frequency' for non-percentage values
with tableForm:
    # Define columns for placing elements
    leftCol, centreCol, rightCol = st.columns((0.4, 0.4, 0.2))
    # Health Outcome Selection Box
    for i in range(st.session_state.outcomeFieldCount): 
        loadKey('outcome', i, 'Infections')
        loadKey('type', i, 'Frequency')
    with leftCol: outcomeSelections = [
        st.selectbox(
            label = 'Health Outcome', options = tableOutcomes, 
            placeholder = 'Health Outcome', key = f'_outcome{i}',
            on_change = saveKey, args = [f'outcome{i}'], # type: ignore
            help = '''
                Select the health outcome you would like to be included 
                as a column on the table.

                ### Options:
                - Infections: the number of individuals infected with 
                the disease in the simulation.
                - Cases: the number of individuals formally diagnosed 
                with the disease in the simulation.
                - Hospitalisations: the number of individuals who go to 
                the hospital for treatment as a result of the disease 
                in the simulation.
                - Deaths: the number of individuals killed by the 
                disease in the simulation.
                - ICU Visits: the number of individuals who are 
                admitted to an Intensive Care Unit (ICU) as a result of 
                the disease in the simulation.
                - GP Visits: the number of individuals who visit their 
                general practitioner due to symptoms of the disease in 
                the simulation.
            '''
        ) for i in range(st.session_state.outcomeFieldCount)
    ]
    # Display Type Selection Box
    with centreCol: typeSelections = [
        st.selectbox(
            label = 'Type', placeholder = 'Type', key = f'_type{j}', 
            on_change = saveKey, args = [f'type{j}'], # type: ignore
            options = {
                'Frequency', 'Percentage of Population', 
                'Difference from Baseline (Frequency)', 
                'Difference from Baseline (Percentage)'
            }, help = '''
                Select the form in which the desired health outcome will be displayed.

                ### Options:
                - Frequency: the median total number of occurrences of 
                this health outcome between all simulation runs within 
                each scenario.
                - Percentage of Population: the median proportion of 
                the total population within the simulation that 
                achieves this health outcome within each scenario, 
                expressed as a percentage.
                - Difference from Baseline (Frequency): The difference 
                between the median occurrences of this health outcome 
                in the baseline scenario and the median occurrences of 
                this health outcome in each other scenario.
                - Difference from Baseline (Percentage): The difference 
                between the median population proportion of this health 
                outcome in the baseline scenario and the median 
                population proportion of this health outcome in each 
                other scenario.
            '''
        ) for j in range(st.session_state.outcomeFieldCount)
    ]
    # Buttons to remove this row of the form
    with rightCol: deleteButtons = [
        st.button(
            label = 'Remove Statistic', icon = ':material/delete:', 
            key = f'healthOutcomeRemove{k}', on_click = deleteFormRow, args = (k,),
            disabled = st.session_state.outcomeFieldCount < 2, 
            help = (
                'Do not include this column in the table.'
            ) if st.session_state.outcomeFieldCount >= 2 else (
                'The table must include at least one health outcome column.'
            )
        ) for k in range(st.session_state.outcomeFieldCount)
    ]
    # Button to add new rows to the form
    addFormRowButton = st.button(
        label = 'Add Health Outcome', 
        icon = ':material/add:', key = 'healthOutcomeAdd', 
        disabled = st.session_state.outcomeFieldCount > 7,
        help = '''
            Add another input field where you can select an additional 
            health outcome to include as a column in the table.
        ''' if st.session_state.outcomeFieldCount <= 7 else (
            'The maximum number of columns for the table has been reached.'
        )
    )
    # Button to generate the table itself
    generateTableButton = st.button(
        label = 'Create Table', icon = ':material/backup_table:', 
        key = 'generateTable'
    )


#TODO: Build the table

#TODO: Select table units based on what's most appropriate