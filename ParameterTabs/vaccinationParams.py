# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where vaccination parameters can be modified

# Imports
import logging

import numpy as np
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import ageCast, paramError, trigCast
from ClientResources.ModelSchema import (
    EfficacyValue,
    Parameters,
    scenarioParameters,
    vaccineCoverage,
    vaccineDose,
    vaccineEfficacy,
)
from ClientResources.ParameterFunctions import (
    hasDuplicates,
    idGet,
    loadKey,
    replaceTableNA,
    saveKey,
    updateParamFromSchema,
    updateTableFromSchema,
)
from ClientResources.SharedResources import (
    ageTimeDict,
    communityPopulation,
    ordinals,
)

# Logging
vaccineLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# TODO: See if the vaccination trigger parameters are fully working
# and reimplement them if they are
@st.fragment
def buildVaccinationTab(id: int, advanced: bool = False):
    """
    Function to generate the parameters for vaccination in a
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
        f"primaryDoseCount{id}": 2,
        f"primWanedRowCount{id}": 0,
        f"boostAgeRowCount{id}": 0,
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
    getRemainingGroups(ageGroupSets, ageCategories.keys())"""

    # Tab Content
    st.header("Vaccination-Related Parameters")
    st.markdown("""
        This tab contains parameters relating to how vaccination is
        integrated into the simulation.
    """)

    # Vaccination
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
    # st.html(f'<span id = "vaccinationTriggerCondition{id}"></span>')
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
            # TODO: Option to disable live vaccination entirely? Another radio?
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
            leftCol, rightCol = st.columns(2)
            loadKey("initialVaccinated", id, 0.0)
            initialVaccinated = leftCol.number_input(
                "Initial Vaccinated Population (% Percentage)",
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
The percentage of the population that will already be vaccinated against the
pathogen at the beginning of the simulation.
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
The percentage of the population that will be targeted by the vaccine schedule
in the simulation. The actual proportion of the population that is vaccinated
may be lower if there are an insufficient number of doses available.
                """,
            )
            '''
            loadKey("targetVaccinated", id, 0.8)
            targetVaccinated = rightCol.number_input(
                "Target Vaccinated Population (% Percentage)",
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
The percentage of the population that will be targeted by the vaccine schedule
in the simulation. The actual percentage that is vaccinated may be lower if
there are an insufficient number of doses available.
                """,
            )

            # Show error if initial proportion is above target
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
                    :primary-badge[:material/vaccines: Vaccination]
                    to be greater than {100 * targetVaccinated:0.5g}%.
                    - Decrease Target Vaccinated Proportion of Population in
                    :primary-badge[:material/vaccines: Vaccination]
                    to be lower than {100 * initialVaccinated:0.5g}%.
                """,
                False,
            )

            # Store age-based proportion values for error checking
            # vacAgeInitials, vacAgeTargets = {}, {}

            # Modifiable-length field for age-specific vaccination
            st.markdown(
                "### Age-Specific Vaccinated Population",
                help="""
