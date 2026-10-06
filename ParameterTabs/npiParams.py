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
    Parameters,
    AllAgesParameters,
    DashboardParameters,
    GeneralParameters,
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
npiLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Names of the possible NPIs
NPI_NAMES = (
    # "Vaccination",
    "School Closure",
    "Withdrawal Increase",
    "Reduced Group Size",
    "Background Contact Count Reduction",
)
NPI_TAGS = ("schoolClosure", "withdrawalIncrease", "reducedGroup", "bcc")
# "vaccination",


# @st.fragment
def buildNPITab(id: int, advanced: bool = False):
    """
    Function to generate the parameters for NPIs in a
    specified container with scenario differentiation.

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.

        advanced (bool): Set to `True` to show more complex parameters like
            NPI trigger thresholds.
    """
    simLength = session.get("cycle_count", 360)
    triggerNames = list(TRIGGER_KEY_CONVERTER.keys())[1:]

    # Tab Content
    st.header("Non-Pharmaceutical Intervention Parameters")
    st.markdown("""
        This tab contains parameters relating to the non-pharmaceutical
        interventions (NPIs) that are integrated into the simulation.
    """)

    # Load variables used by case rates
    schoolClosureTrigger, withdrawalIncreaseTrigger = None, None
    reducedGroupTrigger, bccTrigger, classDismissal = None, None, None

    # General NPIs
    st.html('<span id = "generalTriggerCondition"></span>')
    with st.expander(
        "Social Distancing", key=f"npiContainer{id}", on_change="rerun"
    ) as distancingContainer:
        if distancingContainer.open:
            st.markdown("""
                These parameters control the implementation of
                social distancing and related non-pharmaceutical intervention (NPI)
                techniques, including case isolation and class dismissal.
            """)

            # Case Isolation
            load_key("caseIsolation", id, False)
            st.toggle(
                "Enable Diagnosed Case Isolation",
                value=False,
                on_change=save_key,
                args=["caseIsolation", id],
                key=f"_caseIsolation{id}",
                help="""
Toggle whether or not individuals who have been
diagnosed as cases of the pathogen will be
forced to isolate at home.
                """,
            )

            # Class Dismissal (if advanced parameters are enabled)
            if advanced:
                load_key("classDismissal", id, False)
                classDismissal = st.toggle(
                    "Enable Class Dismissal",
                    value=False,
                    on_change=save_key,
                    args=["classDismissal", id],
                    key=f"_classDismissal{id}",
                    help="""
Toggle whether or not school classes should be
dismissed when the daily case rate is high enough.

Note that the rate that must be reached before
class dismissal begins to occur is shared with
any other NPIs that are set to use case rates
as their trigger threshold.
                    """,
                )
                if classDismissal:
                    # TODO: Update links to go directly to the desired location
                    st.info(
                        """
                    Due to the design of the *Flusim* model, the case
                    rate thresholds used by class dismissal must be
                    defined globally for all NPIs. You may configure
                    these thresholds using the "Intervention Trigger
                    Thresholds" parameters at the bottom of this page
                    (click [this link](#thresholdTriggerCondition) to
                    go there directly).
                """,
                        icon=":material/info:",
                    )

            # Social distancing
            load_key("socialDistancingToggle", id, False)
            useSocialDistancingToggle = st.toggle(
                "Enable Social Distancing",
                value=False,
                on_change=save_key,
                args=["socialDistancingToggle", id],
                key=f"_socialDistancingToggle{id}",
                help="""
Toggle whether or not social distancing
interventions are implemented in the
simulation, overriding other social distancing parameters.
                """,
            )
            load_key("socialDistancingCompliance", id, 0.9)
            socialDistancingCompliance = round(
                st.slider(
                    "Social Distancing Compliance (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    format="percent",
                    disabled=not useSocialDistancingToggle,
                    on_change=save_key,
                    args=["socialDistancingCompliance", id],
                    key=f"_socialDistancingCompliance{id}",
                    help="""
The probability that an individual will comply
with social distancing interventions in the simulation.
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
                if useSocialDistancingToggle:
                    st.markdown("Double-click a cell in this table to edit its value.")
                load_key(
                    "distanceAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Social Distancing Compliance": [
                                socialDistancingCompliance
                            ],
                        },
                    ),
                    dataframe=True,
                )
                distanceAgeForm = st.data_editor(
                    session[f"distanceAgeForm{id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_distanceAgeForm{id}",
                    on_change=save_key,
                    args=["distanceAgeForm", id],
                    kwargs={"dataframe": True},
                    disabled=not useSocialDistancingToggle,
                    placeholder=(
                        "Enter a value"
                        if useSocialDistancingToggle
                        else "Enable social distancing to edit this parameter"
                    ),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have a specific social distancing compliance
probability defined for it, overriding the base probability.
                            """,
                        ),
                        "Social Distancing Compliance": st.column_config.NumberColumn(
                            "Social Distancing Compliance (Probability)",
                            required=True,
                            default=socialDistancingCompliance,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The probability that an individual in this age group will comply with
social distancing interventions in the simulation.
                            """,
                        ),
                    },
                )
                param_error(
                    "distanceAgeFormDuplicates",
                    id,
                    lambda: has_duplicates(distanceAgeForm),
                    f"""
                        Error: The age-specific social distancing
                        compliance form used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } contains duplicate age group rows. Each age group
                        should only be used in a single row of the form.

                        Please remove or change any rows of the
                        Age-Specific Social Distancing Compliance form in
                        :primary-badge[:material/medical_mask: NPIs]
                        that use the same age group as another row.
                    """,
                    True,
                )
        else:
            # Make sure triggers account for class dismissal
            classDismissal = id_get("classDismissal", id, False)

    # School Closure
    st.html('<span id = "schoolClosureTriggerCondition"></span>')
    with st.expander(
        "School Closure", key=f"schoolClosureContainer{id}", on_change="rerun"
    ):
        st.markdown("""
            These parameters control if and when schools will
            close as a result of the pathogen.
        """)
        load_key("schoolClosureToggle", id, False)
        useSchoolClosureToggle = st.toggle(
            "Enable School Closures",
            value=False,
            on_change=save_key,
            args=["schoolClosureToggle", id],
            key=f"_schoolClosureToggle{id}",
            help="""
Toggle whether or not school closure
interventions are implemented in the
simulation, overriding other school closure parameters.
            """,
        )

        # School closure triggers (if advanced parameters are enabled)
        if advanced:
            with st.container(border=True):
                load_key("schoolClosureTrigger", id, "Always")
                schoolClosureTrigger = st.selectbox(
                    "School Closure Trigger Condition",
                    key=f"_schoolClosureTrigger{id}",
                    options=triggerNames,
                    on_change=save_key,
                    args=["schoolClosureTrigger", id],
                    disabled=not useSchoolClosureToggle,
                    help="""
The type of condition that must be
satisfied before schools will start being
closed in the simulation. Additional
options for configuring the exact trigger
condition will appear after selecting one
of these options.

##### Options:
- Always: Schools will be closed throughout
the entire simulation.
- Timed: Schools will be closed within a
specific time period defined using a start
and end threshold.
- Community Case Rate: Schools will begin
to close if the rate of newly diagnosed
cases per day exceeds a specific threshold,
and will begin to reopen if the rate drops
below a different threshold afterwards.
This trigger rate allows schools to close
and reopen multiple times if the case rate
varies between the two thresholds.
- Community Case Total: Schools will begin
to close after the number of diagnosed
cases in the community exceeds a specific
threshold, and will remain closed for the
rest of the simulation.
- Cases per School: Schools will close
individually when the number of cases
diagnosed within them reaches a certain
threshold, and will remain closed for the
rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if schoolClosureTrigger == "Timed":
                    load_key("schoolClosurePeriod", id, (1, 60))
                    st.slider(
                        "School Closure Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_schoolClosurePeriod{id}",
                        on_change=dynamic_scale_change,
                        args=[
                            "schoolClosurePeriod",
                            "closeTimeForm",
                            "School Closure Time Period",
                            id,
                        ],
                        disabled=not useSchoolClosureToggle,
                        help="""
The time period during which schools
will be closed in the simulation. The
first value is the day on which schools
will initially close (where Day 1 is
the first day of the simulation), and
the second value is the day on which schools will reopen.

Note that if you modify this value, the update
points for school closure compliance defined in
:primary-badge[:material/manage_history: Dynamic]
may have their values altered. For instance, if
you go from school closures ending on Day 60 to
Day 30, an update point set to affect the value
on Day 45 will be changed to affect it on Day 30 instead.
                        """,
                    )

                # Rate triggers
                elif schoolClosureTrigger == "Community Case Rate":
                    st.info(
                        """
                        Due to the design of the *Flusim* model,
                        case rate thresholds must be defined
                        globally. You may configure these
                        thresholds using the "Intervention Trigger
                        Thresholds" parameters at the bottom of
                        this page (click
                        [this link](#thresholdTriggerCondition) to
                        go there directly).
                    """,
                        icon=":material/info:",
                    )
                # Case triggers
                # TODO: Update these links to go directly to the parameter
                # in question (using container.open and the like)
                elif schoolClosureTrigger in {
                    "Community Case Total",
                    "Cases per School",
                }:
                    st.info(
                        """
                    Due to the design of the *Flusim* model, case
                    total thresholds must be defined globally. You
                    may configure these thresholds using the
                    "Intervention Trigger Thresholds" parameters at
                    the bottom of this page (click
                    [this link](#thresholdTriggerCondition) to go
                    there directly).
                """,
                        icon=":material/info:",
                    )

        # School closure compliance
        load_key("schoolClosureCompliance", id, 0.9)
        st.slider(
            "School Closure Compliance (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not useSchoolClosureToggle,
            on_change=save_key,
            args=["schoolClosureCompliance", id],
            key=f"_schoolClosureCompliance{id}",
            help="""
The probability that an individual will
not attend schools when they are closed in the simulation.
            """,
        )

    # Withdrawal Increase
    st.html('<span id = "withdrawalIncreaseTriggerCondition"></span>')
    with st.expander(
        "Withdrawal Increase", key=f"withdrawalContainer{id}", on_change="rerun"
    ):
        st.markdown("""
            These parameters control the properties of
            interventions that increase the likelihood of
            infected individuals withdrawing from work/school
            after becoming symptomatic.

            The base likelihood of infected individuals
            withdrawing from work/school when this intervention
            is not active can be configured in the "Withdrawals
            and Diagnosis" section of the "Community" tab.
        """)
        load_key("withdrawalIncreaseToggle", id, False)
        useWithdrawalIncreaseToggle = st.toggle(
            "Enable Withdrawal Increases",
            value=False,
            on_change=save_key,
            args=["withdrawalIncreaseToggle", id],
            key=f"_withdrawalIncreaseToggle{id}",
            help="""
Toggle whether or not withdrawal increasing
interventions are implemented in the
simulation, overriding other withdrawal
increase parameters.
            """,
        )

        # Withdrawal increase triggers (if advanced parameters are enabled)
        if advanced:
            load_key("withdrawalIncreaseTrigger", id, "Always")
            with st.container(border=True):
                withdrawalIncreaseTrigger = st.selectbox(
                    "Withdrawal Increase Trigger Condition",
                    key=f"_withdrawalIncreaseTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=save_key,
                    args=["withdrawalIncreaseTrigger", id],
                    disabled=not useWithdrawalIncreaseToggle,
                    help="""
The type of condition that must be
satisfied before the rate of withdrawal
will start increasing in the simulation.
Additional options for configuring the
exact trigger condition will appear after
selecting one of these options.

##### Options:
- Always: Withdrawal rates will be
increased throughout the entire simulation.
- Timed: Withdrawal rates will be increased
within a specific time period defined using
a start and end threshold.
- Community Case Rate: Withdrawal rates
will begin increasing if the rate of newly
diagnosed cases per day exceeds a specific
threshold, and will revert to normal if the
rate drops below a different threshold
afterwards. This trigger rate allows
withdrawal rates to increase and decrease
multiple times if the case rate varies
between the two thresholds.
- Community Case Total: Withdrawal rates
will begin increasing after the number of
diagnosed cases in the community exceeds a
specific threshold, and will remain at this
elevated rate for the rest of the
simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if withdrawalIncreaseTrigger == "Timed":
                    load_key("withdrawalIncreasePeriod", id, (1, 60))
                    st.slider(
                        "Withdrawal Increase Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_withdrawalIncreasePeriod{id}",
                        disabled=not useWithdrawalIncreaseToggle,
                        on_change=save_key,
                        args=["withdrawalIncreasePeriod", id],
                        help="""
The time period during which withdrawal
rates will be increased in the
simulation. The first value is the day
on which withdrawal rates will first
increase (where Day 1 is the first day
of the simulation), and the second
value is the day on which withdrawal
rates will return to normal.
                        """,
                    )

                # Rate triggers
                elif withdrawalIncreaseTrigger == "Community Case Rate":
                    st.info(
                        """
                        Due to the design of the *Flusim* model,
                        case rate thresholds must be defined
                        globally. You may configure these
                        thresholds using the "Intervention Trigger
                        Thresholds" parameters at the bottom of
                        this page (click
                        [this link](#thresholdTriggerCondition) to
                        go there directly).
                    """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif withdrawalIncreaseTrigger == "Community Case Total":
                    st.info(
                        """
                        Due to the design of the *Flusim* model,
                        case total thresholds must be defined
                        globally. You may configure these
                        thresholds using the "Intervention Trigger
                        Thresholds" parameters at the bottom of
                        this page (click
                        [this link](#thresholdTriggerCondition) to
                        go there directly).
                    """,
                        icon=":material/info:",
                    )

        # Increased Withdrawal
        load_key("withdrawalIncreaseAdult", id, 0.9)
        withdrawalIncreaseAdult = st.slider(
            "Increased Work Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not useWithdrawalIncreaseToggle,
            on_change=save_key,
            args=["withdrawalIncreaseAdult", id],
            key=f"_withdrawalIncreaseAdult{id}",
            help="""
The probability of an infected adult
withdrawing from work after becoming
symptomatic while a withdrawal increasing
intervention is in effect, overwriting the
normal withdrawal rate.
            """,
        )
        load_key("withdrawalIncreaseChild", id, 1.0)
        withdrawalIncreaseChild = st.slider(
            "Increased School Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            format="percent",
            disabled=not useWithdrawalIncreaseToggle,
            on_change=save_key,
            args=["withdrawalIncreaseChild", id],
            key=f"_withdrawalIncreaseChild{id}",
            help="""
The probability of an infected child
withdrawing from school after becoming
symptomatic while a withdrawal increasing
intervention is in effect, overwriting the
normal withdrawal rate.
            """,
        )

        # Show error if initial proportion is above target
        baseAdultWithdrawal = id_get("withdrawalWork", id, 0.5)
        baseChildWithdrawal = id_get("withdrawalSchool", id, 0.9)
        param_error(
            "withdrawalNPIBelowBaseAdult",
            id,
            lambda: useWithdrawalIncreaseToggle
            and baseAdultWithdrawal >= withdrawalIncreaseAdult,
            f"""
                Error: The work withdrawal rate during
                withdrawal increase NPIs in the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{
                        session[f'scenarioName{id}']
                    }"'
                } is {100 * withdrawalIncreaseAdult:0.3g}%, but the
                standard rate is {100 * baseAdultWithdrawal:0.3g}%.
                As such, work withdrawal rates are not increased
                while the NPI is in effect.

                Please make one of the following changes:
                - Adjust Increased Work Withdrawal Rate in
                :primary-badge[:material/medical_mask: NPIs]
                to be greater than {100 * baseAdultWithdrawal:0.3g}%.
                - Decrease Work Withdrawal Rate in
                :primary-badge[:material/groups: Community]
                to be less than {100 * withdrawalIncreaseAdult:0.3g}%.
            """,
            True,
        )
        param_error(
            "withdrawalNPIBelowBaseChild",
            id,
            lambda: useWithdrawalIncreaseToggle
            and baseChildWithdrawal >= withdrawalIncreaseChild,
            f"""
                Error: The school withdrawal rate during
                withdrawal increase NPIs in the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{
                        session[f'scenarioName{id}']
                    }"'
                } is {100 * withdrawalIncreaseChild:0.3g}%, but the
                standard rate is {100 * baseChildWithdrawal:0.3g}%.
                As such, school withdrawal rates are not increased
                while the NPI is in effect.

                Please make one of the following changes:
                - Adjust Increased School Withdrawal Rate in
                :primary-badge[:material/medical_mask: NPIs]
                to be greater than {100 * baseChildWithdrawal:0.3g}%.
                - Decrease School Withdrawal Rate in
                :primary-badge[:material/groups: Community]
                to be less than {100 * withdrawalIncreaseChild:0.3g}%.
            """,
            True,
        )

    # Reduced Workgroup Size
    st.html('<span id = "reducedGroupTriggerCondition"></span>')
    with st.expander(
        "Reduced Work Group Size", key=f"workGroupContainer{id}", on_change="rerun"
    ):
        st.markdown("""
            These parameters control the properties of
            interventions that reduce the size of work groups
            when in effect. Note that this NPI does not target
            school groups or other gatherings.

            The base size of work groups when this intervention
            is not active can be configured in the "Population
            Behaviours" section of the "Community" tab.
        """)
        load_key("reducedGroupToggle", id, False)
        useReducedGroupToggle = st.toggle(
            "Enable Group Size Reductions",
            value=False,
            on_change=save_key,
            args=["reducedGroupToggle", id],
            key=f"_reducedGroupToggle{id}",
            help="""
Toggle whether or not group size reduction
interventions are implemented in the
simulation, overriding other group size
reduction parameters.
            """,
        )

        # Reduced workgroup triggers (if advanced parameters are enabled)
        if advanced:
            load_key("reducedGroupTrigger", id, "Always")
            with st.container(border=True):
                reducedGroupTrigger = st.selectbox(
                    "Reduced Group Size Trigger Condition",
                    key=f"_reducedGroupTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=save_key,
                    args=["reducedGroupTrigger", id],
                    disabled=not useReducedGroupToggle,
                    help="""
The type of condition that must be
satisfied before the size of work groups
will start decreasing in the simulation.
Additional options for configuring the
exact trigger condition will appear after
selecting one of these options.

##### Options:
- Always: Work group sizes will be
decreased throughout the entire simulation.
- Timed: Work group sizes will be decreased
within a specific time period defined using
a start and end threshold.
- Community Case Rate: Work groups will
begin shrinking if the rate of newly
diagnosed cases per day exceeds a specific
threshold, and will revert to normal size
if the rate drops below a different
threshold afterwards. This trigger rate
allows group sizes to increase and decrease
multiple times if the case rate varies
between the two thresholds.
- Community Case Total: Work groups will
begin shrinking after the number of
diagnosed cases in the community exceeds a
specific threshold, and will remain at this
reduced size for the rest of the simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if reducedGroupTrigger == "Timed":
                    load_key("reducedGroupPeriod", id, (1, 60))
                    st.slider(
                        "Reduced Group Size Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_reducedGroupPeriod{id}",
                        disabled=not useReducedGroupToggle,
                        on_change=save_key,
                        args=["reducedGroupPeriod", id],
                        help="""
The time period during which work
group sizes will be smaller in the
simulation. The first value is the day
on which work groups will first shrink
(where Day 1 is the first day of the
simulation), and the second value is
the day on which work groups will
return to normal.
                        """,
                    )

                # Rate triggers
                elif reducedGroupTrigger == "Community Case Rate":
                    st.info(
                        """
                        Due to the design of the *Flusim* model,
                        case rate thresholds must be defined
                        globally. You may configure these
                        thresholds using the "Intervention Trigger
                        Thresholds" parameters at the bottom of
                        this page (click
                        [this link](#thresholdTriggerCondition) to
                        go there directly).
                    """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif reducedGroupTrigger == "Community Case Total":
                    st.info(
                        """
                        Due to the design of the *Flusim* model,
                        case total thresholds must be defined
                        globally. You may configure these
                        thresholds using the "Intervention Trigger
                        Thresholds" parameters at the bottom of
                        this page (click
                        [this link](#thresholdTriggerCondition) to
                        go there directly).
                    """,
                        icon=":material/info:",
                    )

        # Reduced group size
        load_key("reducedGroupSize", id, 5)
        reducedGroupSize = st.slider(
            "Reduced Work Group Size (Number of People)",
            0,
            25,
            5,
            disabled=not useReducedGroupToggle,
            on_change=save_key,
            args=["reducedGroupSize", id],
            format="%f Person(s)",
            key=f"_reducedGroupSize{id}",
            help="""
The maximum size of work groups while a reduced
group size intervention is in effect,
overwriting the normal maximum.
            """,
        )

        # Show error if reduced size is more than base
        baseGroupSize = id_get("maxWorkGroupSize", id, 10)
        param_error(
            "groupNPIAboveBase",
            id,
            lambda: useReducedGroupToggle and reducedGroupSize >= baseGroupSize,
            f"""
                Error: The maximum work group size during
                reduced group size NPIs in the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{
                        session[f'scenarioName{id}']
                    }"'
                } is {reducedGroupSize}, but the
                standard maximum size is {baseGroupSize}.
                As such, work group sizes are not decreased
                while the NPI is in effect.

                Please make one of the following changes:
                - Adjust Reduced Work Group Size in
                :primary-badge[:material/medical_mask: NPIs]
                to be less than {baseGroupSize}.
                - Increase Maximum Work Group Size in
                :primary-badge[:material/groups: Community]
                to be more than {reducedGroupSize}.
            """,
            True,
        )

    # BCC Reduction
    st.html('<span id = "bccTriggerCondition"></span>')
    with st.expander(
        "Background Contact Count Reduction", key=f"bccContainer{id}", on_change="rerun"
    ):
        st.markdown("""
            These parameters control the properties of
            interventions that reduce the background contact
            count (BCC) in the simulation, thus reducing the
            number of individuals each person interacts with
            per day outside of simulated locations.

            The base background contact count when this
            intervention is not active can be configured in the
            "Population Behaviours" section of the "Community"
            tab.
        """)
        load_key("bccToggle", id, False)
        useBCCToggle = st.toggle(
            "Enable BCC Reduction",
            value=False,
            on_change=save_key,
            args=["bccToggle", id],
            key=f"_bccToggle{id}",
            help="""
Toggle whether or not background contact count
reduction interventions are implemented in the
simulation, overriding other BCC reduction parameters.
            """,
        )

        # BCC triggers (if advanced parameters are enabled)
        if advanced:
            load_key("bccTrigger", id, "Always")
            with st.container(border=True):
                bccTrigger = st.selectbox(
                    "BCC Reduction Trigger Condition",
                    key=f"_bccTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=save_key,
                    args=["bccTrigger", id],
                    disabled=not useBCCToggle,
                    help="""
The type of condition that must be
satisfied before background contact count
will start decreasing in the simulation.
Additional options for configuring the
exact trigger condition will appear after
selecting one of these options.

##### Options:
- Always: Background contact count will be
reduced throughout the entire simulation.
- Timed: Background contact count will be
reduced within a specific time period
defined using a start and end threshold.
- Community Case Rate: Background contact
count will be reduced if the rate of newly
diagnosed cases per day exceeds a specific
threshold, and will revert to normal levels
if the rate drops below a different
threshold afterwards. This trigger rate
allows BCC levels to increase and decrease
multiple times if the case rate varies
between the two thresholds.
- Community Case Total: Background contact
count will be reduced after the number of
diagnosed cases in the community exceeds a
specific threshold, and will remain at this
reduced level for the rest of the
simulation.
                    """,
                )
                # Show additional parameters based on trigger value
                # Timed triggers
                if bccTrigger == "Timed":
                    load_key("bccPeriod", id, (1, 60))
                    st.slider(
                        "BCC Reduction Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_bccPeriod{id}",
                        disabled=not useBCCToggle,
                        on_change=dynamic_scale_change,
                        args=[
                            "bccPeriod",
                            "bccTimeForm",
                            "BCC Reduction Time Period",
                            id,
                        ],
                        help="""
The time period during which background
contact count (BCC) will be reduced in
the simulation. The first value is the
day on which BCC will first be reduced
(where Day 1 is the first day of the
simulation), and the second value is
the day on which BCC will return to normal.
                        """,
                    )

                # Rate triggers
                elif bccTrigger == "Community Case Rate":
                    st.info(
                        """
                    Due to the design of the *Flusim* model, case
                    rate thresholds must be defined globally. You
                    may configure these thresholds using the
                    "Intervention Trigger Thresholds" parameters at
                    the bottom of this page (click
                    [this link](#thresholdTriggerCondition) to go
                    there directly).
                """,
                        icon=":material/info:",
                    )
                # Case triggers
                elif bccTrigger == "Community Case Total":
                    st.info(
                        """
                    Due to the design of the *Flusim* model, case
                    total thresholds must be defined globally. You
                    may configure these thresholds using the
                    "Intervention Trigger Thresholds" parameters at
                    the bottom of this page (click
                    [this link](#thresholdTriggerCondition) to go
                    there directly).
                """,
                        icon=":material/info:",
                    )

        # Reduced BCC rate
        # TODO: Is this precise slider too difficult to control?
        load_key("bccReducedRate", id, 0.2)
        bccReducedRate = st.slider(
            "Reduced Background Contact Count (Interactions per Person per Day)",
            min_value=0.0,
            max_value=10.0,
            value=0.2,
            step=0.05,
            disabled=not useBCCToggle,
            on_change=save_key,
            args=["bccReducedRate", id],
            key=f"_bccReducedRate{id}",
            help="""
The average number of other people each
individual will interact with in the background
phase of each day in the simulation (emulating
interactions outside of simulated locations)
while a BCC reduction intervention is in
effect, overwriting the normal BCC rate.
            """,
        )

        # Show error if initial proportion is above target
        baseBCC = id_get("bccRate", id, 4.0)
        param_error(
            "bccNPIAboveBase",
            id,
            lambda: useBCCToggle and bccReducedRate >= baseBCC,
            f"""
                Error: The background contact count (BCC) during
                BCC reduction NPIs in the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{
                        session[f'scenarioName{id}']
                    }"'
                } is {bccReducedRate} interactions per day, but the
                standard rate is {baseBCC} interactions per day.
                As such, BCC is not decreased while the NPI is in effect.

                Please make one of the following changes:
                - Adjust Reduced Background Contact Count in
                :primary-badge[:material/medical_mask: NPIs]
                to be less than {baseBCC}.
                - Increase Background Contact Count in
                :primary-badge[:material/groups: Community]
                to be more than {bccReducedRate}.
            """,
            True,
        )

    # Trigger Thresholds (if advanced parameters are enabled)
    # TODO: Hide thresholds if no NPIs need them
    if advanced:
        st.html('<span id = "thresholdTriggerCondition"></span>')
        st.subheader("Threshold Parameters")
        with st.expander(
            "Intervention Trigger Thresholds",
            key=f"triggerContainer{id}",
            on_change="rerun",
        ):
            st.markdown("""
                These parameters affect the threshold values that must
                be reached for non-pharmaceutical
                interventions to be triggered in the simulation. Due to
                the design of the *Flusim* simulation model, all
                interventions that are set to use case rates or totals
                as their trigger condition must share these thresholds;
                setting individual thresholds for each intervention is
                not possible unless the "Timed" trigger condition is
                used. Parameters will only appear here if at least one
                intervention is set to use a trigger condition that
                requires them.

                Note that all thresholds that can be configured here
                are based on diagnosed cases, not infections. The
                likelihood of an infected individual being diagnosed as
                a case can be configured in the "Health Burden
                Outcomes" section of the "Community" tab.
            """)

            # Display values based on what is used by the triggers
            interventionTriggers = [
                (schoolClosureTrigger, useSchoolClosureToggle),
                (withdrawalIncreaseTrigger, useWithdrawalIncreaseToggle),
                (reducedGroupTrigger, useReducedGroupToggle),
                (bccTrigger, useBCCToggle),
            ]
            enabledInterventions = [
                trigger for trigger, toggle in interventionTriggers if toggle
            ]
            usesRates = [
                index
                for index, condition in enumerate(enabledInterventions)
                if condition == "Community Case Rate"
            ]
            usesTotals = [
                index
                for index, condition in enumerate(enabledInterventions)
                if condition
                in {"Community Case Total", "Cases per School", "Cases per K-12 School"}
            ]
            if not (usesRates or usesTotals or classDismissal):
                st.info(
                    """
                No interventions are currently using case rates or
                totals for their trigger conditions. Parameters for
                configuring the trigger thresholds will appear here if
                you select any value other than "Always" and "Timed"
                for an intervention's trigger condition.
            """,
                    icon=":material/info:",
                )
            else:
                # Case rates
                if usesRates or classDismissal:
                    # Display links to NPIs that use rates (including
                    # the non-standard Class Dismissal if applicable)
                    st.subheader("Case Rate Trigger Thresholds", divider="grey")
                    st.markdown(
                        """
                            The following interventions currently use
                            the rate thresholds defined below. Click on
                            the names to go to the drop-down container
                            with the trigger condition parameters for
                            that intervention.\n\n
                        """
                        + (
                            "\n- [Class Dismissal](#generalTriggerCondition)"
                            if classDismissal
                            else ""
                        )
                        + "".join(
                            f"\n- [{NPI_NAMES[i]}](#{NPI_TAGS[i]}TriggerCondition)"
                            for i in usesRates
                        )
                    )

                    # Set rate thresholds
                    # TODO: Are the slider mins/maxes realistic?
                    load_key("rateStartThreshold", id, 10)
                    rateStartThreshold = st.slider(
                        "Start Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=10,
                        key=f"_rateStartThreshold{id}",
                        on_change=save_key,
                        args=["rateStartThreshold", id],
                        help="""
Any interventions set to trigger using the
"Community Case Rate" condition will begin
taking effect in the simulation once the
number of newly diagnosed cases per day exceeds this value.
                        """,
                    )
                    load_key("rateRelaxThreshold", id, 5)
                    rateRelaxThreshold = st.slider(
                        "Relaxation Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=5,
                        key=f"_rateRelaxThreshold{id}",
                        on_change=save_key,
                        args=["rateRelaxThreshold", id],
                        help="""
Any active interventions set to trigger
using the "Community Case Rate" condition
will stop taking effect in the simulation
once the number of newly diagnosed cases
per day goes below this value.
                        """,
                    )

                    # Show error if relax threshold is above trigger
                    # Note that this theoretically can be done error-free with
                    # dynamic parameter maximums and/or a 2-element slider,
                    # but those would be less intuitive to the user
                    param_error(
                        "relaxAboveTrigger",
                        id,
                        lambda: rateRelaxThreshold > rateStartThreshold,
                        f"""
                            Warning: The threshold rate that triggers the
                            beginning of NPIs in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[f'scenarioName{id}']
                                }"'
                            } is {rateStartThreshold} cases per day, but the
                            rate that triggers their end is {rateRelaxThreshold}
                            cases per day. As such, NPIs will stop immediately
                            after starting if the case rate is between these values.

                            Please make one of the following changes:
                            - Increase Start Trigger Threshold Rate in
                            :primary-badge[:material/medical_mask: NPIs]
                            to be more than {rateRelaxThreshold}.
                            - Decrease Relaxation Trigger Threshold Rate in
                            :primary-badge[:material/medical_mask: NPIs]
                            to be less than {rateStartThreshold}.
                        """,
                        False,
                    )

                # Case totals
                if usesTotals:
                    # Display links to NPIs that use totals
                    st.subheader("Case Total Trigger Thresholds", divider="grey")
                    st.markdown(
                        """
                            The following interventions currently use
                            the case threshold defined below. Click on
                            the names to go to the drop-down container
                            with the trigger condition parameters for
                            that intervention.\n\n
                        """
                        + "".join(
                            f"\n- [{NPI_NAMES[i]}](#{NPI_TAGS[i]}TriggerCondition)"
                            for i in usesTotals
                        )
                    )

                    # Set total threshold
                    # TODO: Use population as maximum
                    load_key("caseTotalThreshold", id, 1000)
                    caseTotalThreshold = st.number_input(
                        "Start Trigger Case Threshold (Total Community Cases)",
                        0,
                        300000,
                        1000,
                        key=f"_caseTotalThreshold{id}",
                        on_change=save_key,
                        args=["caseTotalThreshold", id],
                        placeholder="Enter a whole number of cases",
                        help="""
Any interventions set to trigger using the
"Community Case Total" or "Cases per School"
conditions will begin taking effect in the
simulation once the total number of diagnosed
cases in the community (for "Community Case
Total") or in each individual school (for
"Cases per School") exceeds this value.
                        """,
                    )

                    # Show error if relax threshold is above trigger
                    # TODO: See if this can be replaced with a max value too
                    population = COMMUNITIES[
                        session.get("community", "newcastle")
                    ].population
                    param_error(
                        "triggerAbovePopulation",
                        id,
                        lambda: caseTotalThreshold >= population,
                        f"""
                            Error: The case threshold that triggers the
                            beginning of NPIs in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[f'scenarioName{id}']
                                }"'
                            } is {caseTotalThreshold} cases, but the
                            total number of people in the simulated community
                            is {population}. As such, the entire simulation
                            will be infected before NPIs are enabled.

                            Please make one of the following changes:
                            - Decrease Start Trigger Case Threshold in
                            :primary-badge[:material/medical_mask: NPIs]
                            to be less than {population}.
                            - Change the simulated community on the
                            :grey-badge[:material/motion_play: Run Simulations]
                            page to a community with a population
                            larger than {caseTotalThreshold}.
                        """,
                        True,
                    )


def npiSaveSchema(
    schema: Parameters,
    id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    includeDashboard: bool = False,
):
    """
    Function to populate the Pydantic model schema with NPI parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to show more complex parameters like
            NPI trigger thresholds.

        baseline (Parameters, optional): A Pydantic model representing the parameters
            set for the baseline scenario. When `id` is not 0, this will be used
            to omit parameters that are already set in the baseline from the final
            scenario.

        includeDashboard (bool): Set to `True` to include the dashboard-exclusive
            social distancing toggle parameter.
    """
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Initialising Scenario Parameters
        scenarioParams = GeneralParameters()

        # Social Distancing
        # TODO: Pandemic alert might be necessary for SD to have an effect
        # Also, Adult might be the only age group to care about SD
        # due to the KLUDGE SD code being commented out
        # TODO: Test in simulation and remove if necessary
        socialDistanceToggle = id_get("socialDistancingToggle", id, False)
        globalCompliance = id_get("socialDistancingCompliance", id, 0.9)

        dashboardParams = DashboardParameters()
        if includeDashboard:
            dashboardParams.enable_social_distancing = socialDistanceToggle
            if id > 0 and baseline is not None:
                schema_remove_baseline(dashboardParams, baseline.Dashboard_Parameter)
            schema_update(schema, "Dashboard_Parameter", dashboardParams)
        if socialDistanceToggle:
            scenarioParams.social_distance_compliance = globalCompliance
        if advanced:
            ageScenarioParams = AllAgesParameters()
            if socialDistanceToggle:
                ageScenarioParams.social_distance = globalCompliance
                distanceAgeForm = id_get(
                    "distanceAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Social Distancing Compliance": [globalCompliance],
                        },
                    ),
                ).copy()
                distanceAgeForm["Social Distancing Compliance"] = (
                    distanceAgeForm["Social Distancing Compliance"].div(100.0).round(6)
                )
                for age in AGE_GROUP_KEYS:
                    if age in distanceAgeForm["Age Group"].values:
                        compliance = distanceAgeForm.loc[
                            distanceAgeForm["Age Group"] == age,
                            "Social Distancing Compliance",
                        ].item()
                        setattr(scenarioParams, f"{age}_social_distance", compliance)
                    else:
                        setattr(
                            scenarioParams, f"{age}_social_distance", globalCompliance
                        )
            else:
                ageScenarioParams.social_distance = 0.0
            # Save age-specific parameters
            if id > 0 and baseline is not None:
                schema_remove_baseline(
                    ageScenarioParams, baseline.Scenario_ParameterWithAgePrefix
                )
            schema_update(schema, "Scenario_ParameterWithAgePrefix", ageScenarioParams)

            # Miscellaneous advanced trigger parameters
            scenarioParams.class_dismissal = id_get("classDismissal", id, False)
            scenarioParams.case_trigger_threshold = id_get(
                "caseTotalThreshold", id, 1000
            )
            scenarioParams.rate_trigger_threshold = id_get("rateStartThreshold", id, 10)
            scenarioParams.rate_relaxation_threshold = id_get(
                "rateRelaxThreshold", id, 5
            )
            scenarioParams.maximum_trigger_count = 250

        # School Closure
        if id_get("schoolClosureToggle", id, False):
            scenarioParams.school_closure_compliance = id_get(
                "schoolClosureCompliance", id, 0.9
            )
            scenarioParams.close_child_education = True
            schoolTrigger = (
                id_get("schoolClosureTrigger", id, "Always") if advanced else "Always"
            )
            scenarioParams.school_closure_trigger = TRIGGER_KEY_CONVERTER[schoolTrigger]
            scenarioParams.school_closure_relaxation = TRIGGER_KEY_CONVERTER[
                schoolTrigger
            ]
            if schoolTrigger == "Always":
                scenarioParams.school_closure_delay = 0
                scenarioParams.school_closure_duration = 9999
            elif schoolTrigger == "Timed":
                schoolPeriod = [
                    i - 1 for i in id_get("schoolClosurePeriod", id, (1, 60))
                ]
                scenarioParams.school_closure_delay = schoolPeriod[0] * 2
                scenarioParams.school_closure_duration = (
                    schoolPeriod[1] - schoolPeriod[0] + 1
                ) * 2
        else:
            scenarioParams.school_closure_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Withdrawal Increase
        if id_get("withdrawalIncreaseToggle", id, False):
            scenarioParams.increased_withdrawal = id_get(
                "withdrawalIncreaseAdult", id, 0.9
            )
            scenarioParams.increased_withdrawal_child = id_get(
                "withdrawalIncreaseChild", id, 1.0
            )
            withdrawalTrigger = (
                id_get("withdrawalIncreaseTrigger", id, "Always")
                if advanced
                else "Always"
            )
            scenarioParams.withdrawal_increase_trigger = TRIGGER_KEY_CONVERTER[
                withdrawalTrigger
            ]
            scenarioParams.withdrawal_increase_relaxation = TRIGGER_KEY_CONVERTER[
                withdrawalTrigger
            ]
            if withdrawalTrigger == "Always":
                scenarioParams.withdrawal_increase_delay = 0
                scenarioParams.withdrawal_increase_duration = 9999
            elif withdrawalTrigger == "Timed":
                withdrawalPeriod = [
                    i - 1 for i in id_get("withdrawalIncreasePeriod", id, (1, 60))
                ]
                scenarioParams.withdrawal_increase_delay = withdrawalPeriod[0] * 2
                scenarioParams.withdrawal_increase_duration = (
                    withdrawalPeriod[1] - withdrawalPeriod[0] + 1
                ) * 2
        else:
            scenarioParams.withdrawal_increase_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Reduced Group Size
        if id_get("reducedGroupToggle", id, False):
            scenarioParams.reduced_workgroup_size = id_get("reducedGroupSize", id, 5)
            reducedGroupTrigger = (
                id_get("reducedGroupTrigger", id, "Always") if advanced else "Always"
            )
            scenarioParams.reduced_workgroup_trigger = TRIGGER_KEY_CONVERTER[
                reducedGroupTrigger
            ]
            scenarioParams.reduced_workgroup_relaxation = TRIGGER_KEY_CONVERTER[
                reducedGroupTrigger
            ]
            if reducedGroupTrigger == "Always":
                scenarioParams.reduced_workgroup_delay = 0
                scenarioParams.reduced_workgroup_duration = 9999
            elif reducedGroupTrigger == "Timed":
                reducedGroupPeriod = [
                    i - 1 for i in id_get("reducedGroupPeriod", id, (1, 60))
                ]
                scenarioParams.reduced_workgroup_delay = reducedGroupPeriod[0] * 2
                scenarioParams.reduced_workgroup_duration = (
                    reducedGroupPeriod[1] - reducedGroupPeriod[0] + 1
                ) * 2
        else:
            scenarioParams.reduced_workgroup_trigger = TRIGGER_KEY_CONVERTER["None"]
        # BCC Reduction
        if id_get("bccToggle", id, False):
            scenarioParams.bcc_reduction = id_get("bccReducedRate", id, 0.2) / id_get(
                "bccRate", id, 4.0
            )
            bccTrigger = id_get("bccTrigger", id, "Always") if advanced else "Always"
            scenarioParams.bcc_reduction_trigger = TRIGGER_KEY_CONVERTER[bccTrigger]
            scenarioParams.bcc_reduction_relaxation = TRIGGER_KEY_CONVERTER[bccTrigger]
            if bccTrigger == "Always":
                scenarioParams.bcc_reduction_delay = 0
                scenarioParams.bcc_reduction_duration = 9999
            elif bccTrigger == "Timed":
                bccPeriod = [i - 1 for i in id_get("bccPeriod", id, (1, 60))]
                scenarioParams.bcc_reduction_delay = bccPeriod[0] * 2
                scenarioParams.bcc_reduction_duration = (
                    bccPeriod[1] - bccPeriod[0] + 1
                ) * 2
        else:
            scenarioParams.bcc_reduction_trigger = TRIGGER_KEY_CONVERTER["None"]
        # Other NPIs
        scenarioParams.diagnosed_case_isolation = id_get("caseIsolation", id, False)

        # Save the updated parameters, removing default baseline values
        distanceTableParams = {f"{age}_social_distance" for age in AGE_GROUP_KEYS}
        if id > 0 and baseline is not None:
            schema_remove_baseline(
                scenarioParams, baseline.Scenario_Parameter, ignore=distanceTableParams
            )
        schema_update(schema, "Scenario_Parameter", scenarioParams)
    except (ValueError, ValidationError) as e:
        npiLog.error(
            (
                f"[vaccinationParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e


def npiLoadSchema(schema: Parameters, scenario_id: int = 0):
    """
    Function to read NPI parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.
    """
    # Load sim length early
    simLength = session.get("cycle_count", 360)

    # Dashboard Parameters
    schemaDash = schema.Dashboard_Parameter
    if schemaDash is not None and schemaDash.enable_social_distancing is not None:
        update_param_from_schema(
            "socialDistancingToggle",
            schemaDash.enable_social_distancing,
            scenario_id,
        )

    # Global Age Parameters
    schemaAge = schema.Scenario_ParameterWithAgePrefix
    if schemaAge is not None and schemaAge.social_distance is not None:
        compliance = schemaAge.social_distance
        update_param_from_schema("socialDistancingCompliance", compliance, scenario_id)
    else:
        compliance = id_get("socialDistanceCompliance", 0, 0.9)

    # General Scenario Parameters
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is not None:
        paramDict = schemaParameters.model_dump(exclude_unset=True, exclude_none=True)
        paramConvert = {
            "class_dismissal": "classDismissal",
            "case_trigger_threshold": "caseTotalThreshold",
            "rate_trigger_threshold": "rateStartThreshold",
            "rate_relaxation_threshold": "rateRelaxThreshold",
            "school_closure_compliance": "schoolClosureCompliance",
            "increased_withdrawal": "withdrawalIncreaseAdult",
            "increased_withdrawal_child": "withdrawalIncreaseChild",
            "reduced_workgroup_size": "reducedGroupSize",
            "social_distance_compliance": "socialDistancingCompliance",
            "diagnosed_case_isolation": "caseIsolation",
        }
        simpleParams = {p: key for p, key in paramConvert.items() if p in paramDict}
        for parameter, key in simpleParams.items():
            update_param_from_schema(key, paramDict[parameter], scenario_id)

        # BCC Reduction
        if "bcc_reduction" in paramDict:
            update_param_from_schema(
                "bccReducedRate",
                paramDict["bcc_reduction"] * id_get("bccRate", scenario_id, 4.0),
                scenario_id,
            )
        elif scenario_id != 0:
            scenarioBCCRate = id_get("bccRate", scenario_id, 4.0)
            baselineBCCRate = id_get("bccRate", 0, 4.0)
            if scenarioBCCRate != baselineBCCRate:
                bccRatio = id_get("bccReducedRate", 0, 0.05) / baselineBCCRate
                update_param_from_schema(
                    "bccReducedRate",
                    round(scenarioBCCRate * bccRatio, 8),
                    scenario_id,
                )

        # NPI periods
        npiPrefixes = {
            "school_closure": "schoolClosure",
            "withdrawal_increase": "withdrawalIncrease",
            "reduced_workgroup": "reducedGroup",
            "bcc_reduction": "bcc",
        }
        triggerDict = {
            "none": "Always",
            "timed": "Timed",
            "community_rate": "Community Case Rate",
            "community_cases": "Community Case Total",
            "per_school_cases": "Cases per School",
        }
        for npi, prefix in npiPrefixes.items():
            npiDelay = paramDict.get(f"{npi}_delay")
            npiDuration = paramDict.get(f"{npi}_duration")

            # Triggers
            # Relaxation always matches start on dashboard, so don't look for it
            startTrigger = paramDict.get(f"{npi}_trigger")
            if startTrigger is not None:
                update_param_from_schema(
                    f"{prefix}Toggle", startTrigger != "none", scenario_id
                )
                if startTrigger == "timed" and npiDelay == 0 and npiDuration == 9999:
                    update_param_from_schema(f"{prefix}Trigger", "Always", scenario_id)
                elif startTrigger != "none":
                    update_param_from_schema(
                        f"{prefix}Trigger", triggerDict[startTrigger], scenario_id
                    )
            # Disambiguate between Timed and Always via baseline trigger
            elif scenario_id != 0:
                baselineTrigger = id_get(f"{prefix}Trigger", 0, None)
                if baselineTrigger == "Timed" and npiDuration == 9999:
                    update_param_from_schema(f"{prefix}Trigger", "Always", scenario_id)
                elif baselineTrigger == "Always" and (
                    npiDelay not in {None, 0} or npiDuration not in {None, 9999}
                ):
                    update_param_from_schema(f"{prefix}Trigger", "Timed", scenario_id)

            # Periods
            if npiDelay is not None or npiDuration is not None:
                # Ensure baseline has all values
                if None in {npiDelay, npiDuration} and scenario_id == 0:
                    raise AssertionError(f"""
                        {npi} activation period parameters were only partially
                        defined for the baseline scenario
                    """)
                # Use baseline values to plug None gaps
                basePeriodStart, basePeriodEnd = id_get(f"{prefix}Period", 0, (1, 60))
                if npiDelay is None:
                    npiDelay = (basePeriodStart - 1) * 2
                if npiDuration is None:
                    npiDuration = (basePeriodEnd - basePeriodStart + 1) * 2

                # Calculate NPI period
                npiPeriodStart = (npiDelay // 2) + 1
                npiPeriodEnd = min(simLength, (npiDelay + npiDuration) // 2)
                update_param_from_schema(
                    f"{prefix}Period", (npiPeriodStart, npiPeriodEnd), scenario_id
                )

        # Social Distancing Table
        # TODO: Identical-to-global values are getting kept here
        distanceParams = {
            p.removesuffix("_social_distance"): v
            for p, v in paramDict.items()
            if p.endswith("_social_distance") and v != compliance
        }
        distanceTable = pd.DataFrame(
            columns=("Age Group", "Social Distancing Compliance")
        )
        for param, value in distanceParams.items():
            distanceTable.loc[distanceTable.shape[0]] = [param, value]
        if not distanceTable.empty:
            distanceTable["Social Distancing Compliance"] = (
                distanceTable["Social Distancing Compliance"].mul(100.0).round(6)
            )
        update_table_from_schema(
            "distanceAgeForm",
            distanceTable,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Social Distancing Compliance": [
                        paramDict.get(
                            id_get("socialDistancingCompliance", scenario_id, 0.0),
                        )
                    ],
                },
            ),
        )
