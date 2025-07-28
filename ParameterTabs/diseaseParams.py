# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where disease parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from pydantic import ValidationError
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow, dayCount
)
from ClientResources.SharedResources import ageCategories, kappaLocations
from ClientResources.ModelSchema import (
    Parameters, scenarioParameters, strainParameters
)

# Logging
diseaseLog = logging.getLogger(__name__)

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
    getRemainingGroups(ageGroupSets, ageCategories.keys())
    getRemainingGroups(locationGroupSets, kappaLocations.keys())





    # Tab Content
    # TODO: Warn for nonsensical conditions like reduced BCC being 
    # lower than regular BCC
    with container:
        st.header('Disease Parameters')
        st.markdown('''
            This tab contains parameters relating to the disease 
            itself, including how it initially enters the community, 
            the rate at which it spreads and how long infection lasts 
            before recovery.
            
            Note that despite being related to the disease's effects, 
            hospitalisation and mortality rate are defined in the 
            Community Parameters tab instead of this tab, in order to 
            group them with other health outcomes.
        ''')

        # Potential Catchable Errors:
        # - Disease total infection duration is less than what is 
        # calculated using the other time parameters
        # - Disease total infection length is longer than simulation 
        # time?



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
                'Infection Seeding Time Period (Days)', range(720), (0, 29), 
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
                - $\\beta$ (beta) is the basic transmission parameter 
                for the disease
                - $sym(I_i)$ is a parameter based on whether or not the 
                infected individual has shown symptoms
                - $inf(I_i)$ is the infectiousness parameter for the 
                infected individual
                - $susc(I_s)$ is the susceptibility parameter for the 
                uninfected individual
                - $\\kappa$ is the location parameter for the area the 
                interaction is occurring in
                
                The parameters in this section will control the values 
                of each of these parameters under various conditions.
            ''')

            # Beta and symptom multipliers
            st.select_slider(
                'Basic Transmission Parameter (β)', 
                np.linspace(0.001, 1.0, 1000), 0.11, 
                format_func = lambda x: f'{x:0.3g}', key = f'beta{id}', 
                help = '''
                    The value of the basic transmission parameter 
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
                    The value of the transmissibility modifier 
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
                    The value of the transmissibility modifier 
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
                    
                This section allows for unique values of $inf(I_i)$ and 
                $susc(I_s)$ to be defined for each age group, modifying 
                the probability of infection for interactions involving 
                individuals in said age groups. These parameters will 
                assume a default value of 1 (i.e. no change in 
                probability) if they are not specified for a specific 
                age group. 
            ''')
            # Save relevant params as variables to avoid lookups
            transRowCount = st.session_state[f'transRowCount{id}']
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
                        infectiousness and susceptibility parameters 
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
                    'Infectiousness', 
                    np.linspace(0.0, 1.0, 1001), 1.0, 
                    key = f'transInfect{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the infectiousness parameter 
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
                    'Susceptibility', 
                    np.linspace(0.0, 1.0, 1001), 1.0, 
                    key = f'transSuscept{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the susceptibility parameter 
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
                        age-specific transmission parameters from the 
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
                    parameters.
                ''' if transRowCount <= 9 else '''
                    All age groups have been given unique transmission 
                    parameters, so a new age group cannot be added.
                '''
            )

            # Location-based kappa parameters
            # TODO: Link to Background Contact Count if Background 
            # Kappa is present in this form
            st.markdown('''
                ### Location-Specific Transmission Modifiers
                    
                This section allows for unique modifiers for the 
                transmissibility function (represented in the formula 
                as $\\kappa$) to be defined for each location type used 
                in the simulation, modifying the probability of 
                infection for interactions taking place in said 
                locations. These parameters will assume a default 
                value of 1 (i.e. no change in probability) if they are 
                not specified for a particular location.
            ''')
            # Save relevant params as variables to avoid lookups
            kappaRowCount = st.session_state[f'kappaRowCount{id}']
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
                        A location that will have a specific 
                        transmissibility modifier defined for it, 
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
                # Kappa value column
                with kappaValueColumn: st.select_slider(
                    'Transmissibility Modifier', np.linspace(0.0, 5.0, 1001), 
                    1.0, key = f'kappaValue{id}-{i}', 
                    format_func = lambda x: f'{x:0.3g}', help = '''
                        The value of the transmissibility modifier 
                        $\\kappa$ when an interaction takes place in 
                        this location. The higher this value is, the 
                        more likely it is for uninfected individuals to 
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
                        location-specific transmissibility parameters 
                        from the simulation.
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
                        )
                    }
                ), 
                disabled = not kappaRowCount < 10, help = '''
                    Add another row to this form, where you can select 
                    an additional location to have unique 
                    transmissibility parameters.
                ''' if kappaRowCount <= 9 else '''
                    All locations have been given unique 
                    transmissibility parameters, so a new location 
                    cannot be added.
                '''
            )





        # Life Cycle Parameters
        with st.expander('Disease Life Cycle Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control the disease's life cycle, 
                including how long individuals are infectious for and 
                the likelihood of developing symptoms.
            ''')

            # Asymptomatic params
            st.select_slider(
                'Probability of Young (0-24) Asymptomatic Case', 
                np.linspace(0.0, 1.0, 1001), 0.35, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                key = f'asymptomaticChild{id}', help = '''
                    The probability that an infected young person 
                    (defined as 0-24 years old) in the simulation will 
                    be asymptomatic (i.e. they never show any symptoms 
                    of the disease despite being infectious).
                '''
            )
            st.select_slider(
                'Probability of Adult (24+) Asymptomatic Case', 
                np.linspace(0.0, 1.0, 1001), 0.35, 
                format_func = lambda x: f'{100 * x:0.3g}%', 
                key = f'asymptomaticAdult{id}', help = '''
                    The probability that an infected adult (defined as 
                    24+ years old) in the simulation will be 
                    asymptomatic (i.e. they never show any symptoms of 
                    the disease despite being infectious).
                '''
            )

            # Duration Parameters
            st.markdown('''
                ### Disease Life Stages
                
                Diseases in the simulation have 5 distinct stages in 
                their life cycle:
                        
                1. Latent: The disease is still developing in the body 
                of the infected individual; they do not yet show 
                symptoms and are not infectious.
                2. Developing: The disease has developed further and 
                the infected individual is now infectious, but they 
                still do not show any symptoms.
                3. Symptomatic: The disease is now showing symptoms in 
                the infected individual, and thus can now be diagnosed.
                4. Post-Symptomatic: The infected individual's 
                condition has improved enough that they no longer show 
                symptoms of the disease, but they are still infectious.
                5. Recovered: The individual is no longer infectious 
                and is considered to have recovered from the disease.
                
                If an individual is asymptomatic, their infection may 
                skip the third and fourth stages and remain in the 
                second stage without symptoms for the disease's entire 
                duration. The lengths of each of these stages is 
                determined through the parameters in this section.
            ''')
            latencyPeriod = st.select_slider(
                'Latency Period Length (Days)', range(91), 10, 
                format_func = dayCount, key = f'latencyPeriod{id}', help = '''
                    The length in days of the disease's latency period, 
                    i.e. the length of time between an individual 
                    initially being infected by the disease and said 
                    individual becoming infectious themselves.
                '''
            )
            incubationPeriod = st.select_slider(
                'Incubation Period Length (Days)', range(91), 12, 
                format_func = dayCount, key = f'incubationPeriod{id}', 
                help = '''
                    The length in days of the disease's incubation 
                    period, i.e. the length of time between an 
                    individual initially being infected by the disease 
                    and said individual beginning to show symptoms.
                '''
            )
            # TODO: Decide between generation time, infectious period, 
            # symptom length
            symptomPeriod = st.select_slider(
                'Symptomatic Period Length (Days)', range(91), 7, 
                format_func = dayCount, key = f'symptomPeriod{id}', help = '''
                    The length in days of the disease's symptomatic 
                    period, i.e. the length of time during which an 
                    infected individual will show symptoms of the 
                    disease.
                '''
            )
            infectionDuration = st.select_slider(
                'Total Infection Duration (Days)', range(181), 20, 
                format_func = dayCount, key = f'infectionDuration{id}', 
                help = '''
                    The length in days of the disease's total lifespan, 
                    i.e. the length of time between an individual 
                    initially being infected by the disease and said 
                    individual being fully recovered/no longer 
                    infectious.
                '''
            )

            # State duration lengths

            st.markdown(f'''
                #### Period Lengths
                
                Using the parameters defined above, the lengths of the 
                disease's life stages are as follows:
                        
                - Latent: {dayCount(latencyPeriod)}
                - Developing: {
                    dayCount(incubationPeriod - latencyPeriod)
                }
                - Symptomatic: {dayCount(symptomPeriod)}
                - Post-Symptomatic: {dayCount(
                    infectionDuration - incubationPeriod - symptomPeriod
                )}
                - Total Infection Duration: {
                    dayCount(infectionDuration)
                }

                Additionally, the Infectious Period for this disease 
                (i.e. the length of time during which an infected 
                individual is themselves infectious) has a length of {
                    dayCount(infectionDuration - latencyPeriod)
                }.
            ''')



        # Waning Immunity Parameters
        with st.expander('Immunity Waning Properties'):
            # Describe what sort of parameters are here
            st.markdown('''
                These parameters control how immunity to the disease 
                conferred by having been infected by it in the past 
                will become less effective over time. Note that 
                individuals in the simulation are assumed to be 
                completely immune to the disease immediately after 
                recovering from it; the efficacy before waning is 100%.
                
                Parameters for controlling how immunity to the disease 
                conferred by vaccines becomes less effective over time 
                can be found in the "Vaccinations and NPIs" tab.
            ''')

            # Waning immunity
            st.slider(
                'Natural Immunity Waning Delay (Months)', 1, 36, 2, 
                key = f'naturalImmunityDuration{id}', help = '''
                    The number of months after an individual fully 
                    recovers from the disease before the immunity 
                    conferred by having been infected begins to 
                    diminish, where a month is 30 days.
                '''
            )
            st.select_slider(
                'Natural Immunity After Waning (Probability)',
                np.linspace(0.0, 1.0, 1001), 0.5, 
                key = f'naturalWanedEfficacy{id}', 
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The final efficacy value that an individual's 
                    natural immunity after recovering from the disease 
                    will approach as it begins to diminish, represented 
                    as the probability that the individual will remain 
                    healthy when exposed to the disease after their 
                    immunity is fully waned.
                '''
            )
            st.slider(
                'Natural Immunity Waning Duration (Months)', 0, 36, 6,
                key = f'naturalWaningRate{id}', help = '''
                    The number of months after the immunity from having 
                    fully recovered from the disease begins waning 
                    before the efficacy of the immunity stabilises, 
                    where a month is 30 days. Natural immunity in the 
                    *Flusim* simulation will wane at a linear rate, so 
                    this parameter represents how long it takes for the 
                    immunity level to decrease from total immunity to 
                    the final immunity probability defined above.

                    If this parameter is set to 0, the immunity 
                    provided by recovering from the disease will never 
                    diminish.
                '''
            )





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
def diseaseSchema(schema, id = 0):
    try:
        # Validate parameters
        if not isinstance(schema, Parameters): raise ValueError(
            'schema should be a Parameters object'
        )

        # Convert dashboard representation to model representation
        seedPeriod = st.session_state[f'seedPeriod{id}']
        incubationPeriod = st.session_state[f'incubationPeriod{id}']

        # Add this tab's parameters to the scenario parameter object
        # TODO: Age-specific trans and susc
        # TODO: Kappas

        # Strain Parameters
        schema.Scenario_Strain = [strainParameters(
            StrainId = 0, Beta = st.session_state[f'beta{id}']
        )]

        # Scenario Parameters
        if not schema.Scenario_Parameter: 
            schema.Scenario_Parameter = scenarioParameters(
                seed_rate = st.session_state[f'seedRate{id}'], 
                seeding_start_cycle = seedPeriod[0] * 2, 
                seeding_duration = (seedPeriod[1] - seedPeriod[0]) * 2, 
                beta_asymptomatic = st.session_state[f'betaAsymptomatic{id}'], 
                beta_post_symptomatic = st.session_state[
                    f'betaPostSymptomatic{id}'
                ], 
                prob_asymptomatic_young = st.session_state[
                    f'asymptomaticChild{id}'
                ], 
                prob_asymptomatic = st.session_state[f'asymptomaticAdult{id}'],
                transmissibility_delay = (
                    st.session_state[f'latencyPeriod{id}'] * 2
                ), 
                symptom_latency = incubationPeriod * 2, 
                generation_time = (
                    incubationPeriod + st.session_state[f'symptomPeriod{id}']
                ) * 2, 
                infection_duration = (
                    st.session_state[f'infectionDuration{id}'] * 2
                ), 
                infection_waning_cycle_delay = (
                    st.session_state[f'naturalImmunityDuration{id}'] * 60
                ), 
                infection_waned_protection = st.session_state[
                    f'naturalWanedEfficacy{id}'
                ], 
                infection_waning_rate_per_cycle = st.session_state[
                    f'naturalWaningRate{id}'
                ]
            )
        else: 
            schema.Scenario_Parameter.seed_rate = st.session_state[
                f'seedRate{id}'
            ]
            schema.Scenario_Parameter.seeding_start_cycle = seedPeriod[0] * 2
            schema.Scenario_Parameter.seeding_duration = (
                (seedPeriod[1] - seedPeriod[0]) * 2
            )
            schema.Scenario_Parameter.beta_asymptomatic = st.session_state[
                f'betaAsymptomatic{id}'
            ]
            schema.Scenario_Parameter.beta_post_symptomatic = st.session_state[
                f'betaPostSymptomatic{id}'
            ]
            (
                schema.Scenario_Parameter.prob_asymptomatic_young
            ) = st.session_state[
                f'asymptomaticChild{id}'
            ]
            schema.Scenario_Parameter.prob_asymptomatic = st.session_state[
                f'asymptomaticAdult{id}'
            ]
            schema.Scenario_Parameter.transmissibility_delay = (
                st.session_state[f'latencyPeriod{id}'] * 2
            )
            schema.Scenario_Parameter.symptom_latency = incubationPeriod * 2
            schema.Scenario_Parameter.generation_time = (
                (incubationPeriod + st.session_state[f'symptomPeriod{id}']) * 2
            )
            schema.Scenario_Parameter.infection_duration = (
                st.session_state[f'infectionDuration{id}'] * 2
            )
            schema.Scenario_Parameter.infection_waning_cycle_delay = (
                st.session_state[f'naturalImmunityDuration{id}'] * 60
            )
            (
                schema.Scenario_Parameter.infection_waned_protection
            ) = st.session_state[
                f'naturalWanedEfficacy{id}'
            ]
            (
                schema.Scenario_Parameter.infection_waning_rate_per_cycle
            ) = st.session_state[
                f'naturalWaningRate{id}'
            ]
        
        # Add procedural Scenario Parameters (age/kappa)
        for i in range(st.session_state[f'transRowCount{id}']):
            varAgeGroup = ageCategories[
                st.session_state[f'transAgeGroup{id}-{i}']
            ]
            setattr(
                schema.Scenario_Parameter, f'{varAgeGroup}_trans', 
                st.session_state[f'transInfect{id}-{i}']
            )
            setattr(
                schema.Scenario_Parameter, f'{varAgeGroup}_susc', 
                st.session_state[f'transSuscept{id}-{i}']
            )
        for i in range(st.session_state[f'kappaRowCount{id}']):
            varLocation = kappaLocations[
                st.session_state[f'kappaLocation{id}-{i}']
            ]
            setattr(
                schema.Scenario_Parameter, f'kappa_{varLocation}', 
                st.session_state[f'kappaValue{id}-{i}']
            )
    except (ValueError, ValidationError) as e:
        diseaseLog.error((
            f'[diseaseParams] Encountered {type(e).__name__} '
            f'while validating parameters for scenario {id}: {e}'
        ))
        raise e