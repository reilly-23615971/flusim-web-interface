# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where disease parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow
)
from ClientResources.SharedResources import ageCategories, kappaLocations

# Logging
vaccineLog = logging.getLogger(__name__)

"""
Function to generate the parameters for the disease in a specified 
container with scenario differentiation

Parameters:
    container: The Streamlit container (likely a tab or expander) in 
    which the parameters will be generated.

    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables.

    globalErrorContainer: A container outside of the tab where error 
    messages will be placed.
"""
def buildDiseaseTab(container, id, globalErrorContainer):
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
        st.header('Disease Parameters')
        st.markdown('''
            This tab contains parameters relating to the disease 
            itself, including how it initially enters the community, 
            the rate at which it spreads and the likelihood of 
            different health outcomes occurring as a result of it.
        ''')

        # Potential Catchable Errors:
        # - none yet!

        # Inclusions: Beta from strain parameters, the age-specifics 
        # once implemented, infection immunity waning, seeding minus 
        # start day, beta symptom multipliers, infection parameters, 
        # kappas?, health outcomes?



        # Seeding Parameters
        with st.expander('Infection Seeding Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control how infected individuals 
                are directly seeded into the community. Seeding is 
                typically used to kickstart the initial epidemic by 
                ensuring a steady number of people are infected 
                daily.
            ''')

            st.select_slider(
                'Infection Seeding Rate (Average Individuals per Day)', 
                np.linspace(0.005, 5.0, 1000), 0.25, key = f'seedRate{id}', 
                format_func = lambda x: f'{x:0.4g}', help = '''
                    The average number of individuals that will be 
                    infected directly via infection seeding each cycle.
                '''
            )
            # TODO: Set time-based parameter maximums based on number 
            # of cycles in simulation
            st.select_slider(
                'Infection Seeding Time Period', range(720), (0, 30), 
                format_func = lambda x: f'Day {x + 1}', 
                key = f'seedPeriod{id}', help = '''
                    The time period during which infection seeding will 
                    occur in the simulation. The first value is the day 
                    on which seeding will begin (where Day 1 is the 
                    first day of the simulation), and the second value 
                    is the day on which it will stop.
                '''
            )


        # Transmission Parameters
        with st.expander('Transmission Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control the likelihood that the 
                disease will spread when an infected individual 
                interacts with others. 
                        
                The probability that an interaction between an infected 
                individual $I_i$ and an uninfected, non-immune 
                individual $I_s$ will result in the infection of $I_s$ 
                is calculated with the following formula 
                [[1](https://www.doi.org/10.1371/journal.pone.0004005)]:
                        
                $$
                P_{trans}(I_i, I_s) = 1 - \\exp{(-\\beta \\times 
                sym(I_i) \\times inf(I_i) \\times susc(I_s) \\times 
                \\kappa)}
                $$
                
                In this formula:
                - $\\beta$ (beta) is the basic transmission coefficient 
                for the disease
                - $sym(I_i)$ is the disease state coefficient for the 
                infected individual
                - $inf(I_i)$ is the infectiousness coefficient for the 
                infected individual
                - $susc(I_s)$ is the susceptibility coefficient for the 
                uninfected individual
                - $\\kappa$ (kappa) is the location coefficient for the 
                area the interaction is occurring in
                
                The parameters in this section will control the values 
                of each of these coefficients under various conditions.
            ''')

            # Beta and symptom multipliers
            st.select_slider(
                'Basic Transmission Coefficient (β)', 
                np.linspace(0.001, 1.0, 1000), 0.11, 
                format_func = lambda x: f'{x:0.3g}', key = f'beta{id}', 
                help = '''
                    The value of the basic transmission coefficient 
                    $\\beta$, the base constant used to calculate the 
                    probability of an individual being infected with 
                    the disease upon interacting with an infected 
                    individual. The higher this value is, the more 
                    likely it is for uninfected individuals to contract 
                    the disease in any interaction with infected 
                    individuals.
                '''
            )
            st.select_slider(
                'Asymptomatic Transmission Multiplier', 
                np.linspace(0.0, 1.0, 1001), 0.55, 
                format_func = lambda x: f'{x:0.3g}', 
                key = f'betaAsymptomatic{id}', help = '''
                    The value of the disease state coefficient 
                    $sym(I_i)$ when the infected individual in an 
                    interaction ($I_i$) is asymptomatic (i.e. has not 
                    shown any symptoms of the disease despite being 
                    infectious). This applies to both individuals who 
                    are too early in the disease's lifespan to show 
                    symptoms as well as individuals who never show 
                    symptoms throughout their infectious period. The 
                    lower this value is, the less likely it is for 
                    uninfected individuals to contract the disease when 
                    interacting with asymptomatic individuals.
                '''
            )
            st.select_slider(
                'Post-Symptomatic Transmission Multiplier', 
                np.linspace(0.0, 1.0, 1001), 0.55, 
                format_func = lambda x: f'{x:0.3g}', 
                key = f'betaPostSymptomatic{id}', help = '''
                    The value of the disease state coefficient 
                    $sym(I_i)$ when the infected individual in an 
                    interaction ($I_i$) is post-symptomatic (i.e. 
                    previously showed symptoms of the disease, but no 
                    longer does). The lower this value is, the less 
                    likely it is for uninfected individuals to contract 
                    the disease when interacting with post-symptomatic 
                    individuals.
                '''
            )

            # Age-based infectiousness and susceptibility parameters
            # TODO: Make these parameters actually work in schema
            st.markdown('''
                ### Age-Specific Infectiousness/Susceptibility 
                Coefficients
                    
                This section allows for unique values of $inf(I_i)$ and 
                $susc(I_s)$ to be defined for each age group, modifying 
                the probability of infection for interactions involving 
                individuals in said age groups. These coefficients will 
                assume a default value of 1 (i.e. no change in 
                probability) if they are not specified for a specific 
                age group. 
            ''')
            # Save relevant params as variables to avoid lookups
            transRowCount = st.session_state[
                f'transRowCount{id}'
            ]
            transRemainingGroups = st.session_state[
                f'transRemainingAgeGroups{id}'
            ]
            transAgeContainer = st.container()
            for i in range(transRowCount): 
                (
                    transGroupColumn, transInfectColumn, 
                    transSusceptColumn, transRemoveColumn
                ) = transAgeContainer.columns((0.25, 0.275, 0.275, 0.2))
                transCurrentGroup = st.session_state.get(
                    f'transAgeGroup{id}-{i}'
                )

                # Age group column
                with transGroupColumn: st.selectbox(
                    'Age Group', key = f'transAgeGroup{id}-{i}', 
                    # Set age group options such that only ages 
                    # that haven't been selected yet can be selected
                    options = (
                        [transCurrentGroup] + [
                            group for group in transRemainingGroups 
                            if group != transCurrentGroup
                        ] if transCurrentGroup else transRemainingGroups
                    ), 
                    disabled = not transRowCount < 10, help = '''
                        An age group that will have specific 
                        infectiousness and susceptibility coefficients 
                        defined for it, modifying the base transmission 
                        probability for interactions involving 
                        individuals in that age group.

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
                # Infectiousness column
                with transInfectColumn: st.select_slider(
                    'Infectiousness Coefficient', 
                    np.linspace(0.0, 1.0, 1001), 1.0, 
                    key = f'transInfect{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the infectiousness coefficient 
                        $inf(I_i)$ when the infected individual in an 
                        interaction ($I_i$) is a member of this age 
                        group. The lower this value is, the less likely 
                        it is for uninfected individuals to contract 
                        the disease when interacting with infected 
                        individuals in this age group.
                    '''
                )
                # Susceptibility column
                with transSusceptColumn: st.select_slider(
                    'Susceptibility Coefficient', 
                    np.linspace(0.0, 1.0, 1001), 1.0, 
                    key = f'transSuscept{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the susceptibility coefficient 
                        $susc(I_s)$ when the uninfected individual in 
                        an interaction ($I_s$) is a member of this age 
                        group. The lower this value is, the less likely 
                        it is for uninfected individuals in this age 
                        group to contract the disease when interacting 
                        with infected individuals.
                    '''
                )
                # Delete button column
                with transRemoveColumn: st.button(
                    label = 'Remove Age Group', icon = ':material/delete:', 
                    key = f'transRemove{id}-{i}', on_click = deleteFormRow, 
                    args = (
                        i, f'transRowCount{id}', {
                            f'transAgeGroup{id}-', f'transInfect{id}-', 
                            f'transSuscept{id}-'
                        }
                    ),
                    help = '''
                        Remove this row of the form and remove these 
                        age-specific transmission coefficients from the 
                        simulation.
                    '''
                )
            # Button to add another row for age specific params
            transAgeContainer.button(
                label = 'Add Age Group', icon = ':material/add:', 
                on_click = addFormRow, key = f'transAdd{id}', args = (
                    f'transRowCount{id}', {
                        f'transAgeGroup{id}-{transRowCount}': (
                            transRemainingGroups[0] 
                            if transRemainingGroups else None
                        ),
                        f'transInfect{id}-{transRowCount}': 1.0,
                        f'transSuscept{id}-{transRowCount}': 1.0
                    }
                ), 
                disabled = not transRowCount < 10, help = '''
                    Add another row to this form, where you can select 
                    an additional age group to have unique transmission 
                    coefficients.
                ''' if transRowCount <= 9 else '''
                    All age groups have been given unique transmission 
                    coefficients, so a new age group cannot be added.
                '''
            )

            # Location-based kappa parameters
            # TODO: Link to Background Contact Count if Background 
            # Kappa is present in this form
            st.markdown('''
                ### Location-Specific Kappa Coefficients
                    
                This section allows for unique values of kappa 
                ($\\kappa$) to be defined for each location type used 
                in the simulation, modifying the probability of 
                infection for interactions taking place in said 
                locations. These coefficients will assume a default 
                value of 1 (i.e. no change in probability) if they are 
                not specified for a specific location. 
            ''')
            # Save relevant params as variables to avoid lookups
            kappaRowCount = st.session_state[
                f'kappaRowCount{id}'
            ]
            kappaRemainingLocations = st.session_state[
                f'kappaRemainingLocations{id}'
            ]
            kappaContainer = st.container()
            for i in range(kappaRowCount): 
                (
                    kappaLocationColumn, kappaValueColumn, 
                    kappaRemoveColumn
                ) = kappaContainer.columns((0.25, 0.55, 0.2))
                kappaCurrentLocation = st.session_state.get(
                    f'kappaLocation{id}-{i}'
                )

                # Age group column
                with kappaLocationColumn: st.selectbox(
                    'Location', key = f'kappaLocation{id}-{i}', 
                    # Set location options such that only places 
                    # that haven't been selected yet can be selected
                    options = (
                        [kappaCurrentLocation] + [
                            place for place in kappaRemainingLocations 
                            if place != kappaCurrentLocation
                        ] if kappaCurrentLocation else kappaRemainingLocations
                    ), 
                    disabled = not kappaRowCount < 10, help = '''
                        A location that will have a specific kappa 
                        ($\\kappa$) coefficients defined for it, 
                        modifying the base transmission probability for 
                        interactions occurring in that location.

                        ##### Options:
                        - Households: Places where individuals live.
                        - K-12 Education: Primary or secondary schools, 
                        and other facilities for educating children.
                        - Tertiary Education: Universities, and other 
                        facilities for educating adults.
                        - Workplaces: Locations where adults go to work.
                        - Childcare: Daycare centres, and other places 
                        that supervise preschool children.
                        - Hospitals: Places that care for sick 
                        individuals.
                        - Background: Interactions taking place during 
                        the model's background phase, simulating 
                        any contact that occurs outside of the other 
                        locations.
                    '''
                )
                # Kappa coefficient column
                with kappaValueColumn: st.select_slider(
                    'Kappa Coefficient (κ)', np.linspace(0.0, 5.0, 1001), 
                    1.0, key = f'kappaValue{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the kappa coefficient $\\kappa$ 
                        when an interaction takes place in this 
                        location. The higher this value is, the more 
                        likely it is for uninfected individuals to 
                        contract the disease when interacting with 
                        infected individuals in this location.
                    '''
                )
                # Delete button column
                with kappaRemoveColumn: st.button(
                    label = 'Remove Location', icon = ':material/delete:', 
                    key = f'kappaRemove{id}-{i}', on_click = deleteFormRow, 
                    args = (
                        i, f'kappaRowCount{id}', {
                            f'kappaLocation{id}-', f'kappaValue{id}-'
                        }
                    ),
                    help = '''
                        Remove this row of the form and remove these 
                        location-specific kappa coefficients from the 
                        simulation.
                    '''
                )
            # Button to add another row for age specific params
            kappaContainer.button(
                label = 'Add Location', icon = ':material/add:', 
                on_click = addFormRow, key = f'kappaAdd{id}', args = (
                    f'kappaRowCount{id}', {
                        f'kappaLocation{id}-{kappaRowCount}': (
                            kappaRemainingLocations[0] 
                            if kappaRemainingLocations else None
                        ),
                        #f'kappaValue{id}-{kappaRowCount}': 1.0
                    }
                ), 
                disabled = not kappaRowCount < 10, help = '''
                    Add another row to this form, where you can select 
                    an additional location to have unique kappa 
                    coefficients.
                ''' if kappaRowCount <= 9 else '''
                    All locations have been given unique kappa 
                    coefficients, so a new location cannot be added.
                '''
            )





        # Symptom Parameters
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************
        #******************COMPLETE THESE PARAMETERS*******************#******************COMPLETE THESE PARAMETERS*******************



        # Disease Attributes (consider further splitting)



        # Health Outcomes

