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
from ClientResources.SharedResources import (
    outcomeAdjectives, outcomeRateVariables, outcomeRateDefaults, tableOutcomes
)

# Page Functions

# Callback function to generate the table
def generateTable(container):
    outcomeColumnCount = st.session_state.healthOutcomeRowCount
    #TODO: Check if any column fields are empty
    columnDetails = [
        (
            st.session_state[f'healthOutcome{colNumber}'], 
            st.session_state[f'useBaselineDifference{colNumber}'],
            st.session_state[f'useProportion{colNumber}'],
        ) for colNumber in range(0, outcomeColumnCount)
    ]
    # Debug code for testing

    st.session_state.DataCommunity = 'newcastle'
    st.session_state.DataHealthOutcomeRates = {
        outcome: {
            scenario: idGet(
                outcomeRateVariables[outcome], i, 
                outcomeRateDefaults[outcome]
            ) 
            for i, scenario in enumerate(['Baseline', 'Surged'])
        }
        for outcome in outcomeRateDefaults.keys()
    }
    with open('./TestData/asirMedianAbsolute.csv', 'rb') as csv:
        rawAsir = ageData = formatAsir(
            csv.read(), ['Baseline', 'Surged'], [('Cases', False, False)]
        )
    
    container.dataframe(rawAsir, key = 'healthOutcomeTable')


# Initialise session variables needed by the vaccination/NPI forms
sessionParameters = {
    'healthOutcomeRowCount': 1,
    'DataCommunity': 'newcastle'
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.get(parameter, default)



st.title('Flusim Disease Model Dashboard')

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

# Form (container) for selecting health outcomes to use for the table
# Save relevant params as variables to avoid lookups
healthOutcomeRowCount = st.session_state[f'healthOutcomeRowCount']
healthOutcomeForm = st.container(border = True)
healthOutcomeErrorContainer = st.container()
healthOutcomeForm.title('Select Health Burden Outcomes')
for i in range(healthOutcomeRowCount): 
    (
        healthOutcomeColumn, healthDifferenceColumn, 
        outcomeTypeColumn, healthRemoveColumn
    ) = healthOutcomeForm.columns((0.25, 0.275, 0.275, 0.2))
    currentOutcome = st.session_state.get(f'healthOutcome{i}', 'Infections')

    # Health burden outcome column
    loadKey(f'healthOutcome', i, currentOutcome, noZeroDefault = True)
    with healthOutcomeColumn: st.selectbox(
        'Health Burden Outcome', key = f'_healthOutcome{i}', 
        # Set health burden options such that only outcomes
        # that haven't been selected yet can be selected
        options = ([currentOutcome] + [
            outcome for outcome in tableOutcomes 
            if outcome != currentOutcome
        ]), 
        on_change = saveKey, args = [f'healthOutcome', i], # type: ignore
        kwargs = {'notScenario': False},
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
        
    # Difference from baseline column
    loadKey('useBaselineDifference', i, False, noZeroDefault = True)
    with healthDifferenceColumn: st.toggle(
        'Difference from Baseline', False, key = f'_useBaselineDifference{i}', 
        on_change = saveKey, args = ['useBaselineDifference', i], # type: ignore
        disabled = st.session_state.get('DataScenarioCount', -1) == 0,
        kwargs = {'notScenario': False}, help = '''
            Toggle whether this column should display the difference 
            between the specified health burden outcome's result in the 
            baseline simulation and the result in the simulation the 
            row is for. For example, if the number of infected 
            individuals was 300 in the baseline scenario and 400 in 
            Scenario 1, an 'Infections' column with this setting 
            enabled would display +100 in the row for Scenario 1.
        ''' if st.session_state.get('DataScenarioCount', -1) != 0 else '''
            There are currently no additional scenarios defined for the 
            simulation data, so a difference from baseline column would 
            display no useful information.
        '''
    )
        
    # Proportion column
    loadKey(f'useProportion', i, False, noZeroDefault = True)
    with outcomeTypeColumn: st.toggle(
        'Percentage', False, key = f'_useProportion{i}', 
        on_change = saveKey, args = [f'useProportion', i], # type: ignore
        kwargs = {'notScenario': False}, help = '''
            Toggle whether this column should display its value as a 
            percentage rather than as a standard number. 
            
            If 'Difference from Baseline' is disabled, this percentage 
            will be relative to the total population of each age group 
            in each scenario's community. For example, if the number of 
            infected adults was 20,000 in a scenario with the Newcastle 
            community (which has 71,299 adults), an 'Infections' column 
            with 'Percentage' disabled would display 20,000 while a 
            column with it enabled would display 28.051%.

            If 'Difference from Baseline' is enabled, this percentage 
            will be relative to the value of the column in the baseline 
            scenario for the given age group. For example, if the 
            number of infected individuals was 300 in the baseline 
            scenario and 400 in Scenario 1, an 'Infections' column with 
            both 'Percentage' and 'Difference from Baseline' enabled 
            would display +33.333% in the row for Scenario 1.
        '''
    )
    
    # Delete button column
    with healthRemoveColumn: st.button(
        label = 'Remove Column', icon = ':material/delete:',
        key = f'healthOutcomeRemove{i}', on_click = deleteFormRow, args = (
            i, 'healthOutcomeRowCount', {
                'healthOutcome', 'outcomeType', 'useBaselineDifference'
            }, 1
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
buttonContainer = st.empty()

tableContainer = st.empty()

buttonContainer.button(
    label = 'Create Table', icon = ':material/backup_table:', 
    key = 'generateTable', type = 'primary', on_click = generateTable, 
    args = [tableContainer], # type: ignore
    disabled = not st.session_state.get('modelDataRawAsir'), help = '''
        Use the data from the last simulation to generate a table 
        displaying different health outcomes on the scenarios in the 
        simulation, with the specific columns displayed depending on 
        the parameters selected above.
    ''' if st.session_state.get('modelDataRawAsir') else '''
        No simulations have completed yet, so there is no data to 
        tabulate.
    '''
)

#TODO: Select table units based on what's most appropriate
#st.header('DEBUG ZONE')
#st.session_state