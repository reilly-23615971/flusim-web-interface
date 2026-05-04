# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where vaccination/NPI parameters can be modified

# Imports
import logging
from typing import Literal, cast

import numpy as np
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import paramError
from ClientResources.ModelSchema import (
    EfficacyValue,
    Parameters,
    ageScenarioParameters,
    scenarioParameters,
    vaccineCoverage,
    vaccineDose,
    vaccineEfficacy,
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
    ordinals,
    triggerConditions,
)

# Logging
vaccineLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# TODO: See if the vaccination trigger parameters are fully working
# and reimplement them if they are
# TODO: Properly integrate the expander rerunning
@st.fragment
def buildVaccinationNPITab(id: int, advanced: bool = False):
    """
    Function to generate the parameters for vaccination and NPIs in a
    specified container with scenario differentiation.

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.

        advanced (bool): Set to `True` to show more complex parameters like
            individual vaccine dose efficacies.
    """

    """
    # Initialise session variables needed by the vaccination/NPI forms
    sessionParameters = {
        # Row counts
        f"vacAgeRowCount{id}": 0,
        f"primaryDoseCount{id}": 1,
        f"primWanedRowCount{id}": 0,
        f"boostAgeRowCount{id}": 0,
        f"socialRowCount{id}": 0,
        # Others
        f"classDismissal{id}": False,
    }
    for parameter, default in sessionParameters.items():
        session[parameter] = session.get(parameter, default)

    # Save primary row count as variable to avoid lookups (this
    # one's defined early since it's used for finalising remaining groups)
    primaryRowCount = session[f"primaryDoseCount{id}"]

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    ageGroupSets = {
        f"vaccineRemainingAgeGroups{id}": (f"vacAgeRowCount{id}", f"vacAgeGroup{id}-"),
        f"primaryRemainingWanedGroups{id}": (
            f"primWanedRowCount{id}",
            f"primWanedGroup{id}-",
        ),
        f"boosterRemainingAgeGroups{id}": (
            f"boostAgeRowCount{id}",
            f"boostAgeGroup{id}-",
        ),
        f"socialRemainingAgeGroups{id}": (
            f"socialRowCount{id}",
            f"socialAgeGroup{id}-",
        ),
    }

    # Calculate primary dose nested age group row counts
    for i in range(primaryRowCount):
        session[f"primAgeRowCount{id}-{i}"] = session.setdefault(
            f"primAgeRowCount{id}-{i}", 0
        )
        ageGroupSets[f"primaryRemainingAgeGroups{id}-{i}"] = (
            f"primAgeRowCount{id}-{i}",
            f"primAgeGroup{id}-{i}-",
        )
    primaryAgeRowCounts = [
        session[f"primAgeRowCount{id}-{i}"] for i in range(primaryRowCount)
    ]

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories.keys())

    # Parameters for keeping track of errors
    ageVacPropError, ageBoostEfficacyError = False, False"""
    simLength = session.get("cycleCount", 360)
    triggerNames = list(triggerConditions.keys())

    # Tab Content
    st.header("Vaccination and NPI Parameters")
    st.markdown("""
        This tab contains parameters relating to whether
        vaccination and non-pharmaceutical interventions (NPIs) are
        integrated into the simulation.
    """)

    # Vaccination
    st.subheader("Vaccination Parameters")
    loadKey("vaccineToggle", id, False)
    useVaccinesToggle = st.toggle(
        "Enable Vaccines in Simulation",
        value=False,
        on_change=saveKey,
        args=["vaccineToggle", id],
        key=f"_vaccineToggle{id}",
        help="""
Toggle whether or not individuals in the simulation
will be vaccinated against the pathogen.
        """,
    )

    # General Vaccination Policy Parameters
    # TODO: Vaccine Presets
    st.html(f'<span id = "vaccinationTriggerCondition{id}"></span>')
    with st.expander(
        "Vaccination Programs", key=f"vaccineProgramContainer{id}", on_change="rerun"
    ) as programContainer:
        if programContainer.open:
            # Describe what sort of parameters are here
            st.markdown("""
                These parameters control the rollout of vaccines in
                the simulation, with parameters such as how frequently
                vaccines are administered and what proportion of the
                population is already vaccinated.
            """)
            # TODO: Get data for a more accurate default
            loadKey("firstDoseRate", id, 300)
            st.number_input(
                "Vaccination Rate (Vaccinations per Day)",
                min_value=1,
                value=300,
                key=f"_firstDoseRate{id}",
                placeholder="Enter a whole number of people",
                on_change=saveKey,
                args=["firstDoseRate", id],
                disabled=not useVaccinesToggle,
                help="""
The number of unvaccinated individuals who will
receive the first dose of the vaccine each day.
                """,
            )

            # Limited Dose Parameters (if advanced parameters are enabled)
            if advanced:
                loadKey("limitDosesToggle", id, False)
                limitDosesToggle = st.toggle(
                    "Enable Limited Number of Vaccine Doses",
                    value=False,
                    key=f"_limitDosesToggle{id}",
                    disabled=not useVaccinesToggle,
                    on_change=saveKey,
                    args=["limitDosesToggle", id],
                    help="""
Toggle whether the number of vaccine doses that can be administered in each
simulation should be limited, putting an upper limit on the number of
vaccinated individuals in the simulation.
                    """,
                )
                if limitDosesToggle:
                    loadKey("initialDoseReserve", id, 0)
                    st.number_input(
                        "Total Number of Vaccine Doses",
                        min_value=0,
                        value=50000,
                        key=f"_initialDoseReserve{id}",
                        disabled=not useVaccinesToggle or not limitDosesToggle,
                        on_change=saveKey,
                        args=["initialDoseReserve", id],
                        placeholder="Enter a whole number of doses",
                        help="""
The total number of vaccine doses that will be available in the simulation. Once
all doses have been administered, any remaining unvaccinated individuals in the
simulation will never be vaccinated.

Note that only the first dose of the vaccine counts towards this limit.
Individuals who have already received the first dose of the vaccine will still
receive future doses regardless of the remaining dose count.
                        """,
                    )
            # TODO: See if imprecise percent sliders are better than no-percent inputs
            leftCol, rightCol = st.columns(2)
            loadKey("initialVaccinated", id, 0.0)
            initialVaccinated = leftCol.number_input(
                "Initial Vaccinated Proportion of Population",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.001,
                format="%0.5g",
                key=f"_initialVaccinated{id}",
                on_change=saveKey,
                args=["initialVaccinated", id],
                disabled=not useVaccinesToggle,
                help="""
The proportion of the population that will
already be vaccinated against the pathogen at
the beginning of the simulation.
                """,
            )
            '''
            initialVaccinated = st.slider(
                "Initial Vaccinated Proportion of Population",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.001,
                format="percent",
                key=f"_initialVaccinated{id}",
                on_change=saveKey,
                args=["initialVaccinated", id],
                disabled=not useVaccinesToggle,
                help="""
The percentage of the population that will
already be vaccinated against the pathogen at
the beginning of the simulation.
                """,
            )
            targetVaccinated = st.slider(
                "Target Vaccinated Proportion of Population",
                min_value=0.0,
                max_value=1.0,
                value=0.8,
                step=0.001,
                format="percent",
                key=f"_targetVaccinated{id}",
                on_change=saveKey,
                args=["targetVaccinated", id],
                disabled=not useVaccinesToggle,
                help="""
The percentage of the population that will be
targeted by the vaccine schedule in the
simulation. The actual proportion of the
population that is vaccinated may be lower if
there are an insufficient number of doses available.
                """,
            )
            '''
            loadKey("targetVaccinated", id, 0.8)
            targetVaccinated = rightCol.number_input(
                "Target Vaccinated Proportion of Population",
                min_value=0.0,
                max_value=1.0,
                value=0.8,
                step=0.001,
                format="%0.5g",
                key=f"_targetVaccinated{id}",
                on_change=saveKey,
                args=["targetVaccinated", id],
                disabled=not useVaccinesToggle,
                help="""
The proportion of the population that will be targeted by the vaccine schedule
in the simulation. The actual proportion of the population that is vaccinated
may be lower if there are an insufficient number of doses available.
                """,
            )

            # Show error if initial proportion is above target
            # TODO: Convert to using proportions if needed
            paramError(
                "vaccineTargetAlreadyFulfilled",
                id,
                lambda: useVaccinesToggle and initialVaccinated > targetVaccinated,
                f"""
                    Warning: The target vaccinated proportion of
                    population in the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{
                            session[f'scenarioName{id}']
                        }"'
                    } is
                    {100 * targetVaccinated:0.5g}% of the
                    population, but the initial vaccinated
                    proportion is {100 * initialVaccinated:0.5g}%. As
                    such, the target proportion will already be met,
                    and no new vaccinations will occur.

                    Please make one of the following changes:

                    - Increase Initial Vaccinated Proportion of Population in
                    :primary-badge[:material/vaccines: Vaccination and NPIs]
                    to be greater than {100 * targetVaccinated:0.5g}%.
                    - Decrease Target Vaccinated Proportion of Population in
                    :primary-badge[:material/vaccines: Vaccination and NPIs]
                    to be lower than {100 * initialVaccinated:0.5g}%.
                """,
                False,
            )

            # Store age-based proportion values for error checking
            # vacAgeInitials, vacAgeTargets = {}, {}

            # Modifiable-length field for age-specific vaccination
            st.markdown(
                "### Age-Specific Vaccinated Proportions",
                help="""
This table allows for unique vaccinated proportion parameters to be defined
for individual age groups in the simulation, overriding the global parameters
defined above.
                """,
            )
            if useVaccinesToggle:
                st.markdown("Double-click a cell in this table to edit its value.")
            loadKey(
                "vacPropAgeForm",
                id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Vaccinated Proportion": [initialVaccinated],
                        "Target Vaccinated Proportion": [targetVaccinated],
                    },
                ),
                dataframe=True,
            )
            vacPropAgeForm = st.data_editor(
                session[f"vacPropAgeForm{id}"],
                height="content",
                num_rows="dynamic",
                key=f"_vacPropAgeForm{id}",
                on_change=saveKey,
                args=["vacPropAgeForm", id],
                kwargs={"dataframe": True},
                disabled=not useVaccinesToggle,
                placeholder=(
                    "Enter a value"
                    if useVaccinesToggle
                    else "Enable vaccines to edit this parameter"
                ),
                column_config={
                    "Age Group": st.column_config.SelectboxColumn(
                        "Age Group",
                        required=True,
                        options=ageTimeDict.keys(),
                        format_func=lambda x: ageTimeDict[x],  # type: ignore
                        help="""
An age group that will have specific vaccine proportions defined for it,
overriding the base proportions.
                        """,
                    ),
                    "Initial Vaccinated Proportion": st.column_config.NumberColumn(
                        "Initial Vaccinated Percentage",
                        required=True,
                        default=initialVaccinated,
                        min_value=0.0,
                        max_value=1.0,
                        format="percent",
                        help="""
The percentage of individuals in this age group that will already be
vaccinated against the pathogen at the beginning of the simulation.
                        """,
                    ),
                    "Target Vaccinated Proportion": st.column_config.NumberColumn(
                        "Target Vaccinated Percentage",
                        required=True,
                        default=targetVaccinated,
                        min_value=0.0,
                        max_value=1.0,
                        format="percent",
                        help="""
The percentage of individuals in this age group that will be targeted by the
vaccine schedule in the simulation. The actual proportion of individuals that
are vaccinated may be lower if there are an insufficient number of doses available.
                        """,
                    ),
                },
            )
            paramError(
                "vacPropAgeFormDuplicates",
                id,
                lambda: hasDuplicates(vacPropAgeForm),
                f"""
                    Error: The age-specific vaccinated proportions form used by the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{session[f'scenarioName{id}']}"'
                    } contains duplicate age group rows. Each age group
                    should only be used in a single row of the form.

                    Please remove or change any rows of the Age-Specific
                    Vaccinated Proportion Parameters form in
                    :primary-badge[:material/vaccines: Vaccinations and NPIs]
                    that use the same age group as another row.
                """,
                True,
            )
            # TODO: make data_editor error messages name the rows
            paramError(
                "vacPropAgeFormTargetAlreadyFulfilled",
                id,
                lambda: np.any(
                    vacPropAgeForm["Initial Vaccinated Proportion"]
                    > vacPropAgeForm["Target Vaccinated Proportion"]
                ),
                f"""
                    Error: The age-specific vaccinated proportions form used by the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{session[f'scenarioName{id}']}"'
                    } contains rows where the initial vaccinated proportion is
                    greater than the target vaccinated proportion. As such,
                    the target proportion will already be met, and no new
                    vaccinations will occur for the age groups specified
                    by these rows.

                    Please make one of the following changes:

                    - Remove all rows of the Age-Specific
                    Vaccinated Proportion Parameters form in
                    :primary-badge[:material/vaccines: Vaccination and NPIs]
                    that have the initial proportion higher than the target proportion.
                    - Decrease the Initial Vaccinated Proportion of Population
                    column in :primary-badge[:material/vaccines: Vaccination and NPIs]
                    to always be lower than the target proportion.
                    - Increase the Target Vaccinated Proportion of Population
                    column in :primary-badge[:material/vaccines: Vaccination and NPIs]
                    to always be higher than the initial proportion.
                """,
                True,
            )

            '''# Save relevant params as variables to avoid lookups
            vaccineRowCount = session[f"vacAgeRowCount{id}"]
            vacAgeRemainingGroups = session[f"vaccineRemainingAgeGroups{id}"]
            vacAgeErrorContainer = st.container()
            vacAgeProportionContainer = st.container()
            for i in range(vaccineRowCount):
                (vacAgeGroupColumn, vacAgeInitialColumn, vacAgeRemoveColumn) = (
                    vacAgeProportionContainer.columns(
                        (0.25, 0.55, 0.2), vertical_alignment="center"
                    )
                )
                vacAgeCurrentGroup = session.get(f"vacAgeGroup{id}-{i}")

                # Age group column
                loadKey(
                    "vacAgeGroup",
                    id,
                    (
                        vacAgeCurrentGroup
                        if vacAgeCurrentGroup
                        else vacAgeRemainingGroups[0]
                    ),
                    f"-{i}",
                )
                with vacAgeGroupColumn:
                    vacAgeGroup = st.selectbox(
                        "Age Group",
                        key=f"_vacAgeGroup{id}-{i}",
                        # Set age group options such that only ages
                        # that haven't been selected yet can be selected
                        options=(
                            [vacAgeCurrentGroup]
                            + [
                                group
                                for group in vacAgeRemainingGroups
                                if group != vacAgeCurrentGroup
                            ]
                            if vacAgeCurrentGroup
                            else vacAgeRemainingGroups
                        ),
                        disabled=(not useVaccinesToggle or not vaccineRowCount < 10),
                        on_change=saveKey,
                        args=["vacAgeGroup", id, f"-{i}"],
                        help="""
                        An age group that will have specific
                        vaccination initial and target proportions
                        defined for it, overriding the base
                        proportions.

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
                # Initial proportion column
                loadKey("vacAgeInitial", id, 0.0, f"-{i}")
                with vacAgeInitialColumn:
                    vacAgeInitials[vacAgeGroup] = st.select_slider(
                        "Initial Vaccinated Proportion of Population",
                        np.linspace(0.0, 1.0, 201),
                        0.0,
                        format_func=lambda x: f"{100 * x:0.3g}%",
                        disabled=not useVaccinesToggle,
                        on_change=saveKey,
                        args=["vacAgeInitial", id, f"-{i}"],
                        key=f"_vacAgeInitial{id}-{i}",
                        help="""
                            The percentage of individuals in this
                            age group that will already be
                            vaccinated against the pathogen at the
                            beginning of the simulation.
                        """,
                    )
                # Target proportion column
                loadKey("vacAgeTarget", id, 0.8, f"-{i}")
                with vacAgeInitialColumn:
                    vacAgeTargets[vacAgeGroup] = st.select_slider(
                        "Target Vaccinated Proportion of Population",
                        np.linspace(0.0, 1.0, 201),
                        0.8,
                        format_func=lambda x: f"{100 * x:0.3g}%",
                        disabled=not useVaccinesToggle,
                        on_change=saveKey,
                        args=["vacAgeTarget", id, f"-{i}"],
                        key=f"_vacAgeTarget{id}-{i}",
                        help="""
                            The percentage of individuals in this
                            age group that will be targeted by the
                            vaccine schedule in the simulation. The
                            actual proportion of individuals that
                            are vaccinated may be lower if there
                            are an insufficient number of doses
                            available.
                        """,
                    )
                # Delete button column
                with vacAgeRemoveColumn:
                    st.button(
                        label="Remove Age Group",
                        icon=":material/delete:",
                        key=f"vacAgeRemove{id}-{i}",
                        on_click=deleteFormRow,
                        args=(
                            i,
                            f"vacAgeRowCount{id}",
                            {
                                f"vacAgeGroup{id}-",
                                f"vacAgeInitial{id}-",
                                f"vacAgeTarget{id}-",
                            },
                        ),
                        disabled=not useVaccinesToggle,
                        help="""
                        Remove this row of the form and remove
                        these age-specific vaccine proportion
                        values from the simulation.
                    """,
                    )
            # Button to add another row for age specific params
            vacAgeProportionContainer.button(
                label="Add Age Group",
                icon=":material/add:",
                on_click=addFormRow,
                key=f"vacAgeAdd{id}",
                args=(
                    f"vacAgeRowCount{id}",
                    {
                        f"vacAgeGroup{id}-{vaccineRowCount}": (
                            vacAgeRemainingGroups[0] if vacAgeRemainingGroups else None
                        ),
                        f"vacAgeInitial{id}-{vaccineRowCount}": initialVaccinated,
                        f"vacAgeTarget{id}-{vaccineRowCount}": targetVaccinated,
                    },
                ),
                disabled=(not useVaccinesToggle or not vaccineRowCount < 10),
                help=(
                    """
                    Add another row to this form, where you can
                    select an additional age group to have unique
                    vaccinated proportion values.
                """
                    if vaccineRowCount <= 9
                    else """
                    All age groups have been given unique
                    vaccinated proportion values, so a new age
                    group cannot be added.
                """
                ),
            )

            # Age-based errors if initial proportion is above target
            for age in vacAgeInitials.keys():
                currentInitial = vacAgeInitials[age]
                currentTarget = vacAgeTargets[age]
                if useVaccinesToggle and currentInitial >= currentTarget:
                    vacAgeErrorContainer.warning(
                        f"""
                        Warning: The target vaccinated proportion
                        in the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{
                                session[f'scenarioName{id}']
                            }"'
                        } for the "{age}" age group is currently
                        set to {100 * currentTarget:0.3g}% of the
                        population, but the initial vaccinated
                        proportion for said age group in this
                        scenario is set to
                        {100 * currentInitial:0.3g}%. As such, the
                        target vaccination level will already be
                        met, and no new vaccinations will occur in
                        this scenario for individuals in the
                        "{age}" age group.

                        If this is not desired behaviour, please
                        address this error by making one of the
                        following changes before running the
                        simulation:

                        - Remove the scenario's age-specific
                        vaccination proportions for the "{age}" age
                        group.
                        - Increase the scenario's Initial
                        Vaccinated Proportion of Population for the
                        "{age}" age group to be greater
                        than {100 * currentTarget:0.3g}%.
                        - Decrease the scenario's Target Vaccinated
                        Proportion of Population for the "{age}"
                        age group to be lower
                        than {100 * currentInitial:0.3g}%.
                    """,
                        icon=":material/warning:",
                    )
                    globalErrorContainer.warning(
                        f"""
                        Warning: The target vaccinated proportion
                        in the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{
                                session[f'scenarioName{id}']
                            }"'
                        } for the "{age}" age group is currently
                        set to {100 * currentTarget:0.3g}% of the
                        population, but the initial vaccinated
                        proportion for said age group in this
                        scenario is set to
                        {100 * currentInitial:0.3g}%. As such, the
                        target vaccination level will already be
                        met, and no new vaccinations will occur in
                        this scenario for individuals in the
                        "{age}" age group.

                        If this is not desired behaviour, please
                        address this error by making one of the
                        following changes before running the
                        simulation:

                        - Remove the scenario's age-specific
                        vaccination proportions for the "{age}" age
                        group from the "Vaccination Programs"
                        section of the "Vaccinations and NPIs" tab.
                        - Increase the scenario's Initial
                        Vaccinated Proportion of Population for the
                        "{age}" age group in the "Vaccination
                        Programs" section of the "Vaccinations and
                        NPIs" tab to be greater
                        than {100 * currentTarget:0.3g}%.
                        - Decrease the scenario's Target Vaccinated
                        Proportion of Population for the "{age}"
                        age group in the "Vaccination Programs"
                        section of the "Vaccinations and NPIs" tab
                        to be lower
                        than {100 * currentInitial:0.3g}%.
                    """,
                        icon=":material/warning:",
                    )
                    session[f"ageVacPropError{id}"] = 1
                    ageVacPropError = True
            # Reset error parameter if none of the age levels error
            if not ageVacPropError:
                session[f"ageVacPropError{id}"] = 0'''

    # Primary Vaccine Parameters
    with st.expander(
        "Vaccine Properties", key=f"vaccinePropertyContainer{id}", on_change="rerun"
    ) as vaccineContainer:
        if vaccineContainer.open:
            # Describe primary vaccines
            st.markdown("""
                These parameters control the properties of the main
                schedule of vaccines that will be administered to
                individuals within the simulation. Each vaccine in
                the schedule can have its own efficacy values set,
                since in many cases multiple doses are required to
                achieve maximum immunity to the pathogen.
            """)

            # Universal primary parameters
            loadKey("primaryDoseCount", id, 1)
            primaryDoseCount = st.slider(
                "Number of Vaccine Doses",
                1,
                5,
                1,
                key=f"_primaryDoseCount{id}",
                on_change=saveKey,
                args=["primaryDoseCount", id],
                disabled=not useVaccinesToggle,
                help="""
The number of times each individual in the
simulation will be administered a vaccine for
the pathogen, excluding booster vaccines.
                """,
            )
            if primaryDoseCount > 1:
                loadKey("primaryDelay", id, 3)
                st.slider(
                    "Time Between Vaccine Doses (Months)",
                    min_value=1,
                    max_value=12,
                    value=3,
                    disabled=(not useVaccinesToggle) or primaryDoseCount == 1,
                    on_change=saveKey,
                    args=["primaryDelay", id],
                    key=f"_primaryDelay{id}",
                    help="""
The number of months after an individual
receives a vaccine dose before they are able to
receive another, where a month is 30 days.
                    """,
                )
            # Waning parameters (only if advanced parameters are enabled)
            if advanced:
                loadKey("vaccineWaningToggle", id, False)
                waningToggle = st.toggle(
                    "Enable Vaccine Immunity Waning",
                    value=False,
                    on_change=saveKey,
                    args=["vaccineWaningToggle", id],
                    key=f"_vaccineWaningToggle{id}",
                    help="""
Toggle whether or not immunity gained from being vaccinated will
wane over time. If this is enabled, individuals in the simulation can be
infected if it has been a sufficiently long time since they were vaccinated.
                    """,
                )
                if waningToggle:
                    loadKey("primaryDuration", id, 6)
                    st.slider(
                        "Vaccine Immunity Waning Delay (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=saveKey,
                        args=["primaryDuration", id],
                        key=f"_primaryDuration{id}",
                        help="""
The number of months after an individual receives a vaccine dose before they
begin losing their immunity, where a month is 30 days.
                        """,
                    )
                    loadKey("primaryWaningRate", id, 12)
                    st.slider(
                        "Vaccine Waning Duration (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=saveKey,
                        args=["primaryWaningRate", id],
                        key=f"_primaryWaningRate{id}",
                        help="""
The number of months after a vaccinated individual begins losing their immunity
before their resistance to the pathogen reaches its lowest point, where a month
is 30 days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                        """,
                    )

                # Store age-based efficacy values for error checking
                # primaryInitialEfficacy = 0.5
                # primAgeInitials = {}

                # Modifiable-length field for each primary dose
                st.markdown(f"""
                    ### {"Individual " if waningToggle else ""}Dose Efficacies

                    Here you can set the {"initial " if waningToggle else ""}efficacy
                    of each vaccine dose in the schedule separately. Note that
                    changing the "Number of Vaccine Doses" parameter
                    will affect how many sections are present here.
                """)
                # TODO: Is 1% precision precise enough?
                for i in range(primaryDoseCount):
                    with st.container(border=True):
                        st.markdown(f"#### {ordinals[i+1]} Vaccine Dose")
                        loadKey("primaryBaseEfficacy", id, 0.5, f"-{i}")
                        baseDoseEfficacy = st.slider(
                            (
                                "Initial Dose Efficacy (Probability)"
                                if waningToggle
                                else "Dose Efficacy (Probability)"
                            ),
                            min_value=0.0,
                            max_value=1.0,
                            value=0.5,
                            format="percent",
                            disabled=not useVaccinesToggle,
                            on_change=saveKey,
                            args=["primaryBaseEfficacy", id, f"-{i}"],
                            key=f"_primaryBaseEfficacy{id}-{i}",
                            help=f"""
The {"initial " if waningToggle else ""}efficacy of this vaccine dose,
represented as the probability that an individual that has received the
dose will remain healthy when exposed to the pathogen.
                            """,
                        )

                        # Age-Specific Primary Efficacy Field
                        st.markdown(
                            (
                                "##### Age-Specific Initial Efficacy"
                                if waningToggle
                                else "##### Age-Specific Efficacy"
                            ),
                            help=f"""
This section allows unique {"initial " if waningToggle else ""}efficacy values
for this dose to be defined for individual age groups in the simulation,
overriding the global efficacy value for this dose defined above.
                            """,
                        )
                        if useVaccinesToggle:
                            st.markdown(
                                "Double-click a cell in this table to edit its value."
                            )
                        loadKey(
                            "vacInitialEfficacyAgeForm",
                            id,
                            pd.DataFrame(
                                {
                                    "Age Group": [None],
                                    "Initial Dose Efficacy": [baseDoseEfficacy],
                                },
                            ),
                            f"-{i}",
                            dataframe=True,
                        )
                        vacInitialEfficacyAgeForm = st.data_editor(
                            session[f"vacInitialEfficacyAgeForm{id}-{i}"],
                            height="content",
                            num_rows="dynamic",
                            key=f"_vacInitialEfficacyAgeForm{id}-{i}",
                            on_change=saveKey,
                            args=["vacInitialEfficacyAgeForm", id, f"-{i}"],
                            kwargs={"dataframe": True},
                            disabled=not useVaccinesToggle,
                            placeholder=(
                                "Enter a value"
                                if useVaccinesToggle
                                else "Enable vaccines to edit this parameter"
                            ),
                            column_config={
                                "Age Group": st.column_config.SelectboxColumn(
                                    "Age Group",
                                    required=True,
                                    options=ageTimeDict.keys(),
                                    format_func=lambda x: ageTimeDict[x],  # type: ignore
                                    help=f"""
An age group that will have a specific
{"initial " if waningToggle else ""}efficacy value defined
for this vaccine dose, overriding the base value.
                                    """,
                                ),
                                "Initial Dose Efficacy": st.column_config.NumberColumn(
                                    (
                                        "Initial Dose Efficacy (Probability)"
                                        if waningToggle
                                        else "Dose Efficacy (Probability)"
                                    ),
                                    required=True,
                                    default=baseDoseEfficacy,
                                    min_value=0.0,
                                    max_value=1.0,
                                    format="percent",
                                    help=f"""
The {"initial " if waningToggle else ""}efficacy of this vaccine dose for
this age group, represented as the probability that a vaccinated individual in
this age group will remain healthy when exposed to the pathogen.
                                    """,
                                ),
                            },
                        )
                        paramError(
                            f"vacInitialEfficacyAgeForm{i}Duplicates",
                            id,
                            lambda: hasDuplicates(vacInitialEfficacyAgeForm),
                            f"""
Error: The age-specific {"initial" if waningToggle else "dose"} efficacy
form used for the {ordinals[i+1].lower()} vaccine dose by the
{'baseline scenario' if id == 0 else f'scenario named "{session[f'scenarioName{id}']}"'}
contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific
{"Initial " if waningToggle else ""}Efficacy form in the {ordinals[i+1]}
Vaccine Dose section of :primary-badge[:material/vaccines: Vaccinations and NPIs]
that use the same age group as another row.
                            """,
                            True,
                        )

                        '''
                        # Save remaining ages to variable to avoid lookups
                        primAgeRemainingGroups = session[
                            f"primaryRemainingAgeGroups{id}-{i}"
                        ]
                        (primEfficacyErrorContainer) = doseEfficacyContainer.container()
                        primEfficacyContainer = doseEfficacyContainer.container()
                        for j in range(primaryAgeRowCounts[i]):
                            (
                                primAgeGroupColumn,
                                primAgeEfficacyColumn,
                                primAgeRemoveColumn
                            ) = (
                                primEfficacyContainer.columns(
                                    (0.25, 0.55, 0.2), vertical_alignment="center"
                                )
                            )
                            primAgeCurrentGroup = session.get(
                                f"primAgeGroup{id}-{i}-{j}"
                            )
                            # Age group column
                            loadKey(
                                "primAgeGroup",
                                id,
                                (
                                    primAgeCurrentGroup
                                    if primAgeCurrentGroup
                                    else primAgeRemainingGroups[0]
                                ),
                                f"-{i}-{j}",
                            )
                            with primAgeGroupColumn:
                                primAgeGroup = st.selectbox(
                                    "Age Group",
                                    key=f"_primAgeGroup{id}-{i}-{j}",
                                    # Set age group options such that only ages
                                    # that haven't been selected yet can be
                                    # selected
                                    options=(
                                        [primAgeCurrentGroup]
                                        + [
                                            group
                                            for group in primAgeRemainingGroups
                                            if group != primAgeCurrentGroup
                                        ]
                                        if primAgeCurrentGroup
                                        else primAgeRemainingGroups
                                    ),
                                    disabled=(
                                        not useVaccinesToggle
                                        or not primaryAgeRowCounts[i] < 10
                                    ),
                                    on_change=saveKey,
                                    args=["primAgeGroup", id, f"-{i}-{j}"],
                                    help="""
                                    An age group that will have specific
                                    initial vaccine efficacy values defined
                                    for it, overriding the base efficacy
                                    value for this vaccine dose.

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
                            # Initial efficacy column
                            loadKey("primAgeEfficacy", id, 0.5, f"-{i}-{j}")
                            with primAgeEfficacyColumn:
                                ageInitialEfficacy = st.select_slider(
                                    "Initial Dose Efficacy (Probability)",
                                    np.linspace(0.0, 1.0, 201),
                                    0.5,
                                    format_func=lambda x: f"{100 * x:0.3g}%",
                                    disabled=not useVaccinesToggle,
                                    key=f"_primAgeEfficacy{id}-{i}-{j}",
                                    on_change=saveKey,
                                    args=["primAgeEfficacy", id, f"-{i}-{j}"],
                                    help="""
                                        The initial efficacy of this
                                        vaccine dose for this age group,
                                        represented as the probability that
                                        a recently vaccinated individual in
                                        this age group will remain healthy
                                        when exposed to the pathogen.
                                    """,
                                )

                                # Last efficacy value is all that's cared
                                # about for error checking purposes
                                if i == primaryDoseCount - 1:
                                    primAgeInitials[primAgeGroup] = ageInitialEfficacy

                            # Delete button column
                            with primAgeRemoveColumn:
                                st.button(
                                    label="Remove Age Group",
                                    icon=":material/delete:",
                                    key=f"primAgeRemove{id}-{i}-{j}",
                                    on_click=deleteFormRow,
                                    args=(
                                        i,
                                        f"primAgeRowCount{id}-{i}",
                                        {f"primAgeGroup{id}-{i}-",
                                        f"primAgeEfficacy{id}-{i}-"},
                                    ),
                                    disabled=not useVaccinesToggle,
                                    help="""
                                    Remove this row of the form and remove
                                    these age-specific initial vaccine
                                    efficacy values from the simulation.
                                """,
                                )
                        # Button to add another row for age-specific params
                        primEfficacyContainer.button(
                            label="Add Age Group",
                            icon=":material/add:",
                            on_click=addFormRow,
                            key=f"primAgeAdd{id}-{i}",
                            args=(
                                f"primAgeRowCount{id}-{i}",
                                {
                                    f"primAgeGroup{id}-{i}-{primaryAgeRowCounts[i]}": (
                                        primAgeRemainingGroups[0]
                                        if primAgeRemainingGroups
                                        else None
                                    ),
                                    (
                                        (
                                            f"primAgeEfficacy{id}-{i}"
                                            f"-{primaryAgeRowCounts[i]}"
                                        )
                                    ): baseDoseEfficacy,
                                },
                            ),
                            disabled=(
                                not useVaccinesToggle
                                or not primaryAgeRowCounts[i] < 10
                            ),
                            help=(
                                """
                                Add another row to this form, where you can
                                select an additional age group to have
                                unique initial vaccine efficacy values.
                            """
                                if primaryAgeRowCounts[i] <= 9
                                else """
                                All age groups have been given unique
                                initial efficacy values for this vaccine
                                dose, so a new age group cannot be added.
                            """
                            ),
                        )

                        # Check errors in age-based primary efficacy
                        if i == primaryDoseCount - 1 and useVaccinesToggle:
                            initialAges = primAgeInitials.keys()
                            wanedAges = primAgeWaneds.keys()
                            for age in list(initialAges) + list(
                                set(wanedAges) - set(initialAges)
                            ):
                                initialAgeEfficacy = primAgeInitials.get(
                                    age, primaryInitialEfficacy
                                )
                                wanedAgeEfficacy = primAgeWaneds.get(
                                    age, primaryWanedEfficacy
                                )
                                ageIsInitial = age in initialAges
                                ageIsWaned = age in wanedAges
                                if initialAgeEfficacy > wanedAgeEfficacy:
                                    primEfficacyErrorContainer.error(
                                        f"""
                                        Error: The initial vaccine efficacy
                                        in the {
                                            'baseline scenario' if id == 0
                                            else f'scenario named "{
                                                session[
                                                    f'scenarioName{id}'
                                                ]
                                            }"'
                                        } for the final dose in the "{age}"
                                        age group is currently set to {
                                            '' if ageIsInitial
                                            else 'the scenario base value of'
                                        } {100 * initialAgeEfficacy:0.3g}%
                                        effectiveness, but the final
                                        vaccine efficacy after immunity
                                        waning for said age group in this
                                        scenario is set to {
                                            '' if ageIsWaned
                                            else 'the scenario base value of'
                                        } {100 * wanedAgeEfficacy:0.3g}%.
                                        As such, the immunity to the
                                        pathogen conferred by the vaccine
                                        will get stronger over time instead
                                        of weaker for individuals in the
                                        "{age}" age group.

                                        To address this error, please make
                                        one of the following changes before
                                        running the simulation:

                                        - Remove the scenario's
                                        age-specific {
                                            'initial (final dose)'
                                            if ageIsInitial else ''
                                        }{
                                            'and ' if ageIsInitial and ageIsWaned
                                            else ''
                                        }{
                                            'waned ' if ageIsInitial else ''
                                        }dose efficacy rate{
                                            's' if ageIsInitial and ageIsWaned
                                            else ''
                                        } for the "{age}" age group.
                                        - Increase the scenario's {
                                            'age-specific' if ageIsInitial
                                            else 'base'
                                        } Initial Dose Efficacy for the
                                        final vaccine dose in the program
                                        to be greater than
                                        {100 * wanedAgeEfficacy:0.3g}%.
                                        - Decrease the scenario's {
                                            'age-specific' if ageIsInitial
                                            else 'base'
                                        } Dose Efficacy After Immunity
                                        Waning to be lower than
                                        {100 * initialAgeEfficacy:0.3g}%.
                                    """,
                                        icon=":material/error:",
                                    )
                                    globalErrorContainer.error(
                                        f"""
                                        Error: The initial vaccine efficacy
                                        in the {
                                            'baseline scenario' if id == 0
                                            else f'scenario named "{
                                                session[
                                                    f'scenarioName{id}'
                                                ]
                                            }"'
                                        } for the final dose in the "{age}"
                                        age group is currently set to {
                                            '' if age in initialAges
                                            else 'the scenario base value of'
                                        } {100 * initialAgeEfficacy:0.3g}%
                                        effectiveness, but the final
                                        vaccine efficacy after immunity
                                        waning for said age group in this
                                        scenario is set to {
                                            '' if age in wanedAges
                                            else 'the scenario base value of'
                                        } {100 * wanedAgeEfficacy:0.3g}%.
                                        As such, the immunity to the
                                        pathogen conferred by the vaccine
                                        will get stronger over time instead
                                        of weaker for individuals in the
                                        "{age}" age group.

                                        To address this error, please make
                                        one of the following changes before
                                        running the simulation:

                                        - Remove the scenario's
                                        age-specific {
                                            'initial (final dose)'
                                            if ageIsInitial else ''
                                        }{
                                            'and ' if ageIsInitial and ageIsWaned
                                            else ''
                                        }{
                                            'waned ' if ageIsInitial else ''
                                        }dose efficacy rate{
                                            's' if ageIsInitial and ageIsWaned
                                            else ''
                                        } for the "{age}" age group in the
                                        "Vaccination Properties" section of
                                        the "Vaccinations and NPIs" tab.
                                        - Increase the scenario's {
                                            'age-specific' if ageIsInitial
                                            else 'base'
                                        } Initial Dose Efficacy for the
                                        final vaccine dose in the program
                                        in the "Vaccination Properties"
                                        section of the "Vaccinations and
                                        NPIs" tab to be greater than
                                        {100 * wanedAgeEfficacy:0.3g}%.
                                        - Decrease the scenario's {
                                            'age-specific' if ageIsInitial
                                            else 'base'
                                        } Dose Efficacy After Immunity
                                        Waning in the "Vaccination
                                        Properties" section of the
                                        "Vaccinations and NPIs" tab to be
                                        lower than
                                        {100 * initialAgeEfficacy:0.3g}%.
                                    """,
                                        icon=":material/error:",
                                    )
                                    session[f"agePrimEfficacyError{id}"] = 2
                                    ageBoostEfficacyError = True
                            # Reset error parameter if no errors
                            if not ageBoostEfficacyError:
                                session[f"agePrimEfficacyError{id}"] = 0'''

                # Efficacy After Waning
                if waningToggle:
                    loadKey("primaryWanedEfficacy", id, 0.0)
                    primaryWanedEfficacy = st.slider(
                        "Dose Efficacy After Immunity Waning (Probability)",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.0,
                        format="percent",
                        disabled=not useVaccinesToggle,
                        on_change=saveKey,
                        args=["primaryWanedEfficacy", id],
                        key=f"_primaryWanedEfficacy{id}",
                        help="""
The efficacy of a vaccinated individual's immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                        """,
                    )
                    # Last efficacy value is all that's cared about
                    # for error checking purposes
                    finalDose = primaryDoseCount - 1
                    finalInitialEfficacy = idGet(
                        "primaryBaseEfficacy", id, 0.5, f"-{finalDose}"
                    )
                    paramError(
                        "wanedEfficacyAboveInitial",
                        id,
                        lambda: useVaccinesToggle
                        and primaryWanedEfficacy > finalInitialEfficacy,
                        f"""
                            Error: The initial vaccine efficacy for
                            the final vaccine dose in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[f'scenarioName{id}']
                                }"'
                            } is {100 * finalInitialEfficacy:0.3g}%, but the
                            efficacy after waning is {100 * primaryWanedEfficacy:0.3g}%.
                            As such, a vaccinated person's immunity to the
                            pathogen will get stronger over time instead of weaker.

                            Please make one of the following changes:

                            - Increase Initial Dose Efficacy for the final dose in
                            :primary-badge[:material/vaccines: Vaccination and NPIs]
                            to be greater than {100 * primaryWanedEfficacy:0.3g}%.
                            - Decrease Dose Efficacy After Immunity Waning in
                            :primary-badge[:material/vaccines: Vaccination and NPIs]
                            to be lower than {100 * finalInitialEfficacy:0.3g}%.
                        """,
                        True,
                    )

                    # Store age-based waned efficacy values for error checks
                    # primAgeWaneds = {}

                    # Age-Specific Waned Efficacy Field
                    st.markdown(
                        "#### Age-Specific Efficacy After Immunity Waning",
                        help="""
This table allows for unique final efficacy values after immunity waning
to be defined for individual age groups in the simulation, overriding
the global waned efficacy defined above.
                        """,
                    )
                    if useVaccinesToggle:
                        st.markdown(
                            "Double-click a cell in this table to edit its value."
                        )
                    loadKey(
                        "vacWaneAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Dose Efficacy After Waning": [primaryWanedEfficacy],
                            },
                        ),
                        dataframe=True,
                    )
                    vacWaneAgeForm = st.data_editor(
                        session[f"vacWaneAgeForm{id}"],
                        height="content",
                        num_rows="dynamic",
                        key=f"_vacWaneAgeForm{id}",
                        on_change=saveKey,
                        args=["vacWaneAgeForm", id],
                        kwargs={"dataframe": True},
                        disabled=not useVaccinesToggle,
                        placeholder=(
                            "Enter a value"
                            if useVaccinesToggle
                            else "Enable vaccines to edit this parameter"
                        ),
                        column_config={
                            "Age Group": st.column_config.SelectboxColumn(
                                "Age Group",
                                required=True,
                                options=ageTimeDict.keys(),
                                format_func=lambda x: ageTimeDict[x],  # type: ignore
                                help="""
An age group that will have a specific final efficacy value after
immunity waning defined for it, overriding the base value.
                                """,
                            ),
                            "Dose Efficacy After Waning": st.column_config.NumberColumn(
                                "Dose Efficacy After Immunity Waning (Probability)",
                                required=True,
                                default=primaryWanedEfficacy,
                                min_value=0.0,
                                max_value=1.0,
                                format="percent",
                                help="""
The efficacy of a vaccinated individual in this age group's immunity after the
full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                            ),
                        },
                    )
                    paramError(
                        "vacWaneAgeFormDuplicates",
                        id,
                        lambda: hasDuplicates(vacWaneAgeForm),
                        f"""
                            Error: The age-specific efficacy after
                            immunity waning form used by the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{session[f'scenarioName{id}']}"'
                            } contains duplicate age group rows. Each age group
                            should only be used in a single row of the form.

                            Please remove or change any rows of the Age-Specific Efficacy
                            After Immunity Waning form in the Vaccine Properties section
                            of :primary-badge[:material/vaccines: Vaccinations and NPIs]
                            that use the same age group as another row.
                        """,
                        True,
                    )
                    # TODO: Have these errors highlight specific ages
                    finalInitialEfficacyAgeForm = idGet(
                        "vacInitialEfficacyAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [
                                    idGet(
                                        "primaryBaseEfficacy", id, 0.5, f"-{finalDose}"
                                    )
                                ],
                            },
                        ),
                        f"-{finalDose}",
                    )
                    combinedEfficacy = pd.merge(
                        finalInitialEfficacyAgeForm,
                        vacWaneAgeForm,
                        how="inner",
                        on="Age Group",
                    )
                    # TODO: make data_editor error messages name the row
                    # (and not break on dupes)
                    paramError(
                        "ageWanedEfficiencyAboveInitial",
                        id,
                        lambda: np.any(
                            combinedEfficacy["Initial Dose Efficacy"]
                            < combinedEfficacy["Dose Efficacy After Waning"]
                        ),
                        f"""
                            Error: The vaccine age-specific
                            efficacy forms used for the final vaccine dose by the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{session[f'scenarioName{id}']}"'
                            } contains rows where the initial vaccine efficacy is
                            greater than the efficacy after immunity waning. As such, the
                            immunity to the pathogen conferred by the vaccine will get
                            stronger over time instead of weaker for the age groups
                            specified by these rows.

                            Please modify the Age-Specific Initial Efficacy form
                            for the final vaccine dose alongside the Age-Specific
                            Efficacy After Immunity Waning form
                            in :primary-badge[:material/vaccines: Vaccination and NPIs]
                            such that no age group has its initial efficacy lower
                            than its waned efficacy.
                        """,
                        True,
                    )

                '''# Save relevant params as variables to avoid lookups
                primaryWanedRowCount = session[f"primWanedRowCount{id}"]
                primWanedRemainingGroups = session[
                    f"primaryRemainingWanedGroups{id}"
                ]
                primWanedContainer = st.container()
                for i in range(primaryWanedRowCount):
                    (primWanedGroupColumn, primWanedEffColumn, primWanedRemoveColumn) = (
                        primWanedContainer.columns(
                            (0.25, 0.55, 0.2), vertical_alignment="center"
                        )
                    )
                    primWanedCurrentGroup = session.get(f"primWanedGroup{id}-{i}")

                    # Age group column
                    loadKey(
                        "primWanedGroup",
                        id,
                        (
                            primWanedCurrentGroup
                            if primWanedCurrentGroup
                            else primWanedRemainingGroups[0]
                        ),
                        f"-{i}",
                    )
                    with primWanedGroupColumn:
                        primWanedGroup = st.selectbox(
                            "Age Group",
                            key=f"_primWanedGroup{id}-{i}",
                            # Set age group options such that only ages
                            # that haven't been selected yet can be selected
                            options=(
                                [primWanedCurrentGroup]
                                + [
                                    group
                                    for group in primWanedRemainingGroups
                                    if group != primWanedCurrentGroup
                                ]
                                if primWanedCurrentGroup
                                else primWanedRemainingGroups
                            ),
                            disabled=(
                                not useVaccinesToggle or not primaryWanedRowCount < 10
                            ),
                            on_change=saveKey,
                            args=["primWanedGroup", id, f"-{i}"],
                            help="""
                            An age group that will have a specific
                            final efficacy value after immunity waning
                            defined for it, overriding the base waned
                            efficacy value.

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
                    # Waned efficacy column
                    loadKey("primAgeWanedEfficacy", id, 0.0, f"-{i}")
                    with primWanedEffColumn:
                        primAgeWaneds[primWanedGroup] = st.select_slider(
                            (("Dose Efficacy After Immunity Waning (Probability)")),
                            np.linspace(0.0, 1.0, 201),
                            0.0,
                            format_func=lambda x: f"{100 * x:0.3g}%",
                            disabled=not useVaccinesToggle,
                            on_change=saveKey,
                            args=["primAgeWanedEfficacy", id, f"-{i}"],
                            key=f"_primAgeWanedEfficacy{id}-{i}",
                            help="""
                                The final efficacy value that the
                                vaccine schedule will approach for this
                                age group as the immunity it provides
                                begins to diminish, represented as the
                                probability that an individual in this
                                age group with completely waned
                                immunity will not remain healthy when
                                exposed to the pathogen.
                            """,
                        )
                    # Delete button column
                    with primWanedRemoveColumn:
                        st.button(
                            label="Remove Age Group",
                            icon=":material/delete:",
                            key=f"primWanedRemove{id}-{i}",
                            on_click=deleteFormRow,
                            args=(
                                i,
                                f"primWanedRowCount{id}",
                                {f"primWanedGroup{id}-", f"primAgeWanedEfficacy{id}-"},
                            ),
                            disabled=not useVaccinesToggle,
                            help="""
                            Remove this row of the form and remove
                            these age-specific vaccine waned efficacy
                            values from the simulation.
                        """,
                        )
                # Button to add another row for age-specific params
                primWanedContainer.button(
                    label="Add Age Group",
                    icon=":material/add:",
                    on_click=addFormRow,
                    key=f"primWanedAdd{id}",
                    args=(
                        f"primWanedRowCount{id}",
                        {
                            f"primWanedGroup{id}-{primaryWanedRowCount}": (
                                primWanedRemainingGroups[0]
                                if primWanedRemainingGroups
                                else None
                            ),
                            f"primAgeWanedEfficacy{id}-{primaryWanedRowCount}":
                            primaryWanedEfficacy,
                        },
                    ),
                    disabled=(not useVaccinesToggle or not primaryWanedRowCount < 10),
                    help=(
                        """
                        Add another row to this form, where you can
                        select an additional age group to have unique
                        vaccine waned efficacy values.
                    """
                        if primaryWanedRowCount <= 9
                        else """
                        All age groups have been given unique waned
                        efficacy values, so a new age group cannot be
                        added.
                    """
                    ),
                )'''
            else:
                # Vaccine Efficacy for All Doses
                loadKey("primarySingleEfficacy", id, 0.5)
                doseEfficacy = st.slider(
                    "Vaccine Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    format="percent",
                    disabled=not useVaccinesToggle,
                    on_change=saveKey,
                    args=["primarySingleEfficacy", id],
                    key=f"_primarySingleEfficacy{id}",
                    help="""
The efficacy of each vaccine dose,
represented as the probability that an
individual that has recently received a
dose will remain healthy when exposed to the pathogen.
                    """,
                )

                # Age-Specific Primary Efficacy Field
                st.markdown(
                    "##### Age-Specific Vaccine Efficacy",
                    help="""
This section allows unique vaccine efficacy values to be defined
for individual age groups in the simulation, overriding the global
efficacy value defined above.
                    """,
                )
                if useVaccinesToggle:
                    st.markdown("Double-click a cell in this table to edit its value.")
                loadKey(
                    "vacSingleEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [doseEfficacy],
                        },
                    ),
                    dataframe=True,
                )
                vacEfficacyAgeForm = st.data_editor(
                    session[f"vacSingleEfficacyAgeForm{id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_vacSingleEfficacyAgeForm{id}",
                    on_change=saveKey,
                    args=["vacSingleEfficacyAgeForm", id],
                    kwargs={"dataframe": True},
                    disabled=not useVaccinesToggle,
                    placeholder=(
                        "Enter a value"
                        if useVaccinesToggle
                        else "Enable vaccines to edit this parameter"
                    ),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=ageTimeDict.keys(),
                            format_func=lambda x: ageTimeDict[x],  # type: ignore
                            help="""
An age group that will have a specific vaccine efficacy value defined
for it, overriding the base value.
                            """,
                        ),
                        "Vaccine Efficacy": st.column_config.NumberColumn(
                            "Vaccine Efficacy (Probability)",
                            required=True,
                            default=doseEfficacy,
                            min_value=0.0,
                            max_value=1.0,
                            format="percent",
                            help="""
The efficacy of each vaccine dose for this age group, represented as the
probability that a recently vaccinated individual in this age group will
remain healthy when exposed to the pathogen.
                            """,
                        ),
                    },
                )
                paramError(
                    "vacSingleEfficacyAgeFormDuplicates",
                    id,
                    lambda: hasDuplicates(vacEfficacyAgeForm),
                    f"""
                        Error: The age-specific vaccine efficacy form used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } contains duplicate age group rows. Each age group
                        should only be used in a single row of the form.

                        Please remove or change any rows of the
                        Age-Specific Vaccine Efficacy form in
                        :primary-badge[:material/vaccines: Vaccinations and NPIs]
                        that use the same age group as another row.
                    """,
                    True,
                )

    # Booster Parameters (if advanced parameters are enabled)
    if advanced:
        with st.expander(
            "Booster Vaccines", key=f"boosterContainer{id}", on_change="rerun"
        ) as boosterContainer:
            if boosterContainer.open:
                # Describe booster vaccines
                st.markdown("""
                    These parameters control the properties of booster
                    vaccines, additional doses of a vaccine only
                    administered to individuals who have already
                    received all vaccines in the initial schedule.
                    Unlike the main vaccine doses defined above, all
                    booster vaccine doses share the same efficacy
                    values. Booster vaccines are primarily used with
                    diseases like COVID-19, meningococcal disease and
                    diphtheria to preserve an individual's immunity to
                    the pathogen as it wanes over time.
                """)

                # Universal booster parameters
                loadKey("boosterToggle", id, False)
                useBoostersToggle = st.toggle(
                    "Enable Booster Vaccines",
                    value=False,
                    key=f"_boosterToggle{id}",
                    on_change=saveKey,
                    args=["boosterToggle", id],
                    disabled=not useVaccinesToggle,
                    help="""
Toggle whether or not booster vaccines are
administered in the simulation, overriding other booster-related parameters.
                    """,
                )
                loadKey("boosterDoseCount", id, 3)
                boosterDoseCount = st.slider(
                    "Number of Booster Doses",
                    1,
                    10,
                    3,
                    key=f"_boosterDoseCount{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=saveKey,
                    args=["boosterDoseCount", id],
                    help="""
The number of times each individual in the
simulation will be administered a booster vaccine.
                    """,
                )
                loadKey("boosterDelay", id, 3)
                boosterDelay = st.slider(
                    "Time Between Booster Doses (Months)",
                    1,
                    12,
                    3,
                    disabled=not useVaccinesToggle
                    or not useBoostersToggle
                    or boosterDoseCount == 1,
                    on_change=saveKey,
                    args=["boosterDelay", id],
                    key=f"_boosterDelay{id}",
                    help="""
The number of months after an individual receives
one booster vaccine dose before they are able
to receive another, where a month is 30 days.
                    """,
                )
                loadKey("boosterDuration", id, 4)
                boosterDuration = st.slider(
                    "Booster Immunity Waning Delay (Months)",
                    1,
                    12,
                    4,
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=saveKey,
                    args=["boosterDuration", id],
                    key=f"_boosterDuration{id}",
                    help="""
The number of months after an individual receives a booster vaccine dose
before they begin losing their immunity, where a month is 30 days.
                    """,
                )
                loadKey("boosterWaningRate", id, 6)
                st.slider(
                    "Booster Waning Duration (Months)",
                    0,
                    12,
                    6,
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=saveKey,
                    args=["boosterWaningRate", id],
                    key=f"_boosterWaningRate{id}",
                    help="""
The number of months after a booster-vaccinated individual begins losing their
immunity before their resistance to the pathogen reaches its lowest point, where
a month is 30 days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                        """,
                )
                paramError(
                    "boosterWanesTooFast",
                    id,
                    lambda: useVaccinesToggle
                    and useBoostersToggle
                    and boosterDelay > boosterDuration,
                    f"""
                        Error: The time between booster vaccine doses used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } is longer than the time before a booster vaccine's efficacy
                        begins to wane. As such, the booster vaccines will begin waning
                        before all doses have been received.

                        Please make one of the following changes:

                        - Increase Booster Immunity Waning Delay in
                        :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to be greater than {boosterDelay}.
                        - Decrease Time Between Booster Doses in
                        :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to be lower than {boosterDuration}.
                    """,
                    True,
                )
                loadKey("boosterBaseEfficacy", id, 0.9)
                boosterBaseEfficacy = st.slider(
                    "Initial Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    format="percent",
                    key=f"_boosterBaseEfficacy{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=saveKey,
                    args=["boosterBaseEfficacy", id],
                    help="""
The initial efficacy of each booster vaccine,
represented as the probability that an
individual that has recently received the
booster will remain healthy when exposed to the pathogen.
                    """,
                )
                loadKey("boosterWanedEfficacy", id, 0.6)
                boosterWanedEfficacy = st.slider(
                    "Booster Efficacy After Immunity Waning (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.6,
                    format="percent",
                    key=f"_boosterWanedEfficacy{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=saveKey,
                    args=["boosterWanedEfficacy", id],
                    help="""
The efficacy of a booster-vaccinated individual's immunity after the
full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                )

                # Show error if waned efficacy is above initial
                paramError(
                    "boosterWanedEfficiencyAboveInitial",
                    id,
                    lambda: useVaccinesToggle
                    and useBoostersToggle
                    and boosterWanedEfficacy > boosterBaseEfficacy,
                    f"""
                        Error: The initial vaccine efficacy for
                        booster vaccines in the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{
                                session[f'scenarioName{id}']
                            }"'
                        } is {100 * boosterBaseEfficacy:0.3g}%, but the
                        efficacy after waning is {100 * boosterWanedEfficacy:0.3g}%.
                        As such, a vaccinated person's immunity to the
                        pathogen will get stronger over time instead of weaker.

                        Please make one of the following changes:

                        - Increase Initial Booster Efficacy in
                        :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to be greater than {100 * boosterWanedEfficacy:0.3g}%.
                        - Decrease Booster Efficacy After Immunity Waning in
                        :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to be lower than {100 * boosterBaseEfficacy:0.3g}%.
                    """,
                    True,
                )

                # Store age-based booster efficacy values for error checking
                # boostAgeInitials, boostAgeWaneds = {}, {}

                # Modifiable-length field for age-specific efficacy
                st.markdown(
                    "### Age-Specific Booster Efficacies",
                    help="""
This table allows for unique booster efficacy values (both initial and final)
to be defined for individual age groups in the simulation, overriding the
global booster efficacy values defined above.
                    """,
                )
                if useVaccinesToggle and useBoostersToggle:
                    st.markdown("Double-click a cell in this table to edit its value.")
                loadKey(
                    "boostEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Initial Booster Efficacy": [boosterBaseEfficacy],
                            "Booster Efficacy After Waning": [boosterWanedEfficacy],
                        },
                    ),
                    dataframe=True,
                )
                boostEfficacyAgeForm = st.data_editor(
                    session[f"boostEfficacyAgeForm{id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_boostEfficacyAgeForm{id}",
                    on_change=saveKey,
                    args=["boostEfficacyAgeForm", id],
                    kwargs={"dataframe": True},
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    placeholder=(
                        "Enter a value"
                        if useVaccinesToggle and useBoostersToggle
                        else "Enable booster vaccines to edit this parameter"
                    ),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=ageTimeDict.keys(),
                            format_func=lambda x: ageTimeDict[x],  # type: ignore
                            help="""
An age group that will have specific booster vaccine efficacy values defined
for it, overriding the base efficacy value for booster vaccines.
                            """,
                        ),
                        "Initial Booster Efficacy": st.column_config.NumberColumn(
                            "Initial Booster Efficacy (Probability)",
                            required=True,
                            default=boosterBaseEfficacy,
                            min_value=0.0,
                            max_value=1.0,
                            format="percent",
                            help="""
The initial efficacy of each booster vaccine for this age group, represented
as the probability that a recently vaccinated individual in this age group
will remain healthy when exposed to the pathogen.
                            """,
                        ),
                        "Booster Efficacy After Waning": st.column_config.NumberColumn(
                            "Booster Efficacy After Immunity Waning (Probability)",
                            required=True,
                            default=boosterWanedEfficacy,
                            min_value=0.0,
                            max_value=1.0,
                            format="percent",
                            help="""
The efficacy of a booster-vaccinated individual in this age group's immunity
after the full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                        ),
                    },
                )
                paramError(
                    "boostEfficacyAgeFormDuplicates",
                    id,
                    lambda: hasDuplicates(boostEfficacyAgeForm),
                    f"""
                        Error: The booster vaccine age-specific
                        efficacy form used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } contains duplicate age group rows. Each age group
                        should only be used in a single row of the form.

                        Please remove or change any rows of the
                        Age-Specific Booster Efficacies form in
                        :primary-badge[:material/vaccines: Vaccinations and NPIs]
                        that use the same age group as another row.
                    """,
                    True,
                )
                # TODO: make data_editor error messages name the row
                paramError(
                    "boostEfficacyAgeFormWanedAboveInitial",
                    id,
                    lambda: np.any(
                        boostEfficacyAgeForm["Initial Booster Efficacy"]
                        < boostEfficacyAgeForm["Booster Efficacy After Waning"]
                    ),
                    f"""
                        Error: The booster vaccine age-specific
                        efficacy form used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } contains rows where the initial vaccine efficacy is
                        greater than the efficacy after immunity waning. As such, the
                        immunity to the pathogen conferred by the booster will get
                        stronger over time instead of weaker for the age groups
                        specified by these rows.

                        Please make one of the following changes:

                        - Remove all rows of the Age-Specific Booster Efficacies form
                        in :primary-badge[:material/vaccines: Vaccination and NPIs]
                        that have the initial efficacy higher than the efficacy
                        after waning.
                        - Increase the Initial Booster Efficacy column in
                        :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to always be higher than the efficacy after waning.
                        - Decrease the Booster Efficacy After Immunity Waning column
                        in :primary-badge[:material/vaccines: Vaccination and NPIs]
                        to always be lower than the initial efficacy.
                    """,
                    True,
                )

                '''# Save relevant params as variables to avoid lookups
                boosterRowCount = session[f"boostAgeRowCount{id}"]
                boostAgeRemainingGroups = session[f"boosterRemainingAgeGroups{id}"]
                boostAgeErrorContainer = st.container()
                boostAgeEfficacyContainer = st.container()
                for i in range(boosterRowCount):
                    (boostAgeGroupColumn, boostAgeEfficacyColumn, boostAgeRemoveColumn) = (
                        boostAgeEfficacyContainer.columns(
                            (0.25, 0.55, 0.2), vertical_alignment="center"
                        )
                    )
                    boostAgeCurrentGroup = session.get(f"boostAgeGroup{id}-{i}")
                    # Age group column
                    loadKey(
                        "boostAgeGroup",
                        id,
                        (
                            boostAgeCurrentGroup
                            if boostAgeCurrentGroup
                            else boostAgeRemainingGroups[0]
                        ),
                        f"-{i}",
                    )
                    with boostAgeGroupColumn:
                        boostAgeGroup = st.selectbox(
                            # Set age group options such that only ages
                            # that haven't been selected yet can be selected
                            "Age Group",
                            key=f"_boostAgeGroup{id}-{i}",
                            options=(
                                [boostAgeCurrentGroup]
                                + [
                                    group
                                    for group in boostAgeRemainingGroups
                                    if group != boostAgeCurrentGroup
                                ]
                                if boostAgeCurrentGroup
                                else boostAgeRemainingGroups
                            ),
                            disabled=(
                                not useVaccinesToggle
                                or not useBoostersToggle
                                or not boosterRowCount < 10
                            ),
                            on_change=saveKey,
                            args=["boostAgeGroup", id, f"-{i}"],
                            help="""
                            An age group that will have specific
                            booster vaccine efficacy values defined for
                            it, overriding the base efficacy value for
                            booster vaccines.

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
                    # Standard efficacy column
                    loadKey("boostAgeEfficacy", id, 0.9, f"-{i}")
                    with boostAgeEfficacyColumn:
                        boostAgeInitials[boostAgeGroup] = st.select_slider(
                            "Initial Booster Efficacy (Probability)",
                            np.linspace(0.0, 1.0, 201),
                            0.9,
                            disabled=(not useVaccinesToggle or not useBoostersToggle),
                            format_func=lambda x: f"{100 * x:0.3g}%",
                            on_change=saveKey,
                            args=["boostAgeEfficacy", id, f"-{i}"],
                            key=f"_boostAgeEfficacy{id}-{i}",
                            help="""
                                The initial efficacy of each booster
                                vaccine for this age group, represented
                                as the probability that a recently
                                vaccinated individual in this age group
                                will remain healthy when exposed to the
                                pathogen.
                            """,
                        )
                    # Waned efficacy column
                    loadKey("boostAgeWanedEfficacy", id, 0.6, f"-{i}")
                    with boostAgeEfficacyColumn:
                        boostAgeWaneds[boostAgeGroup] = st.select_slider(
                            (("Booster Efficacy After Immunity Waning (Probability)")),
                            np.linspace(0.0, 1.0, 201),
                            0.6,
                            disabled=(not useVaccinesToggle or not useBoostersToggle),
                            format_func=lambda x: f"{100 * x:0.3g}%",
                            on_change=saveKey,
                            args=["boostAgeWanedEfficacy", id, f"-{i}"],
                            key=f"_boostAgeWanedEfficacy{id}-{i}",
                            help="""
                                The final efficacy value that the
                                booster vaccine will approach for this
                                age group as the immunity it provides
                                begins to diminish, represented as the
                                probability that an individual in this
                                age group with completely waned
                                immunity will remain healthy when
                                exposed to the pathogen.
                            """,
                        )
                    # Delete button column
                    with boostAgeRemoveColumn:
                        st.button(
                            label="Remove Age Group",
                            icon=":material/delete:",
                            key=f"boostAgeRemove{id}-{i}",
                            on_click=deleteFormRow,
                            args=(
                                i,
                                f"boostAgeRowCount{id}",
                                {
                                    f"boostAgeGroup{id}-",
                                    f"boostAgeEfficacy{id}-",
                                    f"boostAgeWanedEfficacy{id}-",
                                },
                            ),
                            disabled=(not useVaccinesToggle or not useBoostersToggle),
                            help="""
                            Remove this row of the form and remove
                            these age-specific booster vaccine efficacy
                            values from the simulation.
                        """,
                        )
                # Button to add another row for age-specific params
                boostAgeEfficacyContainer.button(
                    label="Add Age Group",
                    icon=":material/add:",
                    on_click=addFormRow,
                    key=f"boostAgeAdd{id}",
                    args=(
                        f"boostAgeRowCount{id}",
                        {
                            f"boostAgeGroup{id}-{boosterRowCount}": (
                                boostAgeRemainingGroups[0]
                                if boostAgeRemainingGroups
                                else None
                            ),
                            f"boostAgeEfficacy{id}-{boosterRowCount}": boosterBaseEfficacy,
                            f"boostAgeWanedEfficacy{id}-{boosterRowCount}":
                            boosterWanedEfficacy,
                        },
                    ),
                    disabled=(
                        not useVaccinesToggle
                        or not useBoostersToggle
                        or not boosterRowCount < 10
                    ),
                    help=(
                        """
                        Add another row to this form, where you can
                        select an additional age group to have unique
                        booster vaccine efficacy values.
                    """
                        if boosterRowCount <= 9
                        else """
                        All age groups have been given unique booster
                        vaccine efficacy values.
                    """
                    ),
                )

                # Age-based errors if waned efficacy is above initial
                for age in boostAgeInitials.keys():
                    currentInitial = boostAgeInitials[age]
                    currentWaned = boostAgeWaneds[age]
                    if (
                        useVaccinesToggle
                        and useBoostersToggle
                        and currentInitial < currentWaned
                    ):
                        boostAgeErrorContainer.error(
                            f"""
                            Error: The initial booster vaccine efficacy
                            in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[
                                        f'scenarioName{id}'
                                        ]
                                }"'
                            } for the "{age}" age group is currently
                            set to {100 * currentInitial:0.3g}%
                            effectiveness, but the final booster
                            vaccine efficacy after immunity waning for
                            said age group in this scenario is set to
                            {100 * currentWaned:0.3g}%. As such, the
                            immunity to the pathogen conferred by the
                            booster will get stronger over time instead
                            of weaker for individuals in the "{age}"
                            age group.

                            To address this error, please make one of
                            the following changes before running the
                            simulation:

                            - Remove the scenario's age-specific
                            booster efficacies for the "{age}" age
                            group.
                            - Increase the scenario's Initial Booster
                            Efficacy for the "{age}" age group to be
                            greater than {100 * currentWaned:0.3g}%.
                            - Decrease the scenario's Booster Efficacy
                            After Immunity Waning for the "{age}" age
                            group to be lower
                            than {100 * currentInitial:0.3g}%.
                        """,
                            icon=":material/error:",
                        )
                        globalErrorContainer.error(
                            f"""
                            Error: The initial booster vaccine efficacy
                            in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[
                                        f'scenarioName{id}'
                                    ]
                                }"'
                            } for the "{age}" age group is currently
                            set to {100 * currentInitial:0.3g}%
                            effectiveness, but the final booster
                            vaccine efficacy after immunity waning for
                            said age group in this scenario is set to
                            {100 * currentWaned:0.3g}%. As such, the
                            immunity to the pathogen conferred by the
                            booster will get stronger over time instead
                            of weaker for individuals in the "{age}"
                            age group.

                            To address this error, please make one of
                            the following changes before running the
                            simulation:

                            - Remove the scenario's age-specific
                            booster efficacies for the "{age}" age
                            group in the "Booster Vaccines" section of
                            the "Vaccinations and NPIs" tab.
                            - Increase the scenario's Initial Booster
                            Efficacy for the "{age}" age group in the
                            "Booster Vaccines" section of the
                            "Vaccinations and NPIs" tab to be greater
                            than {100 * currentWaned:0.3g}%.
                            - Decrease the scenario's Booster Efficacy
                            After Immunity Waning for the "{age}" age
                            group in the "Booster Vaccines" section of
                            the "Vaccinations and NPIs" tab to be lower
                            than {100 * currentInitial:0.3g}%.
                        """,
                            icon=":material/error:",
                        )
                        session[f"ageBoostEfficacyError{id}"] = 2
                        ageBoostEfficacyError = True
                # Reset error parameter if none of the age levels error
                if not ageBoostEfficacyError:
                    session[f"ageBoostEfficacyError{id}"] = 0'''

    # NPIs
    st.subheader("Non-Pharmaceutical Intervention (NPI) Parameters")

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
                        :primary-badge[:material/vaccines: Vaccinations and NPIs]
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
            # TODO: Account for NPI toggles being off
            # TODO: Rewrite to not need seven type: ignores
            interventionTriggers = [
                schoolClosureTrigger,  # type: ignore
                withdrawalIncreaseTrigger,  # type: ignore
                reducedGroupTrigger,  # type: ignore
                bccTrigger,  # type: ignore
            ]
            usesRates = [
                index
                for index, condition in enumerate(interventionTriggers)
                if condition == "Community Case Rate"
            ]
            usesTotals = [
                index
                for index, condition in enumerate(interventionTriggers)
                if condition
                in {"Community Case Total", "Cases per School", "Cases per K-12 School"}
            ]
            if not (usesRates or usesTotals or classDismissal):  # type: ignore
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
                if usesRates or classDismissal:  # type: ignore
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
                            if classDismissal  # type: ignore
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


def ageCast(x: str) -> Literal[
    "young_infant",
    "infant",
    "young_child",
    "child",
    "adolescent",
    "young_adult",
    "adult",
    "older_adult",
    "senior",
    "older_senior",
]:
    """
    Simple function to cast age strings into literals for validation.

    Parameters:
        x (str): The string to be cast.

    Returns:
        Literal: A literal with the same value as the string.
    """
    return cast(
        Literal[
            "young_infant",
            "infant",
            "young_child",
            "child",
            "adolescent",
            "young_adult",
            "adult",
            "older_adult",
            "senior",
            "older_senior",
        ],
        x,
    )


def trigCast(x: str) -> Literal[
    "none",
    "timed",
    "per_school_cases",
    "community_cases",
    "community_rate",
    "per_primary_high_school_cases",
]:
    """
    Simple function to cast trigger strings into literals for validation.

    Parameters:
        x (str): The string to be cast.

    Returns:
        Literal: A literal with the same value as the string.
    """
    return cast(
        Literal[
            "none",
            "timed",
            "per_school_cases",
            "community_cases",
            "community_rate",
            "per_primary_high_school_cases",
        ],
        triggerConditions[x],
    )


def vaccineSaveSchema(schema: Parameters, id: int = 0, advanced: bool = False) -> bool:
    """
    Function to populate the Pydantic model schema with vaccination/NPI parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to show more complex parameters like
            individual vaccine dose efficacies.

    Returns:
        bool: `True` if vaccines were used in the scenario, permitting
            direct vs. indirect protection calculations.
    """
    # TODO: Make code clearer (split up advanced section if needed)

    # Load reused parameters immediately to save time
    vaccineToggle = idGet("vaccineToggle", id, False)
    waningToggle = idGet("vaccineWaningToggle", id, False)
    boosterToggle = idGet("boosterToggle", id, False)
    socialDistanceToggle = idGet("socialDistancingToggle", id, False)
    ageNames = list(ageTimeDict.keys())
    simLength = session.get("cycleCount", 360) * 2
    primDoseCount = idGet("primaryDoseCount", id, 1)
    initialProportion = idGet("initialVaccinated", id, 0.0)
    targetProportion = idGet("targetVaccinated", id, 0.8)
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

            # Vaccine Parameters
            if vaccineToggle:
                primBaseEfficacy = [
                    idGet("primaryBaseEfficacy", id, 0.5, f"-{i}")
                    for i in range(primDoseCount)
                ]
                primWanedEfficacy = (
                    idGet("primaryWanedEfficacy", id, 0.0) if waningToggle else 0.0
                )
                boostBaseEfficacy = idGet("boosterBaseEfficacy", id, 0.9)
                boostWanedEfficacy = idGet("boosterWanedEfficacy", id, 0.6)

                # Scenario Vaccine Dose Efficacy

                # Base Primary Efficacy Values
                efficacyParams = [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=primWanedEfficacy,
                        Efficacy=primBaseEfficacy,
                    )
                ]
                # Age-Specific Primary Efficacy Values
                vacInitialEfficacyAgeForms = [
                    idGet(
                        "vacInitialEfficacyAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [primBaseEfficacy[i]],
                            },
                        ),
                        f"-{i}",
                    )
                    for i in range(primDoseCount)
                ]
                ageInitialDict = {
                    age: [
                        next(
                            iter(
                                df.loc[df["Age Group"] == age, "Initial Dose Efficacy"]
                            ),
                            default,
                        )
                        for df, default in zip(
                            vacInitialEfficacyAgeForms, primBaseEfficacy
                        )
                    ]
                    for age in ageNames
                }
                ageWaneDict = {age: primWanedEfficacy for age in ageNames}
                vacWaneAgeForm = idGet(
                    "vacWaneAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Dose Efficacy After Waning": [primWanedEfficacy],
                        },
                    ),
                ).dropna()
                ageWaneDict.update(
                    vacWaneAgeForm.set_index("Age Group")[
                        "Dose Efficacy After Waning"
                    ].to_dict()
                )

                efficacyParams += [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=ageCast(age),
                        Efficacy=ageInitialDict[age],
                        WanedEfficacy=ageWaneDict[age],
                    )
                    for age in ageNames
                    if ageInitialDict[age] != primBaseEfficacy
                    or ageWaneDict[age] != primWanedEfficacy
                ]

                """
                primAgeEfficacies = dict.fromkeys(ageNames, primBaseEfficacy)
                for i in range(primDoseCount):
                    for j in range(session.get(f"primAgeRowCount{id}-{i}", 0)):
                        primAgeEfficacies[session[f"primAgeGroup{id}-{i}-{j}"]][
                            i
                        ] = idGet(
                            "primAgeEfficacy",
                            id,
                            primBaseEfficacy[i], f"-{i}-{j}"
                        )
                agePrimEfficacyParams = [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=ageCast(age),
                        Efficacy=primAgeEfficacies[age],
                        WanedEfficacy=primWanedEfficacy,
                    )
                    for age in ageNames
                ]
                for i in range(session.get(f"primWanedRowCount{id}", 0)):
                    agePrimEfficacyParams[
                        ageNames.index(session[f"primWanedGroup{id}-{i}"])
                    ].WanedEfficacy = idGet(
                        "primAgeWanedEfficacy", id, primWanedEfficacy, f"-{i}"
                    )
                efficacyParams += agePrimEfficacyParams"""

                # Booster Efficacy Values
                if boosterToggle:
                    boostEfficacyAgeForm = idGet(
                        "boostEfficacyAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Booster Efficacy": [boostBaseEfficacy],
                                "Booster Efficacy After Waning": [boostWanedEfficacy],
                            },
                        ),
                    )
                    efficacyParams += [
                        vaccineEfficacy(
                            DoseType="booster",
                            Age=None,
                            Efficacy=boostBaseEfficacy,
                            WanedEfficacy=boostWanedEfficacy,
                        )
                    ] + [
                        vaccineEfficacy(
                            DoseType="booster",
                            Age=age,
                            Efficacy=initial,
                            WanedEfficacy=waned,
                        )
                        for age, initial, waned in zip(
                            boostEfficacyAgeForm["Age Group"],
                            boostEfficacyAgeForm["Initial Booster Efficacy"],
                            boostEfficacyAgeForm["Booster Efficacy After Waning"],
                        )
                        if age
                    ]
                    """[
                        vaccineEfficacy(
                            DoseType="booster",
                            Age=ageCast(session[f"boostAgeGroup{id}-{i}"]),
                            Efficacy=idGet(
                                "boostAgeEfficacy", id, boostBaseEfficacy, f"-{i}"
                            ),
                            WanedEfficacy=idGet(
                                "boostAgeWanedEfficacy", id, boostWanedEfficacy, f"-{i}"
                            ),
                        )
                        for i in range(session.get(f"boostAgeRowCount{id}", 0))
                    ]"""
                # All together
                schema.Scenario_VaccineDoseEfficacy = efficacyParams

                # Scenario Vaccine Dose
                primWaningDuration = idGet("primaryWaningRate", id, 12) * 60
                doseParams = [
                    vaccineDose(
                        DoseType="primary",
                        Count=primDoseCount,
                        DoseSpacingCycles=idGet("primaryDelay", id, 3) * 60,
                        WaningDelay=(
                            idGet("primaryDuration", id, 6) * 60
                            if waningToggle
                            else simLength
                        ),
                        WaningRatePerCycle=(
                            0.0
                            if not waningToggle
                            else (
                                1.0
                                if primWaningDuration == 0
                                else (primBaseEfficacy[-1] - primWanedEfficacy)
                                / primWaningDuration
                            )
                        ),
                    )
                ]
                if boosterToggle:
                    boostWaningDuration = idGet("boosterWaningRate", id, 6) * 60
                    doseParams += [
                        vaccineDose(
                            DoseType="booster",
                            Count=idGet("boosterDoseCount", id, 3),
                            DoseSpacingCycles=idGet("boosterDelay", id, 3) * 60,
                            WaningDelay=idGet("boosterDuration", id, 4) * 60,
                            WaningRatePerCycle=(
                                1.0
                                if boostWaningDuration == 0
                                else (boostBaseEfficacy - boostWanedEfficacy)
                                / boostWaningDuration
                            ),
                        )
                    ]
                schema.Scenario_VaccineDose = doseParams

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
        else:
            if vaccineToggle:
                doseEfficacy = idGet("primarySingleEfficacy", id, 0.5)
                doseEfficacyAgeForm = idGet(
                    "vacSingleEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [doseEfficacy],
                        },
                    ),
                )
                schema.Scenario_VaccineDoseEfficacy = [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=0.0,
                        Efficacy=[doseEfficacy] * primDoseCount,
                    )
                ] + [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=ageCast(age),
                        WanedEfficacy=0.0,
                        Efficacy=[efficacy] * primDoseCount,
                    )
                    for age, efficacy in zip(
                        doseEfficacyAgeForm["Age Group"],
                        doseEfficacyAgeForm["Vaccine Efficacy"],
                    )
                    if age
                ]
                schema.Scenario_VaccineDose = [
                    vaccineDose(
                        DoseType="primary",
                        Count=primDoseCount,
                        DoseSpacingCycles=idGet("primaryDelay", id, 3) * 60,
                        WaningDelay=simLength,
                        WaningRatePerCycle=0.0,
                    )
                ]

        # Vaccine-Related Parameters
        if vaccineToggle:
            # Scenario Vaccine Coverage
            vacPropAgeForm = idGet(
                "vacPropAgeForm",
                id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Vaccinated Proportion": [initialProportion],
                        "Target Vaccinated Proportion": [targetProportion],
                    },
                ),
            )
            schema.Scenario_VaccineCoverage = [
                vaccineCoverage(
                    Age=None, Initial=initialProportion, Target=targetProportion
                )
            ] + [
                vaccineCoverage(Age=age, Initial=initial, Target=target)
                for age, initial, target in zip(
                    vacPropAgeForm["Age Group"],
                    vacPropAgeForm["Initial Vaccinated Proportion"],
                    vacPropAgeForm["Target Vaccinated Proportion"],
                )
                if age
            ]

            """[
                vaccineCoverage(
                    Age=ageCast(session[f"vacAgeGroup{id}-{i}"]),
                    Initial=idGet("vacAgeInitial", id, initialProportion, f"-{i}"),
                    Target=idGet("vacAgeTarget", id, targetProportion, f"-{i}"),
                )
                for i in range(session.get(f"vacAgeRowCount{id}", 0))
            ]"""

            # TODO: See if these can be reintegrated onto the dashboard
            scenarioParams.vaccination_delay = 0
            scenarioParams.vaccination_duration = 2500
            scenarioParams.vaccination_trigger = trigCast("Timed")
            scenarioParams.vaccination_relaxation = trigCast("Always")

            # Ensure doses do not exceed the integer limit
            scenarioParams.vaccine_doses = min(
                (
                    idGet("initialDoseReserve", id, 0)
                    if advanced and idGet("limitDosesToggle", id, False)
                    else 99999999
                ),
                2000000000,
            )
            scenarioParams.vaccination_first_dose_rate = min(
                idGet("firstDoseRate", id, 300), 2000000000
            )

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
        vaccineLog.error(
            (
                f"[vaccinationNPIParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e
    return vaccineToggle


def vaccineLoadSchema(schema: Parameters, scenarioID: int = 0):
    """
    Function to read vaccination/NPI parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.
    """
    # Keep track of whether any toggle-controlled parameters have shown up
    useVaccines, useBoosters, useSocialDistancing = False, False, False
    useNPIs = {
        "schoolClosure": False,
        "withdrawalIncrease": False,
        "reducedGroup": False,
        "bcc": False,
    }

    # Ordering dictionary to ensure global values are checked first
    ageOrder = {
        None: 0,
        "young_infant": 1,
        "infant": 2,
        "young_child": 3,
        "child": 4,
        "adolescent": 5,
        "young_adult": 6,
        "adult": 7,
        "older_adult": 8,
        "senior": 9,
        "older_senior": 10,
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

    # Vaccine Coverage Parameters
    schemaCoverage = schema.Scenario_VaccineCoverage
    if schemaCoverage is not None:
        useVaccines = True
        coverageTable = pd.DataFrame(
            columns=(
                "Age Group",
                "Initial Vaccinated Proportion",
                "Target Vaccinated Proportion",
            )
        )
        # Get the global values (age=None) first
        schemaCoverage.sort(key=lambda x: ageOrder.get(x.Age, 99))
        if len(schemaCoverage) > 0 and schemaCoverage[0].Age is None:
            baseCoverage = schemaCoverage.pop(0)
            baseInitial = 0.0 if baseCoverage.Initial is None else baseCoverage.Initial
            updateParamFromSchema("initialVaccinated", baseInitial, scenarioID)
            baseTarget = baseCoverage.Target
            updateParamFromSchema("targetVaccinated", baseTarget, scenarioID)
        elif scenarioID == 0:
            raise AssertionError("""
                Schema does not include general vaccine coverage
                proportions for the baseline scenario
                """)
        else:
            baseInitial = idGet("initialVaccinated", 0, 0.0)
            baseTarget = idGet("targetVaccinated", 0, 0.8)

        # Iterate over each coverage age
        for coverage in schemaCoverage:
            age, initial, target = coverage.Age, coverage.Initial, coverage.Target
            if age is not None:
                coverageTable.loc[coverageTable.shape[0]] = [
                    age,
                    baseInitial if initial is None else initial,
                    target,
                ]
        updateTableFromSchema(
            "vacPropAgeForm",
            coverageTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Initial Vaccinated Proportion": [baseInitial],
                    "Target Vaccinated Proportion": [baseTarget],
                },
            ),
        )

    # Placeholders for attributes that may not be defined
    # TODO: See which of these can become None to avoid
    # propagating values not in the schema itself
    primaryDoseCount = 1 if scenarioID == 0 else idGet("primaryDoseCount", 0, 1)
    boosterDoseCount = 3 if scenarioID == 0 else idGet("boosterDoseCount", 0, 3)
    primaryRatePerCycle = 12 if scenarioID == 0 else idGet("primaryWaningRate", 0, 12)
    boosterRatePerCycle = 6 if scenarioID == 0 else idGet("boosterWaningRate", 0, 6)
    baseFull = (
        [0.5]
        if scenarioID == 0
        else [idGet("primaryBaseEfficacy", 0, 0.5, f"-{primaryDoseCount - 1}")]
    )
    baseWaned = 0.0 if scenarioID == 0 else idGet("primaryWanedEfficacy", 0, 0.0)
    baseBoostFull = 0.9 if scenarioID == 0 else idGet("boosterBaseEfficacy", 0, 0.9)
    baseBoostWaned = 0.6 if scenarioID == 0 else idGet("boosterWanedEfficacy", 0, 0.6)

    # Vaccine Dosage Parameters
    schemaDose = schema.Scenario_VaccineDose
    if schemaDose is not None:
        useVaccines = True

        # Primary vaccines
        if any(dose.DoseType == "primary" for dose in schemaDose):
            primaryDose = [dose for dose in schemaDose if dose.DoseType == "primary"][0]
            primaryDoseCount = primaryDose.Count
            updateParamFromSchema("primaryDoseCount", primaryDoseCount, scenarioID)
            updateParamFromSchema(
                "primaryDelay", primaryDose.DoseSpacingCycles // 60, scenarioID
            )
            waningDelay = primaryDose.WaningDelay
            updateParamFromSchema("primaryDuration", waningDelay // 60, scenarioID)
            # Efficacy needs to be logged so that waning rate per cycle
            # can be calculated
            primaryRatePerCycle = primaryDose.WaningRatePerCycle
            updateParamFromSchema(
                "vaccineWaningToggle", bool(primaryRatePerCycle), scenarioID
            )

        # Booster Vaccines
        if any(dose.DoseType == "booster" for dose in schemaDose):
            boosterDose = [dose for dose in schemaDose if dose.DoseType == "booster"][0]
            useBoosters = True
            boosterDoseCount = boosterDose.Count
            updateParamFromSchema("boosterDoseCount", boosterDoseCount, scenarioID)
            updateParamFromSchema(
                "boosterDelay", boosterDose.DoseSpacingCycles // 60, scenarioID
            )
            updateParamFromSchema(
                "boosterDuration", boosterDose.WaningDelay // 60, scenarioID
            )
            # Efficacy needs to be logged so that waning rate per cycle
            # can be calculated
            boosterRatePerCycle = boosterDose.WaningRatePerCycle

    # Vaccine Efficacy Parameters
    schemaEfficacy = schema.Scenario_VaccineDoseEfficacy
    if schemaEfficacy is not None:
        useVaccines = True

        # Primary Vaccines
        primaryEfficacySchema = [
            dose for dose in schemaEfficacy if dose.DoseType == "primary"
        ]
        primaryEfficacyTables = [
            pd.DataFrame(columns=("Age Group", "Initial Dose Efficacy"))
            for i in range(primaryDoseCount)
        ]
        primarySingleTable = pd.DataFrame(columns=("Age Group", "Vaccine Efficacy"))
        primaryWanedTable = pd.DataFrame(
            columns=("Age Group", "Dose Efficacy After Waning")
        )

        # Get the global values (age=None) first
        primaryEfficacySchema.sort(key=lambda x: ageOrder.get(x.Age, 99))
        if len(primaryEfficacySchema) > 0 and primaryEfficacySchema[0].Age is None:
            baseEfficacy = primaryEfficacySchema.pop(0)
            baseFull: list = baseEfficacy.Efficacy  # type: ignore
            updateParamFromSchema("primarySingleEfficacy", baseFull[0], scenarioID)
            for index, value in enumerate(baseFull):
                updateParamFromSchema(
                    "primaryBaseEfficacy", value, scenarioID, f"-{index}"
                )
            baseWaned = baseEfficacy.WanedEfficacy
            updateParamFromSchema("primaryWanedEfficacy", baseWaned, scenarioID)
        elif scenarioID == 0:
            raise AssertionError(
                "Schema does not include general primary vaccine efficacy "
                "proportions for the baseline scenario"
            )
        else:
            baseFull = [
                idGet("primaryBaseEfficacy", 0, 0.5, f"-{i}")
                for i in range(primaryDoseCount)
            ]
            baseWaned = idGet("primaryWanedEfficacy", 0, 0.0)

        # Iterate over each efficacy age
        for prim in primaryEfficacySchema:
            age, base, waned = prim.Age, prim.Efficacy, prim.WanedEfficacy
            # Assume correct number of efficacies are used
            # since the schema should error before now otherwise
            if age is not None:
                if waned != baseWaned:
                    primaryWanedTable.loc[primaryWanedTable.shape[0]] = [age, waned]
                for index, value in enumerate(base):  # type: ignore
                    if value != baseFull[index]:
                        currentTable = primaryEfficacyTables[index]
                        currentTable.loc[currentTable.shape[0]] = [age, value]
                        # Use the first dose for the simplified one-efficacy table
                        if index == 0:
                            primarySingleTable.loc[primarySingleTable.shape[0]] = [
                                age,
                                value,
                            ]

        # Save the tables
        updateTableFromSchema(
            "vacWaneAgeForm",
            primaryWanedTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Dose Efficacy After Waning": [baseWaned],
                },
            ),
        )
        updateTableFromSchema(
            "vacSingleEfficacyAgeForm",
            primarySingleTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Vaccine Efficacy": [baseFull[0]],
                },
            ),
        )
        for index, table in enumerate(primaryEfficacyTables):
            updateTableFromSchema(
                "vacInitialEfficacyAgeForm",
                table,
                scenarioID,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Vaccine Efficacy": [baseFull[index]],
                    },
                ),
                extra=f"-{index}",
            )

        # Booster Vaccines
        boosterEfficacySchema = [
            dose for dose in schemaEfficacy if dose.DoseType == "booster"
        ]
        boosterEfficacyTable = pd.DataFrame(
            columns=(
                "Age Group",
                "Initial Booster Efficacy",
                "Booster Efficacy After Waning",
            )
        )

        # Get the global values (age=None) first
        boosterEfficacySchema.sort(key=lambda x: ageOrder.get(x.Age, 99))
        if len(boosterEfficacySchema) > 0 and boosterEfficacySchema[0].Age is None:
            baseBoostEfficacy = boosterEfficacySchema.pop(0)
            baseBoostFull: EfficacyValue = baseBoostEfficacy.Efficacy  # type: ignore
            updateParamFromSchema("boosterBaseEfficacy", baseBoostFull, scenarioID)
            baseBoostWaned = baseBoostEfficacy.WanedEfficacy
            updateParamFromSchema("boosterWanedEfficacy", baseBoostWaned, scenarioID)
        elif useBoosters and scenarioID == 0:
            raise AssertionError(
                "Schema does not include general booster vaccine efficacy "
                "proportions for the baseline scenario"
            )
        else:
            baseBoostFull = idGet("boosterBaseEfficacy", 0, 0.9)
            baseBoostWaned = idGet("boosterWanedEfficacy", 0, 0.6)

        # Iterate over each efficacy age
        for boost in boosterEfficacySchema:
            age, base, waned = boost.Age, boost.Efficacy, boost.WanedEfficacy
            if age is not None:
                boosterEfficacyTable.loc[boosterEfficacyTable.shape[0]] = [
                    age,
                    base,
                    waned,
                ]

        updateTableFromSchema(
            "boostEfficacyAgeForm",
            boosterEfficacyTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Initial Booster Efficacy": [baseBoostFull],
                    "Booster Efficacy After Waning": [baseBoostWaned],
                },
            ),
        )

    # Come back to waning duration since it needs both efficacy and dose
    if primaryRatePerCycle:
        updateParamFromSchema(
            "primaryWaningRate",
            (
                0
                if primaryRatePerCycle == 1.0
                else (baseFull[-1] - baseWaned) // (primaryRatePerCycle * 60)
            ),
            scenarioID,
        )
    if boosterRatePerCycle:
        updateParamFromSchema(
            "boosterWaningRate",
            (
                0
                if boosterRatePerCycle == 1.0
                else (baseBoostFull - baseBoostWaned) // (boosterRatePerCycle * 60)
            ),
            scenarioID,
        )

    # General Scenario Parameters
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is not None:
        paramDict = {p: v for p, v in vars(schemaParameters).items() if v is not None}
        paramConvert = {
            "class_dismissal": "classDismissal",
            "case_trigger_threshold": "caseTotalThreshold",
            "rate_trigger_threshold": "rateStartThreshold",
            "rate_relaxation_threshold": "rateRelaxThreshold",
            "vaccination_first_dose_rate": "firstDoseRate",
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
                if npiDelay == 0 and npiDuration > session.get("cycleCount", 360) * 2:
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
                npiPeriodEnd = (npiDelay + npiDuration) // 2
                updateParamFromSchema(
                    f"{prefix}Period", (npiPeriodStart, npiPeriodEnd), scenarioID
                )

        # Miscellaneous toggles
        if {
            "vaccination_first_dose_rate",
            "vaccine_doses",
        }.intersection(paramDict):
            limitedDoses = bool(
                paramDict.get("vaccine_doses", 9999999)
                < communityPopulation[session.get("community", "newcastle")]
            )
            updateParamFromSchema(
                "limitDosesToggle",
                limitedDoses,
                scenarioID,
            )
            if limitedDoses:
                updateParamFromSchema(
                    "initialDoseReserve",
                    paramDict.get("vaccine_doses"),
                    scenarioID,
                )
            """useVaccines = True
            if (
                paramDict.get("vaccine_doses", 9999999)
                < communityPopulation[session.get("community", "newcastle")]
            ):
                updateParamFromSchema("limitDosesToggle", True, scenarioID)"""
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
        updateParamFromSchema("vaccineToggle", useVaccines, scenarioID)
        updateParamFromSchema("boosterToggle", useBoosters, scenarioID)
        updateParamFromSchema("socialDistancingToggle", useSocialDistancing, scenarioID)
        for prefix, value in useNPIs.items():
            updateParamFromSchema(f"{prefix}Toggle", value, scenarioID)
