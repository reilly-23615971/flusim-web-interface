# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
from ParameterTabs.basicParams import buildBasicTab
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.InterfaceFunctions import saveKey, loadKey, checkErrors

# Logging
scenarioLog = logging.getLogger(__name__)

# Load necessary parameter values
scenarioCount = st.session_state.get('scenarioCount', 0)
errors = [checkErrors(id) for id in range(scenarioCount + 1)]

# Parameter lists for transferring scenarios upon deletion
parameterSet = {
    'scenarioName', 'runCount', 'cycleCount', 'startDay', 'deathRowCount', 
    'deathRemainingAgeGroups', 'caseRatio', 'gpRatio', 'hospitalRatio', 
    'icuRatio', 'deathRatio', 'withdrawalWork', 'withdrawalSchool', 
    'diagnosisDelay', 'bccRate', 'childSupervision', 'maxClassCount', 
    'maxClassSize', 'maxAdultClassSize', 'maxWorkGroupSize', 
    'maxNeighborGroupSize', 'maxChurchGroupSize', 'transRowCount', 
    'kappaRowCount', 'seedPeriodError', 'transRemainingAgeGroups', 
    'kappaRemainingLocations', 'seedRate', 'seedPeriod', 'beta', 
    'betaAsymptomatic', 'betaPostSymptomatic', 'householdKappa', 
    'asymptomaticChild', 'asymptomaticAdult', 'latencyPeriod', 
    'preSymptomPeriod', 'symptomPeriod', 'postSymptomPeriod', 
    'naturalImmunityDuration', 'naturalWanedEfficacy', 'naturalWaningRate', 
    'seedRowCount', 'closeRowCount', 'bccRowCount', 'seedDynamicError', 
    'closeDynamicError', 'bccDynamicError', 'vacAgeRowCount', 
    'primaryDoseCount', 'primWanedRowCount', 'boostAgeRowCount', 
    'socialRowCount', 'baseVacPropError', 'ageVacPropError', 
    'basePrimEfficacyError', 'agePrimEfficacyError', 'baseBoostEfficacyError', 
    'ageBoostEfficacyError', 'schoolTypeError', 'adultWithdrawalError', 
    'childWithdrawalError', 'reducedGroupError', 'bccError', 
    'triggerRateError', 'triggerTotalError', 'vaccinePeriodError', 
    'schoolClosurePeriodError', 'withdrawalIncreasePeriodError', 
    'reducedGroupPeriodError', 'bccPeriodError', 'classDismissal', 
    'vaccineRemainingAgeGroups', 'primaryRemainingWanedGroups', 
    'boosterRemainingAgeGroups', 'socialRemainingAgeGroups', 'vaccineToggle', 
    'vaccineTrigger', 'vaccinePeriod', 'limitDosesToggle', 
    'initialDoseReserve', 'firstDoseRate', 'initialVaccinated', 
    'targetVaccinated', 'primaryDoseCount', 'primaryDelay', 'primaryDuration', 
    'primaryWanedEfficacy', 'primaryWaningRate', 'boosterToggle', 
    'boosterDoseCount', 'boosterDelay', 'boosterDuration', 
    'boosterBaseEfficacy', 'boosterWanedEfficacy', 'boosterWaningRate', 
    'socialDistancingToggle', 'socialDistancingCompliance', 'caseIsolation', 
    'classDismissal', 'schoolClosureToggle', 'schoolClosureTrigger', 
    'schoolClosurePeriod', 'schoolClosureTypes', 'schoolClosureCompliance', 
    'withdrawalIncreaseToggle', 'withdrawalIncreaseTrigger', 
    'withdrawalIncreasePeriod', 'withdrawalIncreaseAdult', 
    'withdrawalIncreaseChild', 'reducedGroupToggle', 'reducedGroupTrigger', 
    'reducedGroupPeriod', 'reducedGroupSize', 'bccToggle', 'bccTrigger', 
    'bccPeriod', 'bccReducedRate', 'rateStartThreshold', 'rateRelaxThreshold', 
    'caseTotalThreshold'
}

