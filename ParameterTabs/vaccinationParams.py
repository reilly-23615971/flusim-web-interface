# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where vaccination parameters can be modified

# Imports
import logging
from typing import Optional

import numpy as np
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
    DashboardParameters,
    GeneralParameters,
    VaccineCoverage,
    VaccineDose,
    VaccineEfficacy,
)
from ClientResources.ParameterFunctions import (
    has_duplicates,
    id_get,
    load_key,
    replace_table_na,
    save_key,
    update_param_from_schema,
    update_table_from_schema,
)
from ClientResources.Constants import ORDINALS
from ClientResources.Types import AGE_GROUP_KEYS, TRIGGER_KEY_CONVERTER

# Logging
vaccineLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# TODO: See if the vaccination trigger parameters are fully working
# and reimplement them if they are
# @st.fragment
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
    # Tab Content
    st.header("Vaccination-Related Parameters")
    st.markdown("""
        This tab contains parameters relating to how vaccination is
        integrated into the simulation.
    """)

    # Vaccination
    load_key("vaccineToggle", id, False)
    useVaccinesToggle = st.toggle(
        "Enable Vaccines in Simulation",
        value=False,
        on_change=save_key,
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
        "Vaccine Coverage", key=f"vaccineProgramContainer{id}", on_change="rerun"
    ) as programContainer:
        if programContainer.open:
            # Describe what sort of parameters are here
            st.markdown("""
                These parameters control the rollout of vaccines in
                the simulation, with parameters such as how frequently
                vaccines are administered and what proportion of the
                population is already vaccinated.
            """)
            if advanced:
                load_key("vaccineDistribution", id, default="Static Proportions")
                vaccineDistribution = st.radio(
                    "Vaccine Distribution",
                    options=["Static Proportions", "Live Distribution"],
                    captions=[
                        "Vaccination status will not change",
                        "New individuals will be vaccinated throughout the experiment",
                    ],
                    key=f"_vaccineDistribution{id}",
                    on_change=save_key,
                    args=["vaccineDistribution", id],
                    disabled=not useVaccinesToggle,
                    help="""
    Select how vaccines will be distributed throughout the population.
    ### Options:
    - Static Proportions: A set proportion of the population will be vaccinated at
    the beginning of the simulation, with no additional vaccinations being made. This
    setting should be used for infections that are regularly vaccinated against, such
    as influenza.
    - Live Distribution: New individuals will be vaccinated throughout the duration
    of the simulation experiment at a regular rate. This setting should be used for
    recent infections where vaccines are either actively in development or not yet
    widely distributed, such as SARS-CoV-2.
                    """,
                )
                staticVaccination = vaccineDistribution == "Static Proportions"
            else:
                staticVaccination = True

            # Vaccinated Proportions
            if staticVaccination:
                # Single vaccination proportion
                load_key("initialVaccinated", id, 0.0)
                initialVaccinated = st.number_input(
                    "Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_initialVaccinated{id}",
                    on_change=save_key,
                    args=["initialVaccinated", id],
                    disabled=not useVaccinesToggle,
                    help="""
The percentage of the population that will be vaccinated against the pathogen.
                    """,
                )
                targetVaccinated = max(initialVaccinated, 80.0)

            else:
                # Initial and target proportions
                leftCol, rightCol = st.columns(2)
                load_key("initialVaccinated", id, 0.0)
                initialVaccinated = leftCol.number_input(
                    "Initial Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_initialVaccinated{id}",
                    on_change=save_key,
                    args=["initialVaccinated", id],
                    disabled=not useVaccinesToggle,
                    help="""
The percentage of the population that will already be vaccinated against the
pathogen at the beginning of the simulation.
                    """,
                )
                '''
                initialVaccinated = st.slider(
                    "Initial Vaccinated Population",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.001,
                    format="percent",
                    key=f"_initialVaccinated{id}",
                    on_change=save_key,
                    args=["initialVaccinated", id],
                    disabled=not useVaccinesToggle,
                    help="""
    The percentage of the population that will
    already be vaccinated against the pathogen at
    the beginning of the simulation.
                    """,
                )
                targetVaccinated = st.slider(
                    "Target Vaccinated Population",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.8,
                    step=0.001,
                    format="percent",
                    key=f"_targetVaccinated{id}",
                    on_change=save_key,
                    args=["targetVaccinated", id],
                    disabled=not useVaccinesToggle,
                    help="""
    The percentage of the population that will be targeted by the vaccine schedule
    in the simulation. The actual proportion of the population that is vaccinated
    may be lower if there are an insufficient number of doses available.
                    """,
                )
                '''
                load_key("targetVaccinated", id, 80.0)
                targetVaccinated = rightCol.number_input(
                    "Target Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=80.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_targetVaccinated{id}",
                    on_change=save_key,
                    args=["targetVaccinated", id],
                    disabled=not useVaccinesToggle,
                    help="""
The percentage of the population that will be targeted by the vaccine schedule
in the simulation. The actual percentage that is vaccinated may be lower if
there are an insufficient number of doses available.
                    """,
                )

                # Show error if initial proportion is above target
                param_error(
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
                        {targetVaccinated:0.5g}% of the
                        population, but the initial vaccinated
                        proportion is {initialVaccinated:0.5g}%. As
                        such, the target proportion will already be met,
                        and no new vaccinations will occur.

                        Please make one of the following changes:

                        - Increase Initial Vaccinated Population in
                        :primary-badge[:material/vaccines: Vaccination]
                        to be greater than {targetVaccinated:0.5g}%.
                        - Decrease Target Vaccinated Population in
                        :primary-badge[:material/vaccines: Vaccination]
                        to be lower than {initialVaccinated:0.5g}%.
                    """,
                    False,
                )

                # Other live distribution parameters
                # TODO: Get data for a more accurate default
                load_key("firstDoseRate", id, 300)
                st.number_input(
                    "Vaccination Rate (Vaccinations per Day)",
                    min_value=1,
                    value=300,
                    key=f"_firstDoseRate{id}",
                    placeholder="Enter a whole number of people",
                    on_change=save_key,
                    args=["firstDoseRate", id],
                    disabled=not useVaccinesToggle,
                    help="""
The number of unvaccinated individuals who will
receive the first dose of the vaccine each day.
                    """,
                )
                # Limited Dose Parameters (if advanced parameters are enabled)
                load_key("limitDosesToggle", id, False)
                limitDosesToggle = st.toggle(
                    "Enable Limited Number of Vaccine Doses",
                    value=False,
                    key=f"_limitDosesToggle{id}",
                    disabled=not useVaccinesToggle,
                    on_change=save_key,
                    args=["limitDosesToggle", id],
                    help="""
Toggle whether the number of vaccine doses that can be administered in each
simulation should be limited, putting an upper limit on the number of
vaccinated individuals in the simulation.
                    """,
                )
                if limitDosesToggle:
                    load_key("initialDoseReserve", id, 0)
                    st.number_input(
                        "Total Number of Vaccine Doses",
                        min_value=0,
                        value=50000,
                        key=f"_initialDoseReserve{id}",
                        disabled=not useVaccinesToggle or not limitDosesToggle,
                        on_change=save_key,
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
            load_key(
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
            # Set N/A values from hidden columns to the current default
            if not staticVaccination:
                session[f"vacPropAgeForm{id}"] = replace_table_na(
                    session[f"vacPropAgeForm{id}"],
                    {
                        "Target Vaccinated Proportion": max(
                            initialVaccinated, targetVaccinated
                        ),
                    },
                )
            vacPropAgeForm = st.data_editor(
                session[f"vacPropAgeForm{id}"],
                height="content",
                num_rows="dynamic",
                key=f"_vacPropAgeForm{id}",
                on_change=save_key,
                args=["vacPropAgeForm", id],
                kwargs={"dataframe": True},
                disabled=not useVaccinesToggle,
                placeholder=("Enter a value" if useVaccinesToggle else "Disabled"),
                column_config={
                    "Age Group": st.column_config.SelectboxColumn(
                        "Age Group",
                        required=True,
                        options=AGE_GROUP_KEYS,
                        format_func=age_display,
                        help="""
An age group that will have specific vaccine proportions defined for it,
overriding the base proportions.
                        """,
                    ),
                    "Initial Vaccinated Proportion": st.column_config.NumberColumn(
                        (
                            "Vaccinated Population (% Percentage)"
                            if staticVaccination
                            else "Initial Vaccinated Population (%)"
                        ),
                        required=True,
                        default=initialVaccinated,
                        min_value=0.0,
                        max_value=100.0,
                        format="%0.5g%%",
                        help=(
                            """
The percentage of individuals in this age group that will be
vaccinated against the pathogen.
                            """
                            if staticVaccination
                            else """
The percentage of individuals in this age group that will already be
vaccinated against the pathogen at the beginning of the simulation.
                            """
                        ),
                    ),
                    "Target Vaccinated Proportion": (
                        None
                        if staticVaccination
                        else st.column_config.NumberColumn(
                            "Target Vaccinated Population (%)",
                            required=True,
                            default=targetVaccinated,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The percentage of individuals in this age group that will be targeted by the
vaccine schedule in the simulation. The actual proportion of individuals that
are vaccinated may be lower if there are an insufficient number of doses available.
                        """,
                        )
                    ),
                },
            )
            param_error(
                "vacPropAgeFormDuplicates",
                id,
                lambda: has_duplicates(vacPropAgeForm),
                f"""
                    Error: The age-specific vaccinated proportions form used by the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{session[f'scenarioName{id}']}"'
                    } contains duplicate age group rows. Each age group
                    should only be used in a single row of the form.

                    Please remove or change any rows of the Age-Specific
                    Vaccinated Population Parameters form in
                    :primary-badge[:material/vaccines: Vaccination]
                    that use the same age group as another row.
                """,
                True,
            )
            # TODO: make data_editor error messages name the rows
            param_error(
                "vacPropAgeFormTargetAlreadyFulfilled",
                id,
                lambda: not staticVaccination
                and np.any(
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
                    Vaccinated Population Parameters form in
                    :primary-badge[:material/vaccines: Vaccination]
                    that have the initial proportion higher than the target proportion.
                    - Decrease the Initial Vaccinated Population
                    column in :primary-badge[:material/vaccines: Vaccination]
                    to always be lower than the target proportion.
                    - Increase the Target Vaccinated Population
                    column in :primary-badge[:material/vaccines: Vaccination]
                    to always be higher than the initial proportion.
                """,
                True,
            )

    # Primary Vaccine Parameters
    with st.expander(
        "Vaccine-Derived Immunity",
        key=f"vaccinePropertyContainer{id}",
        on_change="rerun",
    ) as vaccineContainer:
        if vaccineContainer.open:
            # Describe primary vaccines
            st.markdown("""
                These parameters control the properties of the main
                schedule of vaccines that will be administered to
                individuals within the simulation.
            """)

            # Single vs multi-dose vaccine
            if advanced:
                load_key("multiDoseToggle", id, False)
                multiDoseToggle = st.toggle(
                    "Multiple Vaccine Doses",
                    value=False,
                    on_change=save_key,
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
                load_key("primary_dose_count", id, 2)
                primary_dose_count = st.slider(
                    "Number of Vaccine Doses",
                    2,
                    5,
                    2,
                    key=f"_primary_dose_count{id}",
                    on_change=save_key,
                    args=["primary_dose_count", id],
                    disabled=not useVaccinesToggle,
                    help="""
    The number of times each individual in the
    simulation will be administered a vaccine for
    the pathogen, excluding booster vaccines.
                    """,
                )
                load_key("primaryDelay", id, 3)
                st.slider(
                    "Time Between Vaccine Doses (Months)",
                    min_value=1,
                    max_value=12,
                    value=3,
                    disabled=not useVaccinesToggle,
                    on_change=save_key,
                    args=["primaryDelay", id],
                    key=f"_primaryDelay{id}",
                    help="""
The number of months after an individual
receives a vaccine dose before they are able to
receive another, where a month is 30 days.
                    """,
                )

                # Waning parameters
                load_key("vaccineWaningToggle", id, False)
                waningToggle = st.toggle(
                    "Enable Vaccine-Derived Immunity Waning",
                    value=False,
                    on_change=save_key,
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
                    load_key("primaryDuration", id, 6)
                    st.slider(
                        "Vaccine-Derived Immunity Waning Delay (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
                        args=["primaryDuration", id],
                        key=f"_primaryDuration{id}",
                        help="""
The number of months after an individual receives their final vaccine dose before they
begin losing their immunity, where a month is 30 days.
                        """,
                    )
                    load_key("primaryWaningRate", id, 12)
                    st.slider(
                        "Vaccine Waning Duration (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
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

                # Modifiable-length field for each primary dose
                # TODO: Consider tabs over containers
                st.markdown(f"""
                    ### Individual Dose Efficacies

                    Here you can set the {"initial " if waningToggle else ""}efficacy
                    of each vaccine dose in the schedule separately. Note that
                    changing the "Number of Vaccine Doses" parameter
                    will affect how many sections are present here.
                """)
                for i in range(primary_dose_count):
                    with st.container(border=True):
                        st.markdown(f"#### {ORDINALS[i+1]} Vaccine Dose")
                        load_key("primaryBaseEfficacy", id, 0.5, f"-{i}")
                        # Store efficacy between 0-100 for form compatibility
                        baseDoseEfficacy = round(
                            st.slider(
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
                                on_change=save_key,
                                args=["primaryBaseEfficacy", id, f"-{i}"],
                                key=f"_primaryBaseEfficacy{id}-{i}",
                                help=f"""
The {"initial " if waningToggle else ""}efficacy of this vaccine dose,
represented as the probability that an individual that has received the
dose will remain healthy when exposed to the pathogen.
                            """,
                            )
                            * 100,
                            6,
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
                        load_key(
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
                            on_change=save_key,
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
                                    options=AGE_GROUP_KEYS,
                                    format_func=age_display,
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
                                    max_value=100.0,
                                    format="%0.5g%%",
                                    help=f"""
The {"initial " if waningToggle else ""}efficacy of this vaccine dose for
this age group, represented as the probability that a vaccinated individual in
this age group will remain healthy when exposed to the pathogen.
                                    """,
                                ),
                            },
                        )
                        param_error(
                            f"vacInitialEfficacyAgeForm{i}Duplicates",
                            id,
                            lambda: has_duplicates(vacInitialEfficacyAgeForm),
                            f"""
Error: The age-specific {"initial" if waningToggle else "dose"} efficacy
form used for the {ORDINALS[i+1].lower()} vaccine dose by the
{'baseline scenario' if id == 0 else f'scenario named "{session[f'scenarioName{id}']}"'}
contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific
{"Initial " if waningToggle else ""}Efficacy form in the {ORDINALS[i+1]}
Vaccine Dose section of :primary-badge[:material/vaccines: Vaccination]
that use the same age group as another row.
                            """,
                            True,
                        )

                # Efficacy After Waning
                if waningToggle:
                    load_key("primaryWanedEfficacy", id, 0.0)
                    primaryWanedEfficacy = st.slider(
                        "Minimum Dose Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.0,
                        format="percent",
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
                        args=["primaryWanedEfficacy", id],
                        key=f"_primaryWanedEfficacy{id}",
                        help="""
The efficacy of a vaccinated individual's immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                        """,
                    )
                    percentWanedEfficacy = round(primaryWanedEfficacy * 100, 6)
                    # Last efficacy value is all that's cared about
                    # for error checking purposes
                    finalDose = primary_dose_count - 1
                    finalInitialEfficacy = id_get(
                        "primaryBaseEfficacy", id, 0.5, f"-{finalDose}"
                    )
                    param_error(
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
                    load_key(
                        "vacWaneAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Dose Efficacy After Waning": [percentWanedEfficacy],
                            },
                        ),
                        dataframe=True,
                    )
                    vacWaneAgeForm = st.data_editor(
                        session[f"vacWaneAgeForm{id}"],
                        height="content",
                        num_rows="dynamic",
                        key=f"_vacWaneAgeForm{id}",
                        on_change=save_key,
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
                                options=AGE_GROUP_KEYS,
                                format_func=age_display,
                                help="""
An age group that will have a specific final efficacy value after
immunity waning defined for it, overriding the base value.
                                """,
                            ),
                            "Dose Efficacy After Waning": st.column_config.NumberColumn(
                                "Minimum Dose Efficacy (Probability)",
                                required=True,
                                default=percentWanedEfficacy,
                                min_value=0.0,
                                max_value=99.999999,
                                format="%0.5g%%",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age group
after the full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                            ),
                        },
                    )
                    param_error(
                        "vacWaneAgeFormDuplicates",
                        id,
                        lambda: has_duplicates(vacWaneAgeForm),
                        f"""
                            Error: The age-specific minimum efficacy form used by the {
                                'baseline scenario' if id == 0
                                else f'scenario named "{session[f'scenarioName{id}']}"'
                            } contains duplicate age group rows. Each age group
                            should only be used in a single row of the form.

                            Please remove or change any rows of the Age-Specific
                            Minimum Efficacy form in the Vaccine-Derived Immunity section
                            of :primary-badge[:material/vaccines: Vaccination]
                            that use the same age group as another row.
                        """,
                        True,
                    )
                    # TODO: Have these errors highlight specific ages
                    finalInitialEfficacyAgeForm = id_get(
                        "vacInitialEfficacyAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [
                                    round(
                                        id_get(
                                            "primaryBaseEfficacy",
                                            id,
                                            0.5,
                                            f"-{finalDose}",
                                        )
                                        * 100,
                                        6,
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
                    param_error(
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

            else:
                # Single-dose vaccines

                # Waning parameters (only if advanced parameters are enabled)
                if advanced:
                    load_key("vaccineWaningToggle", id, False)
                    waningToggle = st.toggle(
                        "Enable Vaccine-Derived Immunity Waning",
                        value=False,
                        on_change=save_key,
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
                load_key("primarySingleEfficacy", id, 0.5)
                doseEfficacy = st.slider(
                    f"{"Initial " if waningToggle else ""}Vaccine Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    format="percent",
                    disabled=not useVaccinesToggle,
                    on_change=save_key,
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
                    load_key("primaryWanedEfficacy", id, 0.0)
                    primaryWanedEfficacy = st.slider(
                        "Minimum Vaccine Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.0,
                        format="percent",
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
                        args=["primaryWanedEfficacy", id],
                        key=f"_primaryWanedEfficacy{id}",
                        help="""
The efficacy of a vaccinated individual's immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                        """,
                    )
                    # TODO: Should disabling waning be a listed fix for the error?
                    param_error(
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
                    load_key("primaryDuration", id, 6)
                    st.slider(
                        "Vaccine-Derived Immunity Waning Delay (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
                        args=["primaryDuration", id],
                        key=f"_primaryDuration{id}",
                        help="""
The number of months after an individual receives the vaccine before they
begin losing their immunity, where a month is 30 days.
                        """,
                    )
                    load_key("primaryWaningRate", id, 12)
                    st.slider(
                        "Vaccine Waning Duration (Months)",
                        1,
                        12,
                        6,
                        disabled=not useVaccinesToggle,
                        on_change=save_key,
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

                # Scale to 0-100 for form compatibility
                percentDoseEfficacy = round(doseEfficacy * 100, 6)
                percentWanedEfficacy = round(primaryWanedEfficacy * 100, 6)

                # Age-Specific Primary Efficacy Field
                st.markdown(
                    f"##### Age-Specific Vaccine Efficacy",
                    help=f"""
This section allows unique vaccine efficacy values to be defined
for individual age groups in the simulation, overriding the efficacy defined above.
                    """,
                )
                if useVaccinesToggle:
                    st.markdown("Double-click a cell in this table to edit its value.")

                load_key(
                    "vacSingleEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [percentDoseEfficacy],
                            "Vaccine Efficacy After Waning": [percentWanedEfficacy],
                        },
                    ),
                    dataframe=True,
                )
                # Set N/A values from hidden columns to the current default
                if waningToggle:
                    session[f"vacSingleEfficacyAgeForm{id}"] = replace_table_na(
                        session[f"vacSingleEfficacyAgeForm{id}"],
                        {"Vaccine Efficacy After Waning": percentWanedEfficacy},
                    )
                vacEfficacyAgeForm = st.data_editor(
                    session[f"vacSingleEfficacyAgeForm{id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_vacSingleEfficacyAgeForm{id}",
                    on_change=save_key,
                    args=["vacSingleEfficacyAgeForm", id],
                    kwargs={"dataframe": True},
                    disabled=not useVaccinesToggle,
                    placeholder=("Enter a value" if useVaccinesToggle else "Disabled"),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have a specific vaccine efficacy value defined
for it, overriding the base value.
                            """,
                        ),
                        "Vaccine Efficacy": st.column_config.NumberColumn(
                            f"{"Initial " if waningToggle else ""}Vaccine Efficacy (Probability)",
                            required=True,
                            default=percentDoseEfficacy,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
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
                                default=percentWanedEfficacy,
                                min_value=0.0,
                                max_value=99.999999,
                                format="%0.5g%%",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age group
after the full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                            )
                        ),
                    },
                )
                param_error(
                    "vacSingleEfficacyAgeFormDuplicates",
                    id,
                    lambda: has_duplicates(vacEfficacyAgeForm),
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
                param_error(
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

    # Booster Parameters (if advanced parameters are enabled)
    # TODO: This is a wall of sliders; see if layout can be broken up somehow
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
                load_key("boosterToggle", id, False)
                useBoostersToggle = st.toggle(
                    "Enable Booster Vaccines",
                    value=False,
                    key=f"_boosterToggle{id}",
                    on_change=save_key,
                    args=["boosterToggle", id],
                    disabled=not useVaccinesToggle,
                    help="""
Toggle whether or not booster vaccines are
administered in the simulation, overriding other booster-related parameters.
                    """,
                )
                leftCol, rightCol = st.columns(2)
                load_key("boosterDoseCount", id, 3)
                boosterDoseCount = leftCol.slider(
                    "Number of Booster Doses",
                    1,
                    10,
                    3,
                    key=f"_boosterDoseCount{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=save_key,
                    args=["boosterDoseCount", id],
                    help="""
The number of times each individual in the
simulation will be administered a booster vaccine.
                    """,
                )
                load_key("boosterDelay", id, 3)
                boosterDelay = rightCol.slider(
                    "Time Between Booster Doses (Months)",
                    1,
                    12,
                    3,
                    disabled=not useVaccinesToggle
                    or not useBoostersToggle
                    or boosterDoseCount == 1,
                    on_change=save_key,
                    args=["boosterDelay", id],
                    key=f"_boosterDelay{id}",
                    help="""
The number of months after an individual receives
one booster vaccine dose before they are able
to receive another, where a month is 30 days.
                    """,
                )
                load_key("boosterDuration", id, 4)
                boosterDuration = leftCol.slider(
                    "Booster Immunity Waning Delay (Months)",
                    1,
                    12,
                    4,
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=save_key,
                    args=["boosterDuration", id],
                    key=f"_boosterDuration{id}",
                    help="""
The number of months after an individual receives a booster vaccine dose
before they begin losing their immunity, where a month is 30 days.
                    """,
                )
                load_key("boosterWaningRate", id, 6)
                rightCol.slider(
                    "Booster Waning Duration (Months)",
                    0,
                    12,
                    6,
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=save_key,
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
                param_error(
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
                load_key("boosterBaseEfficacy", id, 0.9)
                boosterBaseEfficacy = leftCol.slider(
                    "Initial Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    format="percent",
                    key=f"_boosterBaseEfficacy{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=save_key,
                    args=["boosterBaseEfficacy", id],
                    help="""
The initial efficacy of each booster vaccine,
represented as the probability that an
individual that has recently received the
booster will remain healthy when exposed to the pathogen.
                    """,
                )
                load_key("boosterWanedEfficacy", id, 0.6)
                boosterWanedEfficacy = rightCol.slider(
                    "Minimum Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.6,
                    format="percent",
                    key=f"_boosterWanedEfficacy{id}",
                    disabled=not useVaccinesToggle or not useBoostersToggle,
                    on_change=save_key,
                    args=["boosterWanedEfficacy", id],
                    help="""
The efficacy of a booster-vaccinated individual's immunity after the
full waning duration, represented as the probability that they will remain
healthy when exposed to the pathogen.
                        """,
                )

                # Show error if waned efficacy is above initial
                param_error(
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

                # Scale to 0-100 for form compatibility
                boostPercentBaseEfficacy = round(boosterBaseEfficacy * 100, 6)
                boostPercentWanedEfficacy = round(boosterWanedEfficacy * 100, 6)

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
                load_key(
                    "boostEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Initial Booster Efficacy": [boostPercentBaseEfficacy],
                            "Booster Efficacy After Waning": [
                                boostPercentWanedEfficacy
                            ],
                        },
                    ),
                    dataframe=True,
                )
                boostEfficacyAgeForm = st.data_editor(
                    session[f"boostEfficacyAgeForm{id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_boostEfficacyAgeForm{id}",
                    on_change=save_key,
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
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have specific booster vaccine efficacy values defined
for it, overriding the base efficacy value for booster vaccines.
                            """,
                        ),
                        "Initial Booster Efficacy": st.column_config.NumberColumn(
                            "Initial Booster Efficacy (Probability)",
                            required=True,
                            default=boostPercentBaseEfficacy,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The initial efficacy of each booster vaccine for this age group, represented
as the probability that a recently vaccinated individual in this age group
will remain healthy when exposed to the pathogen.
                            """,
                        ),
                        "Booster Efficacy After Waning": st.column_config.NumberColumn(
                            "Minimum Booster Efficacy (Probability)",
                            required=True,
                            default=boostPercentWanedEfficacy,
                            min_value=0.0,
                            max_value=99.999999,
                            format="%0.5g%%",
                            help="""
The efficacy of the immunity possessed by a booster-vaccinated individual in
this age group after the full waning duration, represented as the probability
that they will remain healthy when exposed to the pathogen.
                        """,
                        ),
                    },
                )
                param_error(
                    "boostEfficacyAgeFormDuplicates",
                    id,
                    lambda: has_duplicates(boostEfficacyAgeForm),
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
                param_error(
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
    # TODO: Reintegrate trigger thresholds when vaccines care about them


def vaccineSaveSchema(
    schema: Parameters,
    id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    includeDashboard: bool = False,
) -> bool:
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

        baseline (Parameters, optional): A Pydantic model representing the parameters
            set for the baseline scenario. When `id` is not 0, this will be used
            to omit parameters that are already set in the baseline from the final
            scenario.

        includeDashboard (bool): Set to `True` to include the dashboard-exclusive
            vaccine distribution parameter.

    Returns:
        bool: `True` if vaccines were used in the scenario, permitting
            direct vs. indirect protection calculations.
    """

    # TODO: Make code clearer (split up advanced section if needed)
    # TODO: Avoid saving default row values to schema (or loading them)

    # Load reused parameters immediately to save time
    vaccineToggle = id_get("vaccineToggle", id, False)
    multiDoseToggle = id_get("multiDoseToggle", id, False) if advanced else False
    waningToggle = id_get("vaccineWaningToggle", id, False) if advanced else False
    boosterToggle = id_get("boosterToggle", id, False) if advanced else False
    ageNames = list(AGE_GROUP_KEYS)
    simLength = session.get("cycle_count", 360) * 2
    initialProportion = round(id_get("initialVaccinated", id, 0.0) / 100, 6)
    targetProportion = round(id_get("targetVaccinated", id, 80.0) / 100, 6)
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        if vaccineToggle:
            # Vaccination Coverage
            liveDistribution = (
                False
                if not advanced
                else id_get("vaccineDistribution", id, "Static Proportions")
                == "Live Distribution"
            )
            if includeDashboard:
                dashboardParams = DashboardParameters()
                dashboardParams.live_vaccine_distribution = liveDistribution
                if id > 0 and baseline is not None:
                    schema_remove_baseline(
                        dashboardParams, baseline.Dashboard_Parameter
                    )
                schema_update(schema, "Dashboard_Parameter", dashboardParams)

            vacPropAgeForm = id_get(
                "vacPropAgeForm",
                id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Vaccinated Proportion": [initialProportion],
                        "Target Vaccinated Proportion": [targetProportion],
                    },
                ),
            ).copy()
            proportionCols = [
                "Initial Vaccinated Proportion",
                "Target Vaccinated Proportion",
            ]
            vacPropAgeForm[proportionCols] = (
                vacPropAgeForm[proportionCols].div(100.0).round(6)
            )
            # TODO: Scenario coverage with Age=None doesn't overwrite baseline coverage;
            # either add explicit entries for each age or modify the toolbox
            schema.Scenario_VaccineCoverage = [
                VaccineCoverage(
                    Age=None,
                    Initial=initialProportion,
                    Target=targetProportion if liveDistribution else initialProportion,
                )
            ] + [
                VaccineCoverage(
                    Age=age,
                    Initial=initial,
                    Target=target if liveDistribution else initial,
                )
                for age, initial, target in zip(
                    vacPropAgeForm["Age Group"],
                    vacPropAgeForm["Initial Vaccinated Proportion"],
                    vacPropAgeForm["Target Vaccinated Proportion"],
                )
                if age
            ]

            # Scenario Parameters
            scenarioParams = GeneralParameters()

            # TODO: See if these can be reintegrated onto the dashboard
            scenarioParams.vaccination_delay = 0
            scenarioParams.vaccination_duration = 2500
            scenarioParams.vaccination_trigger = TRIGGER_KEY_CONVERTER["Timed"]
            scenarioParams.vaccination_relaxation = TRIGGER_KEY_CONVERTER["Always"]

            # Ensure doses do not exceed the integer limit
            scenarioParams.vaccine_doses = (
                min(id_get("initialDoseReserve", id, 0), 2000000000)
                if liveDistribution and id_get("limitDosesToggle", id, False)
                else 99999999
            )
            scenarioParams.vaccination_first_dose_rate = (
                min(id_get("firstDoseRate", id, 300), 2000000000)
                if liveDistribution
                else 99999999
            )

            if id > 0 and baseline is not None:
                schema_remove_baseline(scenarioParams, baseline.Scenario_Parameter)
            schema_update(schema, "Scenario_Parameter", scenarioParams)

            # Vaccine Doses and Efficacy
            if multiDoseToggle:
                primDoseCount = id_get("primary_dose_count", id, 2)

                # Individual Dose Efficacy Parameters
                primBaseEfficacy = [
                    id_get("primaryBaseEfficacy", id, 0.5, f"-{i}")
                    for i in range(primDoseCount)
                ]
                # Waned is 0 if disabled since it doesn't matter
                primWanedEfficacy = (
                    id_get("primaryWanedEfficacy", id, 0.0) if waningToggle else 0.0
                )

                # Base Primary Efficacy Values
                efficacyParams = [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=primWanedEfficacy,
                        Efficacy=primBaseEfficacy,
                    )
                ]
                # Age-Specific Primary Efficacy Values
                vacInitialEfficacyAgeForms = [
                    id_get(
                        "vacInitialEfficacyAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [
                                    round(primBaseEfficacy[i] * 100, 6)
                                ],
                            },
                        ),
                        f"-{i}",
                    ).copy()
                    for i in range(primDoseCount)
                ]
                for form in vacInitialEfficacyAgeForms:
                    form["Initial Dose Efficacy"] = (
                        form["Initial Dose Efficacy"].div(100.0).round(6)
                    )
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
                vacWaneAgeForm = (
                    id_get(
                        "vacWaneAgeForm",
                        id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Dose Efficacy After Waning": [
                                    round(primWanedEfficacy * 100, 6)
                                ],
                            },
                        ),
                    )
                    .copy()
                    .dropna()
                )
                vacWaneAgeForm["Dose Efficacy After Waning"] = (
                    vacWaneAgeForm["Dose Efficacy After Waning"].div(100.0).round(6)
                )
                ageWaneDict.update(
                    vacWaneAgeForm.set_index("Age Group")[
                        "Dose Efficacy After Waning"
                    ].to_dict()
                )

                efficacyParams += [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=age,
                        Efficacy=ageInitialDict[age],
                        WanedEfficacy=ageWaneDict[age],
                    )
                    for age in ageNames
                    if ageInitialDict[age] != primBaseEfficacy
                    or ageWaneDict[age] != primWanedEfficacy
                ]

                # Dose Parameters
                primWaningDuration = id_get("primaryWaningRate", id, 12) * 60
                doseParams = [
                    VaccineDose(
                        DoseType="primary",
                        Count=primDoseCount,
                        DoseSpacingCycles=id_get("primaryDelay", id, 3) * 60,
                        WaningDelay=(
                            id_get("primaryDuration", id, 6) * 60
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
                singleEfficacy = id_get("primarySingleEfficacy", id, 0.5)
                singleWanedEfficacy = (
                    id_get("primaryWanedEfficacy", id, 0.0) if waningToggle else 0.0
                )
                singleEfficacyAgeForm = id_get(
                    "vacSingleEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [round(singleEfficacy * 100, 6)],
                            "Vaccine Efficacy After Waning": [
                                round(singleWanedEfficacy * 100, 6)
                            ],
                        },
                    ),
                ).copy()
                efficacyCols = ["Vaccine Efficacy", "Vaccine Efficacy After Waning"]
                singleEfficacyAgeForm[efficacyCols] = (
                    singleEfficacyAgeForm[efficacyCols].div(100.0).round(6)
                )

                efficacyParams = [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=singleWanedEfficacy,
                        Efficacy=[singleEfficacy],
                    )
                ] + [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=age,
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
                primWaningDuration = id_get("primaryWaningRate", id, 12) * 60
                doseParams = [
                    VaccineDose(
                        DoseType="primary",
                        Count=1,
                        DoseSpacingCycles=id_get("primaryDelay", id, 3) * 60,
                        WaningDelay=(
                            id_get("primaryDuration", id, 6) * 60
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
                boostBaseEfficacy = id_get("boosterBaseEfficacy", id, 0.9)
                boostWanedEfficacy = id_get("boosterWanedEfficacy", id, 0.6)
                boostEfficacyAgeForm = id_get(
                    "boostEfficacyAgeForm",
                    id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Initial Booster Efficacy": [
                                round(boostBaseEfficacy * 100, 6)
                            ],
                            "Booster Efficacy After Waning": [
                                round(boostWanedEfficacy * 100, 6)
                            ],
                        },
                    ),
                ).copy()
                boosterCols = [
                    "Initial Booster Efficacy",
                    "Booster Efficacy After Waning",
                ]
                boostEfficacyAgeForm[boosterCols] = (
                    boostEfficacyAgeForm[boosterCols].div(100.0).round(6)
                )
                efficacyParams += [
                    VaccineEfficacy(
                        DoseType="booster",
                        Age=None,
                        Efficacy=boostBaseEfficacy,
                        WanedEfficacy=boostWanedEfficacy,
                    )
                ] + [
                    VaccineEfficacy(
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

                boostWaningDuration = id_get("boosterWaningRate", id, 6) * 60
                doseParams += [
                    VaccineDose(
                        DoseType="booster",
                        Count=id_get("boosterDoseCount", id, 3),
                        DoseSpacingCycles=id_get("boosterDelay", id, 3) * 60,
                        WaningDelay=id_get("boosterDuration", id, 4) * 60,
                        WaningRatePerCycle=(
                            1.0
                            if boostWaningDuration == 0
                            else (boostBaseEfficacy - boostWanedEfficacy)
                            / boostWaningDuration
                        ),
                    )
                ]

            # Save efficacy and dose parameters
            # TODO: Rework baseline deduplication to make it feasible to do for vaccines
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


def vaccineLoadSchema(schema: Parameters, scenario_id: int = 0):
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
    schemaDash = schema.Dashboard_Parameter
    missingParams = (
        params is None for params in (schemaDose, schemaEfficacy, schemaCoverage)
    )
    if scenario_id == 0 and any(missingParams) and not all(missingParams):
        raise AssertionError("""
            Vaccination parameters were only partially defined
            for the baseline scenario
        """)

    # Dashboard Parameters
    if schemaDash is not None:
        liveDistribution = schemaDash.live_vaccine_distribution
        if liveDistribution is not None:
            update_param_from_schema(
                "vaccineDistribution",
                "Live Distribution" if liveDistribution else "Static Proportions",
                scenario_id,
            )
    elif scenario_id == 0:
        raise AssertionError("""
            Schema does not include vaccination distribution
            information for the baseline scenario
        """)
    else:
        liveDistribution = (
            id_get("vaccineDistribution", 0, "Static Proportions")
            == "Live Distribution"
        )

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
            baseInitial = (
                0.0
                if baseCoverage.Initial is None
                else round(baseCoverage.Initial * 100, 6)
            )
            update_param_from_schema("initialVaccinated", baseInitial, scenario_id)
            baseTarget = round(baseCoverage.Target * 100, 6)
            update_param_from_schema("targetVaccinated", baseTarget, scenario_id)
        elif scenario_id == 0:
            raise AssertionError("""
                Schema does not include general vaccine coverage
                proportions for the baseline scenario
            """)
        else:
            baseInitial = id_get("initialVaccinated", 0, 0.0)
            baseTarget = id_get("targetVaccinated", 0, 80.0)

        # Iterate over each coverage age
        for coverage in schemaCoverage:
            age, initial, target = coverage.Age, coverage.Initial, coverage.Target
            if age is not None:
                coverageTable.loc[coverageTable.shape[0]] = [
                    age,
                    baseInitial if initial is None else round(initial * 100, 6),
                    round(target * 100, 6),
                ]
        update_table_from_schema(
            "vacPropAgeForm",
            coverageTable,
            scenario_id,
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
    primary_dose_count = id_get("primary_dose_count", 0, 2)
    boosterDoseCount = id_get("boosterDoseCount", 0, 3)
    primaryRatePerCycle = id_get("primaryWaningRate", 0, 12)
    boosterRatePerCycle = id_get("boosterWaningRate", 0, 6)
    baseFull = [id_get("primaryBaseEfficacy", 0, 0.5, f"-{primary_dose_count - 1}")]
    baseWaned = id_get("primaryWanedEfficacy", 0, 0.0)
    baseBoostFull = id_get("boosterBaseEfficacy", 0, 0.9)
    baseBoostWaned = id_get("boosterWanedEfficacy", 0, 0.6)

    # Vaccine Dosage Parameters
    if schemaDose is not None:
        useVaccines = True

        # Primary vaccines
        if any(dose.DoseType == "primary" for dose in schemaDose):
            primary_dose = [dose for dose in schemaDose if dose.DoseType == "primary"][
                0
            ]
            primary_dose_count = primary_dose.Count
            useMultiDose = bool(primary_dose_count != 1)
            setDoseCount = True
            if useMultiDose:
                update_param_from_schema(
                    "primary_dose_count", primary_dose_count, scenario_id
                )
            update_param_from_schema(
                "primaryDelay", primary_dose.DoseSpacingCycles // 60, scenario_id
            )
            waningDelay = primary_dose.WaningDelay
            update_param_from_schema("primaryDuration", waningDelay // 60, scenario_id)
            # Efficacy needs to be logged so that waning rate per cycle
            # can be calculated
            primaryRatePerCycle = primary_dose.WaningRatePerCycle
            update_param_from_schema(
                "vaccineWaningToggle", bool(primaryRatePerCycle), scenario_id
            )
        elif scenario_id == 0:
            raise AssertionError("""
                Primary vaccine dose properties were not defined for the
                baseline scenario, despite booster properties being defined
            """)

        # Booster Vaccines
        if any(dose.DoseType == "booster" for dose in schemaDose):
            boosterDose = [dose for dose in schemaDose if dose.DoseType == "booster"][0]
            useBoosters = True
            boosterDoseCount = boosterDose.Count
            update_param_from_schema("boosterDoseCount", boosterDoseCount, scenario_id)
            update_param_from_schema(
                "boosterDelay", boosterDose.DoseSpacingCycles // 60, scenario_id
            )
            update_param_from_schema(
                "boosterDuration", boosterDose.WaningDelay // 60, scenario_id
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
            if setDoseCount and len(baseFull) != primary_dose_count:
                # Throw error if dose and efficacy disagree on dose count
                scenarioName = id_get(
                    "scenarioName", scenario_id, f"Scenario #{scenario_id}"
                )
                raise AssertionError(f"""
                    Vaccine dose count is inconsistent between dose and efficacy
                    parameters for the {
                        "baseline scenario"
                        if scenario_id == 0
                        else f"scenario named {scenarioName}"
                    }
                """)
            primary_dose_count = len(baseFull)
            useMultiDose = useMultiDose or primary_dose_count > 1
            update_param_from_schema("primarySingleEfficacy", baseFull[0], scenario_id)
            for index, value in enumerate(baseFull):
                update_param_from_schema(
                    "primaryBaseEfficacy", value, scenario_id, f"-{index}"
                )
            baseWaned = baseEfficacy.WanedEfficacy
            update_param_from_schema("primaryWanedEfficacy", baseWaned, scenario_id)
        elif scenario_id == 0:
            raise AssertionError("""
                Schema does not include general primary vaccine efficacy
                proportions for the baseline scenario
            """)
        else:
            baseFull = [
                id_get("primaryBaseEfficacy", 0, 0.5, f"-{i}")
                for i in range(primary_dose_count)
            ]
            baseWaned = id_get("primaryWanedEfficacy", 0, 0.0)

        # Iterate over each efficacy age
        primaryEfficacyTables = [
            pd.DataFrame(columns=("Age Group", "Initial Dose Efficacy"))
            for _ in range(primary_dose_count)
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
            if not table.empty:
                table["Initial Dose Efficacy"] = (
                    table["Initial Dose Efficacy"].mul(100.0).round(6)
                )
            update_table_from_schema(
                "vacInitialEfficacyAgeForm",
                table,
                scenario_id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Dose Efficacy": [round(baseFull[index] * 100, 6)],
                    },
                ),
                extra=f"-{index}",
            )
        if not primaryWanedTable.empty:
            primaryWanedTable["Dose Efficacy After Waning"] = (
                primaryWanedTable["Dose Efficacy After Waning"].mul(100.0).round(6)
            )
        update_table_from_schema(
            "vacWaneAgeForm",
            primaryWanedTable,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Dose Efficacy After Waning": [round(baseWaned * 100, 6)],
                },
            ),
        )
        if not primarySingleTable.empty:
            efficacyCols = [
                "Vaccine Efficacy",
                "Vaccine Efficacy After Waning",
            ]
            primarySingleTable[efficacyCols] = (
                primarySingleTable[efficacyCols].mul(100.0).round(6)
            )
        update_table_from_schema(
            "vacSingleEfficacyAgeForm",
            primarySingleTable,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Vaccine Efficacy": [round(baseFull[0] * 100, 6)],
                    "Vaccine Efficacy After Waning": [round(baseWaned * 100, 6)],
                },
            ),
        )

        # Booster Vaccines
        boosterEfficacySchema = [
            dose for dose in schemaEfficacy if dose.DoseType == "booster"
        ]
        if len(boosterEfficacySchema) > 0:
            if scenario_id == 0 and not useBoosters:
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
            baseBoostFull = baseBoostEfficacy.Efficacy
            assert not isinstance(baseBoostFull, list), "Booster efficacy was list"
            update_param_from_schema("boosterBaseEfficacy", baseBoostFull, scenario_id)
            baseBoostWaned = baseBoostEfficacy.WanedEfficacy
            update_param_from_schema(
                "boosterWanedEfficacy", baseBoostWaned, scenario_id
            )
        elif useBoosters and scenario_id == 0:
            raise AssertionError("""
                Schema does not include general booster vaccine efficacy
                proportions for the baseline scenario
            """)
        else:
            baseBoostFull = id_get("boosterBaseEfficacy", 0, 0.9)
            baseBoostWaned = id_get("boosterWanedEfficacy", 0, 0.6)

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
            assert not isinstance(base, list), "Booster efficacy was list"
            if age is not None:
                boosterEfficacyTable.loc[boosterEfficacyTable.shape[0]] = [
                    age,
                    base,
                    waned,
                ]
        if not boosterEfficacyTable.empty:
            boosterCols = [
                "Initial Booster Efficacy",
                "Booster Efficacy After Waning",
            ]
            boosterEfficacyTable[boosterCols] = (
                boosterEfficacyTable[boosterCols].mul(100.0).round(6)
            )
        update_table_from_schema(
            "boostEfficacyAgeForm",
            boosterEfficacyTable,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Initial Booster Efficacy": [round(baseBoostFull * 100, 6)],
                    "Booster Efficacy After Waning": [round(baseBoostWaned * 100, 6)],
                },
            ),
        )

    # Final Toggles
    # TODO: Ensure that toggles being disabled is distinguishable from
    # parameters being unchanged from baselines
    update_param_from_schema("vaccineToggle", useVaccines, scenario_id)
    update_param_from_schema("boosterToggle", useBoosters, scenario_id)
    update_param_from_schema("multiDoseToggle", useMultiDose, scenario_id)

    # Come back to waning duration since it needs both efficacy and dose
    if primaryRatePerCycle:
        update_param_from_schema(
            "primaryWaningRate",
            (
                0
                if primaryRatePerCycle == 1.0
                else (baseFull[-1] - baseWaned) // (primaryRatePerCycle * 60)
            ),
            scenario_id,
        )
    if boosterRatePerCycle:
        update_param_from_schema(
            "boosterWaningRate",
            (
                0
                if boosterRatePerCycle == 1.0
                else (baseBoostFull - baseBoostWaned) // (boosterRatePerCycle * 60)
            ),
            scenario_id,
        )

    # General Scenario Parameters
    # TODO: Make sure unset values are not used
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is not None:
        # TODO: Add other vaccine stuff if it's made configurable on the dashboard

        # Dose Rate
        if liveDistribution:
            firstDoseRate = schemaParameters.vaccination_first_dose_rate
            doseCount = schemaParameters.vaccine_doses
            if doseCount is not None:
                update_param_from_schema(
                    "limitDosesToggle", doseCount != 99999999, scenario_id
                )
                update_param_from_schema("initialDoseReserve", doseCount, scenario_id)
            if firstDoseRate is not None:
                update_param_from_schema("firstDoseRate", firstDoseRate, scenario_id)