This table allows for unique vaccinated populations to be defined
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
                placeholder=("Enter a value" if useVaccinesToggle else "Disabled"),
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
                        "Initial Vaccinated Population (% Percentage)",
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
                        "Target Vaccinated Population (% Percentage)",
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
                    :primary-badge[:material/vaccines: Vaccination]
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
                    :primary-badge[:material/vaccines: Vaccination]
                    that have the initial proportion higher than the target proportion.
                    - Decrease the Initial Vaccinated Proportion of Population
                    column in :primary-badge[:material/vaccines: Vaccination]
                    to always be lower than the target proportion.
                    - Increase the Target Vaccinated Proportion of Population
                    column in :primary-badge[:material/vaccines: Vaccination]
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
                        section of :primary-badge[:material/vaccines: Vaccination].
                        - Increase the scenario's Initial
                        Vaccinated Proportion of Population for the
                        "{age}" age group in the "Vaccination
                        Programs" section of the "Vaccinations and
                        NPIs" tab to be greater
                        than {100 * currentTarget:0.3g}%.
                        - Decrease the scenario's Target Vaccinated
                        Proportion of Population for the "{age}"
                        age group in the "Vaccination Programs"
                        section of :primary-badge[:material/vaccines: Vaccination]
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
        "Vaccine Immunity", key=f"vaccinePropertyContainer{id}", on_change="rerun"
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

            # Single vs multi-dose vaccine
            if advanced:
                loadKey("multiDoseToggle", id, False)
                multiDoseToggle = st.toggle(
                    "Multiple Vaccine Doses",
                    value=False,
                    on_change=saveKey,
                    args=["multiDoseToggle", id],
                    key=f"_multiDoseToggle{id}",
                    help="""
Toggle whether vaccines in the simulation should require multiple doses for each
individual.
        """,
                )
            else:
                multiDoseToggle = False

            if multiDoseToggle:
                # Multiple doses
                loadKey("primaryDoseCount", id, 2)
                primaryDoseCount = st.slider(
                    "Number of Vaccine Doses",
                    2,
                    5,
                    2,
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
                loadKey("primaryDelay", id, 3)
                st.slider(
                    "Time Between Vaccine Doses (Months)",
                    min_value=1,
                    max_value=12,
                    value=3,
                    disabled=not useVaccinesToggle,
                    on_change=saveKey,
                    args=["primaryDelay", id],
                    key=f"_primaryDelay{id}",
                    help="""
The number of months after an individual
receives a vaccine dose before they are able to
receive another, where a month is 30 days.
                    """,
                )

                # Waning parameters
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
infected if it has been a sufficiently long time since they received their
final vaccine dose.
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
The number of months after an individual receives their final vaccine dose before they
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
                    ### Individual Dose Efficacies

                    Here you can set the {"initial " if waningToggle else ""}efficacy
                    of each vaccine dose in the schedule separately. Note that
                    changing the "Number of Vaccine Doses" parameter
                    will affect how many sections are present here.
                """)
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
                                "Enter a value" if useVaccinesToggle else "Disabled"
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
Vaccine Dose section of :primary-badge[:material/vaccines: Vaccination]
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
                                        :primary-badge[:material/vaccines: Vaccination].
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
                                        Properties" section of
                                        :primary-badge[:material/vaccines: Vaccination] to be lower than
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
                        "Minimum Dose Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
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
                            minimum efficacy is {100 * primaryWanedEfficacy:0.3g}%.
                            As such, a vaccinated person's immunity to the
                            pathogen will get stronger over time instead of weaker.

                            Please make one of the following changes:

                            - Increase Initial Dose Efficacy for the final dose in
                            :primary-badge[:material/vaccines: Vaccination]
                            to be greater than {100 * primaryWanedEfficacy:0.3g}%.
                            - Decrease Minimum Dose Efficacy in
                            :primary-badge[:material/vaccines: Vaccination]
                            to be lower than {100 * finalInitialEfficacy:0.3g}%.
                        """,
                        True,
                    )

                    # Store age-based waned efficacy values for error checks
                    # primAgeWaneds = {}

                    # Age-Specific Waned Efficacy Field
                    st.markdown(
                        "#### Age-Specific Minimum Efficacy",
                        help="""
This table allows for unique minimum efficacy values
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
                            "Enter a value" if useVaccinesToggle else "Disabled"
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
                                "Minimum Dose Efficacy (Probability)",
                                required=True,
                                default=primaryWanedEfficacy,
                                min_value=0.0,
                                max_value=0.999999,
                                format="percent",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age group
after the full waning duration, represented as the probability that they will remain
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
                            Error: The age-specific minimum efficacy form used by the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{session[f'scenarioName{id}']}"'
                            } contains duplicate age group rows. Each age group
                            should only be used in a single row of the form.

                            Please remove or change any rows of the Age-Specific
                            Minimum Efficacy form in the Vaccine Immunity section
                            of :primary-badge[:material/vaccines: Vaccination]
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
                            greater than the minimum efficacy. As such, the
                            immunity to the pathogen conferred by the vaccine will get
                            stronger over time instead of weaker for the age groups
                            specified by these rows.

                            Please modify the Age-Specific Initial Efficacy form
                            for the final vaccine dose alongside the Age-Specific
                            Minimum Efficacy form in 
                            :primary-badge[:material/vaccines: Vaccination]
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
                # Single-dose vaccines

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
                else:
                    waningToggle = False

                # Vaccine Efficacy for All Doses
                loadKey("primarySingleEfficacy", id, 0.5)
                doseEfficacy = st.slider(
                    f"{"Initial " if waningToggle else ""}Vaccine Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    format="percent",
                    disabled=not useVaccinesToggle,
                    on_change=saveKey,
                    args=["primarySingleEfficacy", id],
                    key=f"_primarySingleEfficacy{id}",
                    help=f"""
The {"initial " if waningToggle else ""}efficacy of the vaccine,
represented as the probability that an
individual that has recently received a
dose will remain healthy when exposed to the pathogen.
                    """,
                )

                if waningToggle:
                    loadKey("primaryWanedEfficacy", id, 0.0)
                    primaryWanedEfficacy = st.slider(
                        "Minimum Vaccine Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
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
                    # TODO: Should disabling waning be a listed fix for the error?
                    paramError(
                        "wanedEfficacyAboveInitial",
                        id,
                        lambda: useVaccinesToggle
                        and primaryWanedEfficacy > doseEfficacy,
                        f"""
                            Error: The initial vaccine efficacy in the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{
                                    session[f'scenarioName{id}']
                                }"'
                            } is {100 * doseEfficacy:0.3g}%, but the
                            efficacy after waning is {100 * primaryWanedEfficacy:0.3g}%.
                            As such, a vaccinated person's immunity to the
                            pathogen will get stronger over time instead of weaker.

                            Please make one of the following changes:

                            - Increase Initial Vaccine Efficacy in
                            :primary-badge[:material/vaccines: Vaccination]
                            to be greater than {100 * primaryWanedEfficacy:0.3g}%.
                            - Decrease Minimum Vaccine Efficacy in
                            :primary-badge[:material/vaccines: Vaccination]
                            to be lower than {100 * doseEfficacy:0.3g}%.
                        """,
                        True,
                    )
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
The number of months after an individual receives the vaccine before they
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
                else:
                    primaryWanedEfficacy = 0.0

                # Age-Specific Primary Efficacy Field
                # TODO: Port changes made on single dose waning efficacy
                # to multi dose waning efficacy (and vice versa)
                st.markdown(
                    f"##### Age-Specific Vaccine Efficacy",
                    help=f"""