doubleParameterSet = {
    'deathAgeGroup', 'deathRatio', 'transAgeGroup', 'kappaLocation', 
    'transInfect', 'transSuscept', 'kappaValue', 'seedCycle', 'seedNewRate', 
    'closeCycle', 'closeNewRate', 'bccCycle', 'bccNewRate', 'vacAgeGroup', 
    'primWanedGroup', 'boostAgeGroup', 'socialAgeGroup', 'primAgeRowCount', 
    'primaryRemainingAgeGroups', 'vacAgeInitial', 'vacAgeTarget', 
    'primAgeWanedEfficacy', 'primaryBaseEfficacy', 'boostAgeEfficacy', 
    'boostAgeWanedEfficacy', 'socialCompliance'
}

tripleParameterSet = {
    'primAgeGroup', 'primAgeEfficacy'
}

# Check for active deletion


# Simple function to add an additional scenario
def addScenario(): 
    st.session_state['scenarioCount'] += 1
    newCount = st.session_state['scenarioCount']
    st.session_state[f'scenarioName{newCount}'] = f'Scenario #{newCount}'
    st.session_state['scenarioSetParams'][newCount] = []
    st.session_state['scenarioSetParamsExtra'][newCount] = []

# Function to delete a scenario from the page
@st.dialog('Delete Scenario')
def deleteScenario(scenarioID):
    st.markdown(f'''
        Deleting the "{st.session_state[f'scenarioName{scenarioID}']}" 
        scenario will erase any unique parameter values set for it. Are 
        you sure you want to delete this scenario?
    ''')
    if st.button('Delete Scenario'):
        # Get set of saved params
        savedParams = st.session_state['scenarioSetParams']
        savedExtraParams = st.session_state['scenarioSetParamsExtra']

        # Shift existing values down
        for s in range(scenarioID, scenarioCount):
            for param in savedParams[s]: 
                st.session_state[f'{param}{s}'] = st.session_state[
                    f'{param}{s + 1}'
                ]
                st.session_state[f'_{param}{s}'] = st.session_state[
                    f'_{param}{s + 1}'
                ]
            for param, extra in savedExtraParams[s]: 
                st.session_state[f'{param}{s}{extra}'] = st.session_state[
                    f'{param}{s + 1}{extra}'
                ]
                st.session_state[f'_{param}{s}{extra}'] = st.session_state[
                    f'_{param}{s + 1}{extra}'
                ]
            st.session_state['scenarioSetParams'][s] = savedParams[s + 1]
            st.session_state['scenarioSetParamsExtra'][s] = savedExtraParams[
                s + 1
            ]
        
        # Delete end scenario params
        for param in savedParams[scenarioCount]: 
            del st.session_state[f'{param}{scenarioCount}']
            del st.session_state[f'_{param}{scenarioCount}']
        for param, extra in savedExtraParams[scenarioCount]: 
            del st.session_state[f'{param}{scenarioCount}{extra}']
            del st.session_state[f'_{param}{scenarioCount}{extra}']
        st.session_state['scenarioSetParams'][scenarioCount] = []
        st.session_state['scenarioSetParamsExtra'][scenarioCount] = []  

        # Update scenario count
        st.session_state['scenarioCount'] -= 1
        st.rerun()



# Page Content
st.title('Flusim Disease Model Dashboard')

st.markdown((f'''
    This page allows for configuring the parameters that will be used 
    in different scenarios by the simulation. To allow for direct 
    comparison of different parameter sets, you may define a series of 
    scenarios in which different parameter values are used. Up to 4 
    additional scenarios plus the baseline can be run in a single 
    simulation.

    Select a tab to view or modify the parameters under that category. 
    Hover your mouse over the :material/help: help icon next to a 
    parameter's input field to show an explanation of what that 
    parameter represents. Hover your mouse over any buttons to show an 
    explanation of what that button does.
'''))

