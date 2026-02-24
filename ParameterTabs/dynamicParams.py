# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameters can change mid-simulation

# Imports
import logging
from typing import Literal, cast

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    hasDuplicates,
    idGet,
    loadKey,
    paramError,
    saveKey,
)
from ClientResources.ModelSchema import Parameters, dynamicIntervention

# Logging
dynamicLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.fragment
def buildDynamicTab(id: int):
    """
    Function to generate the dynamic parameters in a specified container
    with scenario differentiation

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.
    """
    # Initialise session variables needed by the disease forms
    sessionParameters = {
        f"seedRowCount{id}": 0,
        f"closeRowCount{id}": 0,
        f"bccRowCount{id}": 0,
        f"seedDynamicError{id}": 0,
        f"closeDynamicError{id}": 0,
        f"bccDynamicError{id}": 0,
    }
    for parameter, default in sessionParameters.items():
        st.session_state[parameter] = st.session_state.get(parameter, default)

    # Avoid flooding the container with errors when many dynamic
    # changes are defined for each parameter
    # firstSeedError, firstCloseError, firstBCCError = True, True, True

    # Tab Content
    # TODO: Sort rows from earliest to latest
    st.header("Dynamic Parameters")
    st.markdown(
        """
        This tab allows for specific parameters to change their
        values at predefined points throughout the simulation.
        Modifying parameters midway through the simulation can be
        used to simulate different events occurring in the
        simulation. For example, changes in infection seeding can
        be used to simulate the spike in cases following a border
        opening, while changing school closure compliance can
        simulate changing policies or increased public awareness of
        the disease.

        The parameters that support dynamic value changes are as
        follows:

        - Infection Seeding Rate
        - School Closure Compliance
        - Reduced Background Contact Count

        The initial value for Infection Seeding Rate can be changed
        in the "Infection Seeding" section of the "Disease" tab.
        The other two parameters can have their initial values
        changed in the "Vaccinations and NPIs" tab. School Closure
        Compliance is in the "School Closure" section, while
        Reduced Background Contact Count is in the "Background
        Contact Count Reduction" section.

        Note that since the latter two parameters are tied to
        non-pharmaceutical interventions (NPIs), any changes to
        their value made here will only affect the simulation if
        the corresponding NPI is active at that time.
    """
    )
    # globalErrorContainer = st.container()

    # Get simulation length for error checking
    simLength = st.session_state.get("cycleCount", 360)

    # Infection Seeding Rate
    st.subheader("Infection Seeding Rate")

    baseSeedValue = idGet("seedRate", id, 0.25)
    seedStart, seedEnd = idGet("seedPeriod", id, (1, 30))
    loadKey(
        "seedTimeForm",
        id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New Infection Seeding Rate": [baseSeedValue],
            },
        ),
        dataframe=True,
    )
    seedTimeForm = st.data_editor(
        session[f"seedTimeForm{id}"],
        num_rows="dynamic",
        key=f"_seedTimeForm{id}",
        on_change=saveKey,
        args=["seedTimeForm", id],
        kwargs={"dataframe": True},
        placeholder="Enter a value",
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=seedStart,
                max_value=seedEnd,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for infection
seeding rate will come into effect.
                """,
            ),
            "New Infection Seeding Rate": st.column_config.NumberColumn(
                "New Infection Seeding Rate (Average Individuals per Day)",
                required=True,
                default=baseSeedValue,
                min_value=0.0,
                help="""
The average number of individuals that will be infected directly via infection
seeding each cycle after the specified point in the simulation. Note that
each day of the simulation is 2 cycles.
                """,
            ),
        },
    )
    paramError(
        "seedingTimeFormDuplicates",
        id,
        lambda: hasDuplicates(seedTimeForm, "Day to Update Parameter"),
        f"""
            Error: The dynamic infection seeding form used by the {
                'baseline scenario' if id == 0
                else f'scenario named "{session[f'scenarioName{id}']}"'
            } contains duplicate update points. Each row of the form
            should specify a different day of the simulation.

            Please remove or change any rows of the Infection Seeding
            Rate form in :primary-badge[:material/manage_history: Dynamic]
            that use the same day as another row.
        """,
        True,
    )

    oldVarLengthForm = '''# Save relevant parameters as variables to avoid lookups
    seedRowCount = st.session_state[f"seedRowCount{id}"]
    baseSeedValue = idGet("seedRate", id, 0.25)
    seedStart, seedEnd = idGet("seedPeriod", id, (0, 29))
    seedErrorContainer = st.container()
    seedContainer = st.container()
    # TODO: Update errors after variable length forms are replaced
    for i in range(seedRowCount):
        (seedCycleColumn, seedNewColumn, seedRemoveColumn) = seedContainer.columns(
            (0.4, 0.4, 0.2), vertical_alignment="center"
        )
        # Cycle column
        loadKey("seedCycle", id, 15, f"-{i}")
        with seedCycleColumn:
            seedUpdatePoint = st.number_input(
                "Day to Update Parameter",
                1,
                720,
                15,
                key=f"_seedCycle{id}-{i}",
                on_change=saveKey,
                args=["seedCycle", id, f"-{i}"],  # type: ignore
                placeholder="Enter the day number",
                help="""
                    The day of the simulation upon which the new
                    value for infection seeding rate will come into
                    effect.
                """,
            )
            # Show error if time is outside of sim/seed periods
            if firstSeedError and seedUpdatePoint >= simLength:
                seedErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the infection seeding rate for this
                    scenario is set to dynamically change on Day
                    {seedUpdatePoint + 1}. As such, the change in
                    the parameter's value will have no effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Infection
                    Seeding Rate in the scenario that are set to
                    values above Day {simLength}.
                    - Move the Day to Update Parameter of all
                    update points for Infection Seeding Rate in the
                    scenario to any point before Day {simLength}.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {seedUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the infection seeding rate for this
                    scenario is set to dynamically change on Day
                    {seedUpdatePoint + 1}. As such, the change in
                    the parameter's value will have no effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Infection
                    Seeding Rate in the scenario's "Dynamic" tab
                    that are set to values above Day {simLength}.
                    - Move the Day to Update Parameter of all
                    update points for Infection Seeding Rate in the
                    scenario's "Dynamic" tab to any point before
                    Day {simLength}.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {seedUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"seedDynamicError{id}"] = 2
                firstSeedError = False
            elif firstSeedError and (
                seedUpdatePoint < seedStart or seedUpdatePoint > seedEnd
            ):
                seedErrorContainer.error(
                    f"""
                    Error: The infection seeding period for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {seedStart + 1}
                    and end on Day {seedEnd + 1}, but the infection
                    seeding rate for this
                    scenario is set to dynamically change on Day
                    {seedUpdatePoint + 1}. The change in the
                    seeding rate's value will thus have no effect,
                    as it is outside the seeding period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Infection
                    Seeding Rate in the scenario that are set to
                    values below Day {seedStart + 1} or above Day {
                        seedEnd + 1
                    }.
                    - Move the Day to Update Parameter of all
                    update points for Infection Seeding Rate in the
                    scenario to any point between Day
                    {seedStart + 1} and Day {seedEnd + 1}.
                    - Modify the scenario's Infection Seeding Time
                    Period in the "Infection Seeding" section of
                    the "Disease" tab to include Day {
                        seedUpdatePoint + 1
                    }.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The infection seeding period for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {seedStart + 1}
                    and end on Day {seedEnd + 1}, but the infection
                    seeding rate for this
                    scenario is set to dynamically change on Day
                    {seedUpdatePoint + 1}. The change in the
                    seeding rate's value will thus have no effect,
                    as it is outside the seeding period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Infection
                    Seeding Rate in the scenario's "Dynamic" tab
                    that are set to values below Day
                    {seedStart + 1} or above Day {seedEnd + 1}.
                    - Move the Day to Update Parameter of all
                    update points for Infection Seeding Rate in the
                    scenario's "Dynamic" tab to any point between
                    Day {seedStart + 1} and Day {seedEnd + 1}.
                    - Modify the scenario's Infection Seeding Time
                    Period in the "Infection Seeding" section of
                    the "Disease" tab to include Day {
                        seedUpdatePoint + 1
                    }.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"seedDynamicError{id}"] = 2
                firstSeedError = False
            else:
                st.session_state[f"seedDynamicError{id}"] = 0
        # New value column
        loadKey("seedNewRate", id, 0.25, f"-{i}")
        with seedNewColumn:
            st.select_slider(
                "New Value (Average Individuals per Day)",
                np.linspace(0.025, 5.0, 200),
                0.25,
                key=f"_seedNewRate{id}-{i}",
                on_change=saveKey,
                args=["seedNewRate", id, f"-{i}"],  # type: ignore
                format_func=lambda x: f"{x:0.4g}",
                help="""
                The average number of individuals that will be
                infected directly via infection seeding each cycle
                after the specified point in the simulation.
            """,
            )
        # Delete button column
        with seedRemoveColumn:
            st.button(
                label="Remove Update Point",
                icon=":material/delete:",
                key=f"seedRemove{id}-{i}",
                on_click=deleteFormRow,
                args=(i, f"seedRowCount{id}", {f"seedCycle{id}-", f"seedNewRate{id}-"}),
                help="""
                Remove this row of the form and remove this change
                in infection seeding rate from the simulation.
            """,
            )
    # Button to add another row for more updates
    seedContainer.button(
        label="Add Update Point",
        icon=":material/add:",
        on_click=addFormRow,
        key=f"seedAdd{id}",
        args=(
            f"seedRowCount{id}",
            {
                f"seedCycle{id}-{seedRowCount}": 29,
                f"seedNewRate{id}-{seedRowCount}": baseSeedValue,
            },
        ),
        disabled=not seedRowCount < 10,
        help=(
            """
            Add another row to this form, where you can select an
            additional point in the simulation where the infection
            seeding rate will change.
        """
            if seedRowCount <= 9
            else """
            To keep the number of parameters manageable, the values
            of each parameter may not be changed more than 10 times
            in a single simulation.
        """
        ),
    )'''

    # School Closure Compliance
    st.subheader("School Closure Compliance")
    closeActive = idGet("schoolClosureToggle", id, False)
    baseCloseValue = idGet("schoolClosureCompliance", id, 0.9)
    closeStart, closeEnd = (
        idGet("schoolClosurePeriod", id, (1, 60))
        if idGet("schoolClosureTrigger", id, "Always") == "Timed"
        else (1, simLength)
    )
    if not closeActive:
        st.info(
            f"""
                Note: School closures are currently disabled in
                {'the baseline' if id == 0 else 'this'} scenario. As
                such, dynamic updates to school closure compliance
                cannot be edited and will not take effect unless you enable the
                NPI in the "School Closure" section of the
                "Vaccinations and NPIs" tab prior to running the
                simulation.
            """,
            icon=":material/info:",
        )
    loadKey(
        "closeTimeForm",
        id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New School Closure Compliance": [baseCloseValue],
            },
        ),
        dataframe=True,
    )
    closeTimeForm = st.data_editor(
        session[f"closeTimeForm{id}"],
        num_rows="dynamic",
        key=f"_closeTimeForm{id}",
        on_change=saveKey,
        args=["closeTimeForm", id],
        kwargs={"dataframe": True},
        placeholder=(
            "Enter a value"
            if closeActive
            else "Enable school closures to add new update points"
        ),
        disabled=not closeActive,
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=closeStart,
                max_value=closeEnd,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for
school closure compliance will come into effect.
                """,
            ),
            "New School Closure Compliance": st.column_config.NumberColumn(
                "New School Closure Compliance (Probability)",
                required=True,
                default=baseCloseValue,
                min_value=0.0,
                max_value=1.0,
                format="percent",
                help="""
The probability that an individual will withdraw from schools when
they are closed after the specified point in the simulation.
                """,
            ),
        },
    )
    paramError(
        "schoolClosureTimeFormDuplicates",
        id,
        lambda: closeActive and hasDuplicates(closeTimeForm, "Day to Update Parameter"),
        f"""
            Error: The dynamic school closure compliance form used by the {
                'baseline scenario' if id == 0
                else f'scenario named "{session[f'scenarioName{id}']}"'
            } contains duplicate update points. Each row of the form
            should specify a different day of the simulation.

            Please remove or change any rows of the School Closure Compliance
            form in :primary-badge[:material/manage_history: Dynamic]
            that use the same day as another row.
        """,
        True,
    )

    oldVarLengthForm = '''# Save relevant parameters as variables to avoid lookups
    closeRowCount = st.session_state[f"closeRowCount{id}"]
    baseCloseValue = idGet("schoolClosureCompliance", id, 0.9)
    closeActive = idGet("schoolClosureToggle", id, False)
    closeTrigger = idGet("schoolClosureTrigger", id, "Always")
    # TODO: Make sure closure period uses new system
    closeStart, closeEnd = idGet("schoolClosurePeriod", id, (29, 59))
    # Warn if school closure is disabled
    if not closeActive:
        if closeRowCount == 0:
            st.info(
                f"""
            Note: School closures are currently disabled in
            {'the baseline' if id == 0 else 'this'} scenario. As
            such, any dynamic updates to school closure compliance
            made here will not take effect unless you enable the
            NPI in the "School Closure" section of the
            "Vaccinations and NPIs" tab prior to running the
            simulation.
        """,
                icon=":material/info:",
            )
        else:
            st.warning(
                f"""
            Note: School closures are currently disabled in
            {'the baseline' if id == 0 else 'this'} scenario. As
            such, the dynamic updates to school closure compliance
            that have been defined here will not take effect unless
            you enable the NPI in the "School Closure" section of
            the "Vaccinations and NPIs" tab prior to running the
            simulation.
        """,
                icon=":material/warning:",
            )
    closeErrorContainer = st.container()
    closeContainer = st.container()
    for i in range(closeRowCount):
        (closeCycleColumn, closeNewColumn, closeRemoveColumn) = closeContainer.columns(
            (0.4, 0.4, 0.2), vertical_alignment="center"
        )
        # Cycle column
        loadKey("closeCycle", id, 15, f"-{i}")
        with closeCycleColumn:
            closeUpdatePoint = st.number_input(
                "Day to Update Parameter",
                0,
                720,
                15,
                key=f"_closeCycle{id}-{i}",
                disabled=not closeActive,
                on_change=saveKey,
                args=["closeCycle", id, f"-{i}"],  # type: ignore
                format_func=lambda x: f"Day {x + 1}",
                help="""
                    The day of the simulation upon which the new
                    value for school closure compliance will come
                    into effect.
                """,
            )
            # Display error if update point is beyond sim length
            if firstCloseError and closeUpdatePoint >= simLength:
                closeErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the school closure compliance probability
                    for this scenario is set to dynamically change
                    on Day {closeUpdatePoint + 1}. As such, the
                    change in the parameter's value will have no
                    effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for School Closure
                    Compliance in the scenario that are set to
                    values above Day {simLength}.
                    - Move the Day to Update Parameter of all
                    update points for School Closure Compliance in
                    the scenario to any point before Day {
                        simLength
                    }.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {closeUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the school closure compliance probability
                    for this scenario is set to dynamically change
                    on Day {closeUpdatePoint + 1}. As such, the
                    change in the parameter's value will have no
                    effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for School Closure
                    Compliance in the scenario's "Dynamic" tab that
                    are set to values above Day {simLength}.
                    - Move the Day to Update Parameter of all
                    update points for School Closure Compliance in
                    the scenario's "Dynamic" tab to any point
                    before Day {simLength}.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {closeUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"closeDynamicError{id}"] = 2
                firstCloseError = False
            elif (
                firstCloseError
                and closeTrigger == "Timed"
                and (closeUpdatePoint < closeStart or closeUpdatePoint > closeEnd)
            ):
                closeErrorContainer.error(
                    f"""
                    Error: The school closure NPI for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {closeStart + 1}
                    and end on Day {closeEnd + 1}, but the school
                    closure compliance probability for this
                    scenario is set to dynamically change on Day
                    {closeUpdatePoint + 1}. The change in the
                    probability's value will thus have no effect,
                    as it is outside the NPI's active period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for School Closure
                    Compliance in the scenario that are set to
                    values below Day {closeStart + 1} or above Day {
                        closeEnd + 1
                    }.
                    - Move the Day to Update Parameter of all
                    update points for School Closure Compliance in
                    the scenario to any point between Day
                    {closeStart + 1} and Day {closeEnd + 1}.
                    - Change the scenario's School Closure Trigger
                    Condition in the "School Closure" section of
                    the "Vaccinations and NPIs" tab to any option
                    other than "Timed".
                    - Modify the scenario's School Closure Time
                    Period in the "School Closure" section of the
                    "Vaccinations and NPIs" tab to include Day {
                        closeUpdatePoint + 1
                    }.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The school closure NPI for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {closeStart + 1}
                    and end on Day {closeEnd + 1}, but the school
                    closure compliance probability for this
                    scenario is set to dynamically change on Day
                    {closeUpdatePoint + 1}. The change in the
                    probability's value will thus have no effect,
                    as it is outside the NPI's active period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for School Closure
                    Compliance in the scenario's "Dynamic" tab that
                    are set to values below Day {closeStart + 1} or
                    above Day {closeEnd + 1}.
                    - Move the Day to Update Parameter of all
                    update points for School Closure Compliance in
                    the scenario's "Dynamic" tab to any point
                    between Day {closeStart + 1} and Day {
                        closeEnd + 1
                    }.
                    - Change the scenario's School Closure Trigger
                    Condition in the "School Closure" section of
                    the "Vaccinations and NPIs" tab to any option
                    other than "Timed".
                    - Modify the scenario's School Closure Time
                    Period in the "School Closure" section of the
                    "Vaccinations and NPIs" tab to include Day {
                        closeUpdatePoint + 1
                    }.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"closeDynamicError{id}"] = 2
                firstCloseError = False
            else:
                st.session_state[f"closeDynamicError{id}"] = 0
        # New value column
        loadKey("closeNewRate", id, 0.9, f"-{i}")
        with closeNewColumn:
            st.select_slider(
                "New Value (Probability)",
                np.linspace(0.0, 1.0, 201),
                0.9,
                key=f"_closeNewRate{id}-{i}",
                disabled=not closeActive,
                on_change=saveKey,
                args=["closeNewRate", id, f"-{i}"],  # type: ignore
                format_func=lambda x: f"{100 * x:0.3g}%",
                help="""
                The probability that an individual will withdraw
                from schools when they are closed after the
                specified point in the simulation.
            """,
            )
        # Delete button column
        with closeRemoveColumn:
            st.button(
                label="Remove Update Point",
                icon=":material/delete:",
                key=f"closeRemove{id}-{i}",
                on_click=deleteFormRow,
                disabled=not closeActive,
                args=(
                    i,
                    f"closeRowCount{id}",
                    {f"closeCycle{id}-", f"closeNewRate{id}-"},
                ),
                help="""
                Remove this row of the form and remove this change
                in school closure compliance from the simulation.
            """,
            )
    # Button to add another row for more updates
    closeContainer.button(
        label="Add Update Point",
        icon=":material/add:",
        on_click=addFormRow,
        key=f"closeAdd{id}",
        args=(
            f"closeRowCount{id}",
            {
                f"closeCycle{id}-{closeRowCount}": 29,
                f"closeNewRate{id}-{closeRowCount}": baseCloseValue,
            },
        ),
        disabled=not closeActive or not closeRowCount < 10,
        help=(
            """
            Add another row to this form, where you can select an
            additional point in the simulation where school closure
            compliance will change.
        """
            if closeRowCount <= 9
            else """
            To keep the number of parameters manageable, the values
            of each parameter may not be changed more than 10 times
            in a single simulation.
        """
        ),
    )'''

    # Reduced Background Contact Count
    st.subheader("Reduced Background Contact Count")
    bccActive = idGet("bccToggle", id, False)
    baseBCCValue = idGet("bccReducedRate", id, 0.2)
    bccStart, bccEnd = (
        idGet("bccPeriod", id, (1, 60))
        if idGet("bccTrigger", id, "Always") == "Timed"
        else (1, simLength)
    )
    if not bccActive:
        st.info(
            f"""
                Note: Background contact count reduction is currently disabled in
                {'the baseline' if id == 0 else 'this'} scenario. As
                such, dynamic updates to the reduced BCC cannot be edited
                and will not take effect unless you enable the
                NPI in the "Background Contact Count Reduction" section of the
                "Vaccinations and NPIs" tab prior to running the
                simulation.
            """,
            icon=":material/info:",
        )
    loadKey(
        "bccTimeForm",
        id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New Reduced Background Contact Count": [baseBCCValue],
            },
        ),
        dataframe=True,
    )
    bccTimeForm = st.data_editor(
        session[f"bccTimeForm{id}"],
        num_rows="dynamic",
        key=f"_bccTimeForm{id}",
        on_change=saveKey,
        args=["bccTimeForm", id],
        kwargs={"dataframe": True},
        placeholder=(
            "Enter a value"
            if bccActive
            else "Enable BCC reduction to add new update points"
        ),
        disabled=not bccActive,
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=bccStart,
                max_value=bccEnd,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for
reduced background contact count will come into effect.
                """,
            ),
            "New Reduced Background Contact Count": st.column_config.NumberColumn(
                (
                    "Reduced Background Contact Count (Average "
                    "Number of Interactions per Person per Day)"
                ),
                required=True,
                default=baseBCCValue,
                min_value=0.0,
                help="""
The average number of other people each individual will interact with in
the background phase of each day in the simulation (emulating interactions
outside of simulated locations) while a BCC reduction intervention is in
effect, overwriting the normal BCC rate.
                """,
            ),
        },
    )
    paramError(
        "bccReductionTimeFormDuplicates",
        id,
        lambda: bccActive and hasDuplicates(bccTimeForm, "Day to Update Parameter"),
        f"""
            Error: The dynamic background contact count reduction form used by the {
                'baseline scenario' if id == 0
                else f'scenario named "{session[f'scenarioName{id}']}"'
            } contains duplicate update points. Each row of the form
            should specify a different day of the simulation.

            Please remove or change any rows of the Reduced Background Contact
            Count form in :primary-badge[:material/manage_history: Dynamic]
            that use the same day as another row.
        """,
        True,
    )

    oldVarLengthForm = '''# Save relevant parameters as variables to avoid lookups
    bccRowCount = st.session_state[f"bccRowCount{id}"]
    baseBCCValue = idGet("bccReducedRate", id, 0.2)
    bccActive = idGet("bccToggle", id, False)
    bccTrigger = idGet("bccTrigger", id, "Always")
    bccStart, bccEnd = idGet("bccPeriod", id, (30, 60))
    # Warn if BCC reduction is disabled
    if not bccActive:
        if bccRowCount == 0:
            st.info(
                f"""
            Note: Background contact count (BCC)
            reduction NPIs are currently disabled in
            {'the baseline' if id == 0 else 'this'} scenario. As
            such, any dynamic updates to reduced BCC made here will
            not take effect unless you enable the NPI in the
            "Background Contact Count Reduction" section of the
            "Vaccinations and NPIs" tab prior to running the
            simulation.
        """,
                icon=":material/info:",
            )
        else:
            st.warning(
                f"""
            Note: Background contact count (BCC)
            reduction NPIs are currently disabled in
            {'the baseline' if id == 0 else 'this'} scenario. As
            such, the dynamic updates to reduced BCC that have been
            defined here will not take effect unless you enable the
            NPI in the "Background Contact Count Reduction" section
            of the "Vaccinations and NPIs" tab prior to running the
            simulation.
        """,
                icon=":material/warning:",
            )
    bccErrorContainer = st.container()
    bccContainer = st.container()
    for i in range(bccRowCount):
        (bccCycleColumn, bccNewColumn, bccRemoveColumn) = bccContainer.columns(
            (0.4, 0.4, 0.2), vertical_alignment="center"
        )
        # Cycle column
        loadKey("bccCycle", id, 15, f"-{i}")
        with bccCycleColumn:
            bccUpdatePoint = st.number_input(
                "Day to Update Parameter",
                0,
                720,
                15,
                key=f"_bccCycle{id}-{i}",
                disabled=not bccActive,
                on_change=saveKey,
                args=["bccCycle", id, f"-{i}"],  # type: ignore
                format_func=lambda x: f"Day {x + 1}",
                help="""
                    The day of the simulation upon which the new value
                    for reduced background contact count will come into
                    effect.
                """,
            )
            # Display error if update point is beyond sim length
            if firstBCCError and bccUpdatePoint >= simLength:
                bccErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the reduced background contact count value
                    for this scenario is set to dynamically change
                    on Day {bccUpdatePoint + 1}. As such, the
                    change in the parameter's value will have no
                    effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Reduced BCC in
                    the scenario that are set to values above Day {
                        simLength
                    }.
                    - Move the Day to Update Parameter of all
                    update points for Reduced BCC in the scenario
                    to any point before Day {simLength}.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {bccUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to last {simLength} days,
                    but the reduced background contact count value
                    for this scenario is set to dynamically change
                    on Day {bccUpdatePoint + 1}. As such, the
                    change in the parameter's value will have no
                    effect.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Reduced BCC in
                    the scenario's "Dynamic" tab that are set to
                    values above Day {simLength}.
                    - Move the Day to Update Parameter of all
                    update points for Reduced BCC in the scenario's
                    "Dynamic" tab to any point before Day {
                        simLength
                    }.
                    - Increase the scenario's Length of Simulation
                    in the "Initialisation" tab to be
                    {bccUpdatePoint + 1} days or more.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"bccDynamicError{id}"] = 2
                firstBCCError = False
            elif (
                firstBCCError
                and bccTrigger == "Timed"
                and (bccUpdatePoint < bccStart or bccUpdatePoint > bccEnd)
            ):
                bccErrorContainer.error(
                    f"""
                    Error: The reduced background contact count NPI
                    for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {bccStart + 1}
                    and end on Day {bccEnd + 1}, but the reduced
                    background contact count value for this
                    scenario is set to dynamically change on Day
                    {bccUpdatePoint + 1}. The change in the
                    parameter's value will thus have no effect, as
                    it is outside the NPI's active period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Reduced BCC in
                    the scenario that are set to values below Day
                    {bccStart + 1} or above Day {bccEnd + 1}.
                    - Move the Day to Update Parameter of all
                    update points for Reduced BCC in the scenario
                    to any point between Day {bccStart + 1} and
                    Day {bccEnd + 1}.
                    - Change the scenario's BCC Reduction Trigger
                    Condition in the "Background Contact Count
                    Reduction" section of the "Vaccinations and
                    NPIs" tab to any option other than "Timed".
                    - Modify the scenario's BCC Reduction Time
                    Period in the "Background Contact Count
                    Reduction" section of the "Vaccinations and
                    NPIs" tab to include Day {bccUpdatePoint + 1}.
                """,
                    icon=":material/error:",
                )
                globalErrorContainer.error(
                    f"""
                    Error: The reduced background contact count NPI
                    for the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            st.session_state[f'scenarioName{id}']
                        }"'
                    } is currently set to begin on Day {bccStart + 1}
                    and end on Day {bccEnd + 1}, but the reduced
                    background contact count value for this
                    scenario is set to dynamically change on Day
                    {bccUpdatePoint + 1}. The change in the
                    parameter's value will thus have no effect, as
                    it is outside the NPI's active period.

                    To address this error, please make one of the
                    following changes before running the simulation:

                    - Remove any update points for Reduced BCC in
                    the scenario's "Dynamic" tab that are set to
                    values below Day {bccStart + 1} or above Day {
                        bccEnd + 1
                    }.
                    - Move the Day to Update Parameter of all
                    update points for Reduced BCC in the scenario's
                    "Dynamic" tab to any point between Day
                    {bccStart + 1} and Day {bccEnd + 1}.
                    - Change the scenario's BCC Reduction Trigger
                    Condition in the "Background Contact Count
                    Reduction" section of the "Vaccinations and
                    NPIs" tab to any option other than "Timed".
                    - Modify the scenario's BCC Reduction Time
                    Period in the "Background Contact Count
                    Reduction" section of the "Vaccinations and
                    NPIs" tab to include Day {bccUpdatePoint + 1}.
                """,
                    icon=":material/error:",
                )
                st.session_state[f"bccDynamicError{id}"] = 2
                firstBCCError = False
            else:
                st.session_state[f"bccDynamicError{id}"] = 0

        # New value column
        loadKey("bccNewRate", id, 0.2, f"-{i}")
        with bccNewColumn:
            st.slider(
                "New Value (Average Interactions/Person)",
                0.0,
                8.0,
                0.2,
                disabled=not bccActive,
                on_change=saveKey,
                args=["bccNewRate", id, f"-{i}"],  # type: ignore
                key=f"_bccNewRate{id}-{i}",
                help="""
                The average number of other people each individual
                will interact with in the background phase of the
                simulation (emulating interactions outside of
                simulated locations) while a BCC reduction
                intervention is in effect after the specified point
                in the simulation.
            """,
            )
        # Delete button column
        with bccRemoveColumn:
            st.button(
                label="Remove Update Point",
                icon=":material/delete:",
                key=f"bccRemove{id}-{i}",
                on_click=deleteFormRow,
                disabled=not bccActive,
                args=(i, f"bccRowCount{id}", {f"bccCycle{id}-", f"bccNewRate{id}-"}),
                help="""
                Remove this row of the form and remove this change
                in reduced background contact count from the
                simulation.
            """,
            )
    # Button to add another row for more updates
    bccContainer.button(
        label="Add Update Point",
        icon=":material/add:",
        on_click=addFormRow,
        key=f"bccAdd{id}",
        args=(
            f"bccRowCount{id}",
            {
                f"bccCycle{id}-{bccRowCount}": 29,
                f"bccNewRate{id}-{bccRowCount}": baseBCCValue,
            },
        ),
        disabled=not bccActive or not bccRowCount < 10,
        help=(
            """
            Add another row to this form, where you can select an
            additional point in the simulation where reduced
            background contact count will change.
        """
            if bccRowCount <= 9
            else """
            To keep the number of parameters manageable, the values
            of each parameter may not be changed more than 10 times
            in a single simulation.
        """
        ),
    )'''


