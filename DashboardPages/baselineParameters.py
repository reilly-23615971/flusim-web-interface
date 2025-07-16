# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import numpy as np
import streamlit as st
# import streamlit_sortables as sts
from ClientResources.InterfaceFunctions import (
    getRemainingAgeGroups, addFormRow, deleteFormRow
)
from ClientResources.SharedResources import (
    npis, npiCamel, ageCategories, ordinals, triggerConditions
)

# Logging
baselineLog = logging.getLogger(__name__)

# Initialise session variables
sessionParameters = {
    'vacAgeRowCount0': 0,
    'primaryDoseCount0': 2,
    'primWanedRowCount0': 0,
    'boostAgeRowCount0': 0, 
    'boosterRemainingAgeGroups0': list(dict.fromkeys(ageCategories))
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.setdefault(
        parameter, default
    )

vaccineRowCount = st.session_state['vacAgeRowCount0']
primaryRowCount = st.session_state['primaryDoseCount0']
primaryWanedRowCount = st.session_state['primWanedRowCount0']
boosterRowCount = st.session_state['boostAgeRowCount0']

# Ensure age selections only give possible parameters
# Dictionary format: 'remaining groups variable': (
#   'number of rows variable', 'group row variable prefix'
# )
ageGroupSets = {
    'vaccineRemainingAgeGroups0': (
        'vacAgeRowCount0', 'vacAgeGroup0-'
    ),
    'primaryRemainingWanedGroups0': (
        'primWanedRowCount0', 'primWanedGroup0-'
    ),
    'boosterRemainingAgeGroups0': (
        'boostAgeRowCount0', 'boostAgeGroup0-'
    )
}

# Handle primary dose nested age group row counts
for i in range(primaryRowCount):
    st.session_state[f'primAgeRowCount0-{i}'] = st.session_state.setdefault(
        f'primAgeRowCount0-{i}', 0
    )
    ageGroupSets[f'primaryRemainingAgeGroups0-{i}'] = (
        f'primAgeRowCount0-{i}', f'primAgeGroup0-{i}-'
    )

primaryAgeRowCounts = [
    st.session_state[f'primAgeRowCount0-{i}'] for i in range(primaryRowCount)
]

getRemainingAgeGroups(ageGroupSets)

nonCanon = """
# Hide slider min/max labels
hide_elements = '''
    <style> div[data-testid = 'stSliderTickBar'] {
        display: none;
    } </style>
'''
st.html(hide_elements)
"""


# TODO: Warn for nonsensical conditions like reduced BCC > regular BCC
# TODO: Split off tabs into their own files, both for file size 
# reduction and preparation for scenario implementation



# Page Content



st.title('Flusim Disease Model Web Dashboard')

st.markdown('''
    This page allows for configuring the parameters that will be used 
    as a baseline for the simulation. All scenarios that you run will 
    use these parameters unless the scenario explicitly overwrites them.
            
    Select a tab to view or modify the parameters under that category. 
    Hover your mouse over the :material/help: help icon next to a 
    parameter's input field to show an explanation of what that 
    parameter represents. Hover your mouse over any buttons to show an 
    explanation of what that button does.
''')

# Place to put warnings errors in the current parameter selection
alertContainer = st.container()

#TODO: Add more configurable parameters/tabs
#TODO: Consider having templates that load parameters for specific stuff
# Tab ideas: Environment? Health Outcome?

basicTab, diseaseTab, interventionTab, dynamicTab = st.tabs([
    'Basic Parameters', 'Disease Parameters', 
    'Vaccination and NPIs', 'Dynamic Parameters'
])


# Vaccination and NPIs
# TODO: Sync trigger thresholds between different NPIs
with interventionTab:
    st.header('Vaccination and NPI Parameters')
    st.markdown('''
        This tab contains parameters relating to whether vaccination 
        and non-pharmaceutical interventions (NPIs) are integrated into 
        the simulation.
    ''')

    # Potential Catchable Errors:
    # - Duration of NPI is longer that simulation length/simulation 
    #   ends before timed NPI does
    # - Initial vaccinated proportion is greater than target vaccinated 
    #   proportion (including age-specific versions)
    # - Vaccine total program length is greater than simulation time
    # - Final waned efficacy is grater than initial efficacy (including 
    #   age-specific versions and boosters if possible)
    # - Effect of NPI is weaker than base parameters

    # Vaccination
    vaccineContainer = st.container()
    with vaccineContainer:
        st.subheader('Vaccination Parameters')
        useVaccinesToggle = st.toggle(
            'Enable Vaccines in Simulation', value = True, 
            key = 'vaccineToggle0', help = '''
                Toggle whether or not individuals in the simulation 
                will be vaccinated against the disease, overriding all 
                other vaccine-related parameters.
            '''
        )

        # General Vaccination Policy Parameters
        st.html('<span id = "vaccinationTriggerCondition"></span>')
        with st.expander('Vaccination Policies'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control the rollout of vaccines in the 
                simulation, with parameters such as what triggers the 
                introduction of vaccines and how often individuals are 
                vaccinated for the first time.
            ''')

            # Policy parameters
            # TODO: Change relevant population-based fields to have the 
            # population of the current community as a maximum
            with st.container(border = True):
                vaccineTrigger = st.selectbox(
                    'Vaccination Trigger Condition', key = f'vaccineTrigger0', 
                    options = triggerConditions[:-2], 
                    disabled = not useVaccinesToggle, help = '''
                        The type of condition that must be satisfied 
                        before vaccines will start being administered 
                        in the simulation. Additional options for 
                        configuring the exact trigger condition will 
                        appear after selecting one of these options.

                        ##### Options:
                        - Always: Vaccination will occur throughout the 
                        entire simulation.
                        - Timed: Vaccination will begin after a 
                        specific number of days have passed in the 
                        simulation, and will stop after a different 
                        number of days.
                        - Community Case Rate: Vaccination will begin 
                        if the rate of newly diagnosed cases per day 
                        exceeds a specific threshold, and will stop if 
                        the rate drops below a different threshold 
                        afterwards. This trigger rate allows 
                        vaccination programs to start and stop multiple 
                        times if the case rate varies between the two 
                        thresholds.
                        - Community Case Total: Vaccination will begin 
                        after the number of diagnosed cases in the 
                        community exceeds a specific threshold, and 
                        will continue for the rest of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if vaccineTrigger == 'Timed':
                    # TODO: Set time-based parameter maximums based on 
                    # number of cycles in simulation
                    vaccineTimeStart = st.slider(
                        'Vaccination Starting Day', 0, 720, 30, 
                        key = 'vaccineTimeStart0', 
                        disabled = not useVaccinesToggle, help = '''
                            The day of the simulation (starting from 
                            Day 0) on which vaccinations will start 
                            being administered in the simulation.
                        '''
                    )
                    vaccineTimeDuration = st.slider(
                        'Vaccination Period Duration (Days)', 1, 720, 56, 
                        key = 'vaccineTimeDuration0', 
                        disabled = not useVaccinesToggle, help = '''
                            The length (in days) of the period of time 
                            in which vaccinations will be administered 
                            in the simulation.
                        '''
                    )
                # Rate triggers
                elif vaccineTrigger == 'Community Case Rate': st.info('''
                    Due to limitations in the *Flusim* model, case rate 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
                # Case triggers
                elif vaccineTrigger == 'Community Case Total': st.info('''
                    Due to limitations in the *Flusim* model, case total 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
            # Other vaccine program parameters
            st.number_input(
                'Starting Number of Available Doses', 
                0, key = 'initialDoseReserve0', 
                placeholder = 'Enter a whole number of doses',
                disabled = not useVaccinesToggle, help = '''
                    The number of vaccine doses that will be available 
                    to administer to individuals at the beginning of 
                    the simulation.
                '''
            )
            st.number_input(
                'First Dose Vaccination Rate (Vaccinations per Day)', 
                1, value = 300, key = 'firstDoseRate0', 
                placeholder = 'Enter a whole number of people',
                disabled = not useVaccinesToggle, help = '''
                    The number of unvaccinated individuals who will 
                    receive the first dose of the vaccine each day, 
                    assuming there are enough doses available. Must be 
                    a whole number greater than 0.
                '''
            )
            initialVaccinated = st.select_slider(
                'Initial Vaccinated Proportion of Population', 
                np.linspace(0.0, 1.0, 1001), 0.0, key = 'initialVaccinated0', 
                format_func = lambda x: f'{100 * x:0.3g}%',
                disabled = not useVaccinesToggle, help = '''
                    The percentage of the population that will already 
                    be vaccinated against the disease at the beginning 
                    of the simulation.
                '''
            )
            targetVaccinated = st.select_slider(
                'Target Vaccinated Proportion of Population', 
                np.linspace(0.0, 1.0, 1001), 0.8, key = 'targetVaccinated0', 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useVaccinesToggle, help = '''
                    The percentage of the population that will be 
                    targeted by the vaccine program in the simulation. 
                    The actual proportion of the population that is 
                    vaccinated may be lower if there are an 
                    insufficient number of doses available.
                '''
            )

            # Store age-based proportion values for error checking
            vacAgeInitials, vacAgeTargets = {}, {}

            # Modifiable-length field for age-specific vaccination
            # TODO: Show warnings if age specific targets are below 
            # initial values
            st.markdown('''
                ### Age-Specific Vaccinated Proportion Parameters
                
                This section allows for unique vaccinated proportion 
                parameters to be defined for individual age groups in 
                the simulation, overriding the global parameters 
                defined above.
            ''')
            vacAgeProportionContainer = st.container()
            for i in range(vaccineRowCount):
                (
                    vacAgeGroupColumn, vacAgeInitialColumn, 
                    vacAgeTargetColumn, vacAgeRemoveColumn
                ) = vacAgeProportionContainer.columns(
                    (0.25, 0.275, 0.275, 0.2)
                )
                # Age group column
                with vacAgeGroupColumn: vacAgeGroup = st.selectbox(
                    'Age Group', key = f'vacAgeGroup0-{i}', 
                    # Set age group options such that only ages that 
                    # haven't been selected yet can be selected
                    options = (
                        [st.session_state.get(f'vacAgeGroup0-{i}')] 
                        + [
                            group for group in st.session_state[
                                'vaccineRemainingAgeGroups0'
                            ] if group != st.session_state.get(
                                f'vacAgeGroup0-{i}'
                            )
                        ] if st.session_state.get(f'vacAgeGroup0-{i}') 
                        else st.session_state['vaccineRemainingAgeGroups0']
                    ), 
                    disabled = (
                        not useVaccinesToggle or not vaccineRowCount < 10
                    ),
                    help = '''
                        An age group that will have specific 
                        vaccination initial and target proportions 
                        defined for it, overriding the base proportions.

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
                with vacAgeInitialColumn: 
                    vacAgeInitials[vacAgeGroup] = st.select_slider(
                        'Initial Vaccinated Proportion of Population', 
                        np.linspace(0.0, 1.0, 1001), 0.0,  
                        format_func = lambda x: f'{100 * x:0.3g}%',
                        disabled = not useVaccinesToggle, 
                        key = f'vacAgeInitial0-{i}', help = '''
                            The percentage of individuals in this age 
                            group that will already be vaccinated 
                            against the disease at the beginning of the 
                            simulation.
                        '''
                    )
                # Target proportion column
                with vacAgeTargetColumn: 
                    vacAgeTargets[vacAgeGroup] = st.select_slider(
                        'Target Vaccinated Proportion of Population', 
                        np.linspace(0.0, 1.0, 1001), 0.8, 
                        format_func = lambda x: f'{100 * x:0.3g}%',
                        disabled = not useVaccinesToggle, 
                        key = f'vacAgeTarget0-{i}', help = '''
                            The percentage of individuals in this age 
                            group that will be targeted by the vaccine 
                            program in the simulation. The actual 
                            proportion of individuals that are 
                            vaccinated may be lower if there are an 
                            insufficient number of doses available.
                        '''
                    )
                # Delete button column
                with vacAgeRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:', 
                    key = f'vacAgeRemove0-{i}', on_click = deleteFormRow, 
                    args = (
                        i, 'vacAgeRowCount0', {
                            'vacAgeGroup0-', 'vacAgeInitial0-', 
                            'vacAgeTarget0-'
                        }
                    ),
                    disabled = not useVaccinesToggle, help = '''
                        Remove this row of the form and remove these 
                        age-specific vaccine proportion values from the 
                        simulation.
                    '''
                )
            # Button to add another row for additional age specification
            vacAgeProportionContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = 'vacAgeAdd0', args = (
                    'vacAgeRowCount0', {
                        f'vacAgeGroup0-{vaccineRowCount}': 
                        (
                            st.session_state['vaccineRemainingAgeGroups0'][0] 
                            if st.session_state['vaccineRemainingAgeGroups0'] 
                            else None
                        ),
                        f'vacAgeInitial0-{vaccineRowCount}': 
                        initialVaccinated,
                        f'vacAgeTarget0-{vaccineRowCount}': 
                        targetVaccinated,
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not vaccineRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have unique vaccinated 
                    proportion values.
                ''' if vaccineRowCount <= 9 else '''
                    All age groups have been given unique vaccinated 
                    proportion values, so a new age group cannot be 
                    added.
                '''
            )



        # Primary Vaccine Parameters
        with st.expander('Primary Vaccine Properties'):
            # Describe primary vaccines
            st.markdown('''
                These parameters control the properties of the main
                program of vaccines that will be administered to 
                individuals within the simulation. Each vaccine in the 
                program can have its own efficacy values set, since in 
                many cases multiple doses are required to achieve 
                maximum immunity to the disease.
            ''')

            # Universal primary parameters
            primaryDoseCount = st.slider(
                'Number of Vaccine Doses', 1, 5, 2, key = 'primaryDoseCount0',
                disabled = not useVaccinesToggle, help = '''
                    The number of times each individual in the 
                    simulation will be administered a vaccine for the 
                    disease, excluding booster vaccines. 
                    
                    Note that since efficacy is defined separately for 
                    each vaccine dose in the program, modifying this 
                    value will change the number of fields for 
                    specifying efficacy below.
                '''
            )
            primaryDelay = st.slider(
                'Time Between Vaccine Doses (Days)', 1, 180, 56,
                disabled = not useVaccinesToggle, key = 'primaryDelay0', 
                help = '''
                    The number of days after an individual receives a 
                    vaccine dose before they are able to receive 
                    another.
                '''
            )
            st.slider(
                'Vaccine Immunity Waning Delay (Days)', 1, 180, 30, 
                disabled = not useVaccinesToggle, key = 'primaryDuration0', 
                help = '''
                    The number of days after an individual receives a 
                    vaccine dose before the immunity conferred by this 
                    vaccine begins to diminish.
                '''
            )
            primaryWanedEfficacy = st.select_slider(
                ((
                    'Dose Efficacy After Immunity '
                    'Waning (Proportion of Population)'
                )), 
                np.linspace(0.0, 1.0, 1001), 0.0, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useVaccinesToggle, 
                key = f'primaryWanedEfficacy0', help = '''
                    The final efficacy value that the vaccine program 
                    will approach as the immunity it provides begins to 
                    diminish, represented as the percentage of 
                    individuals with completely waned immunity who will 
                    not become infected when exposed to the disease.
                '''
            )
            # TODO: See if better methods of representing waning rate 
            # (e.g. vaccine effectiveness dropoff) are feasible
            oldPrimaryWaningRate = """
            primaryWaningRate = st.slider(
                'Vaccine Immunity Waning Rate (Probability)', 0.0, 0.02, 0.005,
                step = 0.0005, format = '%0.4g', 
                disabled = not useVaccinesToggle, key = 'primaryWaningRate0', 
                help = '''
                    The probability that an individual will lose the 
                    immunity conferred by a vaccine dose each day after 
                    the vaccine's duration has passed.
                '''
            )
            """
            st.slider(
                'Vaccine Waning Duration (Days)', 0, 720, 180,
                disabled = not useVaccinesToggle, key = 'primaryWaningRate0', 
                help = '''
                    The number of days after the immunity from a 
                    vaccine dose begins waning before the efficacy of 
                    the vaccine stabilises. Vaccine-conferred immunity 
                    in the *Flusim* simulation will wane at a linear 
                    rate, so this parameter represents how long it 
                    takes for the vaccine's efficacy to decrease from 
                    the final dose's initial value to its final value.

                    If this parameter is set to 0, the immunity 
                    provided by the main vaccine program will never 
                    diminish.
                '''
            )

            # Store age-based waned efficacy values for error checking
            primAgeWaneds = {}

            # Age-Specific Waned Efficacy Field
            st.markdown('''
                #### Age-Specific Efficacy After Immunity Waning
                
                This section allows for unique final efficacy values 
                after immunity waning to be defined for individual age 
                groups in the simulation, overriding the global waned 
                efficacy defined above.
            ''')
            primWanedContainer = st.container()
            for i in range(primaryWanedRowCount):
                (
                    primWanedGroupColumn, primWanedEffColumn, 
                    primWanedRemoveColumn
                ) = primWanedContainer.columns((0.25, 0.55, 0.2))
                # Age group column
                with primWanedGroupColumn: primWanedAgeGroup = st.selectbox(
                    'Age Group', key = f'primWanedGroup0-{i}', 
                    # Set age group options such that only ages that 
                    # haven't been selected yet can be selected
                    options = (
                        [st.session_state.get(f'primWanedGroup0-{i}')] 
                        + [
                            group for group in st.session_state[
                                f'primaryRemainingWanedGroups0'
                            ] if group != st.session_state.get(
                                f'primWanedGroup0-{i}'
                            )
                        ] if st.session_state.get(f'primWanedGroup0-{i}')
                        else st.session_state[
                            f'primaryRemainingWanedGroups0'
                        ]
                    ), 
                    disabled = (
                        not useVaccinesToggle or not primaryWanedRowCount < 10
                    ),
                    help = '''
                        An age group that will have a specific final 
                        efficacy value after immunity waning defined 
                        for it, overriding the base waned efficacy 
                        value.

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
                with primWanedEffColumn: 
                    primAgeWaneds[primWanedAgeGroup] = st.select_slider(
                        ((
                            'Dose Efficacy After Immunity '
                            'Waning \n\n(Proportion of Population)'
                        )), 
                        np.linspace(0.0, 1.0, 1001), 0.0, 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        disabled = not useVaccinesToggle, 
                        key = f'primAgeWanedEfficacy0-{i}', help = '''
                            The final efficacy value that the vaccine 
                            program will approach for this age group as 
                            the immunity it provides begins to 
                            diminish, represented as the percentage of 
                            individuals in this age group with 
                            completely waned immunity who will not 
                            become infected when exposed to the disease.
                        '''
                    )
                # Delete button column
                with primWanedRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:',
                    key = f'primWanedRemove0-{i}', 
                    on_click = deleteFormRow, args = (
                        i, f'primWanedRowCount0', {
                            f'primWanedGroup0-', 
                            f'primAgeWanedEfficacy0-'
                        }
                    ),
                    disabled = not useVaccinesToggle, help = '''
                        Remove this row of the form and remove these 
                        age-specific vaccine waned efficacy values from 
                        the simulation.
                    '''
                )
            # Button to add another row for additional age specification
            primWanedContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'primWanedAdd0', args = (
                    f'primWanedRowCount0', {
                        f'primWanedGroup0-{primaryWanedRowCount}': 
                        (
                            st.session_state[
                                f'primaryRemainingWanedGroups0'
                            ][0] if st.session_state[
                                f'primaryRemainingWanedGroups0'
                            ] else None
                        ),
                        f'primAgeWanedEfficacy0-{primaryWanedRowCount}': 
                        primaryWanedEfficacy
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not primaryWanedRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have unique vaccine 
                    waned efficacy values.
                ''' if primaryWanedRowCount <= 9 else '''
                    All age groups have been given unique waned 
                    efficacy values, so a new age group cannot be added.
                '''
            )

            # Store age-based initial efficacy values for error checking
            primDoseInitials = [None for _ in range(primaryDoseCount)]
            primAgeInitials = [{} for _ in range(primaryDoseCount)]

            # Modifiable-length field for each primary dose
            st.markdown('''
                ### Individual Dose Efficacies
                
                Here you can set the initial efficacy of each vaccine 
                dose in the program separately. Changing the "Number of 
                Vaccine Doses" parameter will affect how many sections 
                are present here.
            ''')
            for i in range(primaryDoseCount):
                doseEfficacyContainer = st.container(border = True)
                doseEfficacyContainer.markdown(
                    f'#### {ordinals[i+1]} Vaccine Dose'
                )
                primDoseInitials[i] = doseEfficacyContainer.select_slider(
                    'Initial Dose Efficacy (Proportion of Population)', 
                    np.linspace(0.0, 1.0, 1001), 0.5, 
                    format_func = lambda x: f'{100 * x:0.3g}%', 
                    disabled = not useVaccinesToggle, 
                    key = f'primaryBaseEfficacy0-{i}', help = '''
                        The initial efficacy of this vaccine dose, 
                        represented as the percentage of individuals 
                        that have recently received the dose who will 
                        not become infected when exposed to the disease.
                    '''
                )

                # Age-Specific Primary Efficacy Field
                doseEfficacyContainer.markdown('''
                    ##### Age-Specific Efficacy Rates
                    
                    This section allows unique initial efficacy values 
                    for this dose to be defined for individual age 
                    groups in the simulation, overriding the global 
                    initial efficacy value for this dose defined above.
                ''')
                primAgeEfficacyContainer = doseEfficacyContainer.container()
                for j in range(primaryAgeRowCounts[i]):
                    (
                        primAgeGroupColumn, primAgeEfficacyColumn, 
                        primAgeRemoveColumn
                    ) = primAgeEfficacyContainer.columns(
                        (0.25, 0.55, 0.2)
                    )
                    # Age group column
                    with primAgeGroupColumn: primAgeGroup = st.selectbox(
                        'Age Group', key = f'primAgeGroup0-{i}-{j}', 
                        # Set age group options such that only ages that 
                        # haven't been selected yet can be selected
                        options = (
                            [st.session_state.get(f'primAgeGroup0-{i}-{j}')] 
                            + [
                                group for group in st.session_state[
                                    f'primaryRemainingAgeGroups0-{i}'
                                ] if group != st.session_state.get(
                                    f'primAgeGroup0-{i}-{j}'
                                )
                            ] if st.session_state.get(f'primAgeGroup0-{i}-{j}')
                            else st.session_state[
                                f'primaryRemainingAgeGroups0-{i}'
                            ]
                        ), 
                        disabled = (
                            not useVaccinesToggle 
                            or not primaryAgeRowCounts[i] < 10
                        ),
                        help = '''
                            An age group that will have specific 
                            initial vaccine efficacy values defined for 
                            it, overriding the base efficacy value for 
                            this vaccine dose.

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
                    with primAgeEfficacyColumn: 
                        primAgeInitials[i][primAgeGroup] = st.select_slider(
                            'Initial Dose Efficacy (Proportion of Population)',
                            np.linspace(0.0, 1.0, 1001), 0.5, 
                            format_func = lambda x: f'{100 * x:0.3g}%', 
                            disabled = not useVaccinesToggle, 
                            key = f'primAgeEfficacy0-{i}-{j}', help = '''
                                The initial efficacy of this vaccine 
                                dose for this age group, represented as 
                                the percentage of recently vaccinated 
                                individuals in this age group who will 
                                not become infected when exposed to the 
                                disease.
                            '''
                        )
                    # Delete button column
                    with primAgeRemoveColumn: st.button(
                        label = 'Remove Age Group', icon = ':material/delete:',
                        key = f'primAgeRemove0-{i}-{j}', 
                        on_click = deleteFormRow, args = (
                            i, f'primAgeRowCount0-{i}', {
                                f'primAgeGroup0-{i}-', 
                                f'primAgeEfficacy0-{i}-'
                            }
                        ),
                        disabled = not useVaccinesToggle, help = '''
                            Remove this row of the form and remove 
                            these age-specific initial vaccine efficacy 
                            values from the simulation.
                        '''
                    )
                # Button to add another row for additional age specification
                primAgeEfficacyContainer.button(
                    label = 'Add Age Group', icon = ':material/add:', 
                    on_click = addFormRow, key = f'primAgeAdd0-{i}', args = (
                        f'primAgeRowCount0-{i}', {
                            f'primAgeGroup0-{i}-{primaryAgeRowCounts[i]}': 
                            (
                                st.session_state[
                                    f'primaryRemainingAgeGroups0-{i}'
                                ][0] if st.session_state[
                                    f'primaryRemainingAgeGroups0-{i}'
                                ] else None
                            ),
                            f'primAgeEfficacy0-{i}-{primaryAgeRowCounts[i]}': 
                            primDoseInitials[i]
                        }
                    ), 
                    disabled = (
                        not useVaccinesToggle 
                        or not primaryAgeRowCounts[i] < 10
                    ),
                    help = '''
                        Add another row to this form, where you can 
                        select an additional age group to have unique 
                        initial vaccine efficacy values.
                    ''' if primaryAgeRowCounts[i] <= 9 else '''
                        All age groups have been given unique initial 
                        efficacy values for this vaccine dose, so a new 
                        age group cannot be added.
                    '''
                )



        # Booster Parameters
        with st.expander('Booster Vaccine Properties'):
            # Describe booster vaccines
            st.markdown('''
                These parameters control the properties of booster 
                vaccines, additional doses of a vaccine only 
                administered to individuals who have already received 
                all vaccines in the initial program. Unlike the main 
                vaccine doses defined above, all booster vaccine doses 
                share the same efficacy values. Booster vaccines are 
                primarily used with diseases like COVID-19, 
                meningococcal disease and diphtheria to preserve an 
                individual's immunity to the disease as it wanes over 
                time.
            ''')

            # Universal booster parameters
            useBoostersToggle = st.toggle(
                'Enable Booster Vaccines', value = True, 
                key = 'boosterToggle0', disabled = not useVaccinesToggle,
                help = '''
                    Toggle whether or not booster vaccines are 
                    administered in the simulation, overriding other 
                    booster-related parameters.
                '''
            )
            st.slider(
                'Number of Booster Doses', 1, 10, 3, key = 'boosterDoseCount0',
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                help = '''
                    The number of times each individual in the 
                    simulation will be administered a booster vaccine.
                '''
            )
            boosterDelay = st.slider(
                'Time Between Booster Doses (Days)', 1, 180, 90,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterDelay0', help = '''
                    The number of days after an individual receives one 
                    booster vaccine dose before they are able to 
                    receive another.
                '''
            )
            st.slider(
                'Booster Immunity Waning Delay (Days)', 1, 180, 60,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterDuration0', help = '''
                    The number of days after an individual receives a 
                    booster vaccine dose before the immunity conferred 
                    by this vaccine begins to diminish.
                '''
            )
            boosterBaseEfficacy = st.select_slider(
                'Initial Booster Efficacy (Proportion of Population)', 
                np.linspace(0.0, 1.0, 1001), 0.9, key = 'boosterBaseEfficacy0',
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The initial efficacy of each booster vaccine, 
                    represented as the percentage of individuals that 
                    have recently received the booster who will not 
                    become infected when exposed to the disease.
                '''
            )
            boosterWanedEfficacy = st.select_slider(
                ((
                    'Booster Efficacy After Immunity '
                    'Waning (Proportion of Population)'
                )), 
                np.linspace(0.0, 1.0, 1001), 0.6, 
                key = 'boosterWanedEfficacy0', 
                disabled = not useVaccinesToggle or not useBoostersToggle,
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The final efficacy value that the booster vaccine 
                    will approach as the immunity it provides begins to 
                    diminish, represented as the percentage of 
                    individuals with completely waned immunity who will 
                    not become infected when exposed to the disease.
                '''
            )
            # TODO: See if better methods of representing waning rate 
            # (e.g. vaccine effectiveness dropoff) are feasible
            oldBoosterWaningRate = """
            boosterWaningRate = st.slider(
                'Booster Immunity Waning Rate (Probability)', 0.0, 0.02, 0.005,
                step = 0.0005, format = '%0.4g', 
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterWaningRate0', help = '''
                    The probability that an individual will lose the 
                    immunity conferred by a booster vaccine each day 
                    after the vaccine's duration has passed.
                '''
            )
            """
            st.slider(
                'Booster Waning Duration (Days)', 0, 720, 180,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterWaningRate0', help = '''
                    The number of days after the immunity from a 
                    booster vaccine begins waning before the efficacy 
                    of the vaccine stabilises. Vaccine-conferred 
                    immunity in the *Flusim* simulation will wane at a 
                    linear rate, so this parameter represents how long 
                    it takes for the vaccine's efficacy to decrease 
                    from its initial value to its final value.

                    If this parameter is set to 0, the immunity 
                    provided by booster vaccines will never diminish.
                '''
            )

            # Store age-based booster efficacy values for error checking
            boostAgeInitials, boostAgeWaneds = {}, {}

            # Modifiable-length field for age-specific efficacy
            st.markdown('''
                ### Age-Specific Booster Efficacies
                
                This section allows for unique booster efficacy values 
                (both initial and final) to be defined for individual 
                age groups in the simulation, overriding the global 
                booster efficacy values defined above.
            ''')
            boostAgeEfficacyContainer = st.container()
            for i in range(boosterRowCount):
                (
                    boostAgeGroupColumn, boostAgeEfficacyColumn, 
                    boostAgeWanedColumn, boostAgeRemoveColumn
                ) = boostAgeEfficacyContainer.columns(
                    (0.25, 0.275, 0.275, 0.2)
                )
                # Age group column
                with boostAgeGroupColumn: boostAgeGroup = st.selectbox(
                    # Set age group options such that only ages that 
                    # haven't been selected yet can be selected
                    'Age Group', key = f'boostAgeGroup0-{i}', options = (
                        [st.session_state.get(f'boostAgeGroup0-{i}')] 
                        + [
                            group for group in st.session_state[
                                'boosterRemainingAgeGroups0'
                            ] if group != st.session_state.get(
                                f'boostAgeGroup0-{i}'
                            )
                        ] if st.session_state.get(f'boostAgeGroup0-{i}') 
                        else st.session_state['boosterRemainingAgeGroups0']
                    ), 
                    disabled = (
                        not useVaccinesToggle or not useBoostersToggle 
                        or not boosterRowCount < 10
                    ),
                    help = '''
                        An age group that will have specific booster 
                        vaccine efficacy values defined for it, 
                        overriding the base efficacy value for booster 
                        vaccines.

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
                with boostAgeEfficacyColumn: 
                    boostAgeInitials[boostAgeGroup] = st.select_slider(
                        'Initial Booster Efficacy (Proportion of Population)', 
                        np.linspace(0.0, 1.0, 1001), 0.9, disabled = (
                            not useVaccinesToggle or not useBoostersToggle
                        ), 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        key = f'boostAgeEfficacy0-{i}', help = '''
                            The initial efficacy of each booster 
                            vaccine for this age group, represented as 
                            the percentage of recently vaccinated individuals 
                            in this age group who will not become infected 
                            when exposed to the disease.
                        '''
                    )
                # Waned efficacy column
                with boostAgeWanedColumn: 
                    boostAgeWaneds[boostAgeGroup] = st.select_slider(
                        ((
                            'Booster Efficacy After Immunity '
                            'Waning (Proportion of Population)'
                        )), 
                        np.linspace(0.0, 1.0, 1001), 0.6, disabled = (
                            not useVaccinesToggle or not useBoostersToggle
                        ), 
                        format_func = lambda x: f'{100 * x:0.3g}%', 
                        key = f'boostAgeWanedEfficacy0-{i}', help = '''
                            The final efficacy value that the booster 
                            vaccine will approach for this age group as the 
                            immunity it provides begins to diminish, 
                            represented as the percentage of individuals in 
                            this age group with completely waned immunity 
                            who will not become infected when exposed to 
                            the disease.
                        '''
                    )
                # Delete button column
                with boostAgeRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:', 
                    key = f'boostAgeRemove0-{i}', on_click = deleteFormRow, 
                    args = (
                        i, 'boostAgeRowCount0', {
                            'boostAgeGroup0-', 'boostAgeEfficacy0-', 
                            'boostAgeWanedEfficacy0-'
                        }
                    ),
                    disabled = not useVaccinesToggle or not useBoostersToggle, 
                    help = '''
                        Remove this row of the form and remove these 
                        age-specific booster vaccine efficacy values 
                        from the simulation.
                    '''
                )
            # Button to add another row for additional age specification
            boostAgeEfficacyContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = 'boostAgeAdd0', args = (
                    'boostAgeRowCount0', {
                        f'boostAgeGroup0-{boosterRowCount}': 
                        (
                            st.session_state['boosterRemainingAgeGroups0'][0] 
                            if st.session_state['boosterRemainingAgeGroups0'] 
                            else None
                        ),
                        f'boostAgeEfficacy0-{boosterRowCount}': 
                        boosterBaseEfficacy,
                        f'boostAgeWanedEfficacy0-{boosterRowCount}': 
                        boosterWanedEfficacy,
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not useBoostersToggle 
                    or not boosterRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have unique booster 
                    vaccine efficacy values.
                ''' if boosterRowCount <= 9 else '''
                    All age groups have been given unique booster 
                    vaccine efficacy values.
                '''
            )
    




    # NPIs
    with st.container():
        st.subheader('Non-Pharmaceutical Intervention (NPI) Parameters')

        # General NPIs
        st.html('<span id = "generalTriggerCondition"></span>')
        with st.expander('General NPI Properties'):
            st.markdown('''
                These parameters control the implementation of simpler 
                non-pharmaceutical intervention (NPI) techniques, 
                including social distancing, case isolation and class 
                dismissal.
            ''')

            # Social distancing
            useSocialDistancingToggle = st.toggle(
                'Enable Social Distancing', value = True, 
                key = 'socialDistancingToggle0', help = '''
                    Toggle whether or not social distancing 
                    interventions are implemented in the simulation, 
                    overriding other social distancing parameters.
                '''
            )
            socialDistancingCompliance = st.select_slider(
                'Social Distancing Compliance (Proportion of Population)', 
                np.linspace(0.0, 1.0, 1001), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useSocialDistancingToggle, 
                key = 'socialDistancingCompliance0', help = '''
                    The percentage of the population that will comply 
                    with social distancing interventions in the 
                    simulation.
                '''
            )       
            
            # TODO: Age-based social distancing probabilities

            # Case Isolation
            st.toggle(
                'Enable Case Isolation', value = True, 
                key = 'caseIsolation0', help = '''
                    Toggle whether or not individuals who have been 
                    diagnosed as cases of the disease will be forced to 
                    isolate at home.
                '''
            )

            # Class Dismissal
            classDismissal = st.toggle(
                'Enable Class Dismissal', value = True, 
                key = 'classDismissal0', help = '''
                    Toggle whether or not classes in childcare and 
                    non-tertiary schools should dismiss classes 
                    when the daily case rate is high enough.
                '''
            )
            if classDismissal: st.info('''
                Due to limitations in the *Flusim* model, case rate 
                thresholds must be defined globally. You may 
                configure these thresholds using the 
                "Intervention Trigger Thresholds" parameters at the 
                bottom of this page (click 
                [this link](#thresholdTriggerCondition) to go there 
                directly).
            ''')
            # Diagnosis Delay will go in environment



        # School Closure
        st.html('<span id = "schoolClosureTriggerCondition"></span>')
        with st.expander('School Closure Properties'):
            st.markdown('''
                These parameters control if and when schools will close 
                as a result of the disease.
            ''')
            useSchoolClosureToggle = st.toggle(
                'Enable School Closures', value = True, 
                key = 'schoolClosureToggle0', help = '''
                    Toggle whether or not school closure interventions 
                    are implemented in the simulation, overriding other 
                    school closure parameters.
                '''
            )
            
            # School closure triggers
            with st.container(border = True):
                schoolClosureTrigger = st.selectbox(
                    'School Closure Trigger Condition', 
                    key = f'schoolClosureTrigger0', 
                    options = triggerConditions, 
                    disabled = not useSchoolClosureToggle, help = '''
                        The type of condition that must be satisfied 
                        before schools will start being closed in the 
                        simulation. Additional options for configuring 
                        the exact trigger condition will appear after 
                        selecting one of these options.

                        ##### Options:
                        - Always: Schools will be closed throughout the 
                        entire simulation.
                        - Timed: Schools will begin to close after a 
                        specific number of days have passed in the 
                        simulation, and will begin to reopen after a 
                        different number of days.
                        - Community Case Rate: Schools will begin to 
                        close if the rate of newly diagnosed cases per 
                        day exceeds a specific threshold, and will 
                        begin to reopen if the rate drops below a 
                        different threshold afterwards. This trigger 
                        rate allows schools to close and reopen 
                        multiple times if the case rate varies between 
                        the two thresholds.
                        - Community Case Total: Schools will begin to 
                        close after the number of diagnosed cases in 
                        the community exceeds a specific threshold, and 
                        will remain closed for the rest of the 
                        simulation.
                        - Cases per School: Schools will close 
                        individually when the number of cases diagnosed 
                        within them reaches a certain threshold, and 
                        will remain closed for the rest of the 
                        simulation.
                        - Cases per K-12 School: Primary and secondary 
                        schools will close individually when the number 
                        of cases diagnosed within them reaches a 
                        certain threshold, and will remain closed for 
                        the rest of the simulation. Childcare 
                        facilities and tertiary schools/universities 
                        will not close, overriding other parameters.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if schoolClosureTrigger == 'Timed':
                    # TODO: Set time-based parameter maximums based on 
                    # number of cycles in simulation
                    schoolClosureTimeStart = st.slider(
                        'School Closure Starting Day', 0, 720, 30, 
                        key = 'schoolClosureTimeStart0', 
                        disabled = not useSchoolClosureToggle, help = '''
                            The day of the simulation (starting from 
                            Day 0) on which schools will start closing 
                            in the simulation.
                        '''
                    )
                    schoolClosureTimeDuration = st.slider(
                        'School Closure Period Duration (Days)', 
                        0, 720, 56, key = 'schoolClosureTimeDuration0', 
                        disabled = not useSchoolClosureToggle, help = '''
                            The length (in days) of the period of time 
                            in which schools will be closed in the 
                            simulation.
                        '''
                    )
                # Rate triggers
                elif schoolClosureTrigger == 'Community Case Rate': st.info('''
                    Due to limitations in the *Flusim* model, case rate 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
                # Case triggers
                elif schoolClosureTrigger in {
                    'Community Case Total', 'Cases per School', 
                    'Cases per K-12 School'
                }: st.info('''
                    Due to limitations in the *Flusim* model, case total 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
            
            # School types and compliance
            schoolClosureTypes = st.segmented_control(
                'Types of School to Close', ('Childcare', 'K-12', 'Tertiary'), 
                selection_mode = 'multi', default = 'K-12', 
                disabled = not useSchoolClosureToggle, 
                key = 'schoolClosureTypes0', help = '''
                    The types of schools that will close under the 
                    effects of this NPI. Multiple school types may be 
                    selected at once, but selecting none is prohibited.

                    ##### Options:
                    - Childcare: Pre-primary childcare facilities.
                    - K-12: Primary and secondary education facilities.
                    - Tertiary: Adult education facilities.
                '''
            )
            st.select_slider(
                'School Closure Compliance (Proportion of Population)', 
                np.linspace(0.0, 1.0, 1001), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                disabled = not useSchoolClosureToggle, 
                key = 'schoolClosureCompliance0', help = '''
                    The proportion of the population that will withdraw 
                    from schools when they are closed in the simulation.
                '''
            )
        


        # Withdrawal Increase
        st.html('<span id = "withdrawalIncreaseTriggerCondition"></span>')
        with st.expander('Withdrawal Increase Properties'):
            st.markdown('''
                These parameters control the properties of 
                interventions that increase the likelihood of infected 
                individuals withdrawing from work/school after becoming 
                symptomatic.
            ''')
            useWithdrawalIncreaseToggle = st.toggle(
                'Enable Withdrawal Increases', value = True, 
                key = 'withdrawalIncreaseToggle0', help = '''
                    Toggle whether or not withdrawal increasing 
                    interventions are implemented in the simulation, 
                    overriding other withdrawal increase parameters.
                '''
            )
            
            # Withdrawal increase triggers
            with st.container(border = True):
                withdrawalIncreaseTrigger = st.selectbox(
                    'Withdrawal Increase Trigger Condition', 
                    key = f'withdrawalIncreaseTrigger0', 
                    options = triggerConditions[:-2], 
                    disabled = not useWithdrawalIncreaseToggle, help = '''
                        The type of condition that must be satisfied 
                        before the rate of withdrawal will start 
                        increasing in the simulation. Additional 
                        options for configuring the exact trigger 
                        condition will appear after selecting one of 
                        these options.

                        ##### Options:
                        - Always: Withdrawal rates will be increased 
                        throughout the entire simulation.
                        - Timed: Withdrawal rates will begin increasing 
                        after a specific number of days have passed in 
                        the simulation, and will revert to normal after 
                        a different number of days.
                        - Community Case Rate: Withdrawal rates will 
                        begin increasing if the rate of newly diagnosed 
                        cases per day exceeds a specific threshold, and 
                        will revert to normal if the rate drops below a 
                        different threshold afterwards. This trigger 
                        rate allows withdrawal rates to increase and 
                        decrease multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Withdrawal rates will 
                        begin increasing after the number of diagnosed 
                        cases in the community exceeds a specific 
                        threshold, and will remain at this elevated 
                        rate for the rest of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if withdrawalIncreaseTrigger == 'Timed':
                    # TODO: Set time-based parameter maximums based on 
                    # number of cycles in simulation
                    withdrawalIncreaseTimeStart = st.slider(
                        'Withdrawal Increase Starting Day', 0, 720, 30, 
                        key = 'withdrawalIncreaseTimeStart0', 
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            The day of the simulation (starting from 
                            Day 0) on which withdrawal rates will start 
                            increasing in the simulation.
                        '''
                    )
                    withdrawalIncreaseTimeDuration = st.slider(
                        'Withdrawal Increase Period Duration (Days)', 
                        0, 720, 56, key = 'withdrawalIncreaseTimeDuration0', 
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            The length (in days) of the period of time 
                            in which withdrawal rates will be increased 
                            in the simulation.
                        '''
                    )
                # Rate triggers
                elif withdrawalIncreaseTrigger == 'Community Case Rate':
                    st.info('''
                        Due to limitations in the *Flusim* model, case 
                        rate thresholds must be defined globally. You 
                        may configure these thresholds using the 
                        "Intervention Trigger Thresholds" parameters at 
                        the bottom of this page (click 
                        [this link](#thresholdTriggerCondition) to go 
                        there directly).
                    ''')
                # Case triggers
                elif withdrawalIncreaseTrigger == 'Community Case Total': 
                    st.info('''
                        Due to limitations in the *Flusim* model, case 
                        total thresholds must be defined globally. You 
                        may configure these thresholds using the 
                        "Intervention Trigger Thresholds" parameters at 
                        the bottom of this page (click 
                        [this link](#thresholdTriggerCondition) to go 
                        there directly).
                    ''')
            
            # Increased withdrawal
            withdrawalIncreaseAdult = st.select_slider(
                'Adult Increased Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                disabled = not useWithdrawalIncreaseToggle, 
                key = 'withdrawalIncreaseAdult0', help = '''
                    The probability of an infected adult withdrawing 
                    from work after becoming symptomatic while a 
                    withdrawal increasing intervention is in effect, 
                    overwriting the normal withdrawal rate.
                '''
            )
            withdrawalIncreaseChild = st.select_slider(
                'Child Increased Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 1.0, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                disabled = not useWithdrawalIncreaseToggle, 
                key = 'withdrawalIncreaseChild0', help = '''
                    The probability of an infected child withdrawing 
                    from school after becoming symptomatic while a 
                    withdrawal increasing intervention is in effect, 
                    overwriting the normal withdrawal rate.
                '''
            )



        # Reduced Workgroup Size
        st.html('<span id = "reducedGroupTriggerCondition"></span>')
        with st.expander('Reduced Group Size Properties'):
            st.markdown('''
                These parameters control the properties of 
                interventions that reduce the size of work groups when 
                in effect. Note that this NPI does not target school 
                groups or other gatherings.
            ''')
            useReducedGroupToggle = st.toggle(
                'Enable Group Size Reductions', value = True, 
                key = 'reducedGroupToggle0', help = '''
                    Toggle whether or not group size reduction 
                    interventions are implemented in the simulation, 
                    overriding other group size reduction parameters.
                '''
            )
            
            # Reduced workgroup triggers
            with st.container(border = True):
                reducedGroupTrigger = st.selectbox(
                    'Reduced Group Size Trigger Condition', 
                    key = f'reducedGroupTrigger0', 
                    options = triggerConditions[:-2], 
                    disabled = not useReducedGroupToggle, help = '''
                        The type of condition that must be satisfied 
                        before the size of work groups will start 
                        decreasing in the simulation. Additional 
                        options for configuring the exact trigger 
                        condition will appear after selecting one of 
                        these options.

                        ##### Options:
                        - Always: Work group sizes will be decreased 
                        throughout the entire simulation.
                        - Timed: Work groups will begin shrinking after 
                        a specific number of days have passed in the 
                        simulation, and will revert to normal size 
                        after a different number of days.
                        - Community Case Rate: Work groups will begin 
                        shrinking if the rate of newly diagnosed cases 
                        per day exceeds a specific threshold, and will 
                        revert to normal size if the rate drops below a 
                        different threshold afterwards. This trigger 
                        rate allows group sizes to increase and 
                        decrease multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Work groups will begin 
                        shrinking after the number of diagnosed cases 
                        in the community exceeds a specific threshold, 
                        and will remain at this reduced size for the 
                        rest of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if reducedGroupTrigger == 'Timed':
                    reducedGroupTimeStart = st.slider(
                        'Reduced Group Size Starting Day', 0, 720, 30, 
                        key = 'reducedGroupTimeStart0', 
                        disabled = not useReducedGroupToggle, help = '''
                            The day of the simulation (starting from 
                            Day 0) on which work groups will start 
                            shrinking in the simulation.
                        '''
                    )
                    reducedGroupTimeDuration = st.slider(
                        'Reduced Group Size Period Duration (Days)', 
                        0, 720, 56, key = 'reducedGroupTimeDuration0', 
                        disabled = not useReducedGroupToggle, help = '''
                            The length (in days) of the period of time 
                            in which work groups will be smaller in the 
                            simulation.
                        '''
                    )
                # Rate triggers
                elif reducedGroupTrigger == 'Community Case Rate': st.info('''
                    Due to limitations in the *Flusim* model, case rate 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
                # Case triggers
                elif reducedGroupTrigger == 'Community Case Total': st.info('''
                    Due to limitations in the *Flusim* model, case total 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
            
            # Reduced group size
            reducedGroupSize = st.slider(
                'Reduced Work Group Size (Number of People)', 0, 25, 5, 
                disabled = not useReducedGroupToggle, 
                key = 'reducedGroupSize0', help = '''
                    The maximum size of work groups while a reduced 
                    group size intervention is in effect, overwriting 
                    the normal maximum.
                '''
            )



        # BCC Reduction
        st.html('<span id = "bccTriggerCondition"></span>')
        with st.expander('Background Contact Count Reduction Properties'):
            st.markdown('''
                These parameters control the properties of 
                interventions that reduce the background contact count 
                (BCC) in the simulation, thus reducing the number of 
                individuals each person interacts with per day outside 
                of simulated locations.
            ''')
            useBCCToggle = st.toggle(
                'Enable BCC Reduction', value = True, 
                key = 'bccToggle0', help = '''
                    Toggle whether or not background contact count 
                    reduction interventions are implemented in the 
                    simulation, overriding other BCC reduction 
                    parameters.
                '''
            )
            
            # BCC triggers
            with st.container(border = True):
                # TODO: Check if school-based triggers are usable for 
                # vaccination and other non-school-closure NPIs
                bccTrigger = st.selectbox(
                    'BCC Reduction Trigger Condition', key = f'bccTrigger0', 
                    options = triggerConditions[:-2], 
                    disabled = not useBCCToggle, help = '''
                        The type of condition that must be satisfied 
                        before background contact count will start 
                        decreasing in the simulation. Additional 
                        options for configuring the exact trigger 
                        condition will appear after selecting one of 
                        these options.

                        ##### Options:
                        - Always: Background contact count will be 
                        reduced throughout the entire simulation.
                        - Timed: Background contact count will be 
                        reduced after a specific number of days have 
                        passed in the simulation, and will revert to 
                        normal levels after a different number of days.
                        - Community Case Rate: Background contact count 
                        will be reduced if the rate of newly diagnosed 
                        cases per day exceeds a specific threshold, and 
                        will revert to normal levels if the rate drops 
                        below a different threshold afterwards. This 
                        trigger rate allows BCC levels to increase and 
                        decrease multiple times if the case rate varies 
                        between the two thresholds.
                        - Community Case Total: Background contact 
                        count will be reduced after the number of 
                        diagnosed cases in the community exceeds a 
                        specific threshold, and will remain at this 
                        reduced level for the rest of the simulation.
                    '''
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if bccTrigger == 'Timed':
                    # TODO: Set time-based parameter maximums based on 
                    # number of cycles in simulation
                    bccTimeStart = st.slider(
                        'BCC Reduction Starting Day', 0, 720, 30, 
                        key = 'bccTimeStart0', disabled = not useBCCToggle, 
                        help = '''
                            The day of the simulation (starting from 
                            Day 0) on which background contact count 
                            will be reduced in the simulation.
                        '''
                    )
                    bccTimeDuration = st.slider(
                        'BCC Reduction Period Duration (Days)', 0, 720, 56, 
                        key = 'bccTimeDuration0', 
                        disabled = not useBCCToggle, help = '''
                            The length (in days) of the period of time 
                            in which background contact count will be 
                            reduced in the simulation.
                        '''
                    )
                # Rate triggers
                elif bccTrigger == 'Community Case Rate': st.info('''
                    Due to limitations in the *Flusim* model, case rate 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
                # Case triggers
                elif vaccineTrigger == 'Community Case Total': st.info('''
                    Due to limitations in the *Flusim* model, case total 
                    thresholds must be defined globally. You may 
                    configure these thresholds using the 
                    "Intervention Trigger Thresholds" parameters at the 
                    bottom of this page (click 
                    [this link](#thresholdTriggerCondition) to go there 
                    directly).
                ''')
            
            # Reduced BCC rate
            bccReducedRate = st.slider(
                'BCC Reduced Rate (Average Number of Interactions per Person)',
                0.0, 5.0, 0.2, disabled = not useBCCToggle,
                key = 'bccReducedRate0', help = '''
                    The number of other people each individual will 
                    interact with in the background phase of the 
                    simulation (emulating interactions outside of 
                    simulated locations) while a BCC reduction 
                    intervention is in effect, overwriting the normal 
                    BCC rate.
                '''
            )
    




    # Trigger Thresholds
    st.html('<span id = "thresholdTriggerCondition"></span>')
    st.subheader('Intervention Trigger Thresholds')
    with st.expander('Trigger Thresholds'):
        st.markdown('''
            These parameters affect the threshold values that must be 
            reached for vaccination or non-pharmaceutical interventions 
            to be triggered in the simulation. Due to limitations in 
            the *Flusim* simulation model, all interventions that are 
            set to use case rates or totals as their trigger condition 
            will use these thresholds; setting individual 
            thresholds for each intervention is not possible. 
            Parameters will only appear here if at least one 
            intervention is set to use a trigger condition that 
            requires them.
        ''')

        # Display values based on what is used by the triggers
        triggerConditions = [
            vaccineTrigger, schoolClosureTrigger, 
            withdrawalIncreaseTrigger, reducedGroupTrigger, bccTrigger
        ]
        rateConditions = [
            index for index, condition in enumerate(triggerConditions) 
            if condition == 'Community Case Rate'
        ]
        totalConditions = [
            index for index, condition in enumerate(triggerConditions) 
            if condition in {
                'Community Case Total', 
                'Cases per School', 'Cases per K-12 School'
            }
        ]
        if not rateConditions and not totalConditions: st.info('''
            No interventions are currently using case rates or totals 
            for their trigger conditions. Parameters for configuring 
            the trigger thresholds will appear here if you select any 
            value other than "Always" and "Timed" for an intervention's 
            trigger condition.
        ''')
        else:
            # Case rates
            if rateConditions:
                # Display links to NPIs that use rates
                st.subheader('Case Rate Trigger Thresholds')
                st.markdown(
                    f'''
                        The following interventions currently use the 
                        rate thresholds defined below. Click on the 
                        names to go to the drop-down container with the 
                        trigger condition parameters for that 
                        intervention.\n\n
                    ''' + (
                        f'\n- [Class Dismissal](#generalTriggerCondition)' 
                        if classDismissal else ''
                    ) + ''.join(
                        f'\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)' 
                        for i in rateConditions
                    )
                )

                # Set rate thresholds
                rateStartThreshold = st.slider(
                    'Start Trigger Threshold Rate (Cases per Day)', 0, 
                    100, 10, key = 'rateStartThreshold0', help = '''
                        Any interventions set to trigger using the 
                        "Community Case Rate" condition will begin 
                        taking effect in the simulation once the number 
                        of newly diagnosed cases per day exceeds this 
                        value.
                    '''
                )
                rateRelaxThreshold = st.slider(
                    'Relaxation Trigger Threshold Rate (Cases per Day)', 0, 
                    100, 5, key = 'rateRelaxThreshold0', help = '''
                        Any active interventions set to trigger using 
                        the "Community Case Rate" condition will stop 
                        taking effect in the simulation once the number 
                        of newly diagnosed cases per day goes below 
                        this value.
                    '''
                )
            
            # Case totals
            if totalConditions:
                # Display links to NPIs that use totals
                st.subheader('Case Total Trigger Thresholds')
                st.markdown(
                    f'''
                        The following interventions currently use the 
                        case threshold defined below. Click on the 
                        names to go to the drop-down container with the 
                        trigger condition parameters for that 
                        intervention.\n\n
                    ''' + ''.join(
                        f'\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)' 
                        for i in totalConditions
                    )
                )

                # Set total threshold
                caseTotalThreshold = st.number_input(
                    'Start Trigger Case Threshold (Total Community Cases)', 
                    0, 300000, 1000, key = 'caseTotalThreshold0', 
                    placeholder = 'Enter a whole number of cases', help = '''
                        Any interventions set to trigger using the 
                        "Community Case Total", "Cases per School", or 
                        "Cases per K-12 School" conditions will begin 
                        taking effect in the simulation once the total 
                        number of diagnosed cases in the community (for 
                        "Community Case Total") or in each individual 
                        school (for "Cases per School" and "Cases per 
                        K-12 School") exceeds this value.
                    '''
                )