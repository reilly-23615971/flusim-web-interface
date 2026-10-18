# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where NPI parameters can be modified

# Imports
import logging
from typing import Optional

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    age_display,
    param_error,
    schema_remove_baseline,
    schema_update,
)
from ClientResources.ModelSchema import (
    AllAgesParameters,
    DashboardParameters,
    GeneralParameters,
    Parameters,
)
from ClientResources.ParameterFunctions import (
    dynamic_scale_change,
    has_duplicates,
    id_get,
    load_key,
    save_key,
    update_param_from_schema,
    update_table_from_schema,
)
from ClientResources.Types import (
    AGE_GROUP_KEYS,
    COMMUNITIES,
    TRIGGER_KEY_CONVERTER,
)

# Logging
npi_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Names of the possible NPIs
NPI_NAMES = (
    "School Closure",
    "Withdrawal Increase",
    "Reduced Group Size",
    "Background Contact Count Reduction",
)
NPI_TAGS = ("school_closure", "withdrawal_increase", "reduced_group_size", "bcc")
TRIGGER_CONVERTER = {
    "none": "Always",
    "timed": "Timed",
    "community_rate": "Community Case Rate",
    "community_cases": "Community Case Total",
    "per_school_cases": "Cases per School",
}


# @st.fragment
def build_npi_tab(scenario_id: int, advanced: bool = False):
    """
    Function to generate the parameters for NPIs in a
    specified container with scenario differentiation.

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables.

        advanced (bool): Set to `True` to show more complex parameters like
            NPI trigger thresholds.
    """

    sim_length = session.get("cycle_count", 360)
    trigger_names = list(TRIGGER_KEY_CONVERTER.keys())[1:]

    # Tab Content
    st.header("Non-Pharmaceutical Intervention Parameters")
    st.markdown("""
This tab contains parameters relating to the non-pharmaceutical interventions
(NPIs) that are integrated into the simulation.
    """)

    # Load variables used by case rates
    school_closure_trigger, withdrawal_increase_trigger = None, None
    reduced_workgroup_trigger, bcc_reduction_trigger, class_dismissal = (
        None,
        None,
        None,
    )

    # General NPIs
    st.html('<span id = "general_trigger_condition"></span>')
    with st.expander(
        "Social Distancing", key=f"npi_container{scenario_id}", on_change="rerun"
    ) as distancing_container:
        if distancing_container.open:
            st.markdown("""
These parameters control the implementation of social distancing and related
non-pharmaceutical intervention (NPI) techniques, including case isolation and
class dismissal.
            """)

            # Case Isolation
            load_key("case_isolation", scenario_id, False)
            st.toggle(
                "Enable Diagnosed Case Isolation",
                value=False,
                on_change=save_key,
                args=["case_isolation", scenario_id],
                key=f"_case_isolation{scenario_id}",
                help="""
Toggle whether or not individuals who have been diagnosed as cases of the
pathogen will be forced to isolate at home.
                """,
            )

            # Class Dismissal (if advanced parameters are enabled)
            if advanced:
                load_key("class_dismissal", scenario_id, False)
                class_dismissal = st.toggle(
                    "Enable Class Dismissal",
                    value=False,
                    on_change=save_key,
                    args=["class_dismissal", scenario_id],
                    key=f"_class_dismissal{scenario_id}",
                    help="""
Toggle whether or not school classes should be dismissed when the daily case
rate is high enough.

Note that the rate that must be reached before class dismissal begins to occur
is shared with any other NPIs that are set to use case rates as their trigger
threshold.
                    """,
                )
                if class_dismissal:
                    # TODO: Update links to go directly to the desired location
                    st.info(
                        """
Due to the design of the *Flusim* model, the case rate thresholds used by class
dismissal must be defined globally for all NPIs. You may configure these
thresholds using the "Intervention Trigger Thresholds" parameters at the bottom
of this page (click [this link](#threshold_trigger_condition) to go there
directly).
                        """,
                        icon=":material/info:",
                    )

            # Social distancing
            load_key("social_distancing_toggle", scenario_id, False)
            use_social_distancing = st.toggle(
                "Enable Social Distancing",
                value=False,
                on_change=save_key,
                args=["social_distancing_toggle", scenario_id],
                key=f"_social_distancing_toggle{scenario_id}",
                help="""
Toggle whether or not social distancing interventions are implemented in the
simulation, overriding other social distancing parameters.
                """,
            )
            load_key("social_distancing_compliance", scenario_id, 0.9)
            social_distancing_compliance = round(
                st.slider(
                    "Social Distancing Compliance (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    format="percent",
                    disabled=not use_social_distancing,
                    on_change=save_key,
                    args=["social_distancing_compliance", scenario_id],
                    key=f"_social_distancing_compliance{scenario_id}",
                    help="""
The probability that an individual will comply with social distancing
interventions in the simulation.
                """,
                )
                * 100,
                6,
            )
            # Age-specific social distancing compliance (if advanced params enabled)
            # TODO: Check sim for social distance nuance
            if advanced:
                st.markdown(
                    "### Age-Specific Social Distancing Compliance",
                    help="""
This table allows for unique social distancing compliance values to be defined
for individual age groups in the simulation, overriding the global probability
defined above.
                    """,
                )
                if use_social_distancing:
                    st.markdown("Double-click a cell in this table to edit its value.")
                load_key(
                    "social_distancing_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Social Distancing Compliance": [
                                social_distancing_compliance
                            ],
                        },
                    ),
                    dataframe=True,
                )
                social_distancing_age_form = st.data_editor(
                    session[f"social_distancing_age_form{scenario_id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_social_distancing_age_form{scenario_id}",
                    on_change=save_key,
                    args=["social_distancing_age_form", scenario_id],
                    kwargs={"dataframe": True},
                    disabled=not use_social_distancing,
                    placeholder=(
                        "Enter a value"
                        if use_social_distancing
                        else "Enable social distancing to edit this parameter"
                    ),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have a specific social distancing compliance probability
defined for it, overriding the base probability.
                            """,
                        ),
                        "Social Distancing Compliance": st.column_config.NumberColumn(
                            "Social Distancing Compliance (Probability)",
                            required=True,
                            default=social_distancing_compliance,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The probability that an individual in this age group will comply with social
distancing interventions in the simulation.
                            """,
                        ),
                    },
                )
                param_error(
                    "social_distancing_duplicates",
                    scenario_id,
                    lambda: has_duplicates(social_distancing_age_form),
                    f"""
Error: The age-specific social distancing compliance form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Social Distancing
Compliance form in :primary-badge[:material/medical_mask: NPIs] that use the
same age group as another row.
                    """,
                    True,
                )
        else:
            # Make sure triggers account for class dismissal
            class_dismissal = id_get("class_dismissal", scenario_id, False)

    # School Closure
    st.html('<span id = "school_closure_trigger_condition"></span>')
    with st.expander(
        "School Closure",
        key=f"school_closure_container{scenario_id}",
        on_change="rerun",
    ):
        st.markdown("""
These parameters control if and when schools will close as a result of the pathogen.
        """)
        load_key("school_closure_toggle", scenario_id, False)
        use_school_closure = st.toggle(
            "Enable School Closures",
            value=False,
            on_change=save_key,
            args=["school_closure_toggle", scenario_id],
            key=f"_school_closure_toggle{scenario_id}",
            help="""
Toggle whether or not school closure interventions are implemented in the
simulation, overriding other school closure parameters.
            """,
        )

        # School closure triggers (if advanced parameters are enabled)
        if advanced:
            with st.container(border=True):
                load_key("school_closure_trigger", scenario_id, "Always")
                school_closure_trigger = st.selectbox(
                    "School Closure Trigger Condition",
                    key=f"_school_closure_trigger{scenario_id}",
                    options=trigger_names,
                    on_change=save_key,
                    args=["school_closure_trigger", scenario_id],
                    disabled=not use_school_closure,
                    help="""
The type of condition that must be satisfied before schools will start being
closed in the simulation. Additional options for configuring the exact trigger
condition will appear after selecting one of these options.

### Options:
- Always: Schools will be closed throughout the entire simulation.
- Timed: Schools will be closed within a specific time period defined using a
start and end threshold.
- Community Case Rate: Schools will begin to close if the rate of newly
diagnosed cases per day exceeds a specific threshold, and will begin to reopen
if the rate drops below a different threshold afterwards. This trigger rate
allows schools to close and reopen multiple times if the case rate varies
between the two thresholds.
- Community Case Total: Schools will begin to close after the number of
diagnosed cases in the community exceeds a specific threshold, and will remain
closed for the rest of the simulation.
- Cases per School: Schools will close individually when the number of cases
diagnosed within them reaches a certain threshold, and will remain closed for
the rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if school_closure_trigger == "Timed":
                    load_key("school_closure_period", scenario_id, (1, 60))
                    st.slider(
                        "School Closure Time Period",
                        min_value=1,
                        max_value=sim_length,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_school_closure_period{scenario_id}",
                        on_change=dynamic_scale_change,
                        args=[
                            "school_closure_period",
                            "school_closure_dynamic_form",
                            "School Closure Time Period",
                            scenario_id,
                        ],
                        disabled=not use_school_closure,
                        help="""
The time period during which schools will be closed in the simulation. The
first value is the day on which schools will initially close (where Day 1 is
the first day of the simulation), and the second value is the day on which
schools will reopen.

Note that if you modify this value, the update points for school closure
compliance defined in :primary-badge[:material/manage_history: Dynamic] may
have their values altered. For instance, if you go from school closures ending
on Day 60 to Day 30, an update point set to affect the value on Day 45 will be
changed to affect it on Day 30 instead.
                        """,
                    )

                # Rate triggers
                elif school_closure_trigger == "Community Case Rate":
                    st.info(
                        """
Due to the design of the *Flusim* model, case rate thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )
                # Case triggers
                # TODO: Update these links to go directly to the parameter
                # in question (using container.open and the like)
                elif school_closure_trigger in {
                    "Community Case Total",
                    "Cases per School",
                }:
                    st.info(
                        """
Due to the design of the *Flusim* model, case total thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )

        # School closure compliance
        load_key("school_closure_compliance", scenario_id, 0.9)
        st.slider(
            "School Closure Compliance (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not use_school_closure,
            on_change=save_key,
            args=["school_closure_compliance", scenario_id],
            key=f"_school_closure_compliance{scenario_id}",
            help="""
The probability that an individual will not attend schools when they are closed
in the simulation.
            """,
        )

    # Withdrawal Increase
    st.html('<span id = "withdrawal_increase_trigger_condition"></span>')
    with st.expander(
        "Withdrawal Increase",
        key=f"withdrawal_increase_container{scenario_id}",
        on_change="rerun",
    ):
        st.markdown("""
These parameters control the properties of interventions that increase the
likelihood of infected individuals withdrawing from work/school after becoming
symptomatic.

The base likelihood of infected individuals withdrawing from work/school when
this intervention is not active can be configured in the "Withdrawals and
Diagnosis" section of the "Community" tab.
        """)
        load_key("withdrawal_increase_toggle", scenario_id, False)
        use_withdrawal_increase = st.toggle(
            "Enable Withdrawal Increases",
            value=False,
            on_change=save_key,
            args=["withdrawal_increase_toggle", scenario_id],
            key=f"_withdrawal_increase_toggle{scenario_id}",
            help="""
Toggle whether or not withdrawal increasing interventions are implemented in
the simulation, overriding other withdrawal increase parameters.
            """,
        )

        # Withdrawal increase triggers (if advanced parameters are enabled)
        if advanced:
            load_key("withdrawal_increase_trigger", scenario_id, "Always")
            with st.container(border=True):
                withdrawal_increase_trigger = st.selectbox(
                    "Withdrawal Increase Trigger Condition",
                    key=f"_withdrawal_increase_trigger{scenario_id}",
                    options=trigger_names[:-1],
                    on_change=save_key,
                    args=["withdrawal_increase_trigger", scenario_id],
                    disabled=not use_withdrawal_increase,
                    help="""
The type of condition that must be satisfied before the rate of withdrawal will
start increasing in the simulation. Additional options for configuring the
exact trigger condition will appear after selecting one of these options.

### Options:
- Always: Withdrawal rates will be increased throughout the entire simulation.
- Timed: Withdrawal rates will be increased within a specific time period
defined using a start and end threshold.
- Community Case Rate: Withdrawal rates will begin increasing if the rate of
newly diagnosed cases per day exceeds a specific threshold, and will revert to
normal if the rate drops below a different threshold afterwards. This trigger
rate allows withdrawal rates to increase and decrease multiple times if the
case rate varies between the two thresholds.
- Community Case Total: Withdrawal rates will begin increasing after the number
of diagnosed cases in the community exceeds a specific threshold, and will
remain at this elevated rate for the rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if withdrawal_increase_trigger == "Timed":
                    load_key("withdrawal_increase_period", scenario_id, (1, 60))
                    st.slider(
                        "Withdrawal Increase Time Period",
                        min_value=1,
                        max_value=sim_length,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_withdrawal_increase_period{scenario_id}",
                        disabled=not use_withdrawal_increase,
                        on_change=save_key,
                        args=["withdrawal_increase_period", scenario_id],
                        help="""
The time period during which withdrawal rates will be increased in the
simulation. The first value is the day on which withdrawal rates will first
increase (where Day 1 is the first day of the simulation), and the second value
is the day on which withdrawal rates will return to normal.
                        """,
                    )

                # Rate triggers
                elif withdrawal_increase_trigger == "Community Case Rate":
                    st.info(
                        """
Due to the design of the *Flusim* model, case rate thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif withdrawal_increase_trigger == "Community Case Total":
                    st.info(
                        """
Due to the design of the *Flusim* model, case total thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )

        # Increased Withdrawal
        load_key("withdrawal_increase_adult", scenario_id, 0.9)
        withdrawal_increase_adult = st.slider(
            "Increased Work Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not use_withdrawal_increase,
            on_change=save_key,
            args=["withdrawal_increase_adult", scenario_id],
            key=f"_withdrawal_increase_adult{scenario_id}",
            help="""
The probability of an infected adult withdrawing from work after becoming
symptomatic while a withdrawal increasing intervention is in effect,
overwriting the normal withdrawal rate.
            """,
        )
        load_key("withdrawal_increase_child", scenario_id, 1.0)
        withdrawal_increase_child = st.slider(
            "Increased School Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            format="percent",
            disabled=not use_withdrawal_increase,
            on_change=save_key,
            args=["withdrawal_increase_child", scenario_id],
            key=f"_withdrawal_increase_child{scenario_id}",
            help="""
The probability of an infected child withdrawing from school after becoming
symptomatic while a withdrawal increasing intervention is in effect,
overwriting the normal withdrawal rate.
            """,
        )

        # Show error if initial proportion is above target
        base_adult_withdrawal = id_get("withdrawal_work", scenario_id, 0.5)
        base_child_withdrawal = id_get("withdrawal_school", scenario_id, 0.9)
        param_error(
            "withdrawal_decrease_adult",
            scenario_id,
            lambda: use_withdrawal_increase
            and base_adult_withdrawal >= withdrawal_increase_adult,
            f"""
Error: The work withdrawal rate during withdrawal increase NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {100 * withdrawal_increase_adult:0.3g}%, but the standard rate is
{100 * base_adult_withdrawal:0.3g}%. As such, work withdrawal rates are not
increased while the NPI is in effect.

Please make one of the following changes:
- Adjust Increased Work Withdrawal Rate in
:primary-badge[:material/medical_mask: NPIs] to be greater than
{100 * base_adult_withdrawal:0.3g}%.
- Decrease Work Withdrawal Rate in :primary-badge[:material/groups: Community]
to be less than {100 * withdrawal_increase_adult:0.3g}%.
            """,
            True,
        )
        param_error(
            "withdrawal_decrease_child",
            scenario_id,
            lambda: use_withdrawal_increase
            and base_child_withdrawal >= withdrawal_increase_child,
            f"""
Error: The school withdrawal rate during withdrawal increase NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {100 * withdrawal_increase_child:0.3g}%, but the standard rate is
{100 * base_child_withdrawal:0.3g}%. As such, school withdrawal rates are not
increased while the NPI is in effect.

Please make one of the following changes:
- Adjust Increased School Withdrawal Rate in
:primary-badge[:material/medical_mask: NPIs] to be greater than
{100 * base_child_withdrawal:0.3g}%.
- Decrease School Withdrawal Rate in
:primary-badge[:material/groups: Community] to be less than
{100 * withdrawal_increase_child:0.3g}%.
            """,
            True,
        )

    # Reduced Workgroup Size
    st.html('<span id = "reduced_workgroup_trigger_condition"></span>')
    with st.expander(
        "Reduced Work Group Size",
        key=f"reduced_workgroup_container{scenario_id}",
        on_change="rerun",
    ):
        st.markdown("""
These parameters control the properties of interventions that reduce the size
of work groups when in effect. Note that this NPI does not target school groups
or other gatherings.

The base size of work groups when this intervention is not active can be
configured in the "Population Behaviours" section of the "Community" tab.
        """)
        load_key("reduced_workgroup_toggle", scenario_id, False)
        use_reduced_workgroup = st.toggle(
            "Enable Work Group Size Reductions",
            value=False,
            on_change=save_key,
            args=["reduced_workgroup_toggle", scenario_id],
            key=f"_reduced_workgroup_toggle{scenario_id}",
            help="""
Toggle whether or not work group size reduction interventions are implemented
in the simulation, overriding other work group size reduction parameters.
            """,
        )

        # Reduced workgroup triggers (if advanced parameters are enabled)
        if advanced:
            load_key("reduced_workgroup_trigger", scenario_id, "Always")
            with st.container(border=True):
                reduced_workgroup_trigger = st.selectbox(
                    "Reduced Work Group Size Trigger Condition",
                    key=f"_reduced_workgroup_trigger{scenario_id}",
                    options=trigger_names[:-1],
                    on_change=save_key,
                    args=["reduced_workgroup_trigger", scenario_id],
                    disabled=not use_reduced_workgroup,
                    help="""
The type of condition that must be satisfied before the size of work groups
will start decreasing in the simulation. Additional options for configuring the
exact trigger condition will appear after selecting one of these options.

### Options:
- Always: Work group sizes will be decreased throughout the entire simulation.
- Timed: Work group sizes will be decreased within a specific time period
defined using a start and end threshold.
- Community Case Rate: Work groups will begin shrinking if the rate of newly
diagnosed cases per day exceeds a specific threshold, and will revert to normal
size if the rate drops below a different threshold afterwards. This trigger
rate allows group sizes to increase and decrease multiple times if the case
rate varies between the two thresholds.
- Community Case Total: Work groups will begin shrinking after the number of
diagnosed cases in the community exceeds a specific threshold, and will remain
at this reduced size for the rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if reduced_workgroup_trigger == "Timed":
                    load_key("reduced_workgroup_period", scenario_id, (1, 60))
                    st.slider(
                        "Reduced Work Group Size Time Period",
                        min_value=1,
                        max_value=sim_length,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_reduced_workgroup_period{scenario_id}",
                        disabled=not use_reduced_workgroup,
                        on_change=save_key,
                        args=["reduced_workgroup_period", scenario_id],
                        help="""
The time period during which work group sizes will be smaller in the
simulation. The first value is the day on which work groups will first shrink
(where Day 1 is the first day of the simulation), and the second value is the
day on which work groups will return to normal.
                        """,
                    )

                # Rate triggers
                elif reduced_workgroup_trigger == "Community Case Rate":
                    st.info(
                        """
Due to the design of the *Flusim* model, case rate thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif reduced_workgroup_trigger == "Community Case Total":
                    st.info(
                        """
Due to the design of the *Flusim* model, case total thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )

        # Reduced group size
        load_key("reduced_workgroup_size", scenario_id, 5)
        reduced_workgroup_size = st.slider(
            "Reduced Work Group Size (Number of People)",
            min_value=0,
            max_value=25,
            value=5,
            disabled=not use_reduced_workgroup,
            on_change=save_key,
            args=["reduced_workgroup_size", scenario_id],
            format="%f Person(s)",
            key=f"_reduced_workgroup_size{scenario_id}",
            help="""
The maximum size of work groups while a reduced work group size intervention is
in effect, overwriting the normal maximum.
            """,
        )

        # Show error if reduced size is more than base
        base_workgroup_size = id_get("max_workgroup_size", scenario_id, 10)
        param_error(
            "increased_workgroup_size",
            scenario_id,
            lambda: use_reduced_workgroup
            and reduced_workgroup_size >= base_workgroup_size,
            f"""
Error: The maximum work group size during reduced work group size NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {reduced_workgroup_size}, but the standard maximum size is
{base_workgroup_size}. As such, work group sizes are not decreased while the
NPI is in effect.

Please make one of the following changes:
- Adjust Reduced Work Group Size in :primary-badge[:material/medical_mask: NPIs]
to be less than {base_workgroup_size}.
- Increase Maximum Work Group Size in :primary-badge[:material/groups: Community]
to be more than {reduced_workgroup_size}.
            """,
            True,
        )

    # BCC Reduction
    st.html('<span id = "bcc_reduction_trigger_condition"></span>')
    with st.expander(
        "Background Contact Count Reduction",
        key=f"bcc_reduction_container{scenario_id}",
        on_change="rerun",
    ):
        st.markdown("""
These parameters control the properties of interventions that reduce the
background contact count (BCC) in the simulation, thus reducing the number of
individuals each person interacts with per day outside of simulated locations.

The base background contact count when this intervention is not active can be
configured in the "Population Behaviours" section of the "Community" tab.
        """)
        load_key("bcc_reduction_toggle", scenario_id, False)
        use_bcc_reduction = st.toggle(
            "Enable BCC Reduction",
            value=False,
            on_change=save_key,
            args=["bcc_reduction_toggle", scenario_id],
            key=f"_bcc_reduction_toggle{scenario_id}",
            help="""
Toggle whether or not background contact count reduction interventions are
implemented in the simulation, overriding other BCC reduction parameters.
            """,
        )

        # BCC triggers (if advanced parameters are enabled)
        if advanced:
            load_key("bcc_reduction_trigger", scenario_id, "Always")
            with st.container(border=True):
                bcc_reduction_trigger = st.selectbox(
                    "BCC Reduction Trigger Condition",
                    key=f"_bcc_reduction_trigger{scenario_id}",
                    options=trigger_names[:-1],
                    on_change=save_key,
                    args=["bcc_reduction_trigger", scenario_id],
                    disabled=not use_bcc_reduction,
                    help="""
The type of condition that must be satisfied before background contact count
will start decreasing in the simulation. Additional options for configuring the
exact trigger condition will appear after selecting one of these options.

### Options:
- Always: Background contact count will be reduced throughout the entire
simulation.
- Timed: Background contact count will be reduced within a specific time period
defined using a start and end threshold.
- Community Case Rate: Background contact count will be reduced if the rate of
newly diagnosed cases per day exceeds a specific threshold, and will revert to
normal levels if the rate drops below a different threshold afterwards. This
trigger rate allows BCC levels to increase and decrease multiple times if the
case rate varies between the two thresholds.
- Community Case Total: Background contact count will be reduced after the
number of diagnosed cases in the community exceeds a specific threshold, and
will remain at this reduced level for the rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if bcc_reduction_trigger == "Timed":
                    load_key("bcc_reduction_period", scenario_id, (1, 60))
                    st.slider(
                        "BCC Reduction Time Period",
                        min_value=1,
                        max_value=sim_length,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_bcc_reduction_period{scenario_id}",
                        disabled=not use_bcc_reduction,
                        on_change=dynamic_scale_change,
                        args=[
                            "bcc_reduction_period",
                            "bcc_reduction_dynamic_form",
                            "BCC Reduction Time Period",
                            scenario_id,
                        ],
                        help="""
The time period during which background contact count (BCC) will be reduced in
the simulation. The first value is the day on which BCC will first be reduced
(where Day 1 is the first day of the simulation), and the second value is the
day on which BCC will return to normal.
                        """,
                    )

                # Rate triggers
                elif bcc_reduction_trigger == "Community Case Rate":
                    st.info(
                        """
Due to the design of the *Flusim* model, case rate thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif bcc_reduction_trigger == "Community Case Total":
                    st.info(
                        """
Due to the design of the *Flusim* model, case total thresholds must be defined
globally. You may configure these thresholds using the "Intervention Trigger
Thresholds" parameters at the bottom of this page (click
[this link](#threshold_trigger_condition) to go there directly).
                        """,
                        icon=":material/info:",
                    )

        # Reduced BCC rate
        # TODO: Is this precise slider too difficult to control?
        load_key("bcc_reduced_rate", scenario_id, 0.2)
        bcc_reduced_rate = st.slider(
            "Reduced Background Contact Count (Interactions per Person per Day)",
            min_value=0.0,
            max_value=10.0,
            value=0.2,
            step=0.05,
            disabled=not use_bcc_reduction,
            on_change=save_key,
            args=["bcc_reduced_rate", scenario_id],
            key=f"_bcc_reduced_rate{scenario_id}",
            help="""
The average number of other people each individual will interact with in the
background phase of each day in the simulation (emulating interactions outside
of simulated locations) while a BCC reduction intervention is in effect,
overwriting the normal BCC rate.
            """,
        )

        # Show error if initial proportion is above target
        base_bcc_rate = id_get("bcc_rate", scenario_id, 4.0)
        param_error(
            "increased_bcc_rate",
            scenario_id,
            lambda: use_bcc_reduction and bcc_reduced_rate >= base_bcc_rate,
            f"""
Error: The background contact count (BCC) during BCC reduction NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {bcc_reduced_rate} interactions per day, but the standard rate is
{base_bcc_rate} interactions per day. As such, BCC is not decreased while the
NPI is in effect.

Please make one of the following changes:
- Adjust Reduced Background Contact Count in
:primary-badge[:material/medical_mask: NPIs] to be less than {base_bcc_rate}.
- Increase Background Contact Count in
:primary-badge[:material/groups: Community] to be more than {bcc_reduced_rate}.
            """,
            True,
        )

    # Trigger Thresholds (if advanced parameters are enabled)
    # TODO: Hide thresholds if no NPIs need them
    if advanced:
        st.html('<span id = "threshold_trigger_condition"></span>')
        st.subheader("Threshold Parameters")
        with st.expander(
            "Intervention Trigger Thresholds",
            key=f"trigger_container{scenario_id}",
            on_change="rerun",
        ):
            st.markdown("""
These parameters affect the threshold values that must be reached for
non-pharmaceutical interventions to be triggered in the simulation. Due to the
design of the *Flusim* simulation model, all interventions that are set to use
case rates or totals as their trigger condition must share these thresholds;
setting individual thresholds for each intervention is not possible unless the
"Timed" trigger condition is used. Parameters will only appear here if at least
one intervention is set to use a trigger condition that requires them.

Note that all thresholds that can be configured here are based on diagnosed
cases, not infections. The likelihood of an infected individual being diagnosed
as a case can be configured in the "Health Burden Outcomes" section of the
"Community" tab.
            """)

            # Display values based on what is used by the triggers
            intervention_triggers = [
                (school_closure_trigger, use_school_closure),
                (withdrawal_increase_trigger, use_withdrawal_increase),
                (reduced_workgroup_trigger, use_reduced_workgroup),
                (bcc_reduction_trigger, use_bcc_reduction),
            ]
            enabled_interventions = [
                trigger for trigger, toggle in intervention_triggers if toggle
            ]
            interventions_using_rates = [
                index
                for index, condition in enumerate(enabled_interventions)
                if condition == "Community Case Rate"
            ]
            interventions_using_totals = [
                index
                for index, condition in enumerate(enabled_interventions)
                if condition
                in {"Community Case Total", "Cases per School", "Cases per K-12 School"}
            ]
            if not (
                interventions_using_rates
                or interventions_using_totals
                or class_dismissal
            ):
                st.info(
                    """
No interventions are currently using case rates or totals for their trigger
conditions. Parameters for configuring the trigger thresholds will appear here
if you select any value other than "Always" and "Timed" for an intervention's
trigger condition.
                    """,
                    icon=":material/info:",
                )
            else:
                # Case rates
                if interventions_using_rates or class_dismissal:
                    # Display links to NPIs that use rates (including
                    # the non-standard Class Dismissal if applicable)
                    st.subheader("Case Rate Trigger Thresholds", divider="grey")
                    st.markdown(
                        """
The following interventions currently use the rate thresholds defined below.
Click on the names to go to the drop-down container with the trigger condition
parameters for that intervention.\n\n
                        """
                        + (
                            "\n- [Class Dismissal](#general_trigger_condition)"
                            if class_dismissal
                            else ""
                        )
                        + "".join(
                            f"\n- [{NPI_NAMES[i]}](#{NPI_TAGS[i]}_trigger_condition)"
                            for i in interventions_using_rates
                        )
                    )

                    # Set rate thresholds
                    # TODO: Are the slider mins/maxes realistic?
                    load_key("start_threshold_rate", scenario_id, 10)
                    start_threshold_rate = st.slider(
                        "Start Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=10,
                        key=f"_start_threshold_rate{scenario_id}",
                        on_change=save_key,
                        args=["start_threshold_rate", scenario_id],
                        help="""
Any interventions set to trigger using the "Community Case Rate" condition will
begin taking effect in the simulation once the number of newly diagnosed cases
per day exceeds this value.
                        """,
                    )
                    load_key("relaxation_threshold_rate", scenario_id, 5)
                    relaxation_threshold_rate = st.slider(
                        "Relaxation Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=5,
                        key=f"_relaxation_threshold_rate{scenario_id}",
                        on_change=save_key,
                        args=["relaxation_threshold_rate", scenario_id],
                        help="""
Any active interventions set to trigger using the "Community Case Rate"
condition will stop taking effect in the simulation once the number of newly
diagnosed cases per day goes below this value.
                        """,
                    )

                    # Show error if relax threshold is above trigger
                    # Note that this theoretically can be done error-free with
                    # dynamic parameter maximums and/or a 2-element slider,
                    # but those would be less intuitive to the user
                    param_error(
                        "relaxation_above_start",
                        scenario_id,
                        lambda: relaxation_threshold_rate > start_threshold_rate,
                        f"""
Warning: The threshold rate that triggers the beginning of NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {start_threshold_rate} cases per day, but the rate that triggers their end
is {relaxation_threshold_rate} cases per day. As such, NPIs will stop
immediately after starting if the case rate is between these values.

Please make one of the following changes:
- Increase Start Trigger Threshold Rate in :primary-badge[:material/medical_mask: NPIs]
to be more than {relaxation_threshold_rate}.
- Decrease Relaxation Trigger Threshold Rate in :primary-badge[:material/medical_mask: NPIs]
to be less than {start_threshold_rate}.
                        """,
                        False,
                    )

                # Case totals
                if interventions_using_totals:
                    # Display links to NPIs that use totals
                    st.subheader("Case Total Trigger Thresholds", divider="grey")
                    st.markdown(
                        """
The following interventions currently use the case threshold defined below.
Click on the names to go to the drop-down container with the trigger condition
parameters for that intervention.\n\n
                        """
                        + "".join(
                            f"\n- [{NPI_NAMES[i]}](#{NPI_TAGS[i]}_trigger_condition)"
                            for i in interventions_using_totals
                        )
                    )

                    # Set total threshold
                    # TODO: Use community population as maximum
                    load_key("start_threshold_total", scenario_id, 1000)
                    start_threshold_total = st.number_input(
                        "Start Trigger Case Threshold (Total Community Cases)",
                        min_value=0,
                        max_value=300000,
                        value=1000,
                        key=f"_start_threshold_total{scenario_id}",
                        on_change=save_key,
                        args=["start_threshold_total", scenario_id],
                        placeholder="Enter a whole number of cases",
                        help="""
Any interventions set to trigger using the "Community Case Total" or "Cases per
School" conditions will begin taking effect in the simulation once the total
number of diagnosed cases in the community (for "Community Case Total") or in
each individual school (for "Cases per School") exceeds this value.
                        """,
                    )

                    # Show error if relax threshold is above trigger
                    # TODO: See if this can be replaced with a max value too
                    population = COMMUNITIES[
                        session.get("community", "newcastle")
                    ].population
                    param_error(
                        "case_total_above_population",
                        scenario_id,
                        lambda: start_threshold_total >= population,
                        f"""
Error: The case threshold that triggers the beginning of NPIs in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {start_threshold_total} cases, but the total number of people in the
simulated community is {population}. As such, the entire simulation will be
infected before NPIs are enabled.

Please make one of the following changes:
- Decrease Start Trigger Case Threshold in :primary-badge[:material/medical_mask: NPIs]
to be less than {population}.
- Change the simulated community on the :grey-badge[:material/motion_play: Run Simulations]
page to a community with a population larger than {start_threshold_total}.
                        """,
                        True,
                    )


def npi_save_schema(
    schema: Parameters,
    scenario_id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    include_dashboard: bool = False,
):
    """
    Function to populate the Pydantic model schema with NPI parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to show more complex parameters like
            NPI trigger thresholds.

        baseline (Parameters, optional): A Pydantic model representing the
            parameters set for the baseline scenario. When `id` is not 0, this
            will be used to omit parameters that are already set in the
            baseline from the final scenario.

        include_dashboard (bool): Set to `True` to include the
            dashboard-exclusive social distancing toggle parameter.
    """

    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Initialising Scenario Parameters
        scenario_params = GeneralParameters()

        # Social Distancing
        # TODO: Pandemic alert might be necessary for SD to have an effect
        # Also, Adult might be the only age group to care about SD
        # due to the KLUDGE SD code being commented out
        # TODO: Test in simulation and remove if necessary
        use_social_distancing = id_get("social_distancing_toggle", scenario_id, False)
        global_compliance = id_get("social_distancing_compliance", scenario_id, 0.9)

        dashboard_params = DashboardParameters()
        if include_dashboard:
            dashboard_params.enable_social_distancing = use_social_distancing
            if scenario_id > 0 and baseline is not None:
                schema_remove_baseline(dashboard_params, baseline.Dashboard_Parameter)
            schema_update(schema, "Dashboard_Parameter", dashboard_params)
        if use_social_distancing:
            scenario_params.social_distance_compliance = global_compliance
        if advanced:
            age_scenario_params = AllAgesParameters()
            if use_social_distancing:
                age_scenario_params.social_distance = global_compliance
                social_distancing_age_form = id_get(
                    "social_distancing_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Social Distancing Compliance": [global_compliance],
                        },
                    ),
                ).copy()
                social_distancing_age_form["Social Distancing Compliance"] = (
                    social_distancing_age_form["Social Distancing Compliance"]
                    .div(100.0)
                    .round(6)
                )
                for age in AGE_GROUP_KEYS:
                    if age in social_distancing_age_form["Age Group"].values:
                        compliance = social_distancing_age_form.loc[
                            social_distancing_age_form["Age Group"] == age,
                            "Social Distancing Compliance",
                        ].item()
                        setattr(scenario_params, f"{age}_social_distance", compliance)
                    else:
                        setattr(
                            scenario_params, f"{age}_social_distance", global_compliance
                        )
            else:
                age_scenario_params.social_distance = 0.0
            # Save age-specific parameters
            if scenario_id > 0 and baseline is not None:
                schema_remove_baseline(
                    age_scenario_params, baseline.Scenario_ParameterWithAgePrefix
                )
            schema_update(
                schema, "Scenario_ParameterWithAgePrefix", age_scenario_params
            )

            # Miscellaneous advanced trigger parameters
            scenario_params.class_dismissal = id_get(
                "class_dismissal", scenario_id, False
            )
            scenario_params.case_trigger_threshold = id_get(
                "start_threshold_total", scenario_id, 1000
            )
            scenario_params.rate_trigger_threshold = id_get(
                "start_threshold_rate", scenario_id, 10
            )
            scenario_params.rate_relaxation_threshold = id_get(
                "relaxation_threshold_rate", scenario_id, 5
            )
            scenario_params.maximum_trigger_count = 250

        # School Closure
        if id_get("school_closure_toggle", scenario_id, False):
            scenario_params.school_closure_compliance = id_get(
                "school_closure_compliance", scenario_id, 0.9
            )
            scenario_params.close_child_education = True
            school_trigger = (
                id_get("school_closure_trigger", scenario_id, "Always")
                if advanced
                else "Always"
            )
            scenario_params.school_closure_trigger = TRIGGER_KEY_CONVERTER[
                school_trigger
            ]
            scenario_params.school_closure_relaxation = TRIGGER_KEY_CONVERTER[
                school_trigger
            ]
            if school_trigger == "Always":
                scenario_params.school_closure_delay = 0
                scenario_params.school_closure_duration = 9999
            elif school_trigger == "Timed":
                school_period = [
                    i - 1 for i in id_get("school_closure_period", scenario_id, (1, 60))
                ]
                scenario_params.school_closure_delay = school_period[0] * 2
                scenario_params.school_closure_duration = (
                    school_period[1] - school_period[0] + 1
                ) * 2
        else:
            scenario_params.school_closure_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Withdrawal Increase
        if id_get("withdrawal_increase_toggle", scenario_id, False):
            scenario_params.increased_withdrawal = id_get(
                "withdrawal_increase_adult", scenario_id, 0.9
            )
            scenario_params.increased_withdrawal_child = id_get(
                "withdrawal_increase_child", scenario_id, 1.0
            )
            withdrawal_trigger = (
                id_get("withdrawal_increase_trigger", scenario_id, "Always")
                if advanced
                else "Always"
            )
            scenario_params.withdrawal_increase_trigger = TRIGGER_KEY_CONVERTER[
                withdrawal_trigger
            ]
            scenario_params.withdrawal_increase_relaxation = TRIGGER_KEY_CONVERTER[
                withdrawal_trigger
            ]
            if withdrawal_trigger == "Always":
                scenario_params.withdrawal_increase_delay = 0
                scenario_params.withdrawal_increase_duration = 9999
            elif withdrawal_trigger == "Timed":
                withdrawal_period = [
                    i - 1
                    for i in id_get("withdrawal_increase_period", scenario_id, (1, 60))
                ]
                scenario_params.withdrawal_increase_delay = withdrawal_period[0] * 2
                scenario_params.withdrawal_increase_duration = (
                    withdrawal_period[1] - withdrawal_period[0] + 1
                ) * 2
        else:
            scenario_params.withdrawal_increase_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Reduced Group Size
        if id_get("reduced_workgroup_toggle", scenario_id, False):
            scenario_params.reduced_workgroup_size = id_get(
                "reduced_workgroup_size", scenario_id, 5
            )
            reduced_workgroup_trigger = (
                id_get("reduced_workgroup_trigger", scenario_id, "Always")
                if advanced
                else "Always"
            )
            scenario_params.reduced_workgroup_trigger = TRIGGER_KEY_CONVERTER[
                reduced_workgroup_trigger
            ]
            scenario_params.reduced_workgroup_relaxation = TRIGGER_KEY_CONVERTER[
                reduced_workgroup_trigger
            ]
            if reduced_workgroup_trigger == "Always":
                scenario_params.reduced_workgroup_delay = 0
                scenario_params.reduced_workgroup_duration = 9999
            elif reduced_workgroup_trigger == "Timed":
                reduced_workgroup_period = [
                    i - 1
                    for i in id_get("reduced_workgroup_period", scenario_id, (1, 60))
                ]
                scenario_params.reduced_workgroup_delay = (
                    reduced_workgroup_period[0] * 2
                )
                scenario_params.reduced_workgroup_duration = (
                    reduced_workgroup_period[1] - reduced_workgroup_period[0] + 1
                ) * 2
        else:
            scenario_params.reduced_workgroup_trigger = TRIGGER_KEY_CONVERTER["None"]
        # BCC Reduction
        if id_get("bcc_reduction_toggle", scenario_id, False):
            scenario_params.bcc_reduction = id_get(
                "bcc_reduced_rate", scenario_id, 0.2
            ) / id_get("bcc_rate", scenario_id, 4.0)
            bcc_reduction_trigger = (
                id_get("bcc_reduction_trigger", scenario_id, "Always")
                if advanced
                else "Always"
            )
            scenario_params.bcc_reduction_trigger = TRIGGER_KEY_CONVERTER[
                bcc_reduction_trigger
            ]
            scenario_params.bcc_reduction_relaxation = TRIGGER_KEY_CONVERTER[
                bcc_reduction_trigger
            ]
            if bcc_reduction_trigger == "Always":
                scenario_params.bcc_reduction_delay = 0
                scenario_params.bcc_reduction_duration = 9999
            elif bcc_reduction_trigger == "Timed":
                bcc_reduction_period = [
                    i - 1 for i in id_get("bcc_reduction_period", scenario_id, (1, 60))
                ]
                scenario_params.bcc_reduction_delay = bcc_reduction_period[0] * 2
                scenario_params.bcc_reduction_duration = (
                    bcc_reduction_period[1] - bcc_reduction_period[0] + 1
                ) * 2
        else:
            scenario_params.bcc_reduction_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Other NPIs
        scenario_params.diagnosed_case_isolation = id_get(
            "case_isolation", scenario_id, False
        )

        # Save the updated parameters, removing default baseline values
        distancing_table_params = {f"{age}_social_distance" for age in AGE_GROUP_KEYS}
        if scenario_id > 0 and baseline is not None:
            schema_remove_baseline(
                scenario_params,
                baseline.Scenario_Parameter,
                ignore=distancing_table_params,
            )
        schema_update(schema, "Scenario_Parameter", scenario_params)
    except (ValueError, ValidationError) as e:
        npi_log.error(
            f"[npi_save_schema] Encountered {type(e).__name__} while validating parameters for scenario {scenario_id}: {e}"
        )
        raise e


def npi_load_schema(schema: Parameters, scenario_id: int = 0):
    """
    Function to read NPI parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.
    """

    # Load sim length early
    sim_length = session.get("cycle_count", 360)

    # Dashboard Parameters
    schema_dashboard = schema.Dashboard_Parameter
    if (
        schema_dashboard is not None
        and schema_dashboard.enable_social_distancing is not None
    ):
        update_param_from_schema(
            "social_distancing_toggle",
            schema_dashboard.enable_social_distancing,
            scenario_id,
        )

    # Global Age Parameters
    schema_age = schema.Scenario_ParameterWithAgePrefix
    if schema_age is not None and schema_age.social_distance is not None:
        compliance = schema_age.social_distance
        update_param_from_schema(
            "social_distancing_compliance", compliance, scenario_id
        )
    else:
        compliance = id_get("social_distancing_compliance", 0, 0.9)

    # General Scenario Parameters
    schema_parameters = schema.Scenario_Parameter
    if schema_parameters is not None:
        param_dict = schema_parameters.model_dump(exclude_unset=True, exclude_none=True)
        param_converter = {
            "class_dismissal": "class_dismissal",
            "case_trigger_threshold": "start_threshold_total",
            "rate_trigger_threshold": "start_threshold_rate",
            "rate_relaxation_threshold": "relaxation_threshold_rate",
            "school_closure_compliance": "school_closure_compliance",
            "increased_withdrawal": "withdrawal_increase_adult",
            "increased_withdrawal_child": "withdrawal_increase_child",
            "reduced_workgroup_size": "reduced_workgroup_size",
            "social_distance_compliance": "social_distancing_compliance",
            "diagnosed_case_isolation": "case_isolation",
        }
        simple_params = {
            p: key for p, key in param_converter.items() if p in param_dict
        }
        for parameter, key in simple_params.items():
            update_param_from_schema(key, param_dict[parameter], scenario_id)

        # BCC Reduction
        if "bcc_reduction" in param_dict:
            update_param_from_schema(
                "bcc_reduced_rate",
                param_dict["bcc_reduction"] * id_get("bcc_rate", scenario_id, 4.0),
                scenario_id,
            )
        elif scenario_id != 0:
            scenario_bcc_rate = id_get("bcc_rate", scenario_id, 4.0)
            baseline_bcc_rate = id_get("bcc_rate", 0, 4.0)
            if scenario_bcc_rate != baseline_bcc_rate:
                bcc_ratio = id_get("bcc_reduced_rate", 0, 0.05) / baseline_bcc_rate
                update_param_from_schema(
                    "bcc_reduced_rate",
                    round(scenario_bcc_rate * bcc_ratio, 8),
                    scenario_id,
                )

        # NPI periods
        for npi in NPI_TAGS:
            npi_delay = param_dict.get(f"{npi}_delay")
            npi_duration = param_dict.get(f"{npi}_duration")

            # Triggers
            # Relaxation always matches start on dashboard, so don't look for it
            start_trigger = param_dict.get(f"{npi}_trigger")
            if start_trigger is not None:
                update_param_from_schema(
                    f"{npi}_toggle", start_trigger != "none", scenario_id
                )
                if start_trigger == "timed" and npi_delay == 0 and npi_duration == 9999:
                    update_param_from_schema(f"{npi}_trigger", "Always", scenario_id)
                elif start_trigger != "none":
                    update_param_from_schema(
                        f"{npi}_trigger",
                        TRIGGER_CONVERTER[start_trigger],
                        scenario_id,
                    )
            # Disambiguate between Timed and Always via baseline trigger
            elif scenario_id != 0:
                baseline_trigger = id_get(f"{npi}_trigger", 0, None)
                if baseline_trigger == "Timed" and npi_duration == 9999:
                    update_param_from_schema(f"{npi}_trigger", "Always", scenario_id)
                elif baseline_trigger == "Always" and (
                    npi_delay not in {None, 0} or npi_duration not in {None, 9999}
                ):
                    update_param_from_schema(f"{npi}_trigger", "Timed", scenario_id)

            # Periods
            if npi_delay is not None or npi_duration is not None:
                # Ensure baseline has all values
                if None in {npi_delay, npi_duration} and scenario_id == 0:
                    raise AssertionError(f"""
{npi} activation period parameters were only partially defined for the baseline
scenario
                    """)
                # Use baseline values to plug None gaps
                baseline_period_start, baseline_period_end = id_get(
                    f"{npi}_period", 0, (1, 60)
                )
                if npi_delay is None:
                    npi_delay = (baseline_period_start - 1) * 2
                if npi_duration is None:
                    npi_duration = (baseline_period_end - baseline_period_start + 1) * 2

                # Calculate NPI period
                npi_period_start = (npi_delay // 2) + 1
                npi_period_end = min(sim_length, (npi_delay + npi_duration) // 2)
                update_param_from_schema(
                    f"{npi}_period", (npi_period_start, npi_period_end), scenario_id
                )

        # Social Distancing Table
        # TODO: Identical-to-global values are getting kept here
        distance_params = {
            p.removesuffix("_social_distance"): v
            for p, v in param_dict.items()
            if p.endswith("_social_distance") and v != compliance
        }
        distancing_table = pd.DataFrame(
            columns=("Age Group", "Social Distancing Compliance")
        )
        for param, value in distance_params.items():
            distancing_table.loc[distancing_table.shape[0]] = [param, value]
        if not distancing_table.empty:
            distancing_table["Social Distancing Compliance"] = (
                distancing_table["Social Distancing Compliance"].mul(100.0).round(6)
            )
        update_table_from_schema(
            "social_distancing_age_form",
            distancing_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Social Distancing Compliance": [
                        param_dict.get(
                            id_get("social_distancing_compliance", scenario_id, 0.0),
                        )
                    ],
                },
            ),
        )
