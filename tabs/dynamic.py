# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where parameters can change mid-simulation

# Imports
import logging
from typing import Literal, cast

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from resources.interface import param_error
from resources.model_schema import (
    DynamicIntervention,
    DynamicParameter,
    Parameters,
)
from resources.parameter import (
    has_duplicates,
    id_get,
    load_key,
    save_key,
    update_table_from_schema,
)

# Logging
dynamic_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# @st.fragment
def build_dynamic_tab(scenario_id: int):
    """
    Function to generate the dynamic parameters in a specified container
    with scenario differentiation.

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables.
    """

    # Tab Content
    # TODO: Sort rows from earliest to latest
    st.header("Dynamic Parameters")
    st.markdown("""
This tab allows for specific parameters to change their values at predefined
points throughout the simulation. Modifying parameters midway through the
simulation can be used to simulate different events occurring in the
simulation. For example, changes in infection seeding can be used to simulate
the spike in cases following a border opening, while changing school closure
compliance can simulate changing policies or increased public awareness of the
pathogen.

The parameters that support dynamic value changes are as follows:

- Infection Seeding Rate
- School Closure Compliance
- Reduced Background Contact Count

The initial value for Infection Seeding Rate can be changed in the "Infection
Seeding" section of :primary-badge[:material/coronavirus: Pathogen]. The other
two parameters can have their initial values changed in
:primary-badge[:material/medical_mask: NPIs]. School Closure Compliance is in
the "School Closure" section, while Reduced Background Contact Count is in the
"Background Contact Count Reduction" section.

Note that since the latter two parameters are tied to non-pharmaceutical
interventions (NPIs), any changes to their value made here will only affect the
simulation if the corresponding NPI is active at that time.
    """)

    # Get simulation length for error checking
    sim_length = session.get("cycle_count", 360)

    # Infection Seeding Rate
    st.subheader("Infection Seeding Rate")
    st.markdown("Double-click a cell in this table to edit its value.")

    base_seeding_rate = id_get("seeding_rate", scenario_id, 0.25)
    seeding_start, seeding_end = id_get("seeding_period", scenario_id, (1, 30))
    load_key(
        "seed_rate_dynamic_form",
        scenario_id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New Infection Seeding Rate": [base_seeding_rate],
            },
        ),
        dataframe=True,
    )
    seed_rate_dynamic_form = st.data_editor(
        session[f"seed_rate_dynamic_form{scenario_id}"],
        height="content",
        num_rows="dynamic",
        key=f"_seed_rate_dynamic_form{scenario_id}",
        on_change=save_key,
        args=["seed_rate_dynamic_form", scenario_id],
        kwargs={"dataframe": True},
        placeholder="Enter a value",
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=seeding_start,
                max_value=seeding_end,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for infection seeding rate
will come into effect.
                """,
            ),
            "New Infection Seeding Rate": st.column_config.NumberColumn(
                "New Infection Seeding Rate (Average Individuals per Day)",
                required=True,
                default=base_seeding_rate,
                min_value=0.0,
                help="""
The average number of individuals that will be infected directly via infection
seeding each cycle after the specified point in the simulation. Note that each
day of the simulation is 2 cycles.
                """,
            ),
        },
    )
    param_error(
        "dynamic_seeding_duplicates",
        scenario_id,
        lambda: has_duplicates(seed_rate_dynamic_form, "Day to Update Parameter"),
        f"""
Error: The dynamic infection seeding form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate update points. Each row of the form should specify a
different day of the simulation.

Please remove or change any rows of the Infection Seeding Rate form in
:primary-badge[:material/manage_history: Dynamic] that use the same day as
another row.
        """,
        True,
    )

    # TODO: Consider hiding inactive forms (e.g. school closure compliance
    # when school closures are disabled) instead of merely disabling input

    # School Closure Compliance
    st.subheader("School Closure Compliance")
    using_school_closure = id_get("school_closure_toggle", scenario_id, False)
    base_school_closure_compliance = id_get(
        "school_closure_compliance", scenario_id, 0.9
    )
    school_closure_start, school_closure_end = (
        id_get("school_closure_period", scenario_id, (1, 60))
        if id_get("school_closure_trigger", scenario_id, "Always") == "Timed"
        else (1, sim_length)
    )
    if not using_school_closure:
        st.info(
            f"""
Note: School closures are currently disabled in
{'the baseline' if scenario_id == 0 else 'this'} scenario. As such, dynamic
updates to school closure compliance cannot be edited and will not take effect
unless you enable the NPI in the "School Closure" section of
:primary-badge[:material/medical_mask: NPIs] prior to running the simulation.
            """,
            icon=":material/info:",
        )
    else:
        st.markdown("Double-click a cell in this table to edit its value.")
    load_key(
        "school_closure_dynamic_form",
        scenario_id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New School Closure Compliance": [base_school_closure_compliance],
            },
        ),
        dataframe=True,
    )
    school_closure_dynamic_form = st.data_editor(
        session[f"school_closure_dynamic_form{scenario_id}"],
        height="content",
        num_rows="dynamic",
        key=f"_school_closure_dynamic_form{scenario_id}",
        on_change=save_key,
        args=["school_closure_dynamic_form", scenario_id],
        kwargs={"dataframe": True},
        placeholder=(
            "Enter a value"
            if using_school_closure
            else "Enable school closures to add new update points"
        ),
        disabled=not using_school_closure,
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=school_closure_start,
                max_value=school_closure_end,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for school closure
compliance will come into effect.
                """,
            ),
            "New School Closure Compliance": st.column_config.NumberColumn(
                "New School Closure Compliance (Probability)",
                required=True,
                default=base_school_closure_compliance,
                min_value=0.0,
                max_value=1.0,
                format="percent",
                help="""
The probability that an individual will withdraw from schools when they are
closed after the specified point in the simulation.
                """,
            ),
        },
    )
    param_error(
        "dynamic_school_closure_duplicates",
        scenario_id,
        lambda: using_school_closure
        and has_duplicates(school_closure_dynamic_form, "Day to Update Parameter"),
        f"""
Error: The dynamic school closure compliance form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate update points. Each row of the form should specify a
different day of the simulation.

Please remove or change any rows of the School Closure Compliance form in
:primary-badge[:material/manage_history: Dynamic] that use the same day as
another row.
        """,
        True,
    )

    # Reduced Background Contact Count
    st.subheader("Reduced Background Contact Count")
    using_bcc_reduction = id_get("bcc_reduction_toggle", scenario_id, False)
    base_bcc_reduction = id_get("bcc_reduced_rate", scenario_id, 0.2)
    bcc_reduction_start, bcc_reduction_end = (
        id_get("bcc_reduction_period", scenario_id, (1, 60))
        if id_get("bcc_reduction_trigger", scenario_id, "Always") == "Timed"
        else (1, sim_length)
    )
    if not using_bcc_reduction:
        st.info(
            f"""
Note: Background contact count reduction is currently disabled in
{'the baseline' if scenario_id == 0 else 'this'} scenario. As such, dynamic
updates to the reduced BCC cannot be edited and will not take effect unless you
enable the NPI in the "Background Contact Count Reduction" section of
:primary-badge[:material/medical_mask: NPIs] prior to running the simulation.
            """,
            icon=":material/info:",
        )
    else:
        st.markdown("Double-click a cell in this table to edit its value.")
    load_key(
        "bcc_reduction_dynamic_form",
        scenario_id,
        pd.DataFrame(
            {
                "Day to Update Parameter": [None],
                "New Reduced Background Contact Count": [base_bcc_reduction],
            },
        ),
        dataframe=True,
    )
    bcc_reduction_dynamic_form = st.data_editor(
        session[f"bcc_reduction_dynamic_form{scenario_id}"],
        height="content",
        num_rows="dynamic",
        key=f"_bcc_reduction_dynamic_form{scenario_id}",
        on_change=save_key,
        args=["bcc_reduction_dynamic_form", scenario_id],
        kwargs={"dataframe": True},
        placeholder=(
            "Enter a value"
            if using_bcc_reduction
            else "Enable BCC reduction to add new update points"
        ),
        disabled=not using_bcc_reduction,
        column_config={
            "Day to Update Parameter": st.column_config.NumberColumn(
                "Day to Update Parameter",
                required=True,
                min_value=bcc_reduction_start,
                max_value=bcc_reduction_end,
                format="Day %d",
                help="""
The day of the simulation upon which the new value for reduced background
contact count will come into effect.
                """,
            ),
            "New Reduced Background Contact Count": st.column_config.NumberColumn(
                (
                    "Reduced Background Contact Count (Average "
                    "Number of Interactions per Person per Day)"
                ),
                required=True,
                default=base_bcc_reduction,
                min_value=0.0,
                max_value=8.0,
                step=0.05,
                help="""
The average number of other people each individual will interact with in the
background phase of each day in the simulation (emulating interactions outside
of simulated locations) while a BCC reduction intervention is in effect,
overwriting the normal BCC rate.
                """,
            ),
        },
    )
    param_error(
        "dynamic_bcc_reduction_duplicates",
        scenario_id,
        lambda: using_bcc_reduction
        and has_duplicates(bcc_reduction_dynamic_form, "Day to Update Parameter"),
        f"""
Error: The dynamic background contact count reduction form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate update points. Each row of the form should specify a
different day of the simulation.

Please remove or change any rows of the Reduced Background Contact Count form
in :primary-badge[:material/manage_history: Dynamic] that use the same day as
another row.
        """,
        True,
    )


