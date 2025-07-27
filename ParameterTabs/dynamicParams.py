# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameters can change mid-simulation

# Imports
import logging
import numpy as np
import streamlit as st
from ClientResources.InterfaceFunctions import (
    getRemainingGroups, addFormRow, deleteFormRow, dayCount
)
from ClientResources.SharedResources import ageCategories, kappaLocations

# Logging
dynamicLog = logging.getLogger(__name__)

"""
Function to generate the dynamic parameters in a specified container 
with scenario differentiation

Parameters:
    container: The Streamlit container (likely a tab or expander) in 
    which the parameters will be generated.

    id: An integer that will be used to differentiate the parameters in 
    different instances of the tab by adding a number to the Streamlit 
    session state variables.

    globalErrorContainer: A container outside of the tab where error 
    messages will be placed.
"""
def buildDynamicTab(container, id, globalErrorContainer):
    # Initialise session variables needed by the disease forms
    sessionParameters = {
        # Toggles
        f'schoolClosureToggle{id}': True,
        f'bccToggle{id}': True,

        # Base values
        f'seedRate{id}': 0.25,
        f'schoolClosureCompliance{id}': 0.9,
        f'bccReducedRate{id}': 0.2,
        # f'schoolClosurePeriod{id}': (30, 60),

        # Row counts
        f'seedRowCount{id}': 0,
        f'closeRowCount{id}': 0,
        f'bccRowCount{id}': 0
        # f'periodRowCount{id}': 0
    }
    for parameter, default in sessionParameters.items(): 
        st.session_state[parameter] = st.session_state.setdefault(
            parameter, default
        )





    # Tab Content
    # TODO: Warn for nonsensical conditions like reduced BCC being 
    # lower than regular BCC
    # TODO: Change time-based parameters to use simulation length as max
    # TODO: Sort rows from earliest to latest
    with container:
        st.header('Dynamic Parameters')
        st.markdown('''
            This tab allows for specific parameters to change their 
            values at predefined points throughout the simulation. The 
            parameters that support this dynamic changing (and the tabs 
            where the starting values may be modified) are as follows:
            
            #### Disease Tab
            - Infection Seeding Rate ("Disease" tab)
            
            #### Vaccinations and NPIs Tab
            - School Closure Compliance
            - Reduced Background Contact Count
            
            Note that since the latter two parameters are tied to 
            non-pharmaceutical interventions (NPIs), any changes to 
            their value made here will only affect the simulation if 
            the corresponding NPI is active at that time.
        ''')

        # Potential Catchable Errors:
        # - First dynamic new value is same as base value
        # - Other consecutive duplicate values
        # - New seeding rate defined outside of seeding period
        # - NPI parameters given dynamic changes when disabled



        # Infection Seeding Rate
        # TODO: Warn if update point is outside of seeding period (or 
        # silently adjust seeding period and add zeroes to fix it)
        st.subheader('Infection Seeding Rate')
        # Save relevant parameters as variables to avoid lookups
        seedRowCount = st.session_state[f'seedRowCount{id}']
        baseSeedValue = st.session_state[f'seedRate{id}']
        seedContainer = st.container()
        for i in range(seedRowCount): 
            (
                seedCycleColumn, seedNewColumn, seedRemoveColumn
            ) = seedContainer.columns((0.4, 0.4, 0.2))
            # Cycle column
            with seedCycleColumn: st.select_slider(
                'Day to Update Parameter', range(720), 
                29, key = f'seedCycle{id}-{i}', 
                format_func = lambda x: f'Day {x + 1}', help = '''
                    The day of the simulation upon which the new value 
                    for infection seeding rate will come into effect.
                '''
            )
            # New value column
            with seedNewColumn: st.select_slider(
                'New Infection Seeding Rate (Average Individuals per Day)', 
                np.linspace(0.005, 5.0, 1000), 0.25, 
                key = f'seedNewRate{id}-{i}', 
                format_func = lambda x: f'{x:0.4g}', help = '''
                    The average number of individuals that will be 
                    infected directly via infection seeding each cycle 
                    after the specified point in the simulation.
                '''
            )
            # Delete button column
            with seedRemoveColumn: st.button(
                label = 'Remove Update Point', icon = ':material/delete:', 
                key = f'seedRemove{id}-{i}', on_click = deleteFormRow, 
                args = (
                    i, f'seedRowCount{id}', {
                        f'seedCycle{id}-', f'seedNewRate{id}-'
                    }
                ),
                help = '''
                    Remove this row of the form and remove this change 
                    in infection seeding rate from the simulation.
                '''
            )
        # Button to add another row for more updates
        seedContainer.button(
            label = 'Add Update Point', icon = ':material/add:', 
            on_click = addFormRow, key = f'seedAdd{id}', args = (
                f'seedRowCount{id}', {
                    f'seedCycle{id}-{seedRowCount}': 29,
                    f'seedNewRate{id}-{seedRowCount}': baseSeedValue
                }
            ), 
            disabled = not seedRowCount < 10, help = '''
                Add another row to this form, where you can select an 
                additional point in the simulation where the infection 
                seeding rate will change.
            ''' if seedRowCount <= 9 else '''
                To keep the number of parameters manageable, the values 
                of each parameter may not be changed more than 10 times 
                in a single simulation.
            '''
        )
        


        # School Closure Compliance
        st.subheader('School Closure Compliance')
        # Save relevant parameters as variables to avoid lookups
        closeRowCount = st.session_state[f'closeRowCount{id}']
        baseCloseValue = st.session_state[f'schoolClosureCompliance{id}']
        closeActive = st.session_state[f'schoolClosureToggle{id}']
        closeContainer = st.container()

        # Warn if school closure is disabled
        if not closeActive: 
            if closeRowCount == 0: st.info(f'''
                Note: School closures are currently disabled in 
                {'the baseline' if id == 0 else 'this'} scenario. As 
                such, any dynamic updates to school closure compliance 
                made here will not take effect unless you enable school 
                closures in the "Vaccinations and NPIs" tab prior to 
                running the simulation.
            ''')
            else: st.warning(f'''
                Note: School closures are currently disabled in 
                {'the baseline' if id == 0 else 'this'} scenario. As 
                such, the dynamic updates to school closure compliance 
                that have been defined here will not take effect unless 
                you enable school closures in the "Vaccinations and 
                NPIs" tab prior to running the simulation.
            ''')
        
        for i in range(closeRowCount): 
            (
                closeCycleColumn, closeNewColumn, closeRemoveColumn
            ) = closeContainer.columns((0.4, 0.4, 0.2))
            # Cycle column
            with closeCycleColumn: st.select_slider(
                'Day to Update Parameter', range(720), 
                29, key = f'closeCycle{id}-{i}', disabled = not closeActive,
                format_func = lambda x: f'Day {x + 1}', help = '''
                    The day of the simulation upon which the new value 
                    for school closure compliance will come into effect.
                '''
            )
            # New value column
            with closeNewColumn: st.select_slider(
                'New School Closure Compliance (Probability)', 
                np.linspace(0.0, 1.0, 1001), 0.9, 
                key = f'closeNewRate{id}-{i}', disabled = not closeActive,
                format_func = lambda x: f'{100 * x:0.3g}%', help = '''
                    The probability that an individual will withdraw 
                    from schools when they are closed after the 
                    specified point in the simulation.
                '''
            )
            # Delete button column
            with closeRemoveColumn: st.button(
                label = 'Remove Update Point', icon = ':material/delete:', 
                key = f'closeRemove{id}-{i}', on_click = deleteFormRow, 
                disabled = not closeActive, args = (
                    i, f'closeRowCount{id}', {
                        f'closeCycle{id}-', f'closeNewRate{id}-'
                    }
                ),
                help = '''
                    Remove this row of the form and remove this change 
                    in school closure compliance from the simulation.
                '''
            )
        # Button to add another row for more updates
        closeContainer.button(
            label = 'Add Update Point', icon = ':material/add:', 
            on_click = addFormRow, key = f'closeAdd{id}', args = (
                f'closeRowCount{id}', {
                    f'closeCycle{id}-{closeRowCount}': 29,
                    f'closeNewRate{id}-{closeRowCount}': baseCloseValue
                }
            ), 
            disabled = not closeActive or not closeRowCount < 10, help = '''
                Add another row to this form, where you can select an 
                additional point in the simulation where school closure 
                compliance will change.
            ''' if closeRowCount <= 9 else '''
                To keep the number of parameters manageable, the values 
                of each parameter may not be changed more than 10 times 
                in a single simulation.
            '''
        )



        # Reduced Background Contact Count
        st.subheader('Reduced Background Contact Count')
        # Save relevant parameters as variables to avoid lookups
        bccRowCount = st.session_state[f'bccRowCount{id}']
        baseBCCValue = st.session_state[f'bccReducedRate{id}']
        bccActive = st.session_state[f'bccToggle{id}']
        bccContainer = st.container()

        # Warn if BCC reduction is disabled
        if not bccActive: 
            if bccRowCount == 0: st.info(f'''
                Note: Background contact count (BCC) 
                reduction NPIs are currently disabled in 
                {'the baseline' if id == 0 else 'this'} scenario. As 
                such, any dynamic updates to reduced BCC made here will 
                not take effect unless you enable BCC reduction in the 
                "Vaccinations and NPIs" tab prior to running the 
                simulation.
            ''')
            else: st.warning(
            f'''
                Note: Background contact count (BCC) 
                reduction NPIs are currently disabled in 
                {'the baseline' if id == 0 else 'this'} scenario. As 
                such, the dynamic updates to reduced BCC that have been 
                defined here will not take effect unless you enable BCC 
                reduction in the "Vaccinations and NPIs" tab prior to 
                running the simulation.
            ''')
        
        for i in range(bccRowCount): 
            (
                bccCycleColumn, bccNewColumn, bccRemoveColumn
            ) = bccContainer.columns((0.4, 0.4, 0.2))
            # Cycle column
            with bccCycleColumn: st.select_slider(
                'Day to Update Parameter', range(720), 
                29, key = f'bccCycle{id}-{i}', disabled = not bccActive, 
                format_func = lambda x: f'Day {x + 1}', help = '''
                    The day of the simulation upon which the new value 
                    for reduced background contact count will come into 
                    effect.
                '''
            )
            # New value column
            with bccNewColumn: st.slider(
                ((
                    'New Reduced Background Contact Count '
                    '(Average Number of Interactions per Person)'
                )),
                0.0, 8.0, 0.2, disabled = not bccActive,
                key = f'bccNewRate{id}-{i}', help = '''
                    The average number of other people each individual 
                    will interact with in the background phase of the 
                    simulation (emulating interactions outside of 
                    simulated locations) while a BCC reduction 
                    intervention is in effect after the specified point 
                    in the simulation.
                '''
            )
            # Delete button column
            with bccRemoveColumn: st.button(
                label = 'Remove Update Point', icon = ':material/delete:', 
                key = f'bccRemove{id}-{i}', on_click = deleteFormRow, 
                disabled = not bccActive, args = (
                    i, f'bccRowCount{id}', {
                        f'bccCycle{id}-', f'bccNewRate{id}-'
                    }
                ),
                help = '''
                    Remove this row of the form and remove this change 
                    in reduced background contact count from the 
                    simulation.
                '''
            )
        # Button to add another row for more updates
        bccContainer.button(
            label = 'Add Update Point', icon = ':material/add:', 
            on_click = addFormRow, key = f'bccAdd{id}', args = (
                f'bccRowCount{id}', {
                    f'bccCycle{id}-{bccRowCount}': 29,
                    f'bccNewRate{id}-{bccRowCount}': baseBCCValue
                }
            ), 
            disabled = not bccActive or not bccRowCount < 10, help = '''
                Add another row to this form, where you can select an 
                additional point in the simulation where reduced 
                background contact count will change.
            ''' if bccRowCount <= 9 else '''
                To keep the number of parameters manageable, the values 
                of each parameter may not be changed more than 10 times 
                in a single simulation.
            '''
        )