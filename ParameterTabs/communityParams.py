# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where community parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow
)
from ClientResources.SharedResources import ageCategories

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
        f'deathRowCount{id}': 0
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
        f'deathRemainingAgeGroups{id}': (
            f'deathRowCount{id}', f'deathAgeGroup{id}-'
        )
    }

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories)





    # Tab Content
    # TODO: Warn for nonsensical conditions like reduced BCC being 
    # lower than regular BCC
    with container:
        st.header('Community Parameters')
        st.markdown('''
            This tab contains parameters relating to the community that 
            is simulated by the model, including the likelihood of 
            different health outcomes, how individuals react to the 
            disease, and the size of groups that individuals form in 
            different locations.
        ''')

        # Potential Catchable Errors:
        # - Base Withdrawal rate (adult or child) is above NPI version


        # Health Outcome Parameters
        with st.expander('Health Outcome Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control how likely different health 
                outcomes are as a result of the disease, including 
                hospitalisation and death. Note that all of these 
                health outcomes will only occur if the infected 
                individual is symptomatic.
            ''')

            # Health Outcomes
            st.select_slider(
                'Diagnosed Case Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.5, key = f'caseRatio{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an infected, symptomatic 
                    individual will be formally diagnosed as a 
                    confirmed case of the disease.
                '''
            )
            st.select_slider(
                'GP Visit Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.333, key = f'gpRatio{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an infected, symptomatic 
                    individual will visit their general practitioner 
                    (GP) as a result of the disease.
                '''
            )
            st.select_slider(
                'Hospitalisation Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.25, key = f'hospitalRatio{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an infected, symptomatic 
                    individual will be admitted to a hospital as a 
                    result of the disease.
                '''
            )
            st.select_slider(
                'ICU Visit Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.1, key = f'icuRatio{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an infected, symptomatic 
                    individual will be admitted to a hospital's 
                    intensive care unit (ICU) as a result of the 
                    disease.
                '''
            )
            deathRate = st.select_slider(
                'Mortality Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.05, key = f'deathRatio{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The base probability that an infected, symptomatic 
                    individual will die as a direct result of the 
                    disease.
                '''
            )

            # Age-based Mortality
            # TODO: Make these parameters actually work in schema
            st.markdown('''
                ### Age-Specific Mortality Rate
                    
                This section allows for unique likelihoods of death to 
                be defined for each age group, overriding the global 
                rate defined above.
            ''')
            # Save relevant params as variables to avoid lookups
            deathRowCount = st.session_state[f'deathRowCount{id}']
            deathRemainingGroups = st.session_state[
                f'deathRemainingAgeGroups{id}'
            ]
            deathAgeContainer = st.container()
            for i in range(deathRowCount): 
                (
                    deathGroupColumn, deathRateColumn, deathRemoveColumn
                ) = deathAgeContainer.columns((0.25, 0.55, 0.2))
                deathCurrentGroup = st.session_state.get(
                    f'deathAgeGroup{id}-{i}'
                )

                # Age group column
                with deathGroupColumn: st.selectbox(
                    'Age Group', key = f'deathAgeGroup{id}-{i}', 
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    options = (
                        [deathCurrentGroup] + [
                            group for group in deathRemainingGroups 
                            if group != deathCurrentGroup
                        ] if deathCurrentGroup else deathRemainingGroups
                    ), 
                    disabled = not deathRowCount < 10, help = '''
                        An age group that will have specific mortality 
                        rates defined for it, overriding the base 
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
                # Mortality column
                with deathRateColumn: st.select_slider(
                    'Mortality Rate (Probability)', 
                    np.linspace(0.0, 1.0, 1001), 0.05, 
                    key = f'deathRatio{id}-{i}', 
                    format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                        The probability that an infected, symptomatic 
                        individual in this age group will die as a 
                        direct result of the disease.
                    '''
                )
                # Delete button column
                with deathRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:', 
                    key = f'deathRemove{id}-{i}', on_click = deleteFormRow, 
                    args = (
                        i, f'deathRowCount{id}', {
                            f'deathAgeGroup{id}-', f'deathRate{id}-'
                        }
                    ),
                    help = '''
                        Remove this row of the form and remove these 
                        age-specific mortality rates from the 
                        simulation.
                    '''
                )
            # Button to add another row for age specific params
            deathAgeContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'deathAdd{id}', args = (
                    f'deathRowCount{id}', {
                        f'deathAgeGroup{id}-{deathRowCount}': (
                            deathRemainingGroups[0] 
                            if deathRemainingGroups else None
                        ),
                        f'deathRatio{id}-{deathRowCount}': deathRate
                    }
                ), 
                disabled = not deathRowCount < 10, help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have a unique mortality 
                    rate.
                ''' if deathRowCount <= 9 else '''
                    All age groups have been given unique mortality 
                    rates, so a new age group cannot be added.
                '''
            )



        # Disease Response Parameters
        with st.expander('Disease Response Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control how individuals in the 
                community will react to symptoms of the disease, 
                including how likely they are to withdraw from 
                work/school and how long it takes until they have their 
                infection officially diagnosed as a case.
                
                Note that this section does not contain parameters 
                related to social distancing and other interventions 
                implemented by the government to reduce the spread of 
                the disease; those parameters can be found in the 
                "Vaccinations and NPIs" tab.
            ''')

            # Withdrawal probabilities
            withdrawalWork = st.select_slider(
                'Work Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.5, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                key = f'withdrawalWork{id}', help = '''
                    The probability of an infected individual in the 
                    simulation voluntarily withdrawing from work after 
                    becoming symptomatic.
                '''
            )
            withdrawalSchool = st.select_slider(
                'School Withdrawal Rate (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.9, 
                format_func = lambda x: f'{100 * x:0.3g}%',
                key = f'withdrawalSchool{id}', help = '''
                    The probability of an infected individual in the 
                    simulation voluntarily withdrawing from school 
                    after becoming symptomatic.
                '''
            )
            # Withdrawal period seems to be unused
            withdrawalPeriod = """
            st.slider(
                'Length of Withdrawal Period (Days)', 0, 30, 8,
                key = f'withdrawalPeriod{id}', help = '''
                    The number of days after an individual begins 
                    withdrawing from work or school before they will 
                    start attending their workplace/school again.
                '''
            )
            """

            # Diagnosis delay
            st.slider(
                'Case Diagnosis Delay (Days)', 0, 14, 1,
                key = f'diagnosisDelay{id}', help = '''
                    The number of days after an individual begins 
                    showing symptoms of the disease before their 
                    infection can be formally diagnosed as a confirmed 
                    case.
                '''
            )
        

        # Behaviour Parameters
        with st.expander('Behaviour Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control various aspects of how 
                individuals behave in the simulation, including the 
                size of groups that they form and how many people they 
                interact with each day.
            ''')

            # BCC and Child Supervision
            bccRate = st.slider(
                ((
                    'Background Contact Count (Average '
                    'Number of Interactions per Person)'
                )),
                0.0, 8.0, 4.0, key = f'bccRate{id}', help = '''
                    The average number of other people each individual 
                    will interact with in the background phase of the 
                    simulation. These interactions emulate interactions 
                    outside of locations simulated by the model.
                '''
            )
            st.select_slider(
                'Child Supervision Rate (Probability)',
                np.linspace(0.0, 1.0, 1001), 1.0, 
                key = f'childSupervision{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an adult in the simulation 
                    will remain at their household if there is at least 
                    one child present and no other adults are at home.
                '''
            )
            st.slider(
                'Number of Class Subgroups', 1, 5, 1, 
                key = f'maxClassCount{id}', help = '''
                    The maximum number of subgroups that may exist 
                    within a single class in the simulation. Subgroups 
                    are defined as sets of individuals that regularly 
                    interact with each other but not with the rest of 
                    the class.
                '''
            )

            # Group Sizes
            st.subheader('Group Size Parameters')
            st.slider(
                'Maximum School Class Size (Number of People)', 
                0, 25, 10, key = f'maxClassSize{id}', help = '''
                    The maximum size of school classes within K-12 
                    schools and childcare facilities in the simulation.
                '''
            )
            st.slider(
                'Maximum Tertiary Class Size (Number of People)', 
                0, 25, 10, key = f'maxAdultClassSize{id}', help = '''
                    The maximum size of classes within universities and 
                    other tertiary education facilities in the 
                    simulation.
                '''
            )
            workgroupSize = st.slider(
                'Maximum Work Group Size (Number of People)', 
                0, 25, 10, key = f'maxWorkGroupSize{id}', help = '''
                    The maximum size of groups within workplaces in the 
                    simulation.
                '''
            )
            st.slider(
                'Maximum Neighbour Group Size (Number of People)', 
                0, 25, 10, key = f'maxNeighborGroupSize{id}', help = '''
                    The maximum size of groups within neighbourhoods in 
                    the simulation.
                '''
            )
            st.slider(
                'Maximum Church Group Size (Number of People)', 
                0, 25, 10, key = f'maxChurchGroupSize{id}', help = '''
                    The maximum size of groups within churches in the 
                    simulation.
                '''
            )