# List current scenarios
st.header('Current Scenarios')

if scenarioCount == 0: st.markdown('''
    No additional scenarios have been defined. If you run the 
    simulation now without adding any additional scenarios, only the 
    baseline scenario will be included in the model, using the 
    parameters defined at the Baseline Parameter Configuration page.
''')
elif scenarioCount == 1: st.markdown(f'''
    There is currently 1 additional scenario defined for the simulation 
    (excluding the baseline scenario), 
    named {st.session_state[f'scenarioName{1}']}.
''')
else: st.markdown(f'''
There are currently {scenarioCount} additional scenarios defined for 
the simulation (excluding the baseline scenario), with the following 
names: 
    
{'\n'.join(
    f'- {st.session_state[f'scenarioName{id}']}' 
    for id in range(1, scenarioCount + 1)
)}
''')
    
# TODO: Run simulation button again?

# TODO: Loadable parameter templates (part of template tab?)

# Scenario addition field
st.header('Scenario Parameter Configuration')
for id in range(1, scenarioCount + 1): 
    with st.container(border = True):
        st.header(f'Scenario #{id}')
        # Scenario name
        loadKey(f'scenarioName', id, f'Scenario #{id}')
        scenarioName = st.text_input(
            'Name of Scenario', f'Scenario #{id}', max_chars = 50, 
            key = f'_scenarioName{id}', autocomplete = 'off', 
            on_change = saveKey, args = [f'scenarioName', id], # type: ignore
            placeholder = 'Enter a name for this scenario', help = '''
                The name to give to this scenario, which will display 
                in tables and graphs generated by the dashboard.
            '''
        )
        # Remove button
        st.button(
            label = 'Remove Scenario', icon = ':material/delete:', 
            key = f'scenarioRemove{id}', on_click = deleteScenario, 
            args = [id], # type: ignore
            help = '''
                Remove this scenario from the simulation set, thus 
                ensuring that it is not ran when you run the 
                simulation.
            '''
        )
        # Parameters for this scenario
        st.subheader('Parameters')

        # Place to put warnings and errors in the current parameter selection
        if max(errors[id]) == 0: st.markdown(
            f'''
            Currently, all parameters for this scenario have been set 
            to valid values. If any errors are detected with the 
            parameters selected for this scenario, they will be 
            described here.
        ''')
        scenarioErrorContainer = st.container()
        with st.container(border = True): 
            (
                basicTab, diseaseTab, communityTab, 
                interventionTab, dynamicTab
            ) = st.tabs([
                ':material/start: Initialisation', 
                ':material/coronavirus: Disease', 
                ':material/groups: Community', 
                ':material/vaccines: Vaccination and NPIs', 
                ':material/manage_history: Dynamic'
            ])

            # Basic parameters
            buildBasicTab(basicTab, id, scenarioErrorContainer)

            # Disease parameters
            buildDiseaseTab(diseaseTab, id, scenarioErrorContainer)

            # Environment parameters
            buildCommunityTab(communityTab, id, scenarioErrorContainer)

            # Vaccination and NPIs
            buildVaccinationNPITab(interventionTab, id, scenarioErrorContainer)

            # Dynamic parameters
            buildDynamicTab(dynamicTab, id, scenarioErrorContainer)
# Button to add another scenario
st.button(
    label = 'Add Scenario', icon = ':material/add:', 
    on_click = addScenario, key = f'scenarioAdd{id}',
    disabled = not scenarioCount < 4, help = '''
        Add another scenario to the simulation, where you can configure 
        different parameter values to use instead of the baseline 
        values.
    ''' if scenarioCount <= 3 else '''
        To keep the number of scenarios manageable, no more than 4 
        scenarios plus the baseline may be added to the simulation set 
        at once.
    '''
)

# TODO: Debug
#st.header('DEBUG ZONE')
#st.write(st.session_state)