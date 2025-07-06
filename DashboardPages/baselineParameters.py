# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st
from ClientResources.InterfaceFunctions import (
    toggle, getRemainingAgeGroups, addFormRow, deleteFormRow
)
from ClientResources.SharedResources import ageCategories, ordinals

# Logging
baselineLog = logging.getLogger(__name__)

# Initialise session variables
sessionParameters = {
    'boostAgeRowCount0': 0, 
    'primaryDoseCount0': 2,
    'boosterRemainingAgeGroups0': list(dict.fromkeys(ageCategories))
}
for parameter, default in sessionParameters.items(): 
    st.session_state[parameter] = st.session_state.setdefault(
        parameter, default
    )

boosterRowCount = st.session_state['boostAgeRowCount0']
primaryRowCount = st.session_state['primaryDoseCount0']

# Ensure age selections only give possible parameters
# Dictionary format: 'remaining groups variable': (
#   'number of rows variable', 'group row variable prefix'
# )
ageGroupSets = {
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
#TODO: Consider having templates that load parameters for specific diseases

basicTab, diseaseTab, interventionTab, dynamicTab = st.tabs([
    'Basic Parameters', 'Disease Parameters', 
    'Vaccination and NPIs', 'Dynamic Parameters'
])


# Vaccination and NPIs
with interventionTab:
    st.header('Vaccination and NPI Parameters')
    st.markdown('''
        This tab contains parameters relating to whether vaccination 
        and non-pharmaceutical interventions (NPIs) are integrated into 
        the simulation.
    ''')
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
            st.markdown('to be completed')
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#DO THESE, THEN OTHER NPIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



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
                disabled = not useVaccinesToggle, 
                key = 'primaryDelay0', help = '''
                    The number of days after an individual receives one 
                    primary vaccine dose before they are able to 
                    receive another.
                '''
            )
            primaryDuration = st.slider(
                'Vaccine Effective Duration', 1, 180, 30,
                disabled = not useVaccinesToggle, 
                key = 'primaryDuration0', help = '''
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
                disabled = not useVaccinesToggle, 
                key = 'primaryWaningRate0', help = '''
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
                    ) = primAgeEfficacyContainer.columns((0.25, 0.275, 0.275, 0.2))
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
                        disabled = not useVaccinesToggle, 
                        help = '''
                            Remove this row of the form and remove these 
                            age-specific vaccine dose efficacy values 
                            from the simulation.
                        '''
                    )
                # Button to add another row for additional age specification
                primAgeAddButton = primAgeEfficacyContainer.button(
                    label = 'Add Age Group', icon = ':material/add:', 
                    on_click = addFormRow, key = f'primAgeAdd0-{i}', 
                    args = (
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
                        Add another row to this form, where you can select 
                        an additional age group to have unique vaccine 
                        dose efficacy values.
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
                ) = boostAgeEfficacyContainer.columns((0.25, 0.275, 0.275, 0.2))
                # Age group column
                with boostAgeGroupColumn: boostAgeGroups = st.selectbox(
                    'Age Group', key = f'boostAgeGroup0-{i}', 
                    # Set age group options such that only ages that 
                    # haven't been selected yet can be selected
                    options = (
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
                on_click = addFormRow, key = 'boostAgeAdd0', 
                args = (
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