def paramCast(x: str):
    """
    Simple function to convert strings into literals for the purpose of type validation

    Parameters:
        x (str): shorthand for the key to cast
    """
    # TODO: Add any new dynamic parameters
    return cast(
        Literal[
            "work_nonattendance",
            "bcc_reduction",
            "school_closure",
            "seed_rate",
            "school_closure_delay",
            "school_closure_duration",
        ],
        {
            "seed": "seed_rate",
            "close": "school_closure",
            "bcc": "bcc_reduction",
        }[x],
    )


def dynamicSchema(schema: Parameters, id: int = 0):
    """
    Function to populate the Pydantic model schema with the parameters in
    this tab with scenario differentiation

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.
    """
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Scenario Dynamic Intervention
        dynamicChanges = []

        for prefix, default in {
            "seed": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Infection Seeding Rate": [idGet("seedRate", id, 0.25)],
                },
            ),
            "close": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New School Closure Compliance": [
                        idGet("schoolClosureCompliance", id, 0.9)
                    ],
                },
            ),
            "bcc": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Reduced Background Contact Count": [
                        idGet("bccReducedRate", id, 0.2)
                    ],
                },
            ),
        }.items():
            timeForm = idGet(f"{prefix}TimeForm", id, default)
            for time, newValue in zip(timeForm.iloc[:, 0], timeForm.iloc[:, 1]):
                if time:
                    dynamicChanges.append(
                        dynamicIntervention(
                            Name=paramCast(prefix),
                            CycleOffset=(time - 1) * 2,
                            NewValue=newValue,
                        )
                    )

        oldVarLengthForm = """for prefix, default in {
            "seed": idGet("seedRate", id, 0.25),
            "close": idGet("schoolClosureCompliance", id, 0.9),
            "bcc": idGet("bccReducedRate", id, 0.2),
        }.items():
            for i in range(st.session_state.get(f"{prefix}RowCount{id}", 0)):
                dynamicChanges.append(
                    dynamicIntervention(
                        Name=paramCast(prefix),
                        CycleOffset=idGet(f"{prefix}Cycle", id, 15, f"-{i}") * 2,
                        NewValue=idGet(f"{prefix}NewRate", id, default, f"-{i}"),
                    )
                )"""
        # Save the updated parameters
        if dynamicChanges:
            schema.Scenario_DynamicIntervention = dynamicChanges
    except (ValueError, ValidationError) as e:
        dynamicLog.error(
            (
                f"[dynamicParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e
