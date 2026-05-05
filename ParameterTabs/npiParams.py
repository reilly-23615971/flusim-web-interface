# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where NPI parameters can be modified

# Imports
import logging

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import paramError, trigCast
from ClientResources.ModelSchema import (
    Parameters,
    ageScenarioParameters,
    scenarioParameters,
)
from ClientResources.ParameterFunctions import (
    dynamicScaleChange,
    hasDuplicates,
    idGet,
    loadKey,
    saveKey,
    updateParamFromSchema,
    updateTableFromSchema,
)
from ClientResources.SharedResources import (
    ageTimeDict,
    communityPopulation,
    npiCamel,
    npis,
    triggerConditions,
)

# Logging
npiLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.fragment
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

    """
    # Initialise session variables needed by the vaccination/NPI forms
    sessionParameters = {
        f"socialRowCount{id}": 0,
        f"classDismissal{id}": False,
    }
    for parameter, default in sessionParameters.items():
        session[parameter] = session.get(parameter, default)

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    ageGroupSets = {
        f"socialRemainingAgeGroups{id}": (
            f"socialRowCount{id}",
            f"socialAgeGroup{id}-",
        ),
    }

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories.keys())"""
    simLength = session.get("cycleCount", 360)
    triggerNames = list(triggerConditions.keys())

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
            loadKey("caseIsolation", id, False)
            st.toggle(
                "Enable Case Isolation",
                value=False,
                on_change=saveKey,
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
                loadKey("classDismissal", id, False)
                classDismissal = st.toggle(
                    "Enable Class Dismissal",
                    value=False,
                    on_change=saveKey,
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
            loadKey("socialDistancingToggle", id, False)
            useSocialDistancingToggle = st.toggle(
                "Enable Social Distancing",
                value=False,
                on_change=saveKey,
                args=["socialDistancingToggle", id],
                key=f"_socialDistancingToggle{id}",
                help="""
Toggle whether or not social distancing
interventions are implemented in the
simulation, overriding other social distancing parameters.
                """,
            )
            loadKey("socialDistancingCompliance", id, 0.9)
            socialDistancingCompliance = st.slider(
                "Social Distancing Compliance (Probability)",
                min_value=0.0,
                max_value=1.0,
                value=0.9,
                format="percent",
                disabled=not useSocialDistancingToggle,
                on_change=saveKey,
                args=["socialDistancingCompliance", id],
                key=f"_socialDistancingCompliance{id}",
                help="""
The probability that an individual will comply
with social distancing interventions in the simulation.
                """,
            )
            # Age-specific social distancing compliance (if advanced params enabled)
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
                loadKey(
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
                    on_change=saveKey,
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
                            options=ageTimeDict.keys(),
                            format_func=lambda x: ageTimeDict[x],  # type: ignore
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
                            max_value=1.0,
                            format="percent",
                            help="""
The probability that an individual in this age group will comply with
social distancing interventions in the simulation.
                            """,
                        ),
                    },
                )
                paramError(
                    "distanceAgeFormDuplicates",
                    id,
                    lambda: hasDuplicates(distanceAgeForm),
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

                '''
                # Save relevant params as variables to avoid lookups
                socialRowCount = session[f"socialRowCount{id}"]
                socialRemainingGroups = session[f"socialRemainingAgeGroups{id}"]
                socialAgeContainer = st.container()
                for i in range(socialRowCount):
                    (socialGroupColumn, socialComplianceColumn, socialRemoveColumn) = (
                        socialAgeContainer.columns(
                            (0.25, 0.55, 0.2), vertical_alignment="center"
                        )
                    )
                    socialCurrentGroup = session.get(f"socialAgeGroup{id}-{i}")

                    # Age group column
                    loadKey(
                        "socialAgeGroup",
                        id,
                        (
                            socialCurrentGroup
                            if socialCurrentGroup
                            else socialRemainingGroups[0]
                        ),
                        f"-{i}",
                    )
                    with socialGroupColumn:
                        st.selectbox(
                            "Age Group",
                            key=f"_socialAgeGroup{id}-{i}",
                            # Set age group options such that only ages
                            # that haven't been selected yet can be selected
                            options=(
                                [socialCurrentGroup]
                                + [
                                    group
                                    for group in socialRemainingGroups
                                    if group != socialCurrentGroup
                                ]
                                if socialCurrentGroup
                                else socialRemainingGroups
                            ),
                            disabled=(
                                not useSocialDistancingToggle or not socialRowCount < 10
                            ),
                            on_change=saveKey,
                            args=["socialAgeGroup", id, f"-{i}"],
                            help="""
                            An age group that will have specific
                            social distancing compliance probability
                            defined for it, overriding the base
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
                        """,
                        )
                    # Compliance column
                    loadKey("socialCompliance", id, 0.9, f"-{i}")
                    with socialComplianceColumn:
                        st.select_slider(
                            "Social Distancing Compliance (Probability)",
                            np.linspace(0.0, 1.0, 201),
                            0.9,
                            format_func=lambda x: f"{100 * x:0.3g}%",
                            disabled=not useSocialDistancingToggle,
                            on_change=saveKey,
                            args=["socialCompliance", id, f"-{i}"],
                            key=f"_socialCompliance{id}-{i}",
                            help="""
                            The probability that an individual in
                            this age group will comply with social
                            distancing interventions in the
                            simulation.
                        """,
                        )
                    # Delete button column
                    with socialRemoveColumn:
                        st.button(
                            label="Remove Age Group",
                            icon=":material/delete:",
                            key=f"socialRemove{id}-{i}",
                            on_click=deleteFormRow,
                            args=(
                                i,
                                f"socialRowCount{id}",
                                {f"socialAgeGroup{id}-", f"socialCompliance{id}-"},
                            ),
                            disabled=not useVaccinesToggle,
                            help="""
                            Remove this row of the form and remove
                            these age-specific vaccine proportion
                            values from the simulation.
                        """,
                        )
                # Button to add another row for age specific params
                socialAgeContainer.button(
                    label="Add Age Group",
                    icon=":material/add:",
                    on_click=addFormRow,
                    key=f"socialAdd{id}",
                    args=(
                        f"socialRowCount{id}",
                        {
                            f"socialAgeGroup{id}-{socialRowCount}": (
                                socialRemainingGroups[0]
                                if socialRemainingGroups else None
                            ),
                            f"socialCompliance{id}-{socialRowCount}":
                            socialDistancingCompliance,
                        },
                    ),
                    disabled=(not useSocialDistancingToggle or not socialRowCount < 10),
                    help=(
                        """
                        Add another row to this form, where you can
                        select an additional age group to have unique
                        social distancing compliance values.
                    """
                        if socialRowCount <= 9
                        else """
                        All age groups have been given unique social
                        distancing compliance values, so a new age
                        group cannot be added.
                    """
                    ),
                )'''
        else:
            # Make sure triggers account for class dismissal
            classDismissal = idGet("classDismissal", id, False)

    # School Closure
    st.html('<span id = "schoolClosureTriggerCondition"></span>')
    with st.expander(
        "School Closure", key=f"schoolClosureContainer{id}", on_change="rerun"
    ):
        st.markdown("""
            These parameters control if and when schools will
            close as a result of the pathogen.
        """)
        loadKey("schoolClosureToggle", id, False)
        useSchoolClosureToggle = st.toggle(
            "Enable School Closures",
            value=False,
            on_change=saveKey,
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
                loadKey("schoolClosureTrigger", id, "Always")
                schoolClosureTrigger = st.selectbox(
                    "School Closure Trigger Condition",
                    key=f"_schoolClosureTrigger{id}",
                    options=triggerNames,
                    on_change=saveKey,
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
                    loadKey("schoolClosurePeriod", id, (1, 60))
                    st.slider(
                        "School Closure Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_schoolClosurePeriod{id}",
                        on_change=dynamicScaleChange,
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
        loadKey("schoolClosureCompliance", id, 0.9)
        st.slider(
            "School Closure Compliance (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not useSchoolClosureToggle,
            on_change=saveKey,
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
        loadKey("withdrawalIncreaseToggle", id, False)
        useWithdrawalIncreaseToggle = st.toggle(
            "Enable Withdrawal Increases",
            value=False,
            on_change=saveKey,
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
            loadKey("withdrawalIncreaseTrigger", id, "Always")
            with st.container(border=True):
                withdrawalIncreaseTrigger = st.selectbox(
                    "Withdrawal Increase Trigger Condition",
                    key=f"_withdrawalIncreaseTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=saveKey,
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
                    loadKey("withdrawalIncreasePeriod", id, (1, 60))
                    st.slider(
                        "Withdrawal Increase Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_withdrawalIncreasePeriod{id}",
                        disabled=not useWithdrawalIncreaseToggle,
                        on_change=saveKey,
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
        loadKey("withdrawalIncreaseAdult", id, 0.9)
        withdrawalIncreaseAdult = st.slider(
            "Increased Work Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            format="percent",
            disabled=not useWithdrawalIncreaseToggle,
            on_change=saveKey,
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
        loadKey("withdrawalIncreaseChild", id, 1.0)
        withdrawalIncreaseChild = st.slider(
            "Increased School Withdrawal Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            format="percent",
            disabled=not useWithdrawalIncreaseToggle,
            on_change=saveKey,
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
        baseAdultWithdrawal = idGet("withdrawalWork", id, 0.5)
        baseChildWithdrawal = idGet("withdrawalSchool", id, 0.9)
        paramError(
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
                :primary-badge[:material/vaccines: Vaccination and NPIs]
                to be greater than {100 * baseAdultWithdrawal:0.3g}%.
                - Decrease Work Withdrawal Rate in
                :primary-badge[:material/groups: Community]
                to be less than {100 * withdrawalIncreaseAdult:0.3g}%.
            """,
            True,
        )
        paramError(
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
                :primary-badge[:material/vaccines: Vaccination and NPIs]
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
        loadKey("reducedGroupToggle", id, False)
        useReducedGroupToggle = st.toggle(
            "Enable Group Size Reductions",
            value=False,
            on_change=saveKey,
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
            loadKey("reducedGroupTrigger", id, "Always")
            with st.container(border=True):
                reducedGroupTrigger = st.selectbox(
                    "Reduced Group Size Trigger Condition",
                    key=f"_reducedGroupTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=saveKey,
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
                    loadKey("reducedGroupPeriod", id, (1, 60))
                    st.slider(
                        "Reduced Group Size Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_reducedGroupPeriod{id}",
                        disabled=not useReducedGroupToggle,
                        on_change=saveKey,
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
        loadKey("reducedGroupSize", id, 5)
        reducedGroupSize = st.slider(
            "Reduced Work Group Size (Number of People)",
            0,
            25,
            5,
            disabled=not useReducedGroupToggle,
            on_change=saveKey,
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
        baseGroupSize = idGet("maxWorkGroupSize", id, 10)
        paramError(
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
                :primary-badge[:material/vaccines: Vaccination and NPIs]
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
        loadKey("bccToggle", id, False)
        useBCCToggle = st.toggle(
            "Enable BCC Reduction",
            value=False,
            on_change=saveKey,
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
            loadKey("bccTrigger", id, "Always")
            with st.container(border=True):
                bccTrigger = st.selectbox(
                    "BCC Reduction Trigger Condition",
                    key=f"_bccTrigger{id}",
                    options=triggerNames[:-1],
                    on_change=saveKey,
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
                    loadKey("bccPeriod", id, (1, 60))
                    st.slider(
                        "BCC Reduction Time Period",
                        min_value=1,
                        max_value=simLength,
                        value=(1, 60),
                        format="Day %i",
                        key=f"_bccPeriod{id}",
                        disabled=not useBCCToggle,
                        on_change=dynamicScaleChange,
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
        loadKey("bccReducedRate", id, 0.2)
        bccReducedRate = st.slider(
            "Reduced Background Contact Count (Interactions per Person per Day)",
            min_value=0.0,
            max_value=8.0,
            value=0.2,
            step=0.05,
            disabled=not useBCCToggle,
            on_change=saveKey,
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
        baseBCC = idGet("bccRate", id, 4.0)
        paramError(
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
                :primary-badge[:material/vaccines: Vaccination and NPIs]
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
                            f"\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)"
                            for i in usesRates
                        )
                    )

                    # Set rate thresholds
                    # TODO: Are the slider mins/maxes realistic?
                    loadKey("rateStartThreshold", id, 10)
                    rateStartThreshold = st.slider(
                        "Start Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=10,
                        key=f"_rateStartThreshold{id}",
                        on_change=saveKey,
                        args=["rateStartThreshold", id],
                        help="""
Any interventions set to trigger using the
"Community Case Rate" condition will begin
taking effect in the simulation once the
number of newly diagnosed cases per day exceeds this value.
                        """,
                    )
                    loadKey("rateRelaxThreshold", id, 5)
                    rateRelaxThreshold = st.slider(
                        "Relaxation Trigger Threshold Rate (Cases per Day)",
                        min_value=0,
                        max_value=100,
                        value=5,
                        key=f"_rateRelaxThreshold{id}",
                        on_change=saveKey,
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
                    paramError(
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
                            :primary-badge[:material/vaccines: Vaccination and NPIs]
                            to be more than {rateRelaxThreshold}.
                            - Decrease Relaxation Trigger Threshold Rate in
                            :primary-badge[:material/vaccines: Vaccination and NPIs]
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
                            f"\n- [{npis[i]}](#{npiCamel[i]}TriggerCondition)"
                            for i in usesTotals
                        )
                    )

                    # Set total threshold
                    # TODO: Use population as maximum
                    loadKey("caseTotalThreshold", id, 1000)
                    caseTotalThreshold = st.number_input(
                        "Start Trigger Case Threshold (Total Community Cases)",
                        0,
                        300000,
                        1000,
                        key=f"_caseTotalThreshold{id}",
                        on_change=saveKey,
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
                    population = communityPopulation[
                        session.get("community", "newcastle")
                    ]
                    paramError(
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
                            :primary-badge[:material/vaccines: Vaccination and NPIs]
                            to be less than {population}.
                            - Change the simulated community on the
                            :grey-badge[:material/motion_play: Run Simulations]
                            page to a community with a population
                            larger than {caseTotalThreshold}.
                        """,
                        True,
                    )


def npiSaveSchema(schema: Parameters, id: int = 0, advanced: bool = False):
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
    """

    # TODO: Make code clearer (split up advanced section if needed)

    # Load reused parameters immediately to save time
    socialDistanceToggle = idGet("socialDistancingToggle", id, False)
    socialCompliance = idGet("socialDistancingCompliance", id, 0.9)
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Initialising Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter
            if schema.Scenario_Parameter
            else scenarioParameters()
        )

        # Advanced parameter differences
        if advanced:
            # Social Distancing
            if socialDistanceToggle:
                ageScenarioParams = (
                    schema.Scenario_ParameterWithAgePrefix
                    if schema.Scenario_ParameterWithAgePrefix
                    else ageScenarioParameters()
                )
                ageScenarioParams.social_distance = socialCompliance
                schema.Scenario_ParameterWithAgePrefix = ageScenarioParams

                distanceAgeForm = idGet(
                    "distanceAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Social Distancing Compliance": [socialCompliance],
                        },
                    ),
                )
                for age, comp in zip(
                    distanceAgeForm["Age Group"],
                    distanceAgeForm["Social Distancing Compliance"],
                ):
                    if age:
                        setattr(scenarioParams, f"{age}_social_distance", comp)
                """
                for i in range(session.get(f"socialRowCount{id}", 0)):
                    setattr(
                        scenarioParams,
                        f"{ageCategories[session[
                        f'socialAgeGroup{id}-{i}']
                        ]}_social_distance",
                        idGet("socialCompliance", id, socialCompliance, f"-{i}"),
                    )"""

            # Triggers
            scenarioParams.class_dismissal = idGet("classDismissal", id, False)
            scenarioParams.case_trigger_threshold = idGet(
                "caseTotalThreshold", id, 1000
            )
            scenarioParams.rate_trigger_threshold = idGet("rateStartThreshold", id, 10)
            scenarioParams.rate_relaxation_threshold = idGet(
                "rateRelaxThreshold", id, 5
            )
            scenarioParams.maximum_trigger_count = 250

        # School Closure
        if idGet("schoolClosureToggle", id, False):
            scenarioParams.school_closure_compliance = idGet(
                "schoolClosureCompliance", id, 0.9
            )
            scenarioParams.close_child_education = True
            schoolTrigger = (
                idGet("schoolClosureTrigger", id, "Always") if advanced else "Always"
            )
            scenarioParams.school_closure_trigger = trigCast(schoolTrigger)
            scenarioParams.school_closure_relaxation = trigCast(schoolTrigger)
            if schoolTrigger == "Always":
                scenarioParams.school_closure_delay = 0
                scenarioParams.school_closure_duration = 99999
            elif schoolTrigger == "Timed":
                schoolPeriod = [
                    i - 1 for i in idGet("schoolClosurePeriod", id, (1, 60))
                ]
                scenarioParams.school_closure_delay = schoolPeriod[0] * 2
                scenarioParams.school_closure_duration = (
                    schoolPeriod[1] - schoolPeriod[0] + 1
                ) * 2
        # Withdrawal Increase
        if idGet("withdrawalIncreaseToggle", id, False):
            scenarioParams.increased_withdrawal = idGet(
                "withdrawalIncreaseAdult", id, 0.9
            )
            scenarioParams.increased_withdrawal_child = idGet(
                "withdrawalIncreaseChild", id, 1.0
            )
            withdrawalTrigger = (
                idGet("withdrawalIncreaseTrigger", id, "Always")
                if advanced
                else "Always"
            )
            scenarioParams.withdrawal_increase_trigger = trigCast(withdrawalTrigger)
            scenarioParams.withdrawal_increase_relaxation = trigCast(withdrawalTrigger)
            if withdrawalTrigger == "Always":
                scenarioParams.withdrawal_increase_delay = 0
                scenarioParams.withdrawal_increase_duration = 99999
            elif withdrawalTrigger == "Timed":
                withdrawalPeriod = [
                    i - 1 for i in idGet("withdrawalIncreasePeriod", id, (1, 60))
                ]
                scenarioParams.withdrawal_increase_delay = withdrawalPeriod[0] * 2
                scenarioParams.withdrawal_increase_duration = (
                    withdrawalPeriod[1] - withdrawalPeriod[0] + 1
                ) * 2
        # Reduced Group Size
        if idGet("reducedGroupToggle", id, False):
            scenarioParams.reduced_workgroup_size = idGet("reducedGroupSize", id, 5)
            reducedGroupTrigger = (
                idGet("reducedGroupTrigger", id, "Always") if advanced else "Always"
            )
            scenarioParams.reduced_workgroup_trigger = trigCast(reducedGroupTrigger)
            scenarioParams.reduced_workgroup_relaxation = trigCast(reducedGroupTrigger)
            if reducedGroupTrigger == "Always":
                scenarioParams.reduced_workgroup_delay = 0
                scenarioParams.reduced_workgroup_duration = 99999
            elif reducedGroupTrigger == "Timed":
                reducedGroupPeriod = [
                    i - 1 for i in idGet("reducedGroupPeriod", id, (1, 60))
                ]
                scenarioParams.reduced_workgroup_delay = reducedGroupPeriod[0] * 2
                scenarioParams.reduced_workgroup_duration = (
                    reducedGroupPeriod[1] - reducedGroupPeriod[0] + 1
                ) * 2
        # BCC Reduction
        if idGet("bccToggle", id, False):
            scenarioParams.bcc_reduction = idGet("bccReducedRate", id, 0.2) / idGet(
                "bccRate", id, 4.0
            )
            bccTrigger = idGet("bccTrigger", id, "Always") if advanced else "Always"
            scenarioParams.bcc_reduction_trigger = trigCast(bccTrigger)
            scenarioParams.bcc_reduction_relaxation = trigCast(bccTrigger)
            if bccTrigger == "Always":
                scenarioParams.bcc_reduction_delay = 0
                scenarioParams.bcc_reduction_duration = 99999
            elif bccTrigger == "Timed":
                bccPeriod = [i - 1 for i in idGet("bccPeriod", id, (1, 60))]
                scenarioParams.bcc_reduction_delay = bccPeriod[0] * 2
                scenarioParams.bcc_reduction_duration = (
                    bccPeriod[1] - bccPeriod[0] + 1
                ) * 2
        # Other NPIs
        if socialDistanceToggle:
            scenarioParams.social_distance_compliance = socialCompliance
        scenarioParams.diagnosed_case_isolation = idGet("caseIsolation", id, False)

        # Save the updated parameters
        schema.Scenario_Parameter = scenarioParams
    except (ValueError, ValidationError) as e:
        npiLog.error(
            (
                f"[vaccinationParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e


def npiLoadSchema(schema: Parameters, scenarioID: int = 0):
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
    simLength = session.get("cycleCount", 360)

    # Keep track of whether any toggle-controlled parameters have shown up
    useSocialDistancing = False
    useNPIs = {
        "schoolClosure": False,
        "withdrawalIncrease": False,
        "reducedGroup": False,
        "bcc": False,
    }

    # Global Age Parameters
    schemaAge = schema.Scenario_ParameterWithAgePrefix
    if schemaAge is not None:
        # TODO: Is 0.0 global SD with nonzero age SD a feasible simulation?
        # Consider adding another dummy parameter to modelSchema
        # if you need a better way to check if SD is disabled
        compliance = schemaAge.social_distance
        if compliance is not None and compliance > 0.0:
            useSocialDistancing = True
        updateParamFromSchema("socialDistancingCompliance", compliance, scenarioID)

    # General Scenario Parameters
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is not None:
        paramDict = {p: v for p, v in vars(schemaParameters).items() if v is not None}
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
            if parameter in paramDict:
                updateParamFromSchema(key, paramDict[parameter], scenarioID)

        # BCC Reduction
        updateParamFromSchema(
            "bccReducedRate",
            paramDict.get("bcc_reduction", 0.05) * idGet("bccRate", scenarioID, 4.0),
            scenarioID,
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
            # Relaxation always matches start on dashboard, so don't look for it
            startTrigger = paramDict.get(f"{npi}_trigger", "none")
            npiDelay = paramDict.get(f"{npi}_delay", 0)
            npiDuration = paramDict.get(f"{npi}_duration", 0)
            if startTrigger != "none":
                useNPIs[prefix] = True

                # Triggers
                if npiDelay == 0 and npiDuration > simLength * 2:
                    updateParamFromSchema(f"{prefix}Trigger", "Always", scenarioID)
                elif startTrigger != "none":
                    updateParamFromSchema(
                        f"{prefix}Trigger", triggerDict[startTrigger], scenarioID
                    )

                # Periods
                # Use baseline values to plug None gaps
                basePeriodStart, basePeriodEnd = idGet(f"{prefix}Period", 0, (1, 60))
                if npiDelay is None:
                    npiDelay = (basePeriodStart - 1) * 2
                if npiDuration is None:
                    npiDuration = (basePeriodEnd - basePeriodStart + 1) * 2

                # Calculate NPI period
                npiPeriodStart = (npiDelay // 2) + 1
                npiPeriodEnd = min(simLength, (npiDelay + npiDuration) // 2)
                updateParamFromSchema(
                    f"{prefix}Period", (npiPeriodStart, npiPeriodEnd), scenarioID
                )

        # Social distancing toggle
        useSocialDistancing = useSocialDistancing or bool(
            paramDict.get("social_distance_compliance", 0.0) > 0.0
        )

        # Social Distancing Table
        distanceParams = {
            p.removesuffix("_social_distance"): v
            for p, v in paramDict.items()
            if p.endswith("_social_distance")
        }
        if distanceParams:
            useSocialDistancing = True
            distanceTable = pd.DataFrame(
                columns=("Age Group", "Social Distancing Compliance")
            )
            for param, value in distanceParams.items():
                distanceTable.loc[distanceTable.shape[0]] = [param, value]
            updateTableFromSchema(
                "distanceAgeForm",
                distanceTable,
                scenarioID,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Social Distancing Compliance": [
                            paramDict.get(
                                idGet("socialDistancingCompliance", scenarioID, 0.0),
                            )
                        ],
                    },
                ),
            )

        # Final Toggles
        # TODO: Ensure that toggles being disabled is distinguishable from
        # parameters being unchanged from baselines
        updateParamFromSchema("socialDistancingToggle", useSocialDistancing, scenarioID)
        for prefix, value in useNPIs.items():
            updateParamFromSchema(f"{prefix}Toggle", value, scenarioID)
