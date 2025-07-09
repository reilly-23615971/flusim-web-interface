# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
# import streamlit_sortables as sts
from ClientResources.InterfaceFunctions import (
    toggle, getRemainingAgeGroups, addFormRow, deleteFormRow
)
from ClientResources.SharedResources import (
    ageCategories, ordinals, triggerConditions
)

# Logging
baselineLog = logging.getLogger(__name__)

# Initialise session variables
sessionParameters = {
    'vacAgeRowCount0': 0,
    'primaryDoseCount0': 2,
    'boostAgeRowCount0': 0, 
    'boosterRemainingAgeGroups0': list(dict.fromkeys(ageCategories))
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.setdefault(
        parameter, default
    )

vaccineRowCount = st.session_state['vacAgeRowCount0']
primaryRowCount = st.session_state['primaryDoseCount0']
boosterRowCount = st.session_state['boostAgeRowCount0']

# Ensure age selections only give possible parameters
# Dictionary format: 'remaining groups variable': (
#   'number of rows variable', 'group row variable prefix'
# )
ageGroupSets = {
    'vaccineRemainingAgeGroups0': (
        'vacAgeRowCount0', 'vacAgeGroup0-'
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

# TODO: Warn for nonsensical conditions like reduced BCC > regular BCC
# TODO: Equalise rate/case condition triggers
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
    #TODO: Generic trigger parameters?

    # Vaccination
    vaccineContainer = st.container()
    with vaccineContainer:
        st.subheader('Vaccination Parameters')
        useVaccinesToggle = st.toggle(
            'Enable Vaccines in Simulation', value = True, 
            key = 'vaccineToggle0', help = '''
                Toggle whether or not individuals in the simulation 
                will be vaccinated against the disease. Overrides all 
                other vaccine-related parameters.
            '''
        )

        # General Vaccination Policy Parameters
        vaccinePolicyContainer = st.expander('Vaccination Policies')
        with vaccinePolicyContainer:
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control the rollout of vaccines in the 
                simulation, with parameters such as what triggers the 
                introduction of vaccines and how often individuals are 
                vaccinated for the first time.
            ''')

            # Policy parameters
            # TODO: Change population-based fields to have the 
            # population of the current community as a maximum
            unusedPriorityParameter = """
                # TODO: VACCINATION PRIORITY (needs sortables package)
                # Lacks disabling feature
                vaccinePriorityHelp = st.markdown('', help = '''
                    Individuals in the categories at the start of this list 
                    will receive vaccine doses before individuals in the 
                    categories at the end.
                ''')
                vaccinePriority = sts.sort_items(
                    [
                        'Elderly', 'Healthcare Workers', 
                        'Essential Workers', 'Others'
                    ],
                    header = 'Vaccination Priority', key = 'vaccinePriority0'
                )
            """
            vaccineTriggerContainer = st.container(border = (
                st.session_state.get('vaccineTrigger0', 'Always') != 'Always'
            ))
            with vaccineTriggerContainer:
                # TODO: Check if school-based triggers are usable for 
                # vaccination and other non-school-closure NPIs
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
                        'Vaccination Period Duration', 0, 720, 56, 
                        key = 'vaccineTimeDuration0', 
                        disabled = not useVaccinesToggle, help = '''
                            The length (in days) of the period of time 
                            in which vaccinations will be administered 
                            in the simulation.
                        '''
                    )
                # Rate triggers
                elif vaccineTrigger == 'Community Case Rate':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the starting and ending rates defined 
                        for vaccinations will be shared with any NPIs 
                        that use community case rates as their trigger 
                        condition.
                    ''')
                    vaccineRateStart = st.slider(
                        'Vaccination Start Trigger Rate', 0, 100, 10, 
                        key = 'vaccineRateStart0', 
                        disabled = not useVaccinesToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day exceeds this value, vaccinations will 
                            start being administered in the simulation.
                        '''
                    )
                    vaccineRateStop = st.slider(
                        'Vaccination Relaxation Trigger Rate', 0, 100, 
                        5, key = 'vaccineRateStop0', 
                        disabled = not useVaccinesToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day is below this value while vaccinations 
                            are being administered in the simulation, 
                            the vaccination program will stop.
                        '''
                    )
                # Case triggers
                elif vaccineTrigger == 'Community Case Total':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the community case threshold defined for 
                        vaccinations will be shared with any NPIs that 
                        use community case totals as their trigger 
                        condition.
                    ''')
                    vaccineTotalStart = st.number_input(
                        'Vaccination Start Trigger Total', 0, 
                        300000, 1000, key = 'vaccineTotalStart0', 
                        placeholder = 'Enter a whole number of cases',
                        disabled = not useVaccinesToggle, help = '''
                            If the total number of diagnosed cases in 
                            the community exceeds this value, 
                            vaccinations will start being administered 
                            in the simulation.
                        '''
                    )
            # Other vaccine program parameters
            initialDoseReserve = st.number_input(
                'Initial Number of Available Doses', 
                0, 300000, key = 'initialDoseReserve0', 
                placeholder = 'Enter a whole number of doses',
                disabled = not useVaccinesToggle, help = '''
                    The number of vaccine doses that will be available 
                    to administer to individuals at the beginning of 
                    the simulation.
                '''
            )
            firstDoseRate = st.number_input(
                'Daily Vaccination Rate (First Dose)', 
                0, 300000, 300, key = 'firstDoseRate0', 
                placeholder = 'Enter a whole number of people',
                disabled = not useVaccinesToggle, help = '''
                    The number of unvaccinated individuals who will 
                    receive the first dose of the vaccine each day, 
                    assuming there are enough doses available.
                '''
            )
            initialVaccinated = st.slider(
                'Initial Vaccinated Proportion', 0.0, 1.0, 0.0,
                disabled = not useVaccinesToggle, key = 'initialVaccinated0', 
                help = '''
                    The proportion of the population that will already 
                    be vaccinated against the disease at the beginning 
                    of the simulation.
                '''
            )
            targetEfficacy = st.slider(
                'Target Vaccinated Proportion', 0.0, 1.0, 0.8,
                disabled = not useVaccinesToggle, key = 'targetEfficacy0', 
            help = '''
                    The proportion of the population that will be 
                    targeted by the vaccine program in the simulation. 
                    The actual proportion of the population that is 
                    vaccinated may be lower if there are an 
                    insufficient number of doses available.
                '''
            )

            # Modifiable-length field for age-specific efficacy
            st.markdown('### Age-Specific Vaccinated Proportion Parameters')
            vacAgeProportionContainer = st.container()
            for i in range(vaccineRowCount):
                (
                    vacAgeGroupColumn, vacAgeInitialColumn, 
                    vacAgeTargetColumn, vacAgeRemoveColumn
                ) = vacAgeProportionContainer.columns(
                    (0.25, 0.275, 0.275, 0.2)
                )
                # Age group column
                with vacAgeGroupColumn: vacAgeGroups = st.selectbox(
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
                # Standard efficacy column
                with vacAgeInitialColumn: vacAgeInitial = st.slider(
                    'Initial Proportion', 0.0, 1.0, 0.0,
                    disabled = not useVaccinesToggle, 
                    key = f'vacAgeInitial0-{i}', help = '''
                        The proportion of individuals in this age group 
                        that will already be vaccinated against the 
                        disease at the beginning of the simulation.
                    '''
                )
                # Waned efficacy column
                with vacAgeTargetColumn: vacAgeTarget = st.slider(
                    'Target Proportion', 0.0, 1.0, 0.8,
                    disabled = not useVaccinesToggle, 
                    key = f'vacAgeTarget0-{i}', help = '''
                        The proportion of individuals in this age group 
                        that will be targeted by the vaccine program in 
                        the simulation. The actual proportion of 
                        individuals that are vaccinated may be lower if 
                        there are an insufficient number of doses 
                        available.
                    '''
                )
                # Delete button column
                with vacAgeRemoveColumn: vacAgeRemoveButtons = st.button(
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
            vacAgeAddButton = vacAgeProportionContainer.button(
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
                        targetEfficacy,
                    }
                ), 
                disabled = (
                    not useVaccinesToggle or not vaccineRowCount < 10
                ),
                help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have unique booster 
                    vaccine efficacy values.
                ''' if vaccineRowCount <= 9 else '''
                    All age groups have been given unique booster 
                    vaccine efficacy values.
                '''
            )



        # Primary Vaccine Parameters
        primaryContainer = st.expander('Primary Vaccine Properties')
        with primaryContainer:
            # Describe primary vaccines
            st.markdown('''
                These parameters control the properties of the initial 
                program of vaccines that will be administered to 
                individuals within the simulation. Each vaccine in the 
                program can have its own efficacy values set, since in 
                many cases multiple doses are required to achieve 
                maximum immunity to the disease.
            ''')

            # Universal primary parameters
            primaryDoseCount = st.slider(
                'Number of Primary Doses', 1, 5, 2, key = 'primaryDoseCount0',
                disabled = not useVaccinesToggle, help = '''
                    The number of times each individual in the 
                    simulation will be administered a vaccine in the 
                    initial vaccine program. Note that modifying this 
                    value will affect the individual dose parameters 
                    below.
                '''
            )
            primaryDelay = st.slider(
                'Time Between Vaccine Doses (Days)', 1, 180, 56,
                disabled = not useVaccinesToggle, key = 'primaryDelay0', 
                help = '''
                    The number of days after an individual receives one 
                    primary vaccine dose before they are able to 
                    receive another.
                '''
            )
            primaryDuration = st.slider(
                'Vaccine Effective Duration', 1, 180, 30, 
                disabled = not useVaccinesToggle, key = 'primaryDuration0', 
                help = '''
                    The number of days after an individual receives a 
                    primary vaccine dose before the immunity conferred 
                    by this vaccine begins to diminish.
                '''
            )
            # TODO: See if better methods of representing waning rate 
            # (e.g. vaccine effectiveness dropoff) are feasible
            primaryWaningRate = st.slider(
                'Vaccine Immunity Waning Rate', 0.0, 0.02, 0.005, 
                step = 0.0005, format = '%0.4g', 
                disabled = not useVaccinesToggle, key = 'primaryWaningRate0', 
                help = '''
                    The probability that an individual will lose the 
                    immunity conferred by a primary vaccine dose each 
                    day after the vaccine's duration has passed.
                '''
            )

            # Modifiable-length field for each primary dose
            st.markdown('''
                ### Individual Dose Efficacies
                
                Modify the "Number of Primary Doses" parameter to 
                change how many doses can be configured here.
            ''')
            for i in range(primaryDoseCount):
                doseEfficacyContainer = st.container(border = True)
                doseEfficacyContainer.markdown(
                    f'#### {ordinals[i+1]} Primary Dose'
                )
                doseBaseEfficacy = doseEfficacyContainer.slider(
                    'Dose Efficacy', 0.0, 1.0, 0.5, 
                    disabled = not useVaccinesToggle, 
                    key = f'primaryBaseEfficacy0-{i}', help = '''
                        The efficacy of this vaccine dose, represented 
                        as the proportion of individuals that have 
                        recently received the dose who will not become 
                        infected when exposed to the disease.
                    '''
                )
                doseWanedEfficacy = doseEfficacyContainer.slider(
                    'Dose Waned Efficacy', 0.0, 1.0, 0.0,
                    disabled = not useVaccinesToggle, 
                    key = f'primaryWanedEfficacy0-{i}', help = '''
                        The efficacy of this vaccine dose when 
                        the immunity conferred by it has diminished but 
                        the next dose has not been received, 
                        represented as the proportion of individuals 
                        with waning immunity who will not become 
                        infected when exposed to the disease.
                    '''
                )
                # Age-Specific Primary Efficacy Field
                doseEfficacyContainer.markdown(
                    '##### Age-Specific Efficacy Rates'
                )
                primAgeEfficacyContainer = doseEfficacyContainer.container()
                for j in range(primaryAgeRowCounts[i]):
                    (
                        primAgeGroupColumn, primAgeEfficacyColumn, 
                        primAgeWanedColumn, primAgeRemoveColumn
                    ) = primAgeEfficacyContainer.columns(
                        (0.25, 0.275, 0.275, 0.2)
                    )
                    # Age group column
                    with primAgeGroupColumn: primAgeGroups = st.selectbox(
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
                            vaccine efficacy values defined for it, 
                            overriding the base efficacy value for this 
                            vaccine dose.

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
                    with primAgeEfficacyColumn: primAgeEfficacies = st.slider(
                        'Dose Efficacy', 0.0, 1.0, 0.9, 
                        disabled = not useVaccinesToggle, 
                        key = f'primAgeEfficacy0-{i}-{j}', help = '''
                            The efficacy of this vaccine dose for this 
                            age group, represented as the proportion of 
                            individuals in this age group that have 
                            recently received the dose who will not 
                            become infected when exposed to the disease.
                        '''
                    )
                    # Waned efficacy column
                    with primAgeWanedColumn: primAgeWanedEfficacies = st.slider(
                        'Dose Waned Efficacy', 0.0, 1.0, 0.6,
                        disabled = not useVaccinesToggle, 
                        key = f'primAgeWanedEfficacy0-{i}-{j}', help = '''
                            The efficacy of this vaccine dose for this 
                            age group when the immunity conferred by it 
                            has diminished but the next dose has not 
                            been received, represented as the 
                            proportion of individuals in this age group 
                            with waning immunity who will not become 
                            infected when exposed to the disease.
                        '''
                    )
                    # Delete button column
                    with primAgeRemoveColumn: primAgeRemoveButtons = st.button(
                        label = 'Remove Age Group', icon = ':material/delete:',
                        key = f'primAgeRemove0-{i}-{j}', 
                        on_click = deleteFormRow, args = (
                            i, f'primAgeRowCount0-{i}', {
                                f'primAgeGroup0-{i}-', 
                                f'primAgeEfficacy0-{i}-', 
                                f'primAgeWanedEfficacy0-{i}-'
                            }
                        ),
                        disabled = not useVaccinesToggle, help = '''
                            Remove this row of the form and remove these 
                            age-specific vaccine dose efficacy values 
                            from the simulation.
                        '''
                    )
                # Button to add another row for additional age specification
                primAgeAddButton = primAgeEfficacyContainer.button(
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
                            doseBaseEfficacy,
                            ((
                                f'primAgeWanedEfficacy0-{i}-'
                                f'{primaryAgeRowCounts[i]}'
                            )): doseWanedEfficacy,
                        }
                    ), 
                    disabled = (
                        not useVaccinesToggle 
                        or not primaryAgeRowCounts[i] < 10
                    ),
                    help = '''
                        Add another row to this form, where you can 
                        select an additional age group to have unique 
                        vaccine dose efficacy values.
                    ''' if primaryAgeRowCounts[i] <= 9 else '''
                        All age groups have been given unique efficacy 
                        values for this vaccine dose.
                    '''
                )



        # Booster Parameters
        boosterContainer = st.expander('Booster Vaccine Properties')
        with boosterContainer:
            # Describe booster vaccines
            st.markdown('''
                These parameters control the properties of booster 
                vaccines, additional doses of a vaccine only 
                administered to individuals who have received all 
                primary vaccines. All doses of booster vaccines have 
                the same efficacy values. Booster vaccines are 
                primarily used to preserve an individual's immunity to 
                the disease as it begins to wane over time.
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
            boosterBaseEfficacy = st.slider(
                'Booster Efficacy', 0.0, 1.0, 0.9,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterBaseEfficacy0', help = '''
                    The efficacy of each booster vaccine, represented 
                    as the proportion of individuals that have recently 
                    received the booster who will not become infected 
                    when exposed to the disease.
                '''
            )
            boosterDoseCount = st.slider(
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
            boosterDuration = st.slider(
                'Booster Effective Duration', 1, 180, 60,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterDuration0', help = '''
                    The number of days after an individual receives a 
                    booster vaccine dose before the immunity conferred 
                    by this vaccine begins to diminish.
                '''
            )
            boosterWanedEfficacy = st.slider(
                'Booster Waned Efficacy', 0.0, 1.0, 0.6,
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterWanedEfficacy0', help = '''
                    The efficacy of the overall vaccine program once 
                    the immunity conferred by booster vaccines has 
                    diminished, represented as the proportion of 
                    individuals with waning booster immunity who will 
                    not become infected when exposed to the disease.
                '''
            )
            # TODO: See if better methods of representing waning rate 
            # (e.g. vaccine effectiveness dropoff) are feasible
            boosterWaningRate = st.slider(
                'Booster Immunity Waning Rate', 0.0, 0.02, 0.005, 
                step = 0.0005, format = '%0.4g', 
                disabled = not useVaccinesToggle or not useBoostersToggle, 
                key = 'boosterWaningRate0', help = '''
                    The probability that an individual will lose the 
                    immunity conferred by a booster vaccine each day 
                    after the vaccine's duration has passed.
                '''
            )

            # Modifiable-length field for age-specific efficacy
            st.markdown('### Age-Specific Efficacy Rates')
            boostAgeEfficacyContainer = st.container()
            for i in range(boosterRowCount):
                (
                    boostAgeGroupColumn, boostAgeEfficacyColumn, 
                    boostAgeWanedColumn, boostAgeRemoveColumn
                ) = boostAgeEfficacyContainer.columns(
                    (0.25, 0.275, 0.275, 0.2)
                )
                # Age group column
                with boostAgeGroupColumn: boostAgeGroups = st.selectbox(
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
                with boostAgeEfficacyColumn: boostAgeEfficacies = st.slider(
                    'Booster Efficacy', 0.0, 1.0, 0.9,
                    disabled = not useVaccinesToggle or not useBoostersToggle, 
                    key = f'boostAgeEfficacy0-{i}', help = '''
                        The efficacy of each booster vaccine for this 
                        age group, represented as the proportion of 
                        individuals in this age group that have 
                        recently received the booster who will not 
                        become infected when exposed to the disease.
                    '''
                )
                # Waned efficacy column
                with boostAgeWanedColumn: boostAgeWanedEfficacies = st.slider(
                    'Booster Waned Efficacy', 0.0, 1.0, 0.6,
                    disabled = not useVaccinesToggle or not useBoostersToggle, 
                    key = f'boostAgeWanedEfficacy0-{i}', help = '''
                        The efficacy of the overall vaccine program for 
                        this age group once the immunity conferred by 
                        booster vaccines has diminished, represented as 
                        the proportion of individuals in this age group 
                        with waning booster immunity who will not 
                        become infected when exposed to the disease.
                    '''
                )
                # Delete button column
                with boostAgeRemoveColumn: boostAgeRemoveButtons = st.button(
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
            boostAgeAddButton = boostAgeEfficacyContainer.button(
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
    npiContainer = st.container()
    with npiContainer:
        st.subheader('NPI Parameters')
        # General NPIs
        generalNPIContainer = st.expander('General NPI Properties')
        with generalNPIContainer:
            st.markdown('''
                These parameters control the implementation of simpler 
                NPI techniques, including social distancing, case 
                isolation and class dismissal.
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
            socialDistancingCompliance = st.slider(
                'Social Distancing Compliance', 0.0, 1.0, 0.9,
                disabled = not useSocialDistancingToggle, 
                key = 'socialDistancingCompliance0', help = '''
                    The proportion of the population that will comply 
                    with social distancing interventions in the 
                    simulation.
                '''
            )
            # TODO: Age-based social distancing probabilities

            # Case Isolation
            caseIsolation = st.toggle(
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
            st.info('''
                Note: Due to limitations in the *Flusim* 
                model, the starting and ending rates defined 
                for class dismissal will be shared with any 
                other interventions that use community case 
                rates as their trigger condition.
            ''')
            classDismissalStart = st.slider(
                'Class Dismissal Start Trigger Rate', 0, 100, 10, 
                disabled = not classDismissal, key = 'classDismissalStart0', 
                help = '''
                    If the number of newly diagnosed cases per day 
                    exceeds this value, classes will start being 
                    dismissed in the simulation.
                '''
            )
            classDismissalStop = st.slider(
                'Class Dismissal Relaxation Trigger Rate', 0, 100, 5, 
                disabled = not classDismissal, key = 'classDismissalStop0', 
                help = '''
                    If the number of newly diagnosed cases per day is 
                    below this value while classes are being dismissed 
                    in the simulation, the dismissals will stop.
                '''
            )
            # Diagnosis Delay will go in environment



        # School Closure
        schoolClosureContainer = st.expander('School Closure Properties')
        with schoolClosureContainer:
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
            schoolClosureTriggerContainer = st.container(border = (
                st.session_state.get('schoolClosureTrigger0', 'Always') 
                != 'Always'
            ))
            with schoolClosureTriggerContainer:
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
                        'School Closure Period Duration', 0, 720, 56, 
                        key = 'schoolClosureTimeDuration0', 
                        disabled = not useSchoolClosureToggle, help = '''
                            The length (in days) of the period of time 
                            in which schools will be closed in the 
                            simulation.
                        '''
                    )
                # Rate triggers
                elif schoolClosureTrigger == 'Community Case Rate':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the starting and ending rates defined 
                        for school closures will be shared with any 
                        other interventions that use community case 
                        rates as their trigger condition.
                    ''')
                    schoolClosureRateStart = st.slider(
                        'School Closure Start Trigger Rate', 0, 100, 10, 
                        key = 'schoolClosureRateStart0', 
                        disabled = not useSchoolClosureToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day exceeds this value, schools will start 
                            closing in the simulation.
                        '''
                    )
                    schoolClosureRateStop = st.slider(
                        'School Closure Relaxation Trigger Rate', 0, 100, 5, 
                        key = 'schoolClosureRateStop0', 
                        disabled = not useSchoolClosureToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day is below this value while schools 
                            are being closed in the simulation, the 
                            schools will reopen.
                        '''
                    )
                # Case triggers
                elif schoolClosureTrigger in {
                    'Community Case Total', 'Cases per School', 
                    'Cases per K-12 School'
                }:
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the community case threshold defined for 
                        school closures will be shared with any other 
                        interventions that use community case totals as 
                        their trigger condition.
                    ''')
                    schoolClosureTotalStart = st.number_input(
                        'School Closure Start Trigger Total', 0, 300000, 1000, 
                        key = 'schoolClosureTotalStart0', 
                        placeholder = 'Enter a whole number of cases',
                        disabled = not useSchoolClosureToggle, help = '''
                            If the total number of diagnosed cases in 
                            the community exceeds this value, schools 
                            will start closing in the simulation.
                        '''
                    )
            
            # School types and compliance
            schoolClosureTypes = st.multiselect(
                'Types of School to Close', ('Childcare', 'K-12', 'Tertiary'), 
                'K-12', key = 'schoolClosureTypes0', 
                disabled = not useSchoolClosureToggle, 
                placeholder = 'Choose any number of school types', help = '''
                    The types of schools that will close under the 
                    effects of this NPI.

                    ##### Options:
                    - Childcare: Pre-primary childcare facilities.
                    - K-12: Primary and secondary education facilities.
                    - Tertiary: Adult education facilities.
                '''
            )
            schoolClosureCompliance = st.slider(
                'School Closure Compliance', 0.0, 1.0, 0.9,
                disabled = not useSchoolClosureToggle, 
                key = 'schoolClosureCompliance0', help = '''
                    The proportion of the population that will withdraw 
                    from schools when they are closed in the simulation.
                '''
            )
        


        # Withdrawal Increase
        withdrawalIncreaseContainer = st.expander('Withdrawal Increase Properties')
        with withdrawalIncreaseContainer:
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
            withdrawalIncreaseTriggerContainer = st.container(border = (
                st.session_state.get('withdrawalIncreaseTrigger0', 'Always') 
                != 'Always'
            ))
            with withdrawalIncreaseTriggerContainer:
                # TODO: Check if school-based triggers are usable for 
                # vaccination and other non-school-closure NPIs
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
                        'Withdrawal Increase Period Duration', 0, 720, 56, 
                        key = 'withdrawalIncreaseTimeDuration0', 
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            The length (in days) of the period of time 
                            in which withdrawal rates will be increased 
                            in the simulation.
                        '''
                    )
                # Rate triggers
                elif withdrawalIncreaseTrigger == 'Community Case Rate':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the starting and ending rates defined 
                        for withdrawal increases will be shared with 
                        any other interventions that use community case 
                        rates as their trigger condition.
                    ''')
                    withdrawalIncreaseRateStart = st.slider(
                        'Withdrawal Increase Start Trigger Rate', 0, 100, 10, 
                        key = 'withdrawalIncreaseRateStart0', 
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day exceeds this value, withdrawal rates will 
                            start increasing in the simulation.
                        '''
                    )
                    withdrawalIncreaseRateStop = st.slider(
                        'Withdrawal Increase Relaxation Trigger Rate', 0, 100, 
                        5, key = 'withdrawalIncreaseRateStop0', 
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day is below this value while withdrawal 
                            rates are increased in the simulation, the 
                            withdrawal rates will revert to normal.
                        '''
                    )
                # Case triggers
                elif withdrawalIncreaseTrigger == 'Community Case Total':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the community case threshold defined for 
                        withdrawal increases will be shared with any 
                        other interventions that use community case 
                        totals as their trigger condition.
                    ''')
                    withdrawalIncreaseTotalStart = st.number_input(
                        'Withdrawal Increase Start Trigger Total', 0, 300000, 
                        1000, key = 'withdrawalIncreaseTotalStart0', 
                        placeholder = 'Enter a whole number of cases',
                        disabled = not useWithdrawalIncreaseToggle, help = '''
                            If the total number of diagnosed cases in 
                            the community exceeds this value, 
                            withdrawal rates will start increasing in 
                            the simulation.
                        '''
                    )
            
            # Increased withdrawal
            withdrawalIncreaseAdult = st.slider(
                'Adult Increased Withdrawal Rate', 0.0, 1.0, 0.9,
                disabled = not useWithdrawalIncreaseToggle, 
                key = 'withdrawalIncreaseAdult0', help = '''
                    The probability of an infected adult withdrawing 
                    from work after becoming symptomatic while a 
                    withdrawal increasing intervention is in effect, 
                    overwriting the normal withdrawal rate.
                '''
            )
            withdrawalIncreaseChild = st.slider(
                'Child Increased Withdrawal Rate', 0.0, 1.0, 1.0,
                disabled = not useWithdrawalIncreaseToggle, 
                key = 'withdrawalIncreaseChild0', help = '''
                    The probability of an infected child withdrawing 
                    from school after becoming symptomatic while a 
                    withdrawal increasing intervention is in effect, 
                    overwriting the normal withdrawal rate.
                '''
            )



        # Reduced Workgroup Size
        reducedGroupContainer = st.expander('Reduced Group Size Properties')
        with reducedGroupContainer:
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
            reducedGroupTriggerContainer = st.container(border = (
                st.session_state.get('reducedGroupTrigger0', 'Always') 
                != 'Always'
            ))
            with reducedGroupTriggerContainer:
                # TODO: Check if school-based triggers are usable for 
                # vaccination and other non-school-closure NPIs
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
                    # TODO: Set time-based parameter maximums based on 
                    # number of cycles in simulation
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
                        'Reduced Group Size Period Duration', 0, 720, 56, 
                        key = 'reducedGroupTimeDuration0', 
                        disabled = not useReducedGroupToggle, help = '''
                            The length (in days) of the period of time 
                            in which work groups will be smaller in the 
                            simulation.
                        '''
                    )
                # Rate triggers
                elif reducedGroupTrigger == 'Community Case Rate':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the starting and ending rates defined 
                        for reduced group sizes will be shared with 
                        any other interventions that use community case 
                        rates as their trigger condition.
                    ''')
                    reducedGroupRateStart = st.slider(
                        'Reduced Group Size Start Trigger Rate', 0, 100, 10, 
                        key = 'reducedGroupRateStart0', 
                        disabled = not useReducedGroupToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day exceeds this value, work groups will 
                            start shrinking in the simulation.
                        '''
                    )
                    reducedGroupRateStop = st.slider(
                        'Reduced Group Size Relaxation Trigger Rate', 0, 100, 
                        5, key = 'reducedGroupRateStop0', 
                        disabled = not useReducedGroupToggle, help = '''
                            If the number of newly diagnosed cases per 
                            day is below this value while work group 
                            sizes are reduced in the simulation, the 
                            work groups will revert to normal.
                        '''
                    )
                # Case triggers
                elif reducedGroupTrigger == 'Community Case Total':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the community case threshold defined for 
                        reduced group sizes will be shared with any 
                        other interventions that use community case 
                        totals as their trigger condition.
                    ''')
                    reducedGroupTotalStart = st.number_input(
                        'Reduced Group Size Start Trigger Total', 0, 300000, 
                        1000, key = 'reducedGroupTotalStart0', 
                        placeholder = 'Enter a whole number of cases',
                        disabled = not useReducedGroupToggle, help = '''
                            If the total number of diagnosed cases in 
                            the community exceeds this value, work 
                            groups will start shrinking in the 
                            simulation.
                        '''
                    )
            
            # Reduced group size
            reducedGroupSize = st.slider(
                'Reduced Work Group Size', 0, 25, 5, 
                disabled = not useReducedGroupToggle, 
                key = 'reducedGroupSize0', help = '''
                    The maximum size of work groups while a reduced 
                    group size intervention is in effect, overwriting 
                    the normal maximum.
                '''
            )



        # Workgroup Nonattendance
        


        # BCC Reduction
        bccContainer = st.expander('BCC Reduction Properties')
        with bccContainer:
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
            bccTriggerContainer = st.container(border = (
                st.session_state.get('bccTrigger0', 'Always') != 'Always'
            ))
            with bccTriggerContainer:
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
                        'BCC Reduction Period Duration', 0, 720, 56, 
                        key = 'bccTimeDuration0', 
                        disabled = not useBCCToggle, help = '''
                            The length (in days) of the period of time 
                            in which background contact count will be 
                            reduced in the simulation.
                        '''
                    )
                # Rate triggers
                elif bccTrigger == 'Community Case Rate':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the starting and ending rates defined 
                        for BCC reduction will be shared with any other 
                        interventions that use community case rates as 
                        their trigger condition.
                    ''')
                    bccRateStart = st.slider(
                        'BCC Reduction Start Trigger Rate', 0, 100, 10, 
                        key = 'bccRateStart0', disabled = not useBCCToggle, 
                        help = '''
                            If the number of newly diagnosed cases per 
                            day exceeds this value, background contact 
                            count will be reduced in the simulation.
                        '''
                    )
                    bccRateStop = st.slider(
                        'BCC Reduction Relaxation Trigger Rate', 0, 100, 5, 
                        key = 'bccRateStop0', disabled = not useBCCToggle, 
                        help = '''
                            If the number of newly diagnosed cases per 
                            day is below this value while background 
                            contact count is reduced in the simulation, 
                            the BCC level will revert to normal.
                        '''
                    )
                # Case triggers
                elif bccTrigger == 'Community Case Total':
                    st.info('''
                        Note: Due to limitations in the *Flusim* 
                        model, the community case threshold defined for 
                        BCC reduction will be shared with any 
                        other interventions that use community case 
                        totals as their trigger condition.
                    ''')
                    bccTotalStart = st.number_input(
                        'BCC Reduction Start Trigger Total', 0, 300000, 1000, 
                        key = 'bccTotalStart0', 
                        placeholder = 'Enter a whole number of cases',
                        disabled = not useBCCToggle, help = '''
                            If the total number of diagnosed cases in 
                            the community exceeds this value, 
                            background contact count will be reduced in 
                            the simulation.
                        '''
                    )
            
            # Reduced BCC rate
            bccReducedRate = st.slider(
                'BCC Reduced Rate', 0.0, 5.0, 0.2, disabled = not useBCCToggle,
                key = 'bccReducedRate0', help = '''
                    The number of other individuals each individual 
                    will encounter in the background phase of the 
                    simulation (emulating interactions outside of 
                    simulated locations) while a BCC reduction 
                    intervention is in effect, overwriting the normal 
                    BCC rate.
                '''
            )