def dynamic_prefix_converter(x: str) -> Literal[
    "work_nonattendance",
    "bcc_reduction",
    "school_closure",
    "seed_rate",
    "school_closure_delay",
    "school_closure_duration",
]:
    """
    Simple function to convert strings into literals for the purpose of type
    validation.

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
            "seeding": "seed_rate",
            "close": "school_closure",
            "bcc": "bcc_reduction",
        }[x],
    )


def dynamic_save_schema(schema: Parameters, scenario_id: int = 0):
    """
    Function to populate the Pydantic model schema with dynamic parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.
    """
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Scenario Dynamic Intervention
        dynamic_changes = []
        dynamic_defaults: dict[DynamicParameter, pd.DataFrame] = {
            "seed_rate": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Infection Seeding Rate": [
                        id_get("seeding_rate", scenario_id, 0.25)
                    ],
                },
            ),
            "school_closure": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New School Closure Compliance": [
                        id_get("school_closure_compliance", scenario_id, 0.9)
                    ],
                },
            ),
            "bcc_reduction": pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Reduced Background Contact Count": [
                        id_get("bcc_reduced_rate", scenario_id, 0.2)
                    ],
                },
            ),
        }

        for prefix, default in dynamic_defaults.items():
            dynamic_form = id_get(f"{prefix}_dynamic_form", scenario_id, default)
            for time, new_value in zip(
                dynamic_form.iloc[:, 0], dynamic_form.iloc[:, 1]
            ):
                if time:
                    dynamic_changes.append(
                        DynamicIntervention(
                            Name=prefix,
                            CycleOffset=(time - 1) * 2,
                            NewValue=new_value,
                        )
                    )

        # Save the updated parameters
        if dynamic_changes:
            schema.Scenario_DynamicIntervention = dynamic_changes
    except (ValueError, ValidationError) as e:
        dynamic_log.error(
            f"[dynamic_save_schema] Encountered {type(e).__name__} while validating parameters for scenario {scenario_id}: {e}"
        )
        raise e


def dynamic_load_schema(schema: Parameters, scenario_id: int = 0):
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
    dynamic_changes = schema.Scenario_DynamicIntervention
    if dynamic_changes is None:
        return
    dynamic_tables = {
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
    dynamic_periods = {
        "seed_rate": id_get("seeding_period", scenario_id, (1, 30)),
        "school_closure": id_get("school_closure_period", scenario_id, (1, 60)),
        "bcc_reduction": id_get("bcc_reduction_period", scenario_id, (1, 60)),
    }
    for update in dynamic_changes:
        # Get value and append to correct dataframe
        param, time, new_value = (
            update.Name,
            round(update.CycleOffset / 2) + 1,
            update.NewValue,
        )
        min_time, max_time = dynamic_periods[param]
        time = min(max_time, max(min_time, time))
        current_table = dynamic_tables[param]
        current_table.loc[current_table.shape[0]] = [time, new_value]

    # Set the new tables into st.session_state, if they were updated at all
    param_converter = {
        "seed_rate": (
            "seed_rate_dynamic_form",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Infection Seeding Rate": [
                        id_get("seeding_rate", scenario_id, 0.25)
                    ],
                },
            ),
        ),
        "school_closure": (
            "school_closure_dynamic_form",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New School Closure Compliance": [
                        id_get("school_closure_compliance", scenario_id, 0.9)
                    ],
                },
            ),
        ),
        "bcc_reduction": (
            "bcc_reduction_dynamic_form",
            pd.DataFrame(
                {
                    "Day to Update Parameter": [None],
                    "New Reduced Background Contact Count": [
                        id_get("bcc_reduced_rate", scenario_id, 0.2)
                    ],
                },
            ),
        ),
    }
    for parameter, (key, default) in param_converter.items():
        update_table_from_schema(key, dynamic_tables[parameter], scenario_id, default)
