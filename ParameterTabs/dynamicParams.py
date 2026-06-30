# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameters can change mid-simulation

# Imports
import logging
from typing import Literal, cast

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import paramError
from ClientResources.ModelSchema import Parameters, dynamicIntervention
from ClientResources.ParameterFunctions import (
    hasDuplicates,
    idGet,
    loadKey,
    saveKey,
    updateTableFromSchema,
)

# Logging
dynamicLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.fragment
def buildDynamicTab(id: int):
    """
    Function to generate the dynamic parameters in a specified container
    with scenario differentiation.

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.
    """

    # Tab Content
    # TODO: Sort rows from earliest to latest
    st.header("Dynamic Parameters")
    st.markdown("""
        This tab allows for specific parameters to change their
        values at predefined points throughout the simulation.
        Modifying parameters midway through the simulation can be
        used to simulate different events occurring in the
        simulation. For example, changes in infection seeding can
        be used to simulate the spike in cases following a border
        opening, while changing school closure compliance can
        simulate changing policies or increased public awareness of
        the pathogen.

        The parameters that support dynamic value changes are as
        follows:

        - Infection Seeding Rate
        - School Closure Compliance
        - Reduced Background Contact Count

        The initial value for Infection Seeding Rate can be changed
        in the "Infection Seeding" section of
        :primary-badge[:material/coronavirus: Pathogen].
        The other two parameters can have their initial values
        changed in :primary-badge[:material/medical_mask: NPIs].
        School Closure Compliance is in the "School Closure" section, while
        Reduced Background Contact Count is in the "Background
        Contact Count Reduction" section.

        Note that since the latter two parameters are tied to
        non-pharmaceutical interventions (NPIs), any changes to
        their value made here will only affect the simulation if
        the corresponding NPI is active at that time.
    """)

    # Get simulation length for error checking
    simLength = session.get("cycleCount", 360)

    # Infection Seeding Rate
    st.subheader("Infection Seeding Rate")
    st.markdown("Double-click a cell in this table to edit its value.")

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
        height="content",
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

    # TODO: Consider hiding inactive forms (e.g. school closure compliance
    # when school closures are disabled) instead of merely disabling input

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
                NPI in the "School Closure" section of
                :primary-badge[:material/medical_mask: NPIs] prior to
                running the simulation.
            """,
            icon=":material/info:",
        )
    else:
        st.markdown("Double-click a cell in this table to edit its value.")
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
        height="content",
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
                NPI in the "Background Contact Count Reduction" section of
                :primary-badge[:material/medical_mask: NPIs] prior to running the
                simulation.
            """,
            icon=":material/info:",
        )
    else:
        st.markdown("Double-click a cell in this table to edit its value.")
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
        height="content",
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
                max_value=8.0,
                step=0.05,
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


def paramCast(x: str) -> Literal[
    "work_nonattendance",
    "bcc_reduction",
    "school_closure",
    "seed_rate",
    "school_closure_delay",
    "school_closure_duration",
]:
    """
    Simple function to convert strings into literals for the purpose of type validation.

    Parameters:
        x (str): Shorthand for the key to cast.

    Returns:
        Literal: A literal with the corresponding value.
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


def dynamicSaveSchema(schema: Parameters, id: int = 0):
    """
    Function to populate the Pydantic model schema with dynamic parameters
    using scenario differentiation.

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


def dynamicLoadSchema(schema: Parameters, scenarioID: int = 0):
    """
    Function to read dynamic parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.
    """
    dynamicChanges = schema.Scenario_DynamicIntervention
    if dynamicChanges is None:
        return
    dynamicTables = {
        "seed_rate": pd.DataFrame(
            columns=(
                "Day to Update Parameter",
                "New Infection Seeding Rate",
            )
        ),
        "school_closure": pd.DataFrame(
            columns=("Day to Update Parameter", "New School Closure Compliance"),
        ),
        "bcc_reduction": pd.DataFrame(
            columns=("Day to Update Parameter", "New Reduced Background Contact Count"),
        ),
    }
    dynamicPeriods = {
        "seed_rate": idGet("seedPeriod", scenarioID, (1, 30)),
        "school_closure": idGet("schoolClosurePeriod", scenarioID, (1, 60)),
        "bcc_reduction": idGet("bccPeriod", scenarioID, (1, 60)),
    }
    for update in dynamicChanges:
        # Get value and append to correct dataframe
        param, time, newValue = (
            update.Name,
            round(update.CycleOffset / 2) + 1,
            update.NewValue,
        )
        minTime, maxTime = dynamicPeriods[param]
        time = min(maxTime, max(minTime, time))
        currentTable = dynamicTables[param]
        currentTable.loc[currentTable.shape[0]] = [time, newValue]

    # Set the new tables into st.session_state, if they were updated at all
    paramConvert = {
        "seed_rate": (
            "seedTimeForm",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Infection Seeding Rate": [idGet("seedRate", scenarioID, 0.25)],
                },
            ),
        ),
        "school_closure": (
            "closeTimeForm",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New School Closure Compliance": [
                        idGet("schoolClosureCompliance", scenarioID, 0.9)
                    ],
                },
            ),
        ),
        "bcc_reduction": (
            "bccTimeForm",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Reduced Background Contact Count": [
                        idGet("bccReducedRate", scenarioID, 0.2)
                    ],
                },
            ),
        ),
    }
    for parameter, (key, default) in paramConvert.items():
        updateTableFromSchema(key, dynamicTables[parameter], scenarioID, default)