This section allows unique vaccine efficacy values to be defined
for individual age groups in the simulation, overriding the efficacy defined above.
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
                            "Vaccine Efficacy After Waning": [primaryWanedEfficacy],
                        },
                    ),
                    dataframe=True,
                )
                baseEfficacyData = replaceTableNA(
                    session[f"vacSingleEfficacyAgeForm{id}"],
                    {"Vaccine Efficacy After Waning": primaryWanedEfficacy},
                )
                vacEfficacyAgeForm = st.data_editor(
                    baseEfficacyData,
                    height="content",
                    num_rows="dynamic",
                    key=f"_vacSingleEfficacyAgeForm{id}",
                    on_change=saveKey,
                    args=["vacSingleEfficacyAgeForm", id],
                    kwargs={"dataframe": True},
                    disabled=not useVaccinesToggle,
                    placeholder=("Enter a value" if useVaccinesToggle else "Disabled"),
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
                            f"{"Initial " if waningToggle else ""}Vaccine Efficacy (Probability)",
                            required=True,
                            default=doseEfficacy,
                            min_value=0.0,
                            max_value=1.0,
                            format="percent",
                            help=f"""
The {"initial " if waningToggle else ""}efficacy of each vaccine dose for this age group, represented as the probability that a recently vaccinated individual in
this age group will remain healthy when exposed to the pathogen.
                            """,
                        ),
                        "Vaccine Efficacy After Waning": (
                            None
                            if not waningToggle
                            else st.column_config.NumberColumn(
                                "Minimum Vaccine Efficacy (Probability)",
                                required=True,
                                default=primaryWanedEfficacy,
                                min_value=0.0,
                                max_value=0.999999,
                                format="percent",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age group
after the full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                            )
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
                        :primary-badge[:material/vaccines: Vaccination]
                        that use the same age group as another row.
                    """,
                    True,
                )
                paramError(
                    "vacSingleEfficacyAgeFormWanedAboveInitial",
                    id,
                    lambda: waningToggle
                    and np.any(
                        vacEfficacyAgeForm["Vaccine Efficacy"]
                        < vacEfficacyAgeForm["Vaccine Efficacy After Waning"]
                    ),
                    f"""
                        Error: The age-specific vaccine efficacy form used by the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{session[f'scenarioName{id}']}"'
                        } contains rows where the minimum vaccine efficacy is
                        greater than the initial efficacy. As such, the
                        immunity to the pathogen conferred by the vaccine will get
                        stronger over time instead of weaker for the age groups
                        specified by these rows.

                        Please make one of the following changes:

                        - Remove all rows of the Age-Specific Vaccine Efficacy form
                        in :primary-badge[:material/vaccines: Vaccination]
                        that have the initial efficacy lower than the minimum
                        efficacy.
                        - Increase the Initial Vaccine Efficacy column in
                        :primary-badge[:material/vaccines: Vaccination]
                        to always be higher than the minimum efficacy.
                        - Decrease the Minimum Vaccine Efficacy column
                        in :primary-badge[:material/vaccines: Vaccination]
                        to always be lower than the initial efficacy.
                    """,
                    True,
                )

                '''
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
                            max_value=0.999999,
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
                        Age-Specific Booster Efficacy form in
                        :primary-badge[:material/vaccines: Vaccination]
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

                        - Remove all rows of the Age-Specific Booster Efficacy form
                        in :primary-badge[:material/vaccines: Vaccination]
                        that have the initial efficacy higher than the efficacy
                        after waning.
                        - Increase the Initial Booster Efficacy column in
                        :primary-badge[:material/vaccines: Vaccination]
                        to always be higher than the efficacy after waning.
                        - Decrease the Booster Efficacy After Immunity Waning column
                        in :primary-badge[:material/vaccines: Vaccination]
                        to always be lower than the initial efficacy.
                    """,
                    True,
                )
                
                '''

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
                        :primary-badge[:material/vaccines: Vaccination]
                        to be greater than {boosterDelay}.
                        - Decrease Time Between Booster Doses in
                        :primary-badge[:material/vaccines: Vaccination]
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
                    "Minimum Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=0.99,
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
                        Error: The initial booster vaccine efficacy in the {
                            'baseline scenario' if id == 0
                            else f'scenario named "{
                                session[f'scenarioName{id}']
                            }"'
                        } is {100 * boosterBaseEfficacy:0.3g}%, but the
                        minimum booster efficacy is {100 * boosterWanedEfficacy:0.3g}%.
                        As such, a vaccinated person's immunity to the
                        pathogen will get stronger over time instead of weaker.

                        Please make one of the following changes:

                        - Increase Initial Booster Efficacy in
                        :primary-badge[:material/vaccines: Vaccination]
                        to be greater than {100 * boosterWanedEfficacy:0.3g}%.
                        - Decrease Minimum Booster Efficacy in
                        :primary-badge[:material/vaccines: Vaccination]
                        to be lower than {100 * boosterBaseEfficacy:0.3g}%.
                    """,
                    True,
                )

                # Store age-based booster efficacy values for error checking
                # boostAgeInitials, boostAgeWaneds = {}, {}

                # Modifiable-length field for age-specific efficacy
                st.markdown(
                    "### Age-Specific Booster Efficacy",
                    help="""
This table allows for unique booster efficacy values (both initial and minimum)
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
                        else "Disabled"
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
                            "Minimum Booster Efficacy (Probability)",
                            required=True,
                            default=boosterWanedEfficacy,
                            min_value=0.0,
                            max_value=0.999999,
                            format="percent",
                            help="""
The efficacy of the immunity possessed by a booster-vaccinated individual in
this age group after the full waning duration, represented as the probability
that they will remain healthy when exposed to the pathogen.
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
                        Age-Specific Booster Efficacy form in
                        :primary-badge[:material/vaccines: Vaccination]
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
                        } contains rows where the initial booster efficacy is
                        greater than the minimum booster efficacy. As such, the
                        immunity to the pathogen conferred by the booster will get
                        stronger over time instead of weaker for the age groups
                        specified by these rows.

                        Please make one of the following changes:

                        - Remove all rows of the Age-Specific Booster Efficacy form
                        in :primary-badge[:material/vaccines: Vaccination]
                        that have the initial efficacy higher than the efficacy
                        after waning.
                        - Increase the Initial Booster Efficacy column in
                        :primary-badge[:material/vaccines: Vaccination]
                        to always be higher than the efficacy after waning.
                        - Decrease the Minimum Booster Efficacy column
                        in :primary-badge[:material/vaccines: Vaccination]
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
                            :primary-badge[:material/vaccines: Vaccination].
                            - Increase the scenario's Initial Booster
                            Efficacy for the "{age}" age group in the
                            "Booster Vaccines" section of
                            :primary-badge[:material/vaccines: Vaccination]
                            to be greater than {100 * currentWaned:0.3g}%.
                            - Decrease the scenario's Booster Efficacy
                            After Immunity Waning for the "{age}" age
                            group in the "Booster Vaccines" section of
                            :primary-badge[:material/vaccines: Vaccination]
                            to be lower than {100 * currentInitial:0.3g}%.
                        """,
                            icon=":material/error:",
                        )
                        session[f"ageBoostEfficacyError{id}"] = 2
                        ageBoostEfficacyError = True
                # Reset error parameter if none of the age levels error
                if not ageBoostEfficacyError:
                    session[f"ageBoostEfficacyError{id}"] = 0'''

    # TODO: Reintegrate trigger thresholds when vaccines care about them


