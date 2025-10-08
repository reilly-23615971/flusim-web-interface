# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where vaccination/NPI parameters can be modified

# Imports
import logging
from typing import Literal, cast
import numpy as np
import streamlit as st
from pydantic import ValidationError
from ClientResources.InterfaceFunctions import (
    saveKey, loadKey, getRemainingGroups, addFormRow, deleteFormRow, idGet
)
from ClientResources.SharedResources import (
    npis, npiCamel, ordinals, triggerConditions, 
    ageCategories, communityPopulation
)
from ClientResources.ModelSchema import (
    Parameters, scenarioParameters, ageScenarioParameters, 
    vaccineCoverage, vaccineDose, vaccineEfficacy
)

# Logging
vaccineLog = logging.getLogger(__name__)

"""
Function to generate the parameters for vaccination and NPIs in a 
specified container with scenario differentiation

Parameters:
    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables.
"""
@st.fragment
def buildVaccinationNPITab(id):
    # Initialise session variables needed by the vaccination/NPI forms
    sessionParameters = {
        # Row counts
        f'vacAgeRowCount{id}': 0,
        f'primaryDoseCount{id}': 2,
        f'primWanedRowCount{id}': 0,
        f'boostAgeRowCount{id}': 0,
        f'socialRowCount{id}': 0,

        # Error trackers
        f'baseVacPropError{id}': 0,
        f'ageVacPropError{id}': 0,
        f'basePrimEfficacyError{id}': 0,
        f'agePrimEfficacyError{id}': 0,
        f'baseBoostEfficacyError{id}': 0,
        f'ageBoostEfficacyError{id}': 0,

        f'schoolTypeError{id}': 0,
        f'adultWithdrawalError{id}': 0,
        f'childWithdrawalError{id}': 0,
        f'reducedGroupError{id}': 0,
        f'bccError{id}': 0,
        f'triggerRateError{id}': 0,
        f'triggerTotalError{id}': 0,

        f'vaccinePeriodError{id}': 0,
        f'schoolClosurePeriodError{id}': 0,
        f'withdrawalIncreasePeriodError{id}': 0,
        f'reducedGroupPeriodError{id}': 0,
        f'bccPeriodError{id}': 0,

        # Others
        f'classDismissal{id}': False,

    }
    for parameter, default in sessionParameters.items(): 
        st.session_state[parameter] = st.session_state.get(
            parameter, default
        )
    
    # Save primary row count as variable to avoid lookups (this one's 
    # defined early since it's used for finalising remaining groups)
    primaryRowCount = st.session_state[f'primaryDoseCount{id}']
    triggerNames = list(triggerConditions.keys())

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    ageGroupSets = {
        f'vaccineRemainingAgeGroups{id}': (
            f'vacAgeRowCount{id}', f'vacAgeGroup{id}-'
        ),
        f'primaryRemainingWanedGroups{id}': (
            f'primWanedRowCount{id}', f'primWanedGroup{id}-'
        ),
        f'boosterRemainingAgeGroups{id}': (
            f'boostAgeRowCount{id}', f'boostAgeGroup{id}-'
        ),
        f'socialRemainingAgeGroups{id}': (
            f'socialRowCount{id}', f'socialAgeGroup{id}-'
        )
    }

    # Calculate primary dose nested age group row counts
    for i in range(primaryRowCount):
        st.session_state[
            f'primAgeRowCount{id}-{i}'
        ] = st.session_state.setdefault(
            f'primAgeRowCount{id}-{i}', 0
        )
        ageGroupSets[f'primaryRemainingAgeGroups{id}-{i}'] = (
            f'primAgeRowCount{id}-{i}', f'primAgeGroup{id}-{i}-'
        )
    primaryAgeRowCounts = [
        st.session_state[f'primAgeRowCount{id}-{i}'] 
        for i in range(primaryRowCount)
    ]

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories.keys())

    # Parameters for keeping track of errors
    simLength = idGet('cycleCount', id, 360)
    ageVacPropError, ageBoostEfficacyError = False, False





    # Tab Content
    st.header('Vaccination and NPI Parameters')
    st.markdown('''
        This tab contains parameters relating to whether 
        vaccination and non-pharmaceutical interventions (NPIs) are 
        integrated into the simulation.
    ''')
    globalErrorContainer = st.container()

    # Vaccination
    with st.container():
        st.subheader('Vaccination Parameters')
        loadKey(f'vaccineToggle', id, False)
        useVaccinesToggle = st.toggle(
            'Enable Vaccines in Simulation', value = False, 
            on_change = saveKey, args = [f'vaccineToggle', id], # type: ignore
            key = f'_vaccineToggle{id}', help = '''
                Toggle whether or not individuals in the simulation 
                will be vaccinated against the disease, overriding 
                all other vaccine-related parameters.
            '''
        )

        # General Vaccination Policy Parameters
        st.html(f'<span id = "vaccinationTriggerCondition{id}"></span>')
        with st.expander('Vaccination Programs'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control the rollout of vaccines in 
                the simulation, with parameters such as what 
                triggers the introduction of vaccines and how often 
                individuals are vaccinated for the first time.
            ''')

            # Policy parameters
            with st.container(border = True):
                loadKey(f'vaccineTrigger', id, 'Always')
                vaccineTrigger = st.selectbox(
                    'Vaccination Trigger Condition', 
                    key = f'_vaccineTrigger{id}', 
                    options = triggerNames[:-2], 
                    on_change = saveKey, args = [f'vaccineTrigger', id], # type: ignore
                    disabled = not useVaccinesToggle, help = '''
                        The type of condition that must be 
                        satisfied before vaccines will start being 
                        administered in the simulation. Additional 
                        options for configuring the exact trigger 
                        condition will appear after selecting one 
                        of these options.

                        ##### Options:
                        - Always: Vaccination will occur throughout 
                        the entire simulation.
                        - Timed: Vaccination will occur within a 
                        specific time period defined using a start 
                        and end threshold.
                        - Community Case Rate: Vaccination will 
                        begin if the rate of newly diagnosed cases 
                        per day exceeds a specific threshold, and 
                        will stop if the rate drops below a 
                        different threshold afterwards. This 
                        trigger rate allows vaccination to start 
                        and stop multiple times if the case rate 
                        varies between the two thresholds.
                        - Community Case Total: Vaccination will 
                        begin after the number of diagnosed cases 
                        in the community exceeds a specific 
                        threshold, and will continue for the rest 
                        of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if vaccineTrigger == 'Timed':
                    vaccinePeriodErrorContainer = st.empty()
                    loadKey(f'vaccinePeriod', id, (29, 59))
                    vaccinePeriod = st.select_slider(
                        'Vaccination Time Period', range(720), (29, 59), 
                        key = f'_vaccinePeriod{id}', 
                        format_func = lambda x: f'Day {x + 1}', 
                        on_change = saveKey, 
                        args = [f'vaccinePeriod', id], # type: ignore
                        disabled = not useVaccinesToggle, help = '''
                            The time period during which 
                            vaccinations will be administered in 
                            the simulation. The first value is the 
                            day on which vaccine distribution will 
                            begin (where Day 1 is the first day of 
                            the simulation), and the second value 
                            is the day on which vaccine 
                            distribution will end.
                        '''
                    )

                    # Show error if time period goes past sim length
                    if vaccinePeriod[0] >= simLength: 
                        vaccinePeriodErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the vaccination time period 
                            for this scenario (defined below) is 
                            set to begin on Day 
                            {vaccinePeriod[0] + 1}. As such, no 
                            vaccinations will ever occur in this 
                            scenario under these parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Vaccination Time Period to 
                            any point before Day {simLength}. 
                            - Change the scenario's Vaccination 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {vaccinePeriod[0] + 1} days or 
                            more.
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the vaccination time period 
                            for this scenario is set to begin on 
                            Day {vaccinePeriod[0] + 1}. As such, no 
                            vaccinations will ever occur in this 
                            scenario under these parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Vaccination Time Period in 
                            the "Vaccination Programs" section of 
                            the "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's Vaccination 
                            Trigger Condition in the "Vaccination 
                            Programs" section of the "Vaccinations 
                            and NPIs" tab to any option other than 
                            "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {vaccinePeriod[0] + 1} days or 
                            more.
                        ''', icon = ':material/error:')
                        st.session_state[f'vaccinePeriodError{id}'] = 2
                    elif vaccinePeriod[1] >= simLength: 
                        vaccinePeriodErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the vaccination time period 
                            for this scenario (defined below) is 
                            set to end on Day 
                            {vaccinePeriod[1] + 1}. As such, 
                            vaccinations will still be ongoing when 
                            the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the 
                            scenario's Vaccination Time Period to 
                            any point before Day {simLength}. 
                            - Change the scenario's Vaccination 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {vaccinePeriod[1] + 1} days or 
                            more.
                        ''', icon = ':material/warning:')
                        globalErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the vaccination time period 
                            for this scenario is set to end on Day 
                            {vaccinePeriod[1] + 1}. As such, 
                            vaccinations will still be ongoing when 
                            the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the 
                            scenario's Vaccination Time Period in 
                            the "Vaccination Programs" section of 
                            the "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's Vaccination 
                            Trigger Condition in the "Vaccination 
                            Programs" section of the "Vaccinations 
                            and NPIs" tab to any option other than 
                            "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {vaccinePeriod[1] + 1} days or 
                            more.
                        ''', icon = ':material/warning:')
                        st.session_state[f'vaccinePeriodError{id}'] = 1
                    else: st.session_state[f'vaccinePeriodError{id}'] = 0
                
                # Rate triggers
                elif vaccineTrigger == 'Community Case Rate': st.info('''
                    Due to the design of the *Flusim* model, case 
                    rate thresholds must be defined globally. You 
                    may configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at 
                    the bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go 
                    there directly).
                ''', icon = ':material/info:')
                # Case triggers
                elif vaccineTrigger == 'Community Case Total': st.info('''
                    Due to the design of the *Flusim* model, case 
                    total thresholds must be defined globally. You 
                    may configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at 
                    the bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go 
                    there directly).
                ''', icon = ':material/info:')
            # Other vaccine schedule parameters
            loadKey(f'limitDosesToggle', id, False)
            limitDosesToggle = st.toggle(
                'Enable Limited Number of Vaccine Doses', value = False, 
                key = f'_limitDosesToggle{id}', on_change = saveKey, 
                args = [f'limitDosesToggle', id], # type: ignore
                help = '''
                    Toggle whether the total number of vaccine 
                    first doses that can be administered across the 
                    whole simulation should be limited to a 
                    specific value, putting an upper limit on the 
                    number of vaccinated individuals in the 
                    simulation.
                '''
            )
            loadKey(f'initialDoseReserve', id, 0)
            st.number_input(
                'Total Number of Vaccine First Doses', 
                0, key = f'_initialDoseReserve{id}', 
                disabled = not useVaccinesToggle or not limitDosesToggle, 
                on_change = saveKey, args = [f'initialDoseReserve', id], # type: ignore
                placeholder = 'Enter a whole number of doses', help = '''
                    The total number of vaccine first doses that 
                    will be available to administer to unvaccinated 
                    individuals throughout the simulation. Once all 
                    first doses have been administered, any 
                    remaining unvaccinated individuals in the 
                    simulation will never be vaccinated. 
                    Individuals who have already received the first 
                    dose of the vaccine will still receive future 
                    doses regardless of the remaining dose count.

                    This parameter is ignored if "Enable Limited 
                    Number of Vaccine Doses" has been toggled off.
                '''
            )
            loadKey(f'firstDoseRate', id, 300)
            st.number_input(
                'First Dose Vaccination Rate (Vaccinations per Day)', 
                1, value = 300, key = f'_firstDoseRate{id}', 
                placeholder = 'Enter a whole number of people', 
                on_change = saveKey, args = [f'firstDoseRate', id], # type: ignore
                disabled = not useVaccinesToggle, help = '''
                    The number of unvaccinated individuals who will 
                    receive the first dose of the vaccine each day, 
                    assuming there are enough doses available.
                '''
            )
            baseVacPropErrorContainer = st.empty()
            loadKey(f'initialVaccinated', id, 0.0)
            initialVaccinated = st.select_slider(
                'Initial Vaccinated Proportion of Population', 
                np.linspace(0.0, 1.0, 201), 0.0, 
                key = f'_initialVaccinated{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                on_change = saveKey, args = [f'initialVaccinated', id], # type: ignore
                disabled = not useVaccinesToggle, help = '''
                    The percentage of the population that will 
                    already be vaccinated against the disease at 
                    the beginning of the simulation.
                '''
            )
            loadKey(f'targetVaccinated', id, 0.8)
            targetVaccinated = st.select_slider(
                'Target Vaccinated Proportion of Population', 
                np.linspace(0.0, 1.0, 201), 0.8, 
                key = f'_targetVaccinated{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                on_change = saveKey, args = [f'targetVaccinated', id], # type: ignore
                disabled = not useVaccinesToggle, help = '''
                    The percentage of the population that will be 
                    targeted by the vaccine schedule in the 
                    simulation. The actual proportion of the 
                    population that is vaccinated may be lower if 
                    there are an insufficient number of doses 
                    available.
                '''
            )

            # Show error if initial proportion is above target
            if useVaccinesToggle and initialVaccinated >= targetVaccinated:
                baseVacPropErrorContainer.warning(f'''
                    Warning: The target vaccinated proportion in 
                    the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } for all age groups is currently set to 
                    {100 * targetVaccinated:0.3g}% of the 
                    population, but the initial vaccinated 
                    proportion for this scenario is set to 
                    {100 * initialVaccinated:0.3g}%. As such, the 
                    target vaccination level will already be met, 
                    and no new vaccinations will occur in this 
                    scenario. 
                    
                    If this is not desired behaviour, please 
                    address this error by making one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Initial Vaccinated 
                    Proportion of Population to be greater 
                    than {100 * targetVaccinated:0.3g}%. 
                    - Decrease the scenario's Target Vaccinated 
                    Proportion of Population to be lower 
                    than {100 * initialVaccinated:0.3g}%. 
                ''', icon = ':material/warning:')
                globalErrorContainer.warning(f'''
                    Warning: The target vaccinated proportion in 
                    the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } for all age groups is currently set to 
                    {100 * targetVaccinated:0.3g}% of the 
                    population, but the initial vaccinated 
                    proportion for this scenario is set to 
                    {100 * initialVaccinated:0.3g}%. As such, the 
                    target vaccination level will already be met, 
                    and no new vaccinations will occur in this 
                    scenario. 
                    
                    If this is not desired behaviour, please 
                    address this error by making one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Initial Vaccinated 
                    Proportion of Population in the "Vaccination 
                    Programs" section of the "Vaccinations and 
                    NPIs" tab to be greater 
                    than {100 * targetVaccinated:0.3g}%. 
                    - Decrease the scenario's Target Vaccinated 
                    Proportion of Population in the "Vaccination 
                    Programs" section of the "Vaccinations and 
                    NPIs" tab to be lower 
                    than {100 * initialVaccinated:0.3g}%. 
                ''', icon = ':material/warning:')
                st.session_state[f'baseVacPropError{id}'] = 1
            else: st.session_state[f'baseVacPropError{id}'] = 0

            # Store age-based proportion values for error checking
            vacAgeInitials, vacAgeTargets = {}, {}

            # Modifiable-length field for age-specific vaccination
            st.markdown('''
                ### Age-Specific Vaccinated Proportion Parameters
                
                This section allows for unique vaccinated 
                proportion parameters to be defined for individual 
                age groups in the simulation, overriding the global 
                parameters defined above.
            ''')
            # Save relevant params as variables to avoid lookups
            vaccineRowCount = st.session_state[f'vacAgeRowCount{id}']
            vacAgeRemainingGroups = st.session_state[
                f'vaccineRemainingAgeGroups{id}'
            ]
            vacAgeErrorContainer = st.container()
            vacAgeProportionContainer = st.container()
            for i in range(vaccineRowCount): 
                (
                    vacAgeGroupColumn, vacAgeInitialColumn, vacAgeRemoveColumn
                ) = vacAgeProportionContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment = 'center'
                )
                vacAgeCurrentGroup = st.session_state.get(
                    f'vacAgeGroup{id}-{i}'
                )

                # Age group column
                loadKey(
                    f'vacAgeGroup', id, 
                    vacAgeCurrentGroup if vacAgeCurrentGroup 
                    else vacAgeRemainingGroups[0], f'-{i}'
                )
                with vacAgeGroupColumn: vacAgeGroup = st.selectbox(
                    'Age Group', key = f'_vacAgeGroup{id}-{i}', 
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    options = (
                        [vacAgeCurrentGroup] + [
                            group for group in vacAgeRemainingGroups 
                            if group != vacAgeCurrentGroup
                        ] if vacAgeCurrentGroup else vacAgeRemainingGroups
                    ), 
                    disabled = (
                        not useVaccinesToggle or not vaccineRowCount < 10
                    ),
                    on_change = saveKey, args = [f'vacAgeGroup', id, f'-{i}'], # type: ignore
                    help = '''
                        An age group that will have specific 
                        vaccination initial and target proportions 
                        defined for it, overriding the base 
                        proportions.

                        ##### Options:
                        - Young Infant: 0-6 months old.
                        - Infant: 7-24 months old.
                        - Young Child: 3-5 years old.
                        - Child: 6-12 years old.
                        - Adolescent: 13-17 years old.
                        - Young Adult: 18-24 years old.
                        - Adult: 25-44 years old.
                        - Older Adult: 45-64 years old.
                        - Senior: 65-79 years old.
                        - Older Senior: 80+ years old.
                    '''
                )
                # Initial proportion column
                loadKey(f'vacAgeInitial', id, 0.0, f'-{i}')
                with vacAgeInitialColumn: 
                    vacAgeInitials[vacAgeGroup] = st.select_slider(
                        'Initial Vaccinated Proportion of Population', 
                        np.linspace(0.0, 1.0, 201), 0.0,  
                        format_func = lambda x: f'{100 * x:0.3g}%',
                        disabled = not useVaccinesToggle, 
                        on_change = saveKey, 
                        args = [f'vacAgeInitial', id, f'-{i}'], # type: ignore
                        key = f'_vacAgeInitial{id}-{i}', help = '''
                            The percentage of individuals in this 
                            age group that will already be 
                            vaccinated against the disease at the 
                            beginning of the simulation.
                        '''
                    )
                # Target proportion column
                loadKey(f'vacAgeTarget', id, 0.8, f'-{i}')
                with vacAgeInitialColumn: 
                    vacAgeTargets[vacAgeGroup] = st.select_slider(
                        'Target Vaccinated Proportion of Population', 
                        np.linspace(0.0, 1.0, 201), 0.8, 
                        format_func = lambda x: f'{100 * x:0.3g}%',
                        disabled = not useVaccinesToggle, 
                        on_change = saveKey, 
                        args = [f'vacAgeTarget', id, f'-{i}'], # type: ignore
                        key = f'_vacAgeTarget{id}-{i}', help = '''
                            The percentage of individuals in this 
                            age group that will be targeted by the 
                            vaccine schedule in the simulation. The 
                            actual proportion of individuals that 
                            are vaccinated may be lower if there 
                            are an insufficient number of doses 
                            available.
                        '''
                    )
                # Delete button column
                with vacAgeRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:',
                    key = f'vacAgeRemove{id}-{i}', 
                    on_click = deleteFormRow, args = (
                        i, f'vacAgeRowCount{id}', {
                            f'vacAgeGroup{id}-', f'vacAgeInitial{id}-', 
                            f'vacAgeTarget{id}-'
                        }
                    ),
                    disabled = not useVaccinesToggle, help = '''
                        Remove this row of the form and remove 
                        these age-specific vaccine proportion 
                        values from the simulation.
                    '''
                )
            # Button to add another row for age specific params
            vacAgeProportionContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'vacAgeAdd{id}', args = (
                    f'vacAgeRowCount{id}', {
                        f'vacAgeGroup{id}-{vaccineRowCount}': (
                            vacAgeRemainingGroups[0] 
                            if vacAgeRemainingGroups else None
                        ),
                        f'vacAgeInitial{id}-{vaccineRowCount}': 
                        initialVaccinated,
                        f'vacAgeTarget{id}-{vaccineRowCount}': 
                        targetVaccinated,
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not vaccineRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can 
                    select an additional age group to have unique 
                    vaccinated proportion values.
                ''' if vaccineRowCount <= 9 else '''
                    All age groups have been given unique 
                    vaccinated proportion values, so a new age 
                    group cannot be added.
                '''
            )

            # Age-based errors if initial proportion is above target
            for age in vacAgeInitials.keys():
                currentInitial = vacAgeInitials[age] 
                currentTarget = vacAgeTargets[age]
                if useVaccinesToggle and currentInitial >= currentTarget: 
                    vacAgeErrorContainer.warning(f'''
                        Warning: The target vaccinated proportion 
                        in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } for the "{age}" age group is currently 
                        set to {100 * currentTarget:0.3g}% of the 
                        population, but the initial vaccinated 
                        proportion for said age group in this 
                        scenario is set to 
                        {100 * currentInitial:0.3g}%. As such, the 
                        target vaccination level will already be 
                        met, and no new vaccinations will occur in 
                        this scenario for individuals in the 
                        "{age}" age group. 
                        
                        If this is not desired behaviour, please 
                        address this error by making one of the 
                        following changes before running the 
                        simulation:
                            
                        - Remove the scenario's age-specific 
                        vaccination proportions for the "{age}" age 
                        group.
                        - Increase the scenario's Initial 
                        Vaccinated Proportion of Population for the 
                        "{age}" age group to be greater 
                        than {100 * currentTarget:0.3g}%. 
                        - Decrease the scenario's Target Vaccinated 
                        Proportion of Population for the "{age}" 
                        age group to be lower 
                        than {100 * currentInitial:0.3g}%. 
                    ''', icon = ':material/warning:')
                    globalErrorContainer.warning(f'''
                        Warning: The target vaccinated proportion 
                        in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } for the "{age}" age group is currently 
                        set to {100 * currentTarget:0.3g}% of the 
                        population, but the initial vaccinated 
                        proportion for said age group in this 
                        scenario is set to 
                        {100 * currentInitial:0.3g}%. As such, the 
                        target vaccination level will already be 
                        met, and no new vaccinations will occur in 
                        this scenario for individuals in the 
                        "{age}" age group. 
                        
                        If this is not desired behaviour, please 
                        address this error by making one of the 
                        following changes before running the 
                        simulation:
                            
                        - Remove the scenario's age-specific 
                        vaccination proportions for the "{age}" age 
                        group from the "Vaccination Programs" 
                        section of the "Vaccinations and NPIs" tab.
                        - Increase the scenario's Initial 
                        Vaccinated Proportion of Population for the 
                        "{age}" age group in the "Vaccination 
                        Programs" section of the "Vaccinations and 
                        NPIs" tab to be greater 
                        than {100 * currentTarget:0.3g}%. 
                        - Decrease the scenario's Target Vaccinated 
                        Proportion of Population for the "{age}" 
                        age group in the "Vaccination Programs" 
                        section of the "Vaccinations and NPIs" tab 
                        to be lower 
                        than {100 * currentInitial:0.3g}%. 
                    ''', icon = ':material/warning:')
                    st.session_state[f'ageVacPropError{id}'] = 1
                    ageVacPropError = True
            # Reset error parameter if none of the age levels error
            if not ageVacPropError: 
                st.session_state[f'ageVacPropError{id}'] = 0
            



        # Primary Vaccine Parameters
        with st.expander('Vaccine Properties'):
            # Describe primary vaccines
            st.markdown('''
                These parameters control the properties of the main
                schedule of vaccines that will be administered to 
                individuals within the simulation. Each vaccine in 
                the schedule can have its own efficacy values set, 
                since in many cases multiple doses are required to 
                achieve maximum immunity to the disease.
            ''')

            # Universal primary parameters
            loadKey(f'primaryDoseCount', id, 2)
            primaryDoseCount = st.slider(
                'Number of Vaccine Doses', 1, 5, 2, 
                key = f'_primaryDoseCount{id}', 
                on_change = saveKey, args = [f'primaryDoseCount', id], # type: ignore
                disabled = not useVaccinesToggle, help = '''
                    The number of times each individual in the 
                    simulation will be administered a vaccine for 
                    the disease, excluding booster vaccines. 
                    
                    Note that since efficacy is defined separately 
                    for each vaccine dose in the schedule, 
                    modifying this value will change the number of 
                    sections used for specifying efficacy below.
                '''
            )
            loadKey(f'primaryDelay', id, 3)
            st.slider(
                'Time Between Vaccine Doses (Months)', 
                1, 36, 3, disabled = not useVaccinesToggle, 
                on_change = saveKey, args = [f'primaryDelay', id], # type: ignore
                key = f'_primaryDelay{id}', help = '''
                    The number of months after an individual 
                    receives a vaccine dose before they are able to 
                    receive another, where a month is 30 days.
                '''
            )
            loadKey(f'primaryDuration', id, 6)
            st.slider(
                'Vaccine Immunity Waning Delay (Months)', 
                1, 36, 6, disabled = not useVaccinesToggle, 
                on_change = saveKey, args = [f'primaryDuration', id], # type: ignore
                key = f'_primaryDuration{id}', help = '''
                    The number of months after an individual 
                    receives a vaccine dose before the immunity 
                    conferred by this vaccine begins to diminish, 
                    where a month is 30 days.
                '''
            )
            loadKey(f'primaryWanedEfficacy', id, 0.0)
            primaryWanedEfficacy = st.select_slider(
                'Dose Efficacy After Immunity Waning (Probability)', 
                np.linspace(0.0, 1.0, 201), 0.0, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useVaccinesToggle, 
                on_change = saveKey, args = [f'primaryWanedEfficacy', id], # type: ignore
                key = f'_primaryWanedEfficacy{id}', help = '''
                    The final efficacy value that the vaccine 
                    schedule will approach as the immunity it 
                    provides begins to diminish, represented as the 
                    probability that an individual with completely 
                    waned immunity will remain healthy when exposed 
                    to the disease.
                '''
            )
            loadKey(f'primaryWaningRate', id, 12)
            st.slider(
                'Vaccine Waning Duration (Months)', 
                0, 36, 12, disabled = not useVaccinesToggle, 
                on_change = saveKey, args = [f'primaryWaningRate', id], # type: ignore
                key = f'_primaryWaningRate{id}', help = '''
                    The number of months after the immunity from a 
                    vaccine dose begins waning before the efficacy 
                    of the vaccine stabilises, where a month is 30 
                    days. Vaccine-conferred immunity in the 
                    *Flusim* simulation will wane at a linear rate, 
                    so this parameter represents how long it takes 
                    for the vaccine's efficacy to decrease from the 
                    final dose's initial value to its final value.

                    If this parameter is set to 0, the immunity 
                    provided by the main vaccine schedule will 
                    never diminish.
                '''
            )

            # Store age-based waned efficacy values for error checks
            primAgeWaneds = {}

            # Age-Specific Waned Efficacy Field
            st.markdown('''
                #### Age-Specific Efficacy After Immunity Waning
                
                This section allows for unique final efficacy 
                values after immunity waning to be defined for 
                individual age groups in the simulation, overriding 
                the global waned efficacy defined above.
            ''')
            # Save relevant params as variables to avoid lookups
            primaryWanedRowCount = st.session_state[
                f'primWanedRowCount{id}'
            ]
            primWanedRemainingGroups = st.session_state[
                f'primaryRemainingWanedGroups{id}'
            ]
            primWanedContainer = st.container()
            for i in range(primaryWanedRowCount):
                (
                    primWanedGroupColumn, primWanedEffColumn, 
                    primWanedRemoveColumn
                ) = primWanedContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment = 'center'
                )
                primWanedCurrentGroup = st.session_state.get(
                    f'primWanedGroup{id}-{i}'
                )

                # Age group column
                loadKey(
                    f'primWanedGroup', id, 
                    primWanedCurrentGroup if primWanedCurrentGroup 
                    else primWanedRemainingGroups[0], f'-{i}'
                )
                with primWanedGroupColumn: primWanedGroup = st.selectbox(
                    'Age Group', key = f'_primWanedGroup{id}-{i}', 
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    options = (
                        [primWanedCurrentGroup] + [
                            group for group in primWanedRemainingGroups 
                            if group != primWanedCurrentGroup
                        ] if primWanedCurrentGroup 
                        else primWanedRemainingGroups
                    ), 
                    disabled = (
                        not useVaccinesToggle 
                        or not primaryWanedRowCount < 10
                    ),
                    on_change = saveKey, 
                    args = [f'primWanedGroup', id, f'-{i}'], # type: ignore
                    help = '''
                        An age group that will have a specific 
                        final efficacy value after immunity waning 
                        defined for it, overriding the base waned 
                        efficacy value.

                        ##### Options:
                        - Young Infant: 0-6 months old.
                        - Infant: 7-24 months old.
                        - Young Child: 3-5 years old.
                        - Child: 6-12 years old.
                        - Adolescent: 13-17 years old.
                        - Young Adult: 18-24 years old.
                        - Adult: 25-44 years old.
                        - Older Adult: 45-64 years old.
                        - Senior: 65-79 years old.
                        - Older Senior: 80+ years old.
                    '''
                )
                # Waned efficacy column
                loadKey(f'primAgeWanedEfficacy', id, 0.0, f'-{i}')
                with primWanedEffColumn: 
                    primAgeWaneds[primWanedGroup] = st.select_slider(
                        ((
                            'Dose Efficacy After Immunity '
                            'Waning (Probability)'
                        )), 
                        np.linspace(0.0, 1.0, 201), 0.0, 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        disabled = not useVaccinesToggle, 
                        on_change = saveKey, 
                        args = [f'primAgeWanedEfficacy', id, f'-{i}'], # type: ignore
                        key = f'_primAgeWanedEfficacy{id}-{i}', help = '''
                            The final efficacy value that the 
                            vaccine schedule will approach for this 
                            age group as the immunity it provides 
                            begins to diminish, represented as the 
                            probability that an individual in this 
                            age group with completely waned 
                            immunity will not remain healthy when 
                            exposed to the disease.
                        '''
                    )
                # Delete button column
                with primWanedRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:',
                    key = f'primWanedRemove{id}-{i}', 
                    on_click = deleteFormRow, args = (
                        i, f'primWanedRowCount{id}', {
                            f'primWanedGroup{id}-', 
                            f'primAgeWanedEfficacy{id}-'
                        }
                    ),
                    disabled = not useVaccinesToggle, help = '''
                        Remove this row of the form and remove 
                        these age-specific vaccine waned efficacy 
                        values from the simulation.
                    '''
                )
            # Button to add another row for age-specific params
            primWanedContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'primWanedAdd{id}', args = (
                    f'primWanedRowCount{id}', {
                        f'primWanedGroup{id}-{primaryWanedRowCount}': (
                            primWanedRemainingGroups[0] 
                            if primWanedRemainingGroups else None
                        ),
                        f'primAgeWanedEfficacy{id}-{primaryWanedRowCount}':
                        primaryWanedEfficacy
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not primaryWanedRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can 
                    select an additional age group to have unique 
                    vaccine waned efficacy values.
                ''' if primaryWanedRowCount <= 9 else '''
                    All age groups have been given unique waned 
                    efficacy values, so a new age group cannot be 
                    added.
                '''
            )

            # Store age-based efficacy values for error checking
            primaryInitialEfficacy = 0.5
            primAgeInitials = {}


            # Modifiable-length field for each primary dose
            st.markdown('''
                ### Individual Dose Efficacies
                
                Here you can set the initial efficacy of each 
                vaccine dose in the schedule separately. Note that 
                changing the "Number of Vaccine Doses" parameter 
                will affect how many sections are present here.
            ''')
            for i in range(primaryDoseCount):
                doseEfficacyContainer = st.container(border = True)
                doseEfficacyContainer.markdown(
                    f'#### {ordinals[i+1]} Vaccine Dose'
                )
                loadKey(f'primaryBaseEfficacy', id, 0.5, f'-{i}')
                baseDoseEfficacy = doseEfficacyContainer.select_slider(
                    'Initial Dose Efficacy (Probability)', 
                    np.linspace(0.0, 1.0, 201), 0.5, 
                    format_func = lambda x: f'{100 * x:0.3g}%', 
                    disabled = not useVaccinesToggle, on_change = saveKey, 
                    args = [f'primaryBaseEfficacy', id, f'-{i}'], # type: ignore
                    key = f'_primaryBaseEfficacy{id}-{i}', help = '''
                        The initial efficacy of this vaccine dose, 
                        represented as the probability that an 
                        individual that has recently received the 
                        dose will remain healthy when exposed 
                        to the disease.
                    '''
                )

                # Last efficacy value is all that's cared about
                # for error checking purposes
                if i == primaryDoseCount - 1:
                    primaryInitialEfficacy = baseDoseEfficacy
                    # Show error if waned efficacy is above initial
                    if (
                        useVaccinesToggle 
                        and primaryWanedEfficacy > primaryInitialEfficacy
                    ):
                        st.error(f'''
                            Error: The initial vaccine efficacy in 
                            the {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } for the final vaccine dose in all age 
                            groups is currently set to 
                            {100 * primaryInitialEfficacy:0.3g}% 
                            effectiveness, but the final vaccine 
                            efficacy after immunity waning for this 
                            scenario is set to 
                            {100 * primaryWanedEfficacy:0.3g}%. As 
                            such, the immunity to the disease 
                            conferred by the vaccine will get 
                            stronger over time instead of weaker. 

                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:

                            - Increase the scenario's Initial 
                            Dose Efficacy to be greater than 
                            {100 * primaryWanedEfficacy:0.3g}%. 
                            - Decrease the scenario's Dose Efficacy 
                            After Immunity Waning to be lower than 
                            {100 * primaryInitialEfficacy:0.3g}%. 
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The initial vaccine efficacy in 
                            the {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } for all age groups is currently set 
                            to {100 * primaryInitialEfficacy:0.3g}% 
                            effectiveness, but the final vaccine 
                            efficacy after immunity waning for this 
                            scenario is set to 
                            {100 * primaryWanedEfficacy:0.3g}%. As 
                            such, the immunity to the disease 
                            conferred by the vaccine will get 
                            stronger over time instead of weaker. 

                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:

                            - Increase the scenario's Initial 
                            Dose Efficacy in the "Vaccination 
                            Properties" section of the 
                            "Vaccinations and NPIs" tab to be 
                            greater than 
                            {100 * primaryWanedEfficacy:0.3g}%. 
                            - Decrease the scenario's Dose Efficacy 
                            After Immunity Waning in the 
                            "Vaccination Properties" section of the 
                            "Vaccinations and NPIs" tab to be lower 
                            than 
                            {100 * primaryInitialEfficacy:0.3g}%. 
                        ''', icon = ':material/error:')
                        st.session_state[f'basePrimEfficacyError{id}'] = 2
                    else: 
                        st.session_state[f'basePrimEfficacyError{id}'] = 0

                # Age-Specific Primary Efficacy Field
                doseEfficacyContainer.markdown('''
                    ##### Age-Specific Efficacy Rates
                    
                    This section allows unique initial efficacy 
                    values for this dose to be defined for 
                    individual age groups in the simulation, 
                    overriding the global initial efficacy value 
                    for this dose defined above.
                ''')
                # Save remaining ages to variable to avoid lookups
                primAgeRemainingGroups = st.session_state[
                    f'primaryRemainingAgeGroups{id}-{i}'
                ]
                (
                    primEfficacyErrorContainer
                ) = doseEfficacyContainer.container()
                primEfficacyContainer = doseEfficacyContainer.container()
                for j in range(primaryAgeRowCounts[i]):
                    (
                        primAgeGroupColumn, primAgeEfficacyColumn, 
                        primAgeRemoveColumn
                    ) = primEfficacyContainer.columns(
                        (0.25, 0.55, 0.2), vertical_alignment = 'center'
                    )
                    primAgeCurrentGroup = st.session_state.get(
                        f'primAgeGroup{id}-{i}-{j}'
                    )
                    # Age group column
                    loadKey(
                        f'primAgeGroup', id, 
                        primAgeCurrentGroup if primAgeCurrentGroup 
                        else primAgeRemainingGroups[0], f'-{i}-{j}'
                    )
                    with primAgeGroupColumn: primAgeGroup = st.selectbox(
                        'Age Group', key = f'_primAgeGroup{id}-{i}-{j}', 
                        # Set age group options such that only ages 
                        # that haven't been selected yet can be 
                        # selected
                        options = (
                            [primAgeCurrentGroup] + [
                                group for group in primAgeRemainingGroups 
                                if group != primAgeCurrentGroup
                            ] if primAgeCurrentGroup 
                            else primAgeRemainingGroups
                        ), 
                        disabled = (
                            not useVaccinesToggle 
                            or not primaryAgeRowCounts[i] < 10
                        ), 
                        on_change = saveKey, 
                        args = [f'primAgeGroup', id, f'-{i}-{j}'], # type: ignore
                        help = '''
                            An age group that will have specific 
                            initial vaccine efficacy values defined 
                            for it, overriding the base efficacy 
                            value for this vaccine dose.

                            ##### Options:
                            - Young Infant: 0-6 months old.
                            - Infant: 7-24 months old.
                            - Young Child: 3-5 years old.
                            - Child: 6-12 years old.
                            - Adolescent: 13-17 years old.
                            - Young Adult: 18-24 years old.
                            - Adult: 25-44 years old.
                            - Older Adult: 45-64 years old.
                            - Senior: 65-79 years old.
                            - Older Senior: 80+ years old.
                        '''
                    )
                    # Initial efficacy column
                    loadKey(f'primAgeEfficacy', id, 0.5, f'-{i}-{j}')
                    with primAgeEfficacyColumn: 
                        ageInitialEfficacy = st.select_slider(
                            'Initial Dose Efficacy (Probability)',
                            np.linspace(0.0, 1.0, 201), 0.5, 
                            format_func = lambda x: f'{100 * x:0.3g}%', 
                            disabled = not useVaccinesToggle, 
                            key = f'_primAgeEfficacy{id}-{i}-{j}', 
                            on_change = saveKey, 
                            args = [f'primAgeEfficacy', id, f'-{i}-{j}'], # type: ignore
                            help = '''
                                The initial efficacy of this 
                                vaccine dose for this age group, 
                                represented as the probability that 
                                a recently vaccinated individual in 
                                this age group will remain healthy 
                                when exposed to the disease.
                            '''
                        )

                        # Last efficacy value is all that's cared 
                        # about for error checking purposes
                        if i == primaryDoseCount - 1: 
                            primAgeInitials[
                                primAgeGroup
                            ] = ageInitialEfficacy

                    # Delete button column
                    with primAgeRemoveColumn: st.button(
                        label = 'Remove Age Group', 
                        icon = ':material/delete:',
                        key = f'primAgeRemove{id}-{i}-{j}', 
                        on_click = deleteFormRow, args = (
                            i, f'primAgeRowCount{id}-{i}', {
                                f'primAgeGroup{id}-{i}-', 
                                f'primAgeEfficacy{id}-{i}-'
                            }
                        ),
                        disabled = not useVaccinesToggle, help = '''
                            Remove this row of the form and remove 
                            these age-specific initial vaccine 
                            efficacy values from the simulation.
                        '''
                    )
                # Button to add another row for age-specific params
                primEfficacyContainer.button(
                    label = 'Add Age Group', icon = ':material/add:', 
                    on_click = addFormRow, key = f'primAgeAdd{id}-{i}', 
                    args = (f'primAgeRowCount{id}-{i}', {
                        f'primAgeGroup{id}-{i}-{primaryAgeRowCounts[i]}': 
                        (
                            primAgeRemainingGroups[0] 
                            if primAgeRemainingGroups else None
                        ),
                        ((
                            f'primAgeEfficacy{id}-{i}'
                            f'-{primaryAgeRowCounts[i]}'
                        )): baseDoseEfficacy
                    }), 
                    disabled = (
                        not useVaccinesToggle 
                        or not primaryAgeRowCounts[i] < 10
                    ),
                    help = '''
                        Add another row to this form, where you can 
                        select an additional age group to have 
                        unique initial vaccine efficacy values.
                    ''' if primaryAgeRowCounts[i] <= 9 else '''
                        All age groups have been given unique 
                        initial efficacy values for this vaccine 
                        dose, so a new age group cannot be added.
                    '''
                )

                # Check errors in age-based primary efficacy
                if i == primaryDoseCount - 1 and useVaccinesToggle:
                    initialAges = primAgeInitials.keys()
                    wanedAges = primAgeWaneds.keys()
                    for age in list(initialAges) + list(
                        set(wanedAges) - set(initialAges)
                    ):
                        initialAgeEfficacy = primAgeInitials.get(
                            age, primaryInitialEfficacy
                        )
                        wanedAgeEfficacy = primAgeWaneds.get(
                            age, primaryWanedEfficacy
                        )
                        ageIsInitial = age in initialAges
                        ageIsWaned = age in wanedAges
                        if initialAgeEfficacy > wanedAgeEfficacy: 
                            primEfficacyErrorContainer.error(f'''
                                Error: The initial vaccine efficacy 
                                in the {
                                    'baseline scenario' if id == 0 
                                    else f'scenario named "{
                                        st.session_state[
                                            f'scenarioName{id}'
                                        ]
                                    }"'
                                } for the final dose in the "{age}" 
                                age group is currently set to {
                                    '' if ageIsInitial 
                                    else 'the scenario base value of'
                                } {100 * initialAgeEfficacy:0.3g}% 
                                effectiveness, but the final 
                                vaccine efficacy after immunity 
                                waning for said age group in this 
                                scenario is set to {
                                    '' if ageIsWaned 
                                    else 'the scenario base value of'
                                } {100 * wanedAgeEfficacy:0.3g}%. 
                                As such, the immunity to the 
                                disease conferred by the vaccine
                                will get stronger over time instead 
                                of weaker for individuals in the 
                                "{age}" age group. 

                                To address this error, please make 
                                one of the following changes before 
                                running the simulation:

                                - Remove the scenario's 
                                age-specific {
                                    'initial (final dose)' 
                                    if ageIsInitial else ''
                                }{
                                    'and ' if ageIsInitial and ageIsWaned 
                                    else ''
                                }{
                                    'waned ' if ageIsInitial else ''
                                }dose efficacy rate{
                                    's' if ageIsInitial and ageIsWaned 
                                    else ''
                                } for the "{age}" age group.
                                - Increase the scenario's {
                                    'age-specific' if ageIsInitial 
                                    else 'base'
                                } Initial Dose Efficacy for the 
                                final vaccine dose in the program 
                                to be greater than 
                                {100 * wanedAgeEfficacy:0.3g}%. 
                                - Decrease the scenario's {
                                    'age-specific' if ageIsInitial 
                                    else 'base'
                                } Dose Efficacy After Immunity 
                                Waning to be lower than 
                                {100 * initialAgeEfficacy:0.3g}%. 
                            ''', icon = ':material/error:')
                            globalErrorContainer.error(f'''
                                Error: The initial vaccine efficacy 
                                in the {
                                    'baseline scenario' if id == 0 
                                    else f'scenario named "{
                                        st.session_state[
                                            f'scenarioName{id}'
                                        ]
                                    }"'
                                } for the final dose in the "{age}" 
                                age group is currently set to {
                                    '' if age in initialAges 
                                    else 'the scenario base value of'
                                } {100 * initialAgeEfficacy:0.3g}% 
                                effectiveness, but the final 
                                vaccine efficacy after immunity 
                                waning for said age group in this 
                                scenario is set to {
                                    '' if age in wanedAges 
                                    else 'the scenario base value of'
                                } {100 * wanedAgeEfficacy:0.3g}%. 
                                As such, the immunity to the 
                                disease conferred by the vaccine 
                                will get stronger over time instead 
                                of weaker for individuals in the 
                                "{age}" age group. 

                                To address this error, please make 
                                one of the following changes before 
                                running the simulation:

                                - Remove the scenario's 
                                age-specific {
                                    'initial (final dose)' 
                                    if ageIsInitial else ''
                                }{
                                    'and ' if ageIsInitial and ageIsWaned 
                                    else ''
                                }{
                                    'waned ' if ageIsInitial else ''
                                }dose efficacy rate{
                                    's' if ageIsInitial and ageIsWaned 
                                    else ''
                                } for the "{age}" age group in the 
                                "Vaccination Properties" section of 
                                the "Vaccinations and NPIs" tab.
                                - Increase the scenario's {
                                    'age-specific' if ageIsInitial 
                                    else 'base'
                                } Initial Dose Efficacy for the 
                                final vaccine dose in the program 
                                in the "Vaccination Properties" 
                                section of the "Vaccinations and 
                                NPIs" tab to be greater than 
                                {100 * wanedAgeEfficacy:0.3g}%. 
                                - Decrease the scenario's {
                                    'age-specific' if ageIsInitial 
                                    else 'base'
                                } Dose Efficacy After Immunity 
                                Waning in the "Vaccination 
                                Properties" section of the 
                                "Vaccinations and NPIs" tab to be 
                                lower than 
                                {100 * initialAgeEfficacy:0.3g}%. 
                            ''', icon = ':material/error:')
                            st.session_state[
                                f'agePrimEfficacyError{id}'
                            ] = 2
                            ageBoostEfficacyError = True
                    # Reset error parameter if no errors
                    if not ageBoostEfficacyError: 
                        st.session_state[f'agePrimEfficacyError{id}'] = 0



        # Booster Parameters
        with st.expander('Booster Vaccines'):
            # Describe booster vaccines
            st.markdown('''
                These parameters control the properties of booster 
                vaccines, additional doses of a vaccine only 
                administered to individuals who have already 
                received all vaccines in the initial schedule. 
                Unlike the main vaccine doses defined above, all 
                booster vaccine doses share the same efficacy 
                values. Booster vaccines are primarily used with 
                diseases like COVID-19, meningococcal disease and 
                diphtheria to preserve an individual's immunity to 
                the disease as it wanes over time.
            ''')

            # Universal booster parameters
            loadKey(f'boosterToggle', id, False)
            useBoostersToggle = st.toggle(
                'Enable Booster Vaccines', value = False, 
                key = f'_boosterToggle{id}', on_change = saveKey, 
                args = [f'boosterToggle', id], # type: ignore
                disabled = not useVaccinesToggle, help = '''
                    Toggle whether or not booster vaccines are 
                    administered in the simulation, overriding 
                    other booster-related parameters.
                '''
            )
            loadKey(f'boosterDoseCount', id, 3)
            st.slider(
                'Number of Booster Doses', 
                1, 10, 3, key = f'_boosterDoseCount{id}',
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                on_change = saveKey, args = [f'boosterDoseCount', id], # type: ignore
                help = '''
                    The number of times each individual in the 
                    simulation will be administered a booster 
                    vaccine.
                '''
            )
            loadKey(f'boosterDelay', id, 3)
            boosterDelay = st.slider(
                'Time Between Booster Doses (Months)', 1, 36, 3,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                on_change = saveKey, args = [f'boosterDelay', id], # type: ignore
                key = f'_boosterDelay{id}', help = '''
                    The number of months after an individual receives 
                    one booster vaccine dose before they are able 
                    to receive another, where a month is 30 days.
                '''
            )
            loadKey(f'boosterDuration', id, 2)
            st.slider(
                'Booster Immunity Waning Delay (Months)', 1, 36, 2,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                on_change = saveKey, args = [f'boosterDuration', id], # type: ignore
                key = f'_boosterDuration{id}', help = '''
                    The number of months after an individual receives 
                    a booster vaccine dose before the immunity 
                    conferred by this vaccine begins to diminish, 
                    where a month is 30 days.
                '''
            )
            baseBoostEfficacyErrorContainer = st.empty()
            loadKey(f'boosterBaseEfficacy', id, 0.9)
            boosterBaseEfficacy = st.select_slider(
                'Initial Booster Efficacy (Probability)', 
                np.linspace(0.0, 1.0, 201), 0.9, 
                key = f'_boosterBaseEfficacy{id}',
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                on_change = saveKey, args = [f'boosterBaseEfficacy', id], # type: ignore
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The initial efficacy of each booster vaccine, 
                    represented as the probability that an 
                    individual that has recently received the 
                    booster will remain healthy when exposed to the 
                    disease.
                '''
            )
            loadKey(f'boosterWanedEfficacy', id, 0.6)
            boosterWanedEfficacy = st.select_slider(
                'Booster Efficacy After Immunity Waning (Probability)',
                np.linspace(0.0, 1.0, 201), 0.6, 
                key = f'_boosterWanedEfficacy{id}', 
                disabled = not useVaccinesToggle or not useBoostersToggle,
                on_change = saveKey, args = [f'boosterWanedEfficacy', id], # type: ignore
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The final efficacy value that the booster 
                    vaccine will approach as the immunity it 
                    provides begins to diminish, represented as the 
                    probability that an individual with completely 
                    waned immunity will remain healthy when exposed 
                    to the disease.
                '''
            )

            # Show error if waned efficacy is above initial
            if (
                useVaccinesToggle and useBoostersToggle 
                and boosterWanedEfficacy > boosterBaseEfficacy
            ):
                baseBoostEfficacyErrorContainer.error(f'''
                    Error: The initial booster vaccine efficacy in 
                    the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } for all age groups is currently set to 
                    {100 * boosterBaseEfficacy:0.3g}% 
                    effectiveness, but the final booster vaccine 
                    efficacy after immunity waning for this 
                    scenario is set to 
                    {100 * boosterWanedEfficacy:0.3g}%. As such, 
                    the immunity to the disease conferred by the 
                    booster will get stronger over time instead of 
                    weaker. 

                    To address this error, please make one of the 
                    following changes before running the simulation:

                    - Increase the scenario's Initial Booster 
                    Efficacy to be greater 
                    than {100 * boosterWanedEfficacy:0.3g}%. 
                    - Decrease the scenario's Booster Efficacy 
                    After Immunity Waning to be lower 
                    than {100 * boosterBaseEfficacy:0.3g}%. 
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The initial booster vaccine efficacy in 
                    the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } for all age groups is currently set to 
                    {100 * boosterBaseEfficacy:0.3g}% 
                    effectiveness, but the final booster vaccine 
                    efficacy after immunity waning for this 
                    scenario is set to 
                    {100 * boosterWanedEfficacy:0.3g}%. As such, 
                    the immunity to the disease conferred by the 
                    booster will get stronger over time instead of 
                    weaker. 

                    To address this error, please make one of the 
                    following changes before running the simulation:

                    - Increase the scenario's Initial Booster 
                    Efficacy in the "Booster Vaccines" section of 
                    the "Vaccinations and NPIs" tab to be greater 
                    than {100 * boosterWanedEfficacy:0.3g}%. 
                    - Decrease the scenario's Booster Efficacy 
                    After Immunity Waning in the "Booster Vaccines" 
                    section of the "Vaccinations and NPIs" tab to 
                    be lower than {100 * boosterBaseEfficacy:0.3g}%.
                ''', icon = ':material/error:')
                st.session_state[f'baseBoostEfficacyError{id}'] = 2
            else: st.session_state[f'baseBoostEfficacyError{id}'] = 0

            loadKey(f'boosterWaningRate', id, 6)
            st.slider(
                'Booster Waning Duration (Months)', 0, 36, 6,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                on_change = saveKey, args = [f'boosterWaningRate', id], # type: ignore
                key = f'_boosterWaningRate{id}', help = '''
                    The number of months after the immunity from a 
                    booster vaccine begins waning before the 
                    efficacy of the vaccine stabilises, where a 
                    month is 30 days. Vaccine-conferred immunity in 
                    the *Flusim* simulation will wane at a linear 
                    rate, so this parameter represents how long it 
                    takes for the vaccine's efficacy to decrease 
                    from its initial value to its final value.

                    If this parameter is set to 0, the immunity 
                    provided by booster vaccines will never 
                    diminish.
                '''
            )

            # Store age-based booster efficacy values for error checking
            boostAgeInitials, boostAgeWaneds = {}, {}

            # Modifiable-length field for age-specific efficacy
            st.markdown('''
                ### Age-Specific Booster Efficacies
                
                This section allows for unique booster efficacy 
                values (both initial and final) to be defined for 
                individual age groups in the simulation, overriding 
                the global booster efficacy values defined above.
            ''')
            # Save relevant params as variables to avoid lookups
            boosterRowCount = st.session_state[f'boostAgeRowCount{id}']
            boostAgeRemainingGroups = st.session_state[
                f'boosterRemainingAgeGroups{id}'
            ]
            boostAgeErrorContainer = st.container()
            boostAgeEfficacyContainer = st.container()
            for i in range(boosterRowCount):
                (
                    boostAgeGroupColumn, boostAgeEfficacyColumn, 
                    boostAgeRemoveColumn
                ) = boostAgeEfficacyContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment = 'center'
                )
                boostAgeCurrentGroup = st.session_state.get(
                    f'boostAgeGroup{id}-{i}'
                )
                # Age group column
                loadKey(
                    f'boostAgeGroup', id, 
                    boostAgeCurrentGroup if boostAgeCurrentGroup 
                    else boostAgeRemainingGroups[0], f'-{i}'
                )
                with boostAgeGroupColumn: boostAgeGroup = st.selectbox(
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    'Age Group', key = f'_boostAgeGroup{id}-{i}', 
                    options = (
                        [boostAgeCurrentGroup] + [
                            group for group in boostAgeRemainingGroups 
                            if group != boostAgeCurrentGroup
                        ] if boostAgeCurrentGroup 
                        else boostAgeRemainingGroups
                    ), 
                    disabled = (
                        not useVaccinesToggle or not useBoostersToggle 
                        or not boosterRowCount < 10
                    ), 
                    on_change = saveKey, 
                    args = [f'boostAgeGroup', id, f'-{i}'], # type: ignore
                    help = '''
                        An age group that will have specific 
                        booster vaccine efficacy values defined for 
                        it, overriding the base efficacy value for 
                        booster vaccines.

                        ##### Options:
                        - Young Infant: 0-6 months old.
                        - Infant: 7-24 months old.
                        - Young Child: 3-5 years old.
                        - Child: 6-12 years old.
                        - Adolescent: 13-17 years old.
                        - Young Adult: 18-24 years old.
                        - Adult: 25-44 years old.
                        - Older Adult: 45-64 years old.
                        - Senior: 65-79 years old.
                        - Older Senior: 80+ years old.
                    '''
                )
                # Standard efficacy column
                loadKey(f'boostAgeEfficacy', id, 0.9, f'-{i}')
                with boostAgeEfficacyColumn: 
                    boostAgeInitials[boostAgeGroup] = st.select_slider(
                        'Initial Booster Efficacy (Probability)', 
                        np.linspace(0.0, 1.0, 201), 0.9, disabled = (
                            not useVaccinesToggle or not useBoostersToggle
                        ), 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        on_change = saveKey, 
                        args = [f'boostAgeEfficacy', id, f'-{i}'], # type: ignore
                        key = f'_boostAgeEfficacy{id}-{i}', help = '''
                            The initial efficacy of each booster 
                            vaccine for this age group, represented 
                            as the probability that a recently 
                            vaccinated individual in this age group 
                            will remain healthy when exposed to the 
                            disease.
                        '''
                    )
                # Waned efficacy column
                loadKey(f'boostAgeWanedEfficacy', id, 0.6, f'-{i}')
                with boostAgeEfficacyColumn: 
                    boostAgeWaneds[boostAgeGroup] = st.select_slider(
                        ((
                            'Booster Efficacy After '
                            'Immunity Waning (Probability)'
                        )), 
                        np.linspace(0.0, 1.0, 201), 0.6, disabled = (
                            not useVaccinesToggle or not useBoostersToggle
                        ), 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        on_change = saveKey, 
                        args = [f'boostAgeWanedEfficacy', id, f'-{i}'], # type: ignore
                        key = f'_boostAgeWanedEfficacy{id}-{i}', help = '''
                            The final efficacy value that the 
                            booster vaccine will approach for this 
                            age group as the immunity it provides 
                            begins to diminish, represented as the 
                            probability that an individual in this 
                            age group with completely waned 
                            immunity will remain healthy when 
                            exposed to the disease.
                        '''
                    )
                # Delete button column
                with boostAgeRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:',
                    key = f'boostAgeRemove{id}-{i}', 
                    on_click = deleteFormRow, args = (
                        i, f'boostAgeRowCount{id}', {
                            f'boostAgeGroup{id}-', 
                            f'boostAgeEfficacy{id}-', 
                            f'boostAgeWanedEfficacy{id}-'
                        }
                    ),
                    disabled = (
                        not useVaccinesToggle or not useBoostersToggle
                    ), 
                    help = '''
                        Remove this row of the form and remove 
                        these age-specific booster vaccine efficacy 
                        values from the simulation.
                    '''
                )
            # Button to add another row for age-specific params
            boostAgeEfficacyContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'boostAgeAdd{id}', args = (
                    f'boostAgeRowCount{id}', {
                        f'boostAgeGroup{id}-{boosterRowCount}': (
                            boostAgeRemainingGroups[0] 
                            if boostAgeRemainingGroups else None
                        ),
                        f'boostAgeEfficacy{id}-{boosterRowCount}': 
                        boosterBaseEfficacy,
                        f'boostAgeWanedEfficacy{id}-{boosterRowCount}': 
                        boosterWanedEfficacy,
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not useBoostersToggle 
                    or not boosterRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can 
                    select an additional age group to have unique 
                    booster vaccine efficacy values.
                ''' if boosterRowCount <= 9 else '''
                    All age groups have been given unique booster 
                    vaccine efficacy values.
                '''
            )

            # Age-based errors if waned efficacy is above initial
            for age in boostAgeInitials.keys():
                currentInitial = boostAgeInitials[age] 
                currentWaned = boostAgeWaneds[age]
                if (
                    useVaccinesToggle and useBoostersToggle 
                    and currentInitial < currentWaned
                ): 
                    boostAgeErrorContainer.error(f'''
                        Error: The initial booster vaccine efficacy 
                        in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[
                                    f'scenarioName{id}'
                                    ]
                            }"'
                        } for the "{age}" age group is currently 
                        set to {100 * currentInitial:0.3g}% 
                        effectiveness, but the final booster 
                        vaccine efficacy after immunity waning for 
                        said age group in this scenario is set to 
                        {100 * currentWaned:0.3g}%. As such, the 
                        immunity to the disease conferred by the 
                        booster will get stronger over time instead 
                        of weaker for individuals in the "{age}" 
                        age group. 

                        To address this error, please make one of 
                        the following changes before running the 
                        simulation:

                        - Remove the scenario's age-specific 
                        booster efficacies for the "{age}" age 
                        group.
                        - Increase the scenario's Initial Booster 
                        Efficacy for the "{age}" age group to be 
                        greater than {100 * currentWaned:0.3g}%. 
                        - Decrease the scenario's Booster Efficacy 
                        After Immunity Waning for the "{age}" age 
                        group to be lower 
                        than {100 * currentInitial:0.3g}%. 
                    ''', icon = ':material/error:')
                    globalErrorContainer.error(f'''
                        Error: The initial booster vaccine efficacy 
                        in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[
                                    f'scenarioName{id}'
                                ]
                            }"'
                        } for the "{age}" age group is currently 
                        set to {100 * currentInitial:0.3g}% 
                        effectiveness, but the final booster 
                        vaccine efficacy after immunity waning for 
                        said age group in this scenario is set to 
                        {100 * currentWaned:0.3g}%. As such, the 
                        immunity to the disease conferred by the 
                        booster will get stronger over time instead 
                        of weaker for individuals in the "{age}" 
                        age group. 

                        To address this error, please make one of 
                        the following changes before running the 
                        simulation:

                        - Remove the scenario's age-specific 
                        booster efficacies for the "{age}" age 
                        group in the "Booster Vaccines" section of 
                        the "Vaccinations and NPIs" tab.
                        - Increase the scenario's Initial Booster 
                        Efficacy for the "{age}" age group in the 
                        "Booster Vaccines" section of the 
                        "Vaccinations and NPIs" tab to be greater 
                        than {100 * currentWaned:0.3g}%. 
                        - Decrease the scenario's Booster Efficacy 
                        After Immunity Waning for the "{age}" age 
                        group in the "Booster Vaccines" section of 
                        the "Vaccinations and NPIs" tab to be lower 
                        than {100 * currentInitial:0.3g}%. 
                    ''', icon = ':material/error:')
                    st.session_state[f'ageBoostEfficacyError{id}'] = 2
                    ageBoostEfficacyError = True
            # Reset error parameter if none of the age levels error
            if not ageBoostEfficacyError: 
                st.session_state[f'ageBoostEfficacyError{id}'] = 0
    




    # NPIs
    with st.container():
        st.subheader('Non-Pharmaceutical Intervention (NPI) Parameters')

        # General NPIs
        st.html('<span id = "generalTriggerCondition"></span>')
        with st.expander('General NPI Properties'):
            st.markdown('''
                These parameters control the implementation of 
                simple non-pharmaceutical intervention (NPI) 
                techniques that do not have configurable trigger 
                conditions, including social distancing, case 
                isolation and class dismissal.
            ''')

            # Social distancing
            loadKey(f'socialDistancingToggle', id, False)
            useSocialDistancingToggle = st.toggle(
                'Enable Social Distancing', value = False, 
                on_change = saveKey, 
                args = [f'socialDistancingToggle', id], # type: ignore
                key = f'_socialDistancingToggle{id}', help = '''
                    Toggle whether or not social distancing 
                    interventions are implemented in the 
                    simulation, overriding other social distancing 
                    parameters.
                '''
            )
            loadKey(f'socialDistancingCompliance', id, 0.9)
            socialDistancingCompliance = st.select_slider(
                'Social Distancing Compliance (Probability)', 
                np.linspace(0.0, 1.0, 201), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useSocialDistancingToggle, 
                on_change = saveKey, 
                args = [f'socialDistancingCompliance', id], # type: ignore
                key = f'_socialDistancingCompliance{id}', help = '''
                    The probability that an individual will comply 
                    with social distancing interventions in the 
                    simulation.
                '''
            )
            # Age-specific social distancing compliance
            st.markdown('''
                ### Age-Specific Social Distancing Compliance
                
                This section allows for unique social distancing 
                compliance values to be defined for individual age 
                groups in the simulation, overriding the global 
                probability defined above.
            ''')
            # Save relevant params as variables to avoid lookups
            socialRowCount = st.session_state[f'socialRowCount{id}']
            socialRemainingGroups = st.session_state[
                f'socialRemainingAgeGroups{id}'
            ]
            socialAgeContainer = st.container()
            for i in range(socialRowCount): 
                (
                    socialGroupColumn, socialComplianceColumn, 
                    socialRemoveColumn
                ) = socialAgeContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment = 'center'
                )
                socialCurrentGroup = st.session_state.get(
                    f'socialAgeGroup{id}-{i}'
                )

                # Age group column
                loadKey(
                    f'socialAgeGroup', id, 
                    socialCurrentGroup if socialCurrentGroup 
                    else socialRemainingGroups[0], f'-{i}'
                )
                with socialGroupColumn: st.selectbox(
                    'Age Group', key = f'_socialAgeGroup{id}-{i}', 
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    options = (
                        [socialCurrentGroup] + [
                            group for group in socialRemainingGroups 
                            if group != socialCurrentGroup
                        ] if socialCurrentGroup else socialRemainingGroups
                    ), 
                    disabled = (
                        not useSocialDistancingToggle 
                        or not socialRowCount < 10
                    ),
                    on_change = saveKey, 
                    args = [f'socialAgeGroup', id, f'-{i}'], # type: ignore
                    help = '''
                        An age group that will have specific 
                        social distancing compliance probability 
                        defined for it, overriding the base 
                        probability.

                        ##### Options:
                        - Young Infant: 0-6 months old.
                        - Infant: 7-24 months old.
                        - Young Child: 3-5 years old.
                        - Child: 6-12 years old.
                        - Adolescent: 13-17 years old.
                        - Young Adult: 18-24 years old.
                        - Adult: 25-44 years old.
                        - Older Adult: 45-64 years old.
                        - Senior: 65-79 years old.
                        - Older Senior: 80+ years old.
                    '''
                )
                # Compliance column
                loadKey(f'socialCompliance', id, 0.9, f'-{i}')
                with socialComplianceColumn: st.select_slider(
                    'Social Distancing Compliance (Probability)', 
                    np.linspace(0.0, 1.0, 201), 0.9, 
                    format_func = lambda x: f'{100 * x:0.3g}%', 
                    disabled = not useSocialDistancingToggle, 
                    on_change = saveKey, 
                    args = [f'socialCompliance', id, f'-{i}'], # type: ignore
                    key = f'_socialCompliance{id}-{i}', help = '''
                        The probability that an individual in 
                        this age group will comply with social 
                        distancing interventions in the 
                        simulation.
                    '''
                )
                # Delete button column
                with socialRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:',
                    key = f'socialRemove{id}-{i}', 
                    on_click = deleteFormRow, args = (
                        i, f'socialRowCount{id}', {
                            f'socialAgeGroup{id}-', 
                            f'socialCompliance{id}-'
                        }
                    ),
                    disabled = not useVaccinesToggle, help = '''
                        Remove this row of the form and remove 
                        these age-specific vaccine proportion 
                        values from the simulation.
                    '''
                )
            # Button to add another row for age specific params
            socialAgeContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'socialAdd{id}', args = (
                    f'socialRowCount{id}', {
                        f'socialAgeGroup{id}-{socialRowCount}': (
                            socialRemainingGroups[0] 
                            if socialRemainingGroups else None
                        ),
                        f'socialCompliance{id}-{socialRowCount}': 
                        socialDistancingCompliance
                    }
                ), 
                disabled = (
                    not useSocialDistancingToggle 
                    or not socialRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can 
                    select an additional age group to have unique 
                    social distancing compliance values.
                ''' if socialRowCount <= 9 else '''
                    All age groups have been given unique social 
                    distancing compliance values, so a new age 
                    group cannot be added.
                '''
            )

            # Case Isolation
            loadKey(f'caseIsolation', id, False)
            st.toggle(
                'Enable Case Isolation', value = False, 
                on_change = saveKey, args = [f'caseIsolation', id], # type: ignore
                key = f'_caseIsolation{id}', help = '''
                    Toggle whether or not individuals who have been 
                    diagnosed as cases of the disease will be 
                    forced to isolate at home.
                '''
            )

            # Class Dismissal
            loadKey(f'classDismissal', id, False)
            classDismissal = st.toggle(
                'Enable Class Dismissal', value = False, 
                on_change = saveKey, args = [f'classDismissal', id], # type: ignore
                key = f'_classDismissal{id}', help = '''
                    Toggle whether or not classes in childcare and 
                    non-tertiary schools should dismiss classes 
                    when the daily case rate is high enough.

                    Note that the rate that must be reached before 
                    class dismissal begins to occur is shared with 
                    any other NPIs that are set to use case rates 
                    as their trigger threshold.
                '''
            )
            if classDismissal: st.info(
            '''
                Due to the design of the *Flusim* model, the case 
                rate thresholds used by class dismissal must be 
                defined globally for all NPIs. You may configure 
                these thresholds using the "Intervention Trigger 
                Thresholds" parameters at the bottom of this page 
                (click [this link](#thresholdTriggerCondition) to 
                go there directly).
            ''', icon = ':material/info:')



        # School Closure
        st.html('<span id = "schoolClosureTriggerCondition"></span>')
        with st.expander('School Closure'):
            st.markdown('''
                These parameters control if and when schools will 
                close as a result of the disease.
            ''')
            loadKey(f'schoolClosureToggle', id, False)
            useSchoolClosureToggle = st.toggle(
                'Enable School Closures', value = False, 
                on_change = saveKey, 
                args = [f'schoolClosureToggle', id], # type: ignore
                key = f'_schoolClosureToggle{id}', help = '''
                    Toggle whether or not school closure 
                    interventions are implemented in the 
                    simulation, overriding other school closure 
                    parameters.
                '''
            )
            
            # School closure triggers
            with st.container(border = True):
                loadKey(f'schoolClosureTrigger', id, 'Always')
                schoolClosureTrigger = st.selectbox(
                    'School Closure Trigger Condition', 
                    key = f'_schoolClosureTrigger{id}', 
                    options = triggerNames, on_change = saveKey, 
                    args = [f'schoolClosureTrigger', id], # type: ignore
                    disabled = not useSchoolClosureToggle, help = '''
                        The type of condition that must be 
                        satisfied before schools will start being 
                        closed in the simulation. Additional 
                        options for configuring the exact trigger 
                        condition will appear after selecting one 
                        of these options.

                        ##### Options:
                        - Always: Schools will be closed throughout 
                        the entire simulation.
                        - Timed: Schools will be closed within a 
                        specific time period defined using a start 
                        and end threshold.
                        - Community Case Rate: Schools will begin 
                        to close if the rate of newly diagnosed 
                        cases per day exceeds a specific threshold, 
                        and will begin to reopen if the rate drops 
                        below a different threshold afterwards. 
                        This trigger rate allows schools to close 
                        and reopen multiple times if the case rate 
                        varies between the two thresholds.
                        - Community Case Total: Schools will begin 
                        to close after the number of diagnosed 
                        cases in the community exceeds a specific 
                        threshold, and will remain closed for the 
                        rest of the simulation.
                        - Cases per School: Schools will close 
                        individually when the number of cases 
                        diagnosed within them reaches a certain 
                        threshold, and will remain closed for the 
                        rest of the simulation.
                        - Cases per K-12 School: Primary and 
                        secondary schools will close individually 
                        when the number of cases diagnosed within 
                        them reaches a certain threshold, and will 
                        remain closed for the rest of the 
                        simulation. Childcare facilities and 
                        tertiary schools/universities will not 
                        close, overriding other parameters.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if schoolClosureTrigger == 'Timed':
                    schoolClosurePeriodErrorContainer = st.empty()
                    loadKey(f'schoolClosurePeriod', id, (29, 59))
                    schoolClosurePeriod = st.select_slider(
                        'School Closure Time Period', range(720), 
                        (29, 59), key = f'_schoolClosurePeriod{id}', 
                        format_func = lambda x: f'Day {x + 1}', 
                        on_change = saveKey, 
                        args = [f'schoolClosurePeriod', id], # type: ignore
                        disabled = not useSchoolClosureToggle, help = '''
                            The time period during which schools 
                            will be closed in the simulation. The 
                            first value is the day on which schools 
                            will initially close (where Day 1 is 
                            the first day of the simulation), and 
                            the second value is the day on which 
                            schools will reopen.
                        '''
                    )

                    # Show error if time period goes past sim length
                    if schoolClosurePeriod[0] >= simLength: 
                        schoolClosurePeriodErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the school closure NPI time 
                            period for this scenario (defined 
                            below) is set to begin on Day 
                            {schoolClosurePeriod[0] + 1}. As such, 
                            schools will never be closed in this 
                            scenario under these parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's School Closure Time Period 
                            to any point before Day {simLength}. 
                            - Change the scenario's School Closure 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {schoolClosurePeriod[0] + 1} days 
                            or more.
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the school closure NPI time 
                            period for this scenario is set to 
                            begin on Day 
                            {schoolClosurePeriod[0] + 1}. As such, 
                            schools will never be closed in this 
                            scenario under these parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's School Closure Time Period 
                            in the "School Closure" section of the 
                            "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's School Closure 
                            Trigger Condition in the "School 
                            Closure" section of the "Vaccinations 
                            and NPIs" tab to any option other than 
                            "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {schoolClosurePeriod[0] + 1} days 
                            or more.
                        ''', icon = ':material/error:')
                        st.session_state[
                            f'schoolClosurePeriodError{id}'
                        ] = 2
                    elif schoolClosurePeriod[1] >= simLength: 
                        schoolClosurePeriodErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the school closure NPI time 
                            period for this scenario (defined 
                            below) is set to end on Day 
                            {schoolClosurePeriod[1] + 1}. As such, 
                            schools will still be closed when the 
                            scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            School Closure Time Period to any point 
                            before Day {simLength}. 
                            - Change the scenario's School Closure 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {schoolClosurePeriod[1] + 1} days 
                            or more.
                        ''', icon = ':material/warning:')
                        globalErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the school closure NPI time 
                            period for this scenario is set to end 
                            on Day {schoolClosurePeriod[1] + 1}. As 
                            such, schools will still be closed when 
                            the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            School Closure Time Period in the 
                            "School Closure" section of the 
                            "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's School Closure 
                            Trigger Condition in the "School 
                            Closure" section of the "Vaccinations 
                            and NPIs" tab to any option other than 
                            "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {schoolClosurePeriod[1] + 1} days 
                            or more. 
                        ''', icon = ':material/warning:')
                        st.session_state[
                            f'schoolClosurePeriodError{id}'
                        ] = 1
                    else: st.session_state[
                        f'schoolClosurePeriodError{id}'
                    ] = 0

                # Rate triggers
                elif schoolClosureTrigger == 'Community Case Rate': 
                    st.info('''
                        Due to the design of the *Flusim* model, 
                        case rate thresholds must be defined 
                        globally. You may configure these 
                        thresholds using the "Intervention Trigger 
                        Thresholds" parameters at the bottom of 
                        this page (click 
                        [this link](#thresholdTriggerCondition) to 
                        go there directly).
                    ''', icon = ':material/info:')
                # Case triggers
                elif schoolClosureTrigger in {
                    'Community Case Total', 'Cases per School', 
                    'Cases per K-12 School'
                }: st.info('''
                    Due to the design of the *Flusim* model, case 
                    total thresholds must be defined globally. You 
                    may configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at 
                    the bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go 
                    there directly).
                ''', icon = ':material/info:')
            
            # School types and compliance
            schoolTypeErrorContainer = st.empty()
            loadKey(f'schoolClosureTypes', id, ['K-12'])
            schoolClosureTypes = st.segmented_control(
                'Types of School to Close', 
                ('Childcare', 'K-12', 'Tertiary'), 
                selection_mode = 'multi', default = 'K-12', 
                disabled = not useSchoolClosureToggle, 
                on_change = saveKey, args = [f'schoolClosureTypes', id], # type: ignore
                key = f'_schoolClosureTypes{id}', help = '''
                    The types of schools that will close under the 
                    effects of this NPI. Multiple school types may 
                    be selected at once, but selecting none is 
                    prohibited.

                    ##### Options:
                    - Childcare: Pre-primary childcare facilities.
                    - K-12: Primary and secondary education 
                    facilities.
                    - Tertiary: Adult education facilities.
                '''
            )
            loadKey(f'schoolClosureCompliance', id, 0.9)
            st.select_slider(
                'School Closure Compliance (Probability)', 
                np.linspace(0.0, 1.0, 201), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                disabled = not useSchoolClosureToggle, 
                on_change = saveKey, 
                args = [f'schoolClosureCompliance', id], # type: ignore
                key = f'_schoolClosureCompliance{id}', help = '''
                    The probability that an individual will 
                    withdraw from schools when they are closed in 
                    the simulation.
                '''
            )

            # Show error if no schools selected
            if useSchoolClosureToggle and not schoolClosureTypes: 
                schoolTypeErrorContainer.error(f'''
                    Error: The {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } currently has no school types selected to 
                    close during school closure NPIs. At least one 
                    kind of school must be selected for this NPI in 
                    order for it to have an effect on the scenario. 

                    To address this error, please select at least 
                    one of the Types of School to Close before 
                    running the simulation.
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } currently has no school types selected to 
                    close during school closure NPIs. At least one 
                    kind of school must be selected for this NPI in 
                    order for it to have an effect on the scenario. 

                    To address this error, please select at least 
                    one of the Types of School to Close in the 
                    "School Closure" section of the "Vaccinations 
                    and NPIs" tab before running the simulation.
                ''', icon = ':material/error:')
                st.session_state[f'schoolTypeError{id}'] = 2
            else: st.session_state[f'schoolTypeError{id}'] = 0
        


        # Withdrawal Increase
        st.html('<span id = "withdrawalIncreaseTriggerCondition"></span>')
        with st.expander('Withdrawal Increase'):
            st.markdown('''
                These parameters control the properties of 
                interventions that increase the likelihood of 
                infected individuals withdrawing from work/school 
                after becoming symptomatic.
                
                The base likelihood of infected individuals 
                withdrawing from work/school when this intervention 
                is not active can be configured in the "Withdrawals 
                and Diagnosis" section of the "Community" tab.
            ''')
            loadKey(f'withdrawalIncreaseToggle', id, False)
            useWithdrawalIncreaseToggle = st.toggle(
                'Enable Withdrawal Increases', value = False, 
                on_change = saveKey, 
                args = [f'withdrawalIncreaseToggle', id], # type: ignore
                key = f'_withdrawalIncreaseToggle{id}', help = '''
                    Toggle whether or not withdrawal increasing 
                    interventions are implemented in the 
                    simulation, overriding other withdrawal 
                    increase parameters.
                '''
            )
            
            # Withdrawal increase triggers
            loadKey(f'withdrawalIncreaseTrigger', id, 'Always')
            with st.container(border = True):
                withdrawalIncreaseTrigger = st.selectbox(
                    'Withdrawal Increase Trigger Condition', 
                    key = f'_withdrawalIncreaseTrigger{id}', 
                    options = triggerNames[:-2], on_change = saveKey, 
                    args = [f'withdrawalIncreaseTrigger', id], # type: ignore
                    disabled = not useWithdrawalIncreaseToggle, help = '''
                        The type of condition that must be 
                        satisfied before the rate of withdrawal 
                        will start increasing in the simulation. 
                        Additional options for configuring the 
                        exact trigger condition will appear after 
                        selecting one of these options.

                        ##### Options:
                        - Always: Withdrawal rates will be 
                        increased throughout the entire simulation.
                        - Timed: Withdrawal rates will be increased 
                        within a specific time period defined using 
                        a start and end threshold.
                        - Community Case Rate: Withdrawal rates 
                        will begin increasing if the rate of newly 
                        diagnosed cases per day exceeds a specific 
                        threshold, and will revert to normal if the 
                        rate drops below a different threshold 
                        afterwards. This trigger rate allows 
                        withdrawal rates to increase and decrease 
                        multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Withdrawal rates 
                        will begin increasing after the number of 
                        diagnosed cases in the community exceeds a 
                        specific threshold, and will remain at this 
                        elevated rate for the rest of the 
                        simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if withdrawalIncreaseTrigger == 'Timed':
                    withdrawalIncreasePeriodErrorContainer = st.empty()
                    loadKey(f'withdrawalIncreasePeriod', id, (29, 59))
                    withdrawalIncreasePeriod = st.select_slider(
                        'Withdrawal Increase Time Period', range(720), 
                        (29, 59), key = f'_withdrawalIncreasePeriod{id}', 
                        disabled = not useWithdrawalIncreaseToggle, 
                        on_change = saveKey, 
                        args = [f'withdrawalIncreasePeriod', id], # type: ignore
                        format_func = lambda x: f'Day {x + 1}', help = '''
                            The time period during which withdrawal 
                            rates will be increased in the 
                            simulation. The first value is the day 
                            on which withdrawal rates will first 
                            increase (where Day 1 is the first day 
                            of the simulation), and the second 
                            value is the day on which withdrawal 
                            rates will return to normal.
                        '''
                    )

                    # Show error if time period goes past sim length
                    if withdrawalIncreasePeriod[0] >= simLength: 
                        withdrawalIncreasePeriodErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the withdrawal increase NPI 
                            time period for this scenario (defined 
                            below) is set to begin on Day 
                            {withdrawalIncreasePeriod[0] + 1}. As 
                            such, withdrawal rates will never 
                            increase in this scenario under these 
                            parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Withdrawal Increase Time 
                            Period to any point before Day 
                            {simLength}. 
                            - Change the scenario's Withdrawal 
                            Increase Trigger Condition to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {withdrawalIncreasePeriod[0] + 1} 
                            days or more.
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the withdrawal increase NPI 
                            time period for this scenario is set to 
                            begin on Day 
                            {withdrawalIncreasePeriod[0] + 1}. As 
                            such, withdrawal rates will never 
                            increase in this scenario under these 
                            parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Withdrawal Increase Time 
                            Period in the "Withdrawal Increase" 
                            section of the "Vaccinations and NPIs" 
                            tab to any point before Day {simLength}.
                            - Change the scenario's Withdrawal 
                            Increase Trigger Condition in the 
                            "Withdrawal Increase" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {withdrawalIncreasePeriod[0] + 1} 
                            days or more. 
                        ''', icon = ':material/error:')
                        st.session_state[
                            f'withdrawalIncreasePeriodError{id}'
                        ] = 2
                    elif withdrawalIncreasePeriod[1] >= simLength: 
                        withdrawalIncreasePeriodErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the withdrawal increase NPI 
                            time period for this scenario (defined 
                            below) is set to end on Day 
                            {withdrawalIncreasePeriod[1] + 1}. As 
                            such, withdrawal rates will still be 
                            increased when the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            Withdrawal Increase Time Period to any 
                            point before Day {simLength}. 
                            - Change the scenario's Withdrawal 
                            Increase Trigger Condition to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {withdrawalIncreasePeriod[1] + 1} 
                            days or more.
                        ''', icon = ':material/warning:')
                        globalErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the withdrawal increase NPI 
                            time period for this scenario is set to 
                            end on Day 
                            {withdrawalIncreasePeriod[1] + 1}. As 
                            such, withdrawal rates will still be 
                            increased when the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            Withdrawal Increase Time Period in the 
                            "Withdrawal Increase" section of the 
                            "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's Withdrawal 
                            Increase Trigger Condition in the 
                            "Withdrawal Increase" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {withdrawalIncreasePeriod[1] + 1} 
                            days or more. 
                        ''', icon = ':material/warning:')
                        st.session_state[
                            f'withdrawalIncreasePeriodError{id}'
                            ] = 1
                    else: st.session_state[
                        f'withdrawalIncreasePeriodError{id}'
                    ] = 0
                
                # Rate triggers
                elif withdrawalIncreaseTrigger == 'Community Case Rate':
                    st.info('''
                        Due to the design of the *Flusim* model, 
                        case rate thresholds must be defined 
                        globally. You may configure these 
                        thresholds using the "Intervention Trigger 
                        Thresholds" parameters at the bottom of 
                        this page (click 
                        [this link](#thresholdTriggerCondition) to 
                        go there directly).
                    ''', icon = ':material/info:')
                # Case triggers
                elif withdrawalIncreaseTrigger == 'Community Case Total': 
                    st.info('''
                        Due to the design of the *Flusim* model, 
                        case total thresholds must be defined 
                        globally. You may configure these 
                        thresholds using the "Intervention Trigger 
                        Thresholds" parameters at the bottom of 
                        this page (click 
                        [this link](#thresholdTriggerCondition) to 
                        go there directly).
                    ''', icon = ':material/info:')
            
            # Increased withdrawal
            adultWithdrawalErrorContainer = st.empty()
            loadKey(f'withdrawalIncreaseAdult', id, 0.9)
            withdrawalIncreaseAdult = st.select_slider(
                'Adult Increased Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 201), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                disabled = not useWithdrawalIncreaseToggle, 
                on_change = saveKey, 
                args = [f'withdrawalIncreaseAdult', id], # type: ignore
                key = f'_withdrawalIncreaseAdult{id}', help = '''
                    The probability of an infected adult 
                    withdrawing from work after becoming 
                    symptomatic while a withdrawal increasing 
                    intervention is in effect, overwriting the 
                    normal withdrawal rate.
                '''
            )
            childWithdrawalErrorContainer = st.empty()
            loadKey(f'withdrawalIncreaseChild', id, 1.0)
            withdrawalIncreaseChild = st.select_slider(
                'Child Increased Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 201), 1.0, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useWithdrawalIncreaseToggle, 
                on_change = saveKey, 
                args = [f'withdrawalIncreaseChild', id], # type: ignore
                key = f'_withdrawalIncreaseChild{id}', help = '''
                    The probability of an infected child 
                    withdrawing from school after becoming 
                    symptomatic while a withdrawal increasing 
                    intervention is in effect, overwriting the 
                    normal withdrawal rate.
                '''
            )

            # Show error if initial proportion is above target
            baseAdultWithdrawal = idGet('withdrawalWork', id, 0.5)
            baseChildWithdrawal = idGet('withdrawalSchool', id, 0.9)
            if (
                useWithdrawalIncreaseToggle 
                and baseAdultWithdrawal >= withdrawalIncreaseAdult
            ): 
                adultWithdrawalErrorContainer.error(f'''
                    Error: The work withdrawal probability during 
                    withdrawal increase NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to 
                    {100 * withdrawalIncreaseAdult:0.3g}%, but the 
                    standard work withdrawal probability outside of 
                    this NPI for this scenario is set to 
                    {100 * baseAdultWithdrawal:0.3g}%. As such, the 
                    withdrawal increase NPI {
                        'has no effect on' 
                        if baseAdultWithdrawal == withdrawalIncreaseAdult 
                        else 'actually decreases'
                    } work withdrawal rates in this scenario. 

                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Adult Increased 
                    Withdrawal Rate to any probability 
                    above {100 * baseAdultWithdrawal:0.3g}%. 
                    - Decrease the scenario's Adult Withdrawal Rate 
                    in the "Withdrawals and Diagnosis" section of 
                    the "Community" tab to any probability 
                    below {100 * withdrawalIncreaseAdult:0.3g}%. 
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The work withdrawal probability during 
                    withdrawal increase NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to 
                    {100 * withdrawalIncreaseAdult:0.3g}%, but the 
                    standard work withdrawal probability outside of 
                    this NPI for this scenario is set to 
                    {100 * baseAdultWithdrawal:0.3g}%. As such, the 
                    withdrawal increase NPI {
                        'has no effect on' 
                        if baseAdultWithdrawal == withdrawalIncreaseAdult 
                        else 'actually decreases'
                    } work withdrawal rates in this scenario. 

                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Adult Increased 
                    Withdrawal Rate in the "Withdrawal Increase" 
                    section of the "Vaccinations and NPIs" tab to 
                    any probability 
                    above {100 * baseAdultWithdrawal:0.3g}%. 
                    - Decrease the scenario's Adult Withdrawal Rate 
                    in the "Withdrawals and Diagnosis" section of 
                    the "Community" tab to any probability 
                    below {100 * withdrawalIncreaseAdult:0.3g}%. 
                ''', icon = ':material/error:')
                st.session_state[f'adultWithdrawalError{id}'] = 2
            else: st.session_state[f'adultWithdrawalError{id}'] = 0
            if (
                useWithdrawalIncreaseToggle 
                and baseChildWithdrawal >= withdrawalIncreaseChild
            ): 
                childWithdrawalErrorContainer.error(f'''
                    Error: The school withdrawal probability during 
                    withdrawal increase NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to 
                    {100 * withdrawalIncreaseChild:0.3g}%, but the 
                    standard school withdrawal probability outside 
                    of this NPI for this scenario is set to 
                    {100 * baseChildWithdrawal:0.3g}%. As such, the 
                    withdrawal increase NPI {
                        'has no effect on' 
                        if baseChildWithdrawal == withdrawalIncreaseChild 
                        else 'actually decreases'
                    } school withdrawal rates in this scenario. 

                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Child Increased 
                    Withdrawal Rate to any probability 
                    above {100 * baseChildWithdrawal:0.3g}%. 
                    - Decrease the scenario's Child Withdrawal Rate 
                    in the "Withdrawals and Diagnosis" section of 
                    the "Community" tab to any probability 
                    below {100 * withdrawalIncreaseChild:0.3g}%. 
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The school withdrawal probability during 
                    withdrawal increase NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to 
                    {100 * withdrawalIncreaseChild:0.3g}%, but the 
                    standard school withdrawal probability outside 
                    of this NPI for this scenario is set to 
                    {100 * baseChildWithdrawal:0.3g}%. As such, the 
                    withdrawal increase NPI {
                        'has no effect on' 
                        if baseChildWithdrawal == withdrawalIncreaseChild 
                        else 'actually decreases'
                    } school withdrawal rates in this scenario. 

                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Increase the scenario's Child Increased 
                    Withdrawal Rate in the "Withdrawal Increase" 
                    section of the "Vaccinations and NPIs" tab to 
                    any probability 
                    above {100 * baseChildWithdrawal:0.3g}%. 
                    - Decrease the scenario's Child Withdrawal Rate 
                    in the "Withdrawals and Diagnosis" section of 
                    the "Community" tab to any probability 
                    below {100 * withdrawalIncreaseChild:0.3g}%. 
                ''', icon = ':material/error:')
                st.session_state[f'childWithdrawalError{id}'] = 2
            else: st.session_state[f'childWithdrawalError{id}'] = 0

        # Reduced Workgroup Size
        st.html('<span id = "reducedGroupTriggerCondition"></span>')
        with st.expander('Reduced Work Group Size'):
            st.markdown('''
                These parameters control the properties of 
                interventions that reduce the size of work groups 
                when in effect. Note that this NPI does not target 
                school groups or other gatherings.
                
                The base size of work groups when this intervention 
                is not active can be configured in the "Population 
                Behaviours" section of the "Community" tab.
            ''')
            loadKey(f'reducedGroupToggle', id, False)
            useReducedGroupToggle = st.toggle(
                'Enable Group Size Reductions', value = False, 
                on_change = saveKey, args = [f'reducedGroupToggle', id], # type: ignore
                key = f'_reducedGroupToggle{id}', help = '''
                    Toggle whether or not group size reduction 
                    interventions are implemented in the 
                    simulation, overriding other group size 
                    reduction parameters.
                '''
            )
            
            # Reduced workgroup triggers
            loadKey(f'reducedGroupTrigger', id, 'Always')
            with st.container(border = True):
                reducedGroupTrigger = st.selectbox(
                    'Reduced Group Size Trigger Condition', 
                    key = f'_reducedGroupTrigger{id}', 
                    options = triggerNames[:-2], on_change = saveKey, 
                    args = [f'reducedGroupTrigger', id], # type: ignore
                    disabled = not useReducedGroupToggle, help = '''
                        The type of condition that must be 
                        satisfied before the size of work groups 
                        will start decreasing in the simulation. 
                        Additional options for configuring the 
                        exact trigger condition will appear after 
                        selecting one of these options.

                        ##### Options:
                        - Always: Work group sizes will be 
                        decreased throughout the entire simulation.
                        - Timed: Work group sizes will be decreased 
                        within a specific time period defined using 
                        a start and end threshold.
                        - Community Case Rate: Work groups will 
                        begin shrinking if the rate of newly 
                        diagnosed cases per day exceeds a specific 
                        threshold, and will revert to normal size 
                        if the rate drops below a different 
                        threshold afterwards. This trigger rate 
                        allows group sizes to increase and decrease 
                        multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Work groups will 
                        begin shrinking after the number of 
                        diagnosed cases in the community exceeds a 
                        specific threshold, and will remain at this 
                        reduced size for the rest of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if reducedGroupTrigger == 'Timed':
                    reducedGroupPeriodErrorContainer = st.empty()
                    loadKey(f'reducedGroupPeriod', id, (29, 59))
                    reducedGroupPeriod = st.select_slider(
                        'Reduced Group Size Time Period', range(720), 
                        (29, 59), key = f'_reducedGroupPeriod{id}', 
                        disabled = not useReducedGroupToggle, 
                        on_change = saveKey, 
                        args = [f'reducedGroupPeriod', id], # type: ignore
                        format_func = lambda x: f'Day {x + 1}', help = '''
                            The time period during which work 
                            group sizes will be smaller in the 
                            simulation. The first value is the day 
                            on which work groups will first shrink 
                            (where Day 1 is the first day of the 
                            simulation), and the second value is 
                            the day on which work groups will 
                            return to normal.
                        '''
                    )

                    # Show error if time period goes past sim length
                    if reducedGroupPeriod[0] >= simLength: 
                        reducedGroupPeriodErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the reduced group size NPI 
                            time period for this scenario (defined 
                            below) is set to begin on Day 
                            {reducedGroupPeriod[0] + 1}. As such, 
                            work groups will never decrease in size 
                            in this scenario under these parameters.
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Reduced Group Size Time 
                            Period to any point before Day 
                            {simLength}. 
                            - Change the scenario's Reduced Group
                            Size Trigger Condition to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {reducedGroupPeriod[0] + 1} 
                            days or more. 
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the reduced group size NPI 
                            time period for this scenario is set to 
                            begin on Day 
                            {reducedGroupPeriod[0] + 1}. As such, 
                            work groups will never decrease in size 
                            in this scenario under these parameters.
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's Reduced Group Size Time 
                            Period in the "Reduced Work Group Size" 
                            section of the "Vaccinations and NPIs" 
                            tab to any point before Day {simLength}. 
                            - Change the scenario's Reduced Group
                            Size Trigger Condition in the "Reduced 
                            Work Group Size" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {reducedGroupPeriod[0] + 1} 
                            days or more. 
                        ''', icon = ':material/error:')
                        st.session_state[
                            f'reducedGroupPeriodError{id}'
                        ] = 2
                    elif reducedGroupPeriod[1] >= simLength: 
                        reducedGroupPeriodErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the reduced group size NPI 
                            time period for this scenario (defined 
                            below) is set to end on Day 
                            {reducedGroupPeriod[1] + 1}. As such, 
                            work groups will still be reduced in 
                            size when the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            Reduced Group Size Time Period to any 
                            point before Day {simLength}. 
                            - Change the scenario's Reduced Group 
                            Size Trigger Condition to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {reducedGroupPeriod[1] + 1} 
                            days or more. 
                        ''', icon = ':material/warning:')
                        globalErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the reduced group size NPI 
                            time period for this scenario is set to 
                            end on Day {reducedGroupPeriod[1] + 1}. 
                            As such, work groups will still be 
                            reduced in size when the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            Reduced Group Size Time Period in the 
                            "Reduced Work Group Size" section of 
                            the "Vaccinations and NPIs" tab to any 
                            point before Day {simLength}. 
                            - Change the scenario's Reduced Group 
                            Size Trigger Condition in the "Reduced 
                            Work Group Size" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {reducedGroupPeriod[1] + 1} 
                            days or more. 
                        ''', icon = ':material/warning:')
                        st.session_state[f'reducedGroupPeriodError{id}'] = 1
                    else: st.session_state[f'reducedGroupPeriodError{id}'] = 0

                # Rate triggers
                elif reducedGroupTrigger == 'Community Case Rate': 
                    st.info('''
                        Due to the design of the *Flusim* model, 
                        case rate thresholds must be defined 
                        globally. You may configure these 
                        thresholds using the "Intervention Trigger 
                        Thresholds" parameters at the bottom of 
                        this page (click 
                        [this link](#thresholdTriggerCondition) to 
                        go there directly).
                    ''', icon = ':material/info:')
                # Case triggers
                elif reducedGroupTrigger == 'Community Case Total': 
                    st.info('''
                        Due to the design of the *Flusim* model, 
                        case total thresholds must be defined 
                        globally. You may configure these 
                        thresholds using the "Intervention Trigger 
                        Thresholds" parameters at the bottom of 
                        this page (click 
                        [this link](#thresholdTriggerCondition) to 
                        go there directly).
                    ''', icon = ':material/info:')
            
            # Reduced group size
            reducedGroupErrorContainer = st.empty()
            loadKey(f'reducedGroupSize', id, 5)
            reducedGroupSize = st.slider(
                'Reduced Work Group Size (Number of People)', 0, 25, 5, 
                disabled = not useReducedGroupToggle, on_change = saveKey, 
                args = [f'reducedGroupSize', id], # type: ignore
                key = f'_reducedGroupSize{id}', help = '''
                    The maximum size of work groups while a reduced 
                    group size intervention is in effect, 
                    overwriting the normal maximum.
                '''
            )
            
            # Show error if initial proportion is above target
            baseGroupSize = idGet('maxWorkGroupSize', id, 10)
            if useReducedGroupToggle and reducedGroupSize >= baseGroupSize:
                reducedGroupErrorContainer.error(f'''
                    Error: The reduced work group size during 
                    reduced group size NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to {reducedGroupSize} 
                    people, but the standard work group size 
                    outside of this NPI for this scenario is set to 
                    {baseGroupSize} people. As such, the reduced 
                    group size NPI {
                        'has no effect on' 
                        if baseGroupSize == reducedGroupSize 
                        else 'actually increases'
                    } work group sizes in this scenario. 
                    
                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Decrease the scenario's Reduced Work Group 
                    Size to any value below {baseGroupSize} people. 
                    - Increase the scenario's Maximum Work Group 
                    Size in the "Population Behaviours" section of 
                    the "Community" tab to any value above 
                    {reducedGroupSize} people. 
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The reduced work group size during 
                    reduced group size NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to {reducedGroupSize} 
                    people, but the standard work group size 
                    outside of this NPI for this scenario is set to 
                    {baseGroupSize} people. As such, the reduced 
                    group size NPI {
                        'has no effect on' 
                        if baseGroupSize == reducedGroupSize 
                        else 'actually increases'
                    } work group sizes in this scenario. 
                    
                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Decrease the scenario's Reduced Work Group 
                    Size in the "Reduced Work Group Size" section 
                    of the "Vaccinations and NPIs" tab to any value 
                    below {baseGroupSize} people. 
                    - Increase the scenario's Maximum Work Group 
                    Size in the "Population Behaviours" section of 
                    the "Community" tab to any value above 
                    {reducedGroupSize} people. 
                ''', icon = ':material/error:')
                st.session_state[f'reducedGroupError{id}'] = 2
            else: st.session_state[f'reducedGroupError{id}'] = 0



        # BCC Reduction
        st.html('<span id = "bccTriggerCondition"></span>')
        with st.expander('Background Contact Count Reduction'):
            st.markdown('''
                These parameters control the properties of 
                interventions that reduce the background contact 
                count (BCC) in the simulation, thus reducing the 
                number of individuals each person interacts with 
                per day outside of simulated locations.
                
                The base background contact count when this 
                intervention is not active can be configured in the 
                "Population Behaviours" section of the "Community" 
                tab.
            ''')
            loadKey(f'bccToggle', id, False)
            useBCCToggle = st.toggle(
                'Enable BCC Reduction', value = False, on_change = saveKey, 
                args = [f'bccToggle', id], # type: ignore
                key = f'_bccToggle{id}', help = '''
                    Toggle whether or not background contact count 
                    reduction interventions are implemented in the 
                    simulation, overriding other BCC reduction 
                    parameters.
                '''
            )
            
            # BCC triggers
            loadKey(f'bccTrigger', id, 'Always')
            with st.container(border = True):
                bccTrigger = st.selectbox(
                    'BCC Reduction Trigger Condition', 
                    key = f'_bccTrigger{id}', 
                    options = triggerNames[:-2], on_change = saveKey, 
                    args = [f'bccTrigger', id], # type: ignore
                    disabled = not useBCCToggle, help = '''
                        The type of condition that must be 
                        satisfied before background contact count 
                        will start decreasing in the simulation. 
                        Additional options for configuring the 
                        exact trigger condition will appear after 
                        selecting one of these options.

                        ##### Options:
                        - Always: Background contact count will be 
                        reduced throughout the entire simulation.
                        - Timed: Background contact count will be 
                        reduced within a specific time period 
                        defined using a start and end threshold.
                        - Community Case Rate: Background contact 
                        count will be reduced if the rate of newly 
                        diagnosed cases per day exceeds a specific 
                        threshold, and will revert to normal levels 
                        if the rate drops below a different 
                        threshold afterwards. This trigger rate 
                        allows BCC levels to increase and decrease 
                        multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Background contact 
                        count will be reduced after the number of 
                        diagnosed cases in the community exceeds a 
                        specific threshold, and will remain at this 
                        reduced level for the rest of the 
                        simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if bccTrigger == 'Timed':
                    bccPeriodErrorContainer = st.empty()
                    loadKey(f'bccPeriod', id, (29, 59))
                    bccPeriod = st.select_slider(
                        'BCC Reduction Time Period', range(720), 
                        (29, 59), key = f'_bccPeriod{id}', 
                        disabled = not useBCCToggle, on_change = saveKey, 
                        args = [f'bccPeriod', id], # type: ignore
                        format_func = lambda x: f'Day {x + 1}', help = '''
                            The time period during which background 
                            contact count (BCC) will be reduced in 
                            the simulation. The first value is the 
                            day on which BCC will first be reduced 
                            (where Day 1 is the first day of the 
                            simulation), and the second value is 
                            the day on which BCC will return to 
                            normal.
                        '''
                    )

                    # Show error if time period goes past sim length
                    if bccPeriod[0] >= simLength: 
                        bccPeriodErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the background contact count 
                            (BCC) reduction NPI time period for 
                            this scenario (defined below) is set to 
                            begin on Day {bccPeriod[0] + 1}. As 
                            such, BCC rates will never be reduced 
                            in this scenario under these parameters.
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's BCC Reduction Time Period to 
                            any point before Day {simLength}. 
                            - Change the scenario's BCC Reduction 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {bccPeriod[0] + 1} 
                            days or more. 
                        ''', icon = ':material/error:')
                        globalErrorContainer.error(f'''
                            Error: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the background contact count 
                            (BCC) reduction NPI time period for 
                            this scenario is set to begin on Day 
                            {bccPeriod[0] + 1}. As such, BCC rates 
                            will never be reduced in this scenario 
                            under these parameters. 
                            
                            To address this error, please make one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the start point of the 
                            scenario's BCC Reduction Time Period in 
                            the "Background Contact Count 
                            Reduction" section of the "Vaccinations 
                            and NPIs" tab to any point before Day 
                            {simLength}. 
                            - Change the scenario's BCC Reduction 
                            Trigger Condition in the "Background 
                            Contact Count Reduction" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {bccPeriod[0] + 1} 
                            days or more. 
                        ''', icon = ':material/error:')
                        st.session_state[
                            f'bccPeriodError{id}'
                        ] = 2
                    elif bccPeriod[1] >= simLength: 
                        bccPeriodErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the background contact count 
                            (BCC) reduction NPI time period for 
                            this scenario (defined below) is set to 
                            end on Day {bccPeriod[1] + 1}. As such, 
                            BCC rates will still be reduced when 
                            the scenario ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            BCC Reduction Time Period to any point 
                            before Day {simLength}. 
                            - Change the scenario's BCC Reduction 
                            Trigger Condition to any option other 
                            than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {bccPeriod[1] + 1} days or more. 
                        ''', icon = ':material/warning:')
                        globalErrorContainer.warning(f'''
                            Warning: The {
                                'baseline scenario' if id == 0 
                                else f'scenario named "{
                                    st.session_state[f'scenarioName{id}']
                                }"'
                            } is currently set to last {simLength} 
                            days, but the background contact count 
                            (BCC) reduction NPI time period for 
                            this scenario is set to end on Day 
                            {bccPeriod[1] + 1}. As such, BCC rates 
                            will still be reduced when the scenario 
                            ends. 
                            
                            If this is not desired behaviour, 
                            please address this error by making one 
                            of the following changes before running 
                            the simulation:
                            
                            - Move the end point of the scenario's 
                            BCC Reduction Time Period in the 
                            "Background Contact Count Reduction" 
                            section of the "Vaccinations and NPIs" 
                            tab to any point before Day {simLength}.
                            - Change the scenario's BCC Reduction 
                            Trigger Condition in the "Background 
                            Contact Count Reduction" section of the 
                            "Vaccinations and NPIs" tab to any 
                            option other than "Timed".
                            - Increase the scenario's Length of 
                            Simulation in the "Initialisation" tab 
                            to be {bccPeriod[1] + 1} days or more. 
                        ''', icon = ':material/warning:')
                        st.session_state[f'bccPeriodError{id}'] = 1
                    else: st.session_state[f'bccPeriodError{id}'] = 0
                
                # Rate triggers
                elif bccTrigger == 'Community Case Rate': st.info('''
                    Due to the design of the *Flusim* model, case 
                    rate thresholds must be defined globally. You 
                    may configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at 
                    the bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go 
                    there directly).
                ''', icon = ':material/info:')
                # Case triggers
                elif bccTrigger == 'Community Case Total': st.info('''
                    Due to the design of the *Flusim* model, case 
                    total thresholds must be defined globally. You 
                    may configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at 
                    the bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go 
                    there directly).
                ''', icon = ':material/info:')
            
            # Reduced BCC rate
            bccErrorContainer = st.empty()
            loadKey(f'bccReducedRate', id, 0.2)
            bccReducedRate = st.slider(
                ((
                    'Reduced Background Contact Count (Average '
                    'Number of Interactions per Person per Day)'
                )),
                0.0, 8.0, 0.2, disabled = not useBCCToggle, 
                on_change = saveKey, args = [f'bccReducedRate', id], # type: ignore
                key = f'_bccReducedRate{id}', help = '''
                    The average number of other people each 
                    individual will interact with in the background 
                    phase of each day in the simulation (emulating 
                    interactions outside of simulated locations) 
                    while a BCC reduction intervention is in 
                    effect, overwriting the normal BCC rate.
                '''
            )

            # Show error if initial proportion is above target
            baseBCC = idGet('bccRate', id, 4.0)
            if useBCCToggle and bccReducedRate >= baseBCC:
                bccErrorContainer.error(f'''
                    Error: The reduced background contact count 
                    (BCC) value during BCC reduction NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to {bccReducedRate} 
                    interactions per day, but the standard BCC 
                    outside of this NPI for this scenario is set to 
                    {baseBCC} interactions per day. As such, the 
                    BCC reduction NPI {
                        'has no effect on' 
                        if baseBCC == bccReducedRate 
                        else 'actually increases'
                    } BCC in this scenario. 
                    
                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Decrease the scenario's Reduced Background 
                    Contact Count to any value below {baseBCC} 
                    interactions per person per day. 
                    - Increase the scenario's Background Contact 
                    Count in the "Population Behaviours" section of 
                    the "Community" tab to any value above 
                    {bccReducedRate} interactions per person per 
                    day. 
                ''', icon = ':material/error:')
                globalErrorContainer.error(f'''
                    Error: The reduced background contact count 
                    (BCC) value during BCC reduction NPIs in the {
                        'baseline scenario' if id == 0 
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to {bccReducedRate} 
                    interactions per day, but the standard BCC 
                    outside of this NPI for this scenario is set to 
                    {baseBCC} interactions per day. As such, the 
                    BCC reduction NPI {
                        'has no effect on' 
                        if baseBCC == bccReducedRate 
                        else 'actually increases'
                    } BCC in this scenario. 
                    
                    To address this error, please make one of the 
                    following changes before running the simulation:
                            
                    - Decrease the scenario's Reduced Background 
                    Contact Count in the "Background Contact Count 
                    Reduction" section of the "Vaccinations and 
                    NPIs" tab to any value below {baseBCC} 
                    interactions per person per day. 
                    - Increase the scenario's Background Contact 
                    Count in the "Population Behaviours" section of 
                    the "Community" tab to any value above 
                    {bccReducedRate} interactions per person per 
                    day. 
                ''', icon = ':material/error:')
                st.session_state[f'bccError{id}'] = 2
            else: st.session_state[f'bccError{id}'] = 0
    




    # Trigger Thresholds
    st.html('<span id = "thresholdTriggerCondition"></span>')
    st.subheader('Threshold Parameters')
    with st.expander('Intervention Trigger Thresholds'):
        st.markdown('''
            These parameters affect the threshold values that must 
            be reached for vaccination or non-pharmaceutical 
            interventions to be triggered in the simulation. Due to 
            the design of the *Flusim* simulation model, all 
            interventions that are set to use case rates or totals 
            as their trigger condition must share these thresholds; 
            setting individual thresholds for each intervention is 
            not possible unless the "Timed" trigger condition is 
            used. Parameters will only appear here if at least one 
            intervention is set to use a trigger condition that 
            requires them. 
            
            Note that all thresholds that can be configured here 
            are based on diagnosed cases, not infections. The 
            likelihood of an infected individual being diagnosed as 
            a case can be configured in the "Health Burden 
            Outcomes" section of the "Community" tab.
        ''')

        # Display values based on what is used by the triggers
        interventionTriggers = [
            vaccineTrigger, schoolClosureTrigger, 
            withdrawalIncreaseTrigger, reducedGroupTrigger, bccTrigger
        ]
        rateConditions = [
            index for index, condition in enumerate(interventionTriggers) 
            if condition == 'Community Case Rate'
        ]
        totalConditions = [
            index for index, condition in enumerate(interventionTriggers) 
            if condition in {
                'Community Case Total', 
                'Cases per School', 'Cases per K-12 School'
            }
        ]
        if (
            not rateConditions and not totalConditions 
            and not classDismissal
        ): st.info(
            '''
            No interventions are currently using case rates or 
            totals for their trigger conditions. Parameters for 
            configuring the trigger thresholds will appear here if 
            you select any value other than "Always" and "Timed" 
            for an intervention's trigger condition.
        ''', icon = ':material/info:')
        else:
            # Case rates
            if rateConditions or classDismissal:
                # Display links to NPIs that use rates (including 
                # the non-standard Class Dismissal if applicable)
                st.subheader('Case Rate Trigger Thresholds')
                st.markdown(
                    f'''
                        The following interventions currently use 
                        the rate thresholds defined below. Click on 
                        the names to go to the drop-down container 
                        with the trigger condition parameters for 
                        that intervention.\n\n
                    ''' + (
                        f'\n- [Class Dismissal](#generalTriggerCondition)' 
                        if classDismissal else ''
                    ) + ''.join(
                        f'\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)' 
                        for i in rateConditions
                    )
                )

                # Set rate thresholds
                triggerRateErrorContainer = st.container()
                loadKey(f'rateStartThreshold', id, 10)
                rateStartThreshold = st.slider(
                    'Start Trigger Threshold Rate (Cases per Day)', 0, 
                    100, 10, key = f'_rateStartThreshold{id}', 
                    on_change = saveKey, 
                    args = [f'rateStartThreshold', id], # type: ignore
                    help = '''
                        Any interventions set to trigger using the 
                        "Community Case Rate" condition will begin 
                        taking effect in the simulation once the 
                        number of newly diagnosed cases per day 
                        exceeds this value.
                    '''
                )
                loadKey(f'rateRelaxThreshold', id, 5)
                rateRelaxThreshold = st.slider(
                    'Relaxation Trigger Threshold Rate (Cases per Day)', 0,
                    100, 5, key = f'_rateRelaxThreshold{id}', 
                    on_change = saveKey, 
                    args = [f'rateRelaxThreshold', id], # type: ignore
                    help = '''
                        Any active interventions set to trigger 
                        using the "Community Case Rate" condition 
                        will stop taking effect in the simulation 
                        once the number of newly diagnosed cases 
                        per day goes below this value.
                    '''
                )

                # Show error if relax threshold is above trigger
                if rateRelaxThreshold >= rateStartThreshold:
                    triggerRateErrorContainer.error(f'''
                        Error: The start trigger threshold case 
                        rate for medical interventions in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } is currently set to {rateStartThreshold} 
                        cases per day, but the relaxation trigger 
                        threshold case rate for this scenario is 
                        set to {rateRelaxThreshold} people. As 
                        such, any interventions set to use case 
                        rates as a trigger condition will stop 
                        immediately after starting, as they will 
                        already be below the relaxation rate.  
                        
                        To address this error, please make one of 
                        the following changes before running the 
                        simulation:
                                
                        - Increase the scenario's Start Trigger 
                        Threshold Rate to any value above 
                        {rateRelaxThreshold} cases per day. 
                        - Decrease the scenario's Relaxation 
                        Trigger Threshold Rate to any value below 
                        {rateStartThreshold} cases per day. 
                    ''', icon = ':material/error:')
                    globalErrorContainer.error(f'''
                        Error: The start trigger threshold case 
                        rate for medical interventions in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } is currently set to {rateStartThreshold} 
                        cases per day, but the relaxation trigger 
                        threshold case rate for this scenario is 
                        set to {rateRelaxThreshold} people. As 
                        such, any interventions set to use case 
                        rates as a trigger condition will stop 
                        immediately after starting, as they will 
                        already be below the relaxation rate.  
                        
                        To address this error, please make one of 
                        the following changes before running the 
                        simulation:
                                
                        - Increase the scenario's Start Trigger 
                        Threshold Rate in the "Intervention Trigger 
                        Thresholds" section of the "Vaccinations 
                        and NPIs" tab to any value above 
                        {rateRelaxThreshold} cases per day. 
                        - Decrease the scenario's Relaxation 
                        Trigger Threshold Rate in the "Intervention 
                        Trigger Thresholds" section of the 
                        "Vaccinations and NPIs" tab to any value 
                        below {rateStartThreshold} cases per day. 
                    ''', icon = ':material/error:')
                    st.session_state[f'triggerRateError{id}'] = 2
                else: st.session_state[f'triggerRateError{id}'] = 0
            
            # Case totals
            if totalConditions:
                # Display links to NPIs that use totals
                st.subheader('Case Total Trigger Thresholds')
                st.markdown(
                    f'''
                        The following interventions currently use 
                        the case threshold defined below. Click on 
                        the names to go to the drop-down container 
                        with the trigger condition parameters for 
                        that intervention.\n\n
                    ''' + ''.join(
                        f'\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)' 
                        for i in totalConditions
                    )
                )

                # Set total threshold
                triggerTotalErrorContainer = st.container()
                loadKey(f'caseTotalThreshold', id, 1000)
                caseTotalThreshold = st.number_input(
                    'Start Trigger Case Threshold (Total Community Cases)', 
                    0, 300000, 1000, key = f'_caseTotalThreshold{id}', 
                    on_change = saveKey, 
                    args = [f'caseTotalThreshold', id], # type: ignore
                    placeholder = 'Enter a whole number of cases', help = '''
                        Any interventions set to trigger using the 
                        "Community Case Total", "Cases per School", 
                        or "Cases per K-12 School" conditions will 
                        begin taking effect in the simulation once 
                        the total number of diagnosed cases in the 
                        community (for "Community Case Total") or 
                        in each individual school (for "Cases per 
                        School" and "Cases per K-12 School") 
                        exceeds this value.
                    '''
                )

                # Show error if relax threshold is above trigger
                population = communityPopulation[
                    st.session_state.get('community', 'newcastle')
                ]
                if caseTotalThreshold >= population:
                    triggerTotalErrorContainer.error(f'''
                        Error: The trigger threshold case total for 
                        medical interventions in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } is currently set to {caseTotalThreshold} 
                        cases, but the population of {
                            st.session_state.get(
                                'community', 'newcastle'
                            ).capitalize()
                        } (the community used for this simulation) 
                        is equal to {population} people. As such, 
                        any interventions set to use case totals as 
                        a trigger condition will not activate 
                        unless the entire population is infected, 
                        and will thus have no practical effect in 
                        the simulation. 
                        
                        To address this error, please increase the 
                        scenario's Start Trigger Case Threshold to 
                        any value above {population} cases. 
                    ''', icon = ':material/error:')
                    globalErrorContainer.error(f'''
                        Error: The trigger threshold case total for 
                        medical interventions in the {
                            'baseline scenario' if id == 0 
                            else f'scenario named "{
                                st.session_state[f'scenarioName{id}']
                            }"'
                        } is currently set to {caseTotalThreshold} 
                        cases, but the population of {
                            st.session_state.get(
                                'community', 'newcastle'
                            ).capitalize()
                        } (the community used for this simulation) 
                        is equal to {population} people. As such, 
                        any interventions set to use case totals as 
                        a trigger condition will not activate 
                        unless the entire population is infected, 
                        and will thus have no practical effect in 
                        the simulation. 
                        
                        To address this error, please increase the 
                        scenario's Start Trigger Case Threshold in 
                        the "Intervention Trigger Thresholds" 
                        section of the "Vaccinations and NPIs" tab 
                        to any value above {population} cases. 
                    ''', icon = ':material/error:')
                    st.session_state[f'triggerRateError{id}'] = 2
                else: st.session_state[f'triggerRateError{id}'] = 0



"""
Simple functions to cast strings for validation's sake
"""
def ageCast(x): return cast(Literal[
    'young_infant', 'infant', 'young_child', 'child', 'adolescent', 
    'young_adult', 'adult', 'older_adult', 'senior', 'older_senior'
], ageCategories[x])

def trigCast(x): return cast(Literal[
    'none', 'timed', 'per_school_cases', 'community_cases',
    'community_rate', 'per_primary_high_school_cases'
], triggerConditions[x])



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
def vaccineSchema(schema, id = 0):
    try:
        # Validate parameters
        if not isinstance(schema, Parameters): raise ValueError(
            'schema should be a Parameters object'
        )

        # Load reused parameters immediately to save time
        vaccineToggle = idGet('vaccineToggle', id, False)
        boosterToggle = idGet('boosterToggle', id, False)
        socialDistanceToggle = idGet('socialDistancingToggle', id, False)

        ageNames = list(ageCategories.keys())
        primDoseCount = idGet('primaryDoseCount', id, 2)
        primBaseEfficacy = [idGet(
            'primaryBaseEfficacy', id, 0.5, f'-{i}'
        ) for i in range(primDoseCount)]
        primWanedEfficacy = idGet('primaryWanedEfficacy', id, 0.0)
        boostBaseEfficacy = idGet('boosterBaseEfficacy', id, 0.9)
        boostWanedEfficacy = idGet('boosterWanedEfficacy', id, 0.6)
        initialProportion = idGet('initialVaccinated', id, 0.0)
        targetProportion = idGet('targetVaccinated', id, 0.8)
        socialCompliance = idGet('socialDistancingCompliance', id, 0.9)


            
        # Vaccine-Related Parameters
        if vaccineToggle: 
            # Scenario Vaccine Coverage
            schema.Scenario_VaccineCoverage = [vaccineCoverage(
                Age = None, Initial = initialProportion, 
                Target = targetProportion
            )] + [vaccineCoverage(
                Age = ageCast(st.session_state[f'vacAgeGroup{id}-{i}']),
                Initial = idGet(
                    'vacAgeInitial', id, initialProportion, f'-{i}'
                ),
                Target = idGet('vacAgeTarget', id, targetProportion, f'-{i}')
            ) for i in range(st.session_state.get(f'vacAgeRowCount{id}', 0))]

            # Scenario Vaccine Dose
            doseParams = [vaccineDose(
                DoseType = 'primary', Count = primDoseCount,
                DoseSpacingCycles = idGet('primaryDelay', id, 3) * 60,
                WaningDelay = idGet('primaryDuration', id, 6) * 60,
                WaningRatePerCycle = (
                    primBaseEfficacy[-1] - primWanedEfficacy
                ) / (idGet('primaryWaningRate', id, 12) * 60)
            )]
            if boosterToggle: doseParams += [vaccineDose(
                DoseType = 'booster', 
                Count = idGet('boosterDoseCount', id, 3),
                DoseSpacingCycles = idGet('boosterDelay', id, 3) * 60,
                WaningDelay = idGet('boosterDuration', id, 2) * 60,
                WaningRatePerCycle = (
                    boostBaseEfficacy - boostWanedEfficacy
                ) / (idGet('boosterWaningRate', id, 6) * 60)
            )]
            schema.Scenario_VaccineDose = doseParams
        
            # Scenario Vaccine Dose Efficacy

            # Base Primary Efficacy Values
            efficacyParams = [vaccineEfficacy(
                DoseType = 'primary', Age = None, 
                WanedEfficacy = primWanedEfficacy, Efficacy = primBaseEfficacy
            )]
            # Age-Specific Primary Efficacy Values
            primAgeEfficacies = dict.fromkeys(ageNames, primBaseEfficacy)
            for i in range(primDoseCount):
                for j in range(st.session_state.get(f'primAgeRowCount{id}-{i}', 0)):
                    primAgeEfficacies[
                        st.session_state[f'primAgeGroup{id}-{i}-{j}']
                    ][i] = idGet(
                        'primAgeEfficacy', id, primBaseEfficacy[i], f'-{i}-{j}'
                    )
            agePrimEfficacyParams = [vaccineEfficacy(
                DoseType = 'primary', Age = ageCast(age),
                Efficacy = primAgeEfficacies[age], 
                WanedEfficacy = primWanedEfficacy
            ) for age in ageNames]
            for i in range(st.session_state.get(f'primWanedRowCount{id}', 0)):
                agePrimEfficacyParams[
                    ageNames.index(st.session_state[f'primWanedGroup{id}-{i}'])
                ].WanedEfficacy = idGet(
                    'primAgeWanedEfficacy', id, primWanedEfficacy, f'-{i}'
                )
            efficacyParams += agePrimEfficacyParams
            # Booster Efficacy Values
            if boosterToggle: efficacyParams += [vaccineEfficacy(
                DoseType = 'booster', Age = None, Efficacy = boostBaseEfficacy,
                WanedEfficacy = boostWanedEfficacy
            )] + [vaccineEfficacy(
                DoseType = 'booster', 
                Age = ageCast(st.session_state[f'boostAgeGroup{id}-{i}']), 
                Efficacy = idGet(
                    'boostAgeEfficacy', id, boostBaseEfficacy, f'-{i}'
                ),
                WanedEfficacy = idGet(
                    'boostAgeWanedEfficacy', id, boostWanedEfficacy, f'-{i}'
                )
            ) for i in range(st.session_state.get(f'boostAgeRowCount{id}', 0))]
            # All together
            schema.Scenario_VaccineDoseEfficacy = efficacyParams
            
        # Scenario Parameters With Age Prefix
        ageScenarioParams = (
            schema.Scenario_ParameterWithAgePrefix 
            if schema.Scenario_ParameterWithAgePrefix 
            else ageScenarioParameters()
        )
        ageScenarioParams.social_distance = idGet(
            'socialDistancingCompliance', id, 0.9
        ) if socialDistanceToggle else 0.0
        schema.Scenario_ParameterWithAgePrefix = ageScenarioParams
        
        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter if schema.Scenario_Parameter 
            else scenarioParameters()
        )
        # Vaccination
        if vaccineToggle:
            scenarioParams.vaccine_doses = idGet(
                'initialDoseReserve', id, 0
             ) if idGet('limitDosesToggle', id, False) else 9999
            scenarioParams.vaccination_first_dose_rate = idGet(
                'firstDoseRate', id, 300
            )
            vaccineTrigger = idGet('vaccineTrigger', id, 'Always')
            scenarioParams.vaccination_trigger = trigCast(vaccineTrigger)
            scenarioParams.vaccination_relaxation = trigCast(vaccineTrigger)
            if vaccineTrigger == 'Always':
                scenarioParams.vaccination_delay = 0
                scenarioParams.vaccination_duration = 9999
            elif vaccineTrigger == 'Timed':
                vaccinePeriod = [
                    i * 2 for i in idGet('vaccinePeriod', id, (29, 59))
                ]
                scenarioParams.vaccination_delay = vaccinePeriod[0]
                scenarioParams.vaccination_duration = (
                    vaccinePeriod[1] - vaccinePeriod[0]
                )
        # School Closure
        if idGet('schoolClosureToggle', id, False):
            scenarioParams.school_closure_compliance = idGet(
                'schoolClosureCompliance', id, 0.9
            )
            closedSchoolTypes = idGet('schoolClosureTypes', id, ['K-12'])
            scenarioParams.close_childcare = 'Childcare' in closedSchoolTypes
            scenarioParams.close_child_education = 'K-12' in closedSchoolTypes
            scenarioParams.close_adult_education = (
                'Tertiary' in closedSchoolTypes
            )
            schoolTrigger = idGet('schoolClosureTrigger', id, 'Always')
            scenarioParams.school_closure_trigger = trigCast(schoolTrigger)
            scenarioParams.school_closure_relaxation = trigCast(schoolTrigger)
            if schoolTrigger == 'Always':
                scenarioParams.school_closure_delay = 0
                scenarioParams.school_closure_duration = 9999
            elif schoolTrigger == 'Timed':
                schoolPeriod = [
                    i * 2 for i in idGet('schoolClosurePeriod', id, (29, 59))
                ]
                scenarioParams.school_closure_delay = schoolPeriod[0]
                scenarioParams.school_closure_duration = (
                    schoolPeriod[1] - schoolPeriod[0]
                )
        # Withdrawal Increase
        if idGet('withdrawalIncreaseToggle', id, False):    
            scenarioParams.increased_withdrawal = idGet(
                'withdrawalIncreaseAdult', id, 0.9
            )
            scenarioParams.increased_withdrawal_child = idGet(
                'withdrawalIncreaseChild', id, 1.0
            )
            withdrawalTrigger = idGet(
                'withdrawalIncreaseTrigger', id, 'Always'
            )
            scenarioParams.withdrawal_increase_trigger = trigCast(
                withdrawalTrigger
            )
            scenarioParams.withdrawal_increase_relaxation = trigCast(
                withdrawalTrigger
            )
            if withdrawalTrigger == 'Always':
                scenarioParams.withdrawal_increase_delay = 0
                scenarioParams.withdrawal_increase_duration = 9999
            elif withdrawalTrigger == 'Timed':
                withdrawalPeriod = [i * 2 for i in idGet(
                    'withdrawalIncreasePeriod', id, (29, 59)
                )]
                scenarioParams.withdrawal_increase_delay = withdrawalPeriod[0]
                scenarioParams.withdrawal_increase_duration = (
                    withdrawalPeriod[1] - withdrawalPeriod[0]
                )
        # Reduced Group Size
        if idGet('reducedGroupToggle', id, False): 
            scenarioParams.reduced_workgroup_size = idGet(
                'reducedGroupSize', id, 5
            )
            reducedGroupTrigger = idGet(
                'reducedGroupTrigger{id}', id, 'Always'
            )
            scenarioParams.reduced_workgroup_trigger = trigCast(
                reducedGroupTrigger
            )
            scenarioParams.reduced_workgroup_relaxation = trigCast(
                reducedGroupTrigger
            )
            if reducedGroupTrigger == 'Always':
                scenarioParams.reduced_workgroup_delay = 0
                scenarioParams.reduced_workgroup_duration = 9999
            elif reducedGroupTrigger == 'Timed':
                reducedGroupPeriod = [
                    i * 2 for i in idGet('reducedGroupPeriod', id, (29, 59))
                ]
                scenarioParams.reduced_workgroup_delay = reducedGroupPeriod[0]
                scenarioParams.reduced_workgroup_duration = (
                    reducedGroupPeriod[1] - reducedGroupPeriod[0]
                )
        # BCC Reduction
        if idGet('bccToggle', id, False):
            scenarioParams.bcc_reduction = (idGet('bccReducedRate', id, 0.2) / idGet('bccRate', id, 4.0))
            bccTrigger = idGet('bccTrigger', id, 'Always')
            scenarioParams.bcc_reduction_trigger = trigCast(bccTrigger)
            scenarioParams.bcc_reduction_relaxation = trigCast(bccTrigger)
            if bccTrigger == 'Always':
                scenarioParams.bcc_reduction_delay = 0
                scenarioParams.bcc_reduction_duration = 9999
            elif bccTrigger == 'Timed':
                bccPeriod = [i * 2 for i in idGet('bccPeriod', id, (29, 59))]
                scenarioParams.bcc_reduction_delay = bccPeriod[0]
                scenarioParams.bcc_reduction_duration = (
                    bccPeriod[1] - bccPeriod[0]
                )
        # Other NPIs
        if socialDistanceToggle:
            scenarioParams.social_distance_compliance = socialCompliance
            for i in range(st.session_state.get(f'socialRowCount{id}', 0)): setattr(
                scenarioParams, f'{ageCategories[
                    st.session_state[f'socialAgeGroup{id}-{i}']
                ]}_social_distance', 
                idGet('socialCompliance', id, socialCompliance, f'-{i}')
            )
        scenarioParams.diagnosed_case_isolation = idGet(
            'caseIsolation', id, False
        )
        scenarioParams.class_dismissal = idGet('classDismissal', id, False)
        # Triggers
        scenarioParams.case_trigger_threshold = idGet(
            'caseTotalThreshold', id, 1000
        )
        scenarioParams.rate_trigger_threshold = idGet(
            'rateStartThreshold', id, 10
        )
        scenarioParams.rate_relaxation_threshold = idGet(
            'rateRelaxThreshold', id, 5
        )
        scenarioParams.maximum_trigger_count = 250
        # Save the updated parameters
        schema.Scenario_Parameter = scenarioParams
    except (ValueError, ValidationError) as e:
        vaccineLog.error((
            f'[vaccinationNPIParams] Encountered {type(e).__name__} '
            f'while validating parameters for scenario {id}: {e}'
        ))
        raise e