def vaccineSaveSchema(schema: Parameters, id: int = 0, advanced: bool = False) -> bool:
    """
    Function to populate the Pydantic model schema with vaccination parameters
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
    multiDoseToggle = idGet("multiDoseToggle", id, False) if advanced else False
    waningToggle = idGet("vaccineWaningToggle", id, False) if advanced else False
    boosterToggle = idGet("boosterToggle", id, False) if advanced else False
    ageNames = list(ageTimeDict.keys())
    simLength = session.get("cycleCount", 360) * 2
    initialProportion = idGet("initialVaccinated", id, 0.0)
    targetProportion = idGet("targetVaccinated", id, 0.8)
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        if vaccineToggle:
            # Initialising Scenario Parameters
            scenarioParams = (
                schema.Scenario_Parameter
                if schema.Scenario_Parameter
                else scenarioParameters()
            )

            # Vaccination Coverage
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

            # Vaccination Programs
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

            # Save the program parameters
            schema.Scenario_Parameter = scenarioParams

            # Vaccine Doses and Efficacy
            if multiDoseToggle:
                primDoseCount = idGet("primaryDoseCount", id, 2)

                # Individual Dose Efficacy Parameters
                primBaseEfficacy = [
                    idGet("primaryBaseEfficacy", id, 0.5, f"-{i}")
                    for i in range(primDoseCount)
                ]
                # Waned is 0 if disabled since it doesn't matter
                primWanedEfficacy = (
                    idGet("primaryWanedEfficacy", id, 0.0) if waningToggle else 0.0
                )

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

                # Dose Parameters
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
            else:
                # Single Efficacy Parameters
                singleEfficacy = idGet("primarySingleEfficacy", id, 0.5)
                singleWanedEfficacy = (
                    idGet("primaryWanedEfficacy", id, 0.0) if waningToggle else 0.0
                )
                singleEfficacyAgeForm = idGet(
                    "vacSingleEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [singleEfficacy],
                            "Vaccine Efficacy After Waning": [singleWanedEfficacy],
                        },
                    ),
                )
                efficacyParams = [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=singleWanedEfficacy,
                        Efficacy=[singleEfficacy],
                    )
                ] + [
                    vaccineEfficacy(
                        DoseType="primary",
                        Age=ageCast(age),
                        WanedEfficacy=waned if waningToggle else 0.0,
                        Efficacy=[initial],
                    )
                    for age, initial, waned in zip(
                        singleEfficacyAgeForm["Age Group"],
                        singleEfficacyAgeForm["Vaccine Efficacy"],
                        singleEfficacyAgeForm["Vaccine Efficacy After Waning"],
                    )
                    if age
                ]

                # Dose Parameters
                primWaningDuration = idGet("primaryWaningRate", id, 12) * 60
                doseParams = [
                    vaccineDose(
                        DoseType="primary",
                        Count=1,
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
                                else (singleEfficacy - singleWanedEfficacy)
                                / primWaningDuration
                            )
                        ),
                    )
                ]

            # Booster Efficacy Values
            if boosterToggle:
                boostBaseEfficacy = idGet("boosterBaseEfficacy", id, 0.9)
                boostWanedEfficacy = idGet("boosterWanedEfficacy", id, 0.6)
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

            # Save efficacy and dose parameters
            schema.Scenario_VaccineDoseEfficacy = efficacyParams
            schema.Scenario_VaccineDose = doseParams
    except (ValueError, ValidationError) as e:
        vaccineLog.error(
            (
                f"[vaccinationParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e
    return vaccineToggle


def vaccineLoadSchema(schema: Parameters, scenarioID: int = 0):
    """
    Function to read vaccination parameters from a schema and set the
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

    # Keep track of whether vaccines/boosters have showed up
    # TODO: Distinguish between scenario with vaccines disabled and
    # scenario with no changes to vaccines (only relevant once
    # scenarios are more efficient with less baseline duplication)
    useVaccines, useMultiDose, useBoosters = False, False, False

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

    # Load vaccine parameters
    schemaDose = schema.Scenario_VaccineDose
    schemaEfficacy = schema.Scenario_VaccineDoseEfficacy
    schemaCoverage = schema.Scenario_VaccineCoverage
    missingParams = (
        params is None for params in (schemaDose, schemaEfficacy, schemaCoverage)
    )
    if scenarioID == 0 and any(missingParams) and not all(missingParams):
        raise AssertionError("""
            Vaccination parameters were only partially defined
            for the baseline scenario
        """)

    # Vaccine Coverage Parameters
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
    setDoseCount = False
    primaryDoseCount = idGet("primaryDoseCount", 0, 2)
    boosterDoseCount = idGet("boosterDoseCount", 0, 3)
    primaryRatePerCycle = idGet("primaryWaningRate", 0, 12)
    boosterRatePerCycle = idGet("boosterWaningRate", 0, 6)
    baseFull = [idGet("primaryBaseEfficacy", 0, 0.5, f"-{primaryDoseCount - 1}")]
    baseWaned = idGet("primaryWanedEfficacy", 0, 0.0)
    baseBoostFull = idGet("boosterBaseEfficacy", 0, 0.9)
    baseBoostWaned = idGet("boosterWanedEfficacy", 0, 0.6)

    # Vaccine Dosage Parameters
    if schemaDose is not None:
        useVaccines = True

        # Primary vaccines
        if any(dose.DoseType == "primary" for dose in schemaDose):
            primaryDose = [dose for dose in schemaDose if dose.DoseType == "primary"][0]
            primaryDoseCount = primaryDose.Count
            useMultiDose = bool(primaryDoseCount != 1)
            setDoseCount = True
            if useMultiDose:
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
        elif scenarioID == 0:
            raise AssertionError("""
                Primary vaccine dose properties were not defined for the
                baseline scenario, despite booster properties being defined
            """)

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
    if schemaEfficacy is not None:
        useVaccines = True

        # Primary Vaccines
        primaryEfficacySchema = [
            dose for dose in schemaEfficacy if dose.DoseType == "primary"
        ]
        # Get the global values (age=None) first
        primaryEfficacySchema.sort(key=lambda x: ageOrder.get(x.Age, 99))
        if len(primaryEfficacySchema) > 0 and primaryEfficacySchema[0].Age is None:
            baseEfficacy = primaryEfficacySchema.pop(0)
            if not isinstance(baseEfficacy.Efficacy, list):
                baseFull = [baseEfficacy.Efficacy]
            else:
                baseFull = baseEfficacy.Efficacy
            if setDoseCount and len(baseFull) != primaryDoseCount:
                # Throw error if dose and efficacy disagree on dose count
                scenarioName = idGet(
                    "scenarioName", scenarioID, f"Scenario #{scenarioID}"
                )
                raise AssertionError(f"""
                    Vaccine dose count is inconsistent between dose and efficacy
                    parameters for the {
                        "baseline scenario"
                        if scenarioID == 0
                        else f"scenario named {scenarioName}"
                    }
                """)
            primaryDoseCount = len(baseFull)
            useMultiDose = useMultiDose or primaryDoseCount > 1
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
        primaryEfficacyTables = [
            pd.DataFrame(columns=("Age Group", "Initial Dose Efficacy"))
            for _ in range(primaryDoseCount)
        ]
        primaryWanedTable = pd.DataFrame(
            columns=("Age Group", "Dose Efficacy After Waning")
        )
        primarySingleTable = pd.DataFrame(
            columns=("Age Group", "Vaccine Efficacy", "Vaccine Efficacy After Waning")
        )
        for prim in primaryEfficacySchema:
            age, base, waned = prim.Age, prim.Efficacy, prim.WanedEfficacy
            if not isinstance(base, list):
                base = [base]
            # Assume correct number of efficacies are used
            # since the schema should error before now otherwise
            if age is not None:
                if waned != baseWaned:
                    primaryWanedTable.loc[primaryWanedTable.shape[0]] = [age, waned]
                    primarySingleTable.loc[primarySingleTable.shape[0]] = [
                        age,
                        base[0],
                        waned,
                    ]
                elif base[0] != baseFull[0]:
                    # Use first dose for single table
                    primarySingleTable.loc[primarySingleTable.shape[0]] = [
                        age,
                        base[0],
                        waned,
                    ]
                for index, value in enumerate(base):
                    if value != baseFull[index]:
                        currentTable = primaryEfficacyTables[index]
                        currentTable.loc[currentTable.shape[0]] = [age, value]

        # Save the tables
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
                    "Vaccine Efficacy After Waning": [baseWaned],
                },
            ),
        )

        # Booster Vaccines
        boosterEfficacySchema = [
            dose for dose in schemaEfficacy if dose.DoseType == "booster"
        ]
        if len(boosterEfficacySchema) > 0:
            if scenarioID == 0 and not useBoosters:
                # Throw error if baseline has efficacy params but no dose params
                raise AssertionError("""
                    Booster vaccine parameters were only partially
                    defined for the baseline scenario
                """)
            useBoosters = True
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
        boosterEfficacyTable = pd.DataFrame(
            columns=(
                "Age Group",
                "Initial Booster Efficacy",
                "Booster Efficacy After Waning",
            )
        )
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

    # Final Toggles
    # TODO: Ensure that toggles being disabled is distinguishable from
    # parameters being unchanged from baselines
    updateParamFromSchema("vaccineToggle", useVaccines, scenarioID)
    updateParamFromSchema("boosterToggle", useBoosters, scenarioID)
    updateParamFromSchema("multiDoseToggle", useMultiDose, scenarioID)

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
        firstDoseRate = schemaParameters.vaccination_first_dose_rate
        doseCount = schemaParameters.vaccine_doses
        if doseCount is not None or firstDoseRate is not None:
            limitedDoses = bool(
                doseCount is not None
                and doseCount
                < communityPopulation[session.get("community", "newcastle")]
            )
            updateParamFromSchema("limitDosesToggle", limitedDoses, scenarioID)
            if limitedDoses:
                updateParamFromSchema("initialDoseReserve", doseCount, scenarioID)
        if firstDoseRate is not None:
            updateParamFromSchema("firstDoseRate", firstDoseRate, scenarioID)
