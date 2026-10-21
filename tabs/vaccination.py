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

from resources.constants import ORDINALS
from resources.interface import (
    age_display,
    param_error,
    schema_remove_baseline,
    schema_update,
)
from resources.model_schema import (
    DashboardParameters,
    GeneralParameters,
    Parameters,
    VaccineCoverage,
    VaccineDose,
    VaccineEfficacy,
)
from resources.parameter import (
    has_duplicates,
    id_get,
    load_key,
    replace_table_na,
    save_key,
    update_param_from_schema,
    update_table_from_schema,
)
from resources.types import AGE_GROUP_KEYS, TRIGGER_KEY_CONVERTER

# Logging
vaccine_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Ordering dictionary to ensure global values are checked first
AGE_ORDER = {
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


# TODO: See if the vaccination trigger parameters are fully working
# and reimplement them if they are
# @st.fragment
def build_vaccination_tab(scenario_id: int, advanced: bool = False):
    """
    Function to generate the parameters for vaccination in a
    specified container with scenario differentiation.

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables.

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
    load_key("vaccine_toggle", scenario_id, False)
    use_vaccines = st.toggle(
        "Enable Vaccines in Simulation",
        value=False,
        on_change=save_key,
        args=["vaccine_toggle", scenario_id],
        key=f"_vaccine_toggle{scenario_id}",
        help="""
Toggle whether or not individuals in the simulation will be vaccinated against
the pathogen.
        """,
    )

    # General Vaccination Policy Parameters
    # TODO: Vaccine Presets
    # st.html(f'<span id = "vaccination_trigger_condition{scenario_id}"></span>')
    with st.expander(
        "Vaccine Coverage",
        key=f"vaccine_coverage_container{scenario_id}",
        on_change="rerun",
    ) as coverage_container:
        if coverage_container.open:
            # Describe what sort of parameters are here
            st.markdown("""
These parameters control the rollout of vaccines in the simulation, with
parameters such as how frequently vaccines are administered and what proportion
of the population is already vaccinated.
            """)
            if advanced:
                load_key(
                    "vaccine_distribution", scenario_id, default="Static Proportions"
                )
                vaccine_distribution = st.radio(
                    "Vaccine Distribution",
                    options=["Static Proportions", "Live Distribution"],
                    captions=[
                        "Vaccination status will not change",
                        "New individuals will be vaccinated throughout the experiment",
                    ],
                    key=f"_vaccine_distribution{scenario_id}",
                    on_change=save_key,
                    args=["vaccine_distribution", scenario_id],
                    disabled=not use_vaccines,
                    help="""
Select how vaccines will be distributed throughout the population.
### Options:
- Static Proportions: A set proportion of the population will be vaccinated at
the beginning of the simulation, with no additional vaccinations being made.
This setting should be used for infections that are regularly vaccinated
against, such as influenza.
- Live Distribution: New individuals will be vaccinated throughout the duration
of the simulation experiment at a regular rate. This setting should be used for
recent infections where vaccines are either actively in development or not yet
widely distributed, such as SARS-CoV-2.
                    """,
                )
                static_vaccination = vaccine_distribution == "Static Proportions"
            else:
                static_vaccination = True

            # Vaccinated Proportions
            if static_vaccination:
                # Single vaccination proportion
                load_key("initial_vaccinated_population", scenario_id, 0.0)
                initial_vaccinated_population = st.number_input(
                    "Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_initial_vaccinated_population{scenario_id}",
                    on_change=save_key,
                    args=["initial_vaccinated_population", scenario_id],
                    disabled=not use_vaccines,
                    help="""
The percentage of the population that will be vaccinated against the pathogen.
                    """,
                )
                target_vaccinated_population = max(initial_vaccinated_population, 80.0)

            else:
                # Initial and target proportions
                left_column, right_column = st.columns(2)
                load_key("initial_vaccinated_population", scenario_id, 0.0)
                initial_vaccinated_population = left_column.number_input(
                    "Initial Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_initial_vaccinated_population{scenario_id}",
                    on_change=save_key,
                    args=["initial_vaccinated_population", scenario_id],
                    disabled=not use_vaccines,
                    help="""
The percentage of the population that will already be vaccinated against the
pathogen at the beginning of the simulation.
                    """,
                )
                load_key("target_vaccinated_population", scenario_id, 80.0)
                target_vaccinated_population = right_column.number_input(
                    "Target Vaccinated Population (% Percentage)",
                    min_value=0.0,
                    max_value=100.0,
                    value=80.0,
                    step=1.0,
                    format="%0.5g",
                    placeholder="Enter a percentage between 0 and 100",
                    key=f"_target_vaccinated_population{scenario_id}",
                    on_change=save_key,
                    args=["target_vaccinated_population", scenario_id],
                    disabled=not use_vaccines,
                    help="""
The percentage of the population that will be targeted by the vaccine schedule
in the simulation. The actual percentage that is vaccinated may be lower if
there are an insufficient number of doses available.
                    """,
                )

                # Show error if initial proportion is above target
                param_error(
                    "target_population_below_initial",
                    scenario_id,
                    lambda: use_vaccines
                    and initial_vaccinated_population > target_vaccinated_population,
                    f"""
Warning: The target vaccinated proportion of population in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {target_vaccinated_population:0.5g}% of the population, but the initial
vaccinated proportion is {initial_vaccinated_population:0.5g}%. As such, the
target proportion will already be met, and no new vaccinations will occur.

Please make one of the following changes:

- Increase Initial Vaccinated Population in :primary-badge[:material/vaccines: Vaccination]
to be greater than {target_vaccinated_population:0.5g}%.
- Decrease Target Vaccinated Population in :primary-badge[:material/vaccines: Vaccination]
to be lower than {initial_vaccinated_population:0.5g}%.
                    """,
                    False,
                )

                # Other live distribution parameters
                # TODO: Get data for a more accurate default
                load_key("first_dose_rate", scenario_id, 300)
                st.number_input(
                    "Vaccination Rate (Vaccinations per Day)",
                    min_value=1,
                    value=300,
                    key=f"_first_dose_rate{scenario_id}",
                    placeholder="Enter a whole number of people",
                    on_change=save_key,
                    args=["first_dose_rate", scenario_id],
                    disabled=not use_vaccines,
                    help="""
The number of unvaccinated individuals who will receive the first dose of the
vaccine each day.
                    """,
                )
                # Limited Dose Parameters (if advanced parameters are enabled)
                load_key("use_limited_doses", scenario_id, False)
                use_limited_doses = st.toggle(
                    "Enable Limited Number of Vaccine Doses",
                    value=False,
                    key=f"_use_limited_doses{scenario_id}",
                    disabled=not use_vaccines,
                    on_change=save_key,
                    args=["use_limited_doses", scenario_id],
                    help="""
Toggle whether the number of vaccine doses that can be administered in each
simulation should be limited, putting an upper limit on the number of
vaccinated individuals in the simulation.
                    """,
                )
                if use_limited_doses:
                    load_key("maximum_vaccine_doses", scenario_id, 0)
                    st.number_input(
                        "Total Number of Vaccine Doses",
                        min_value=0,
                        value=50000,
                        key=f"_maximum_vaccine_doses{scenario_id}",
                        disabled=not use_vaccines or not use_limited_doses,
                        on_change=save_key,
                        args=["maximum_vaccine_doses", scenario_id],
                        placeholder="Enter a whole number of doses",
                        help="""
The total number of vaccine doses that will be available in the simulation.
Once all doses have been administered, any remaining unvaccinated individuals
in the simulation will never be vaccinated.

Note that only the first dose of the vaccine counts towards this limit.
Individuals who have already received the first dose of the vaccine will still
receive future doses regardless of the remaining dose count.
                        """,
                    )

            # Modifiable-length field for age-specific vaccination
            st.markdown(
                "### Age-Specific Vaccinated Population",
                help="""
This table allows for unique vaccinated populations to be defined for
individual age groups in the simulation, overriding the global parameters
defined above.
                """,
            )
            if use_vaccines:
                st.markdown("Double-click a cell in this table to edit its value.")
            load_key(
                "vaccinated_population_form",
                scenario_id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Vaccinated Proportion": [
                            initial_vaccinated_population
                        ],
                        "Target Vaccinated Proportion": [target_vaccinated_population],
                    },
                ),
                dataframe=True,
            )
            # Set N/A values from hidden columns to the current default
            if not static_vaccination:
                session[f"vaccinated_population_form{scenario_id}"] = replace_table_na(
                    session[f"vaccinated_population_form{scenario_id}"],
                    {
                        "Target Vaccinated Proportion": max(
                            initial_vaccinated_population, target_vaccinated_population
                        ),
                    },
                )
            vaccinated_population_form = st.data_editor(
                session[f"vaccinated_population_form{scenario_id}"],
                height="content",
                num_rows="dynamic",
                key=f"_vaccinated_population_form{scenario_id}",
                on_change=save_key,
                args=["vaccinated_population_form", scenario_id],
                kwargs={"dataframe": True},
                disabled=not use_vaccines,
                placeholder=("Enter a value" if use_vaccines else "Disabled"),
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
                            if static_vaccination
                            else "Initial Vaccinated Population (%)"
                        ),
                        required=True,
                        default=initial_vaccinated_population,
                        min_value=0.0,
                        max_value=100.0,
                        format="%0.5g%%",
                        help=(
                            """
The percentage of individuals in this age group that will be vaccinated against
the pathogen.
                            """
                            if static_vaccination
                            else """
The percentage of individuals in this age group that will already be vaccinated
against the pathogen at the beginning of the simulation.
                            """
                        ),
                    ),
                    "Target Vaccinated Proportion": (
                        None
                        if static_vaccination
                        else st.column_config.NumberColumn(
                            "Target Vaccinated Population (%)",
                            required=True,
                            default=target_vaccinated_population,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The percentage of individuals in this age group that will be targeted by the
vaccine schedule in the simulation. The actual proportion of individuals that
are vaccinated may be lower if there are an insufficient number of doses
available.
                        """,
                        )
                    ),
                },
            )
            param_error(
                "vaccinated_population_duplicates",
                scenario_id,
                lambda: has_duplicates(vaccinated_population_form),
                f"""
Error: The age-specific vaccinated proportions form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Vaccinated Population
Parameters form in :primary-badge[:material/vaccines: Vaccination] that use the
same age group as another row.
                """,
                True,
            )
            # TODO: make data_editor error messages name the rows
            param_error(
                "age_target_population_below_initial",
                scenario_id,
                lambda: not static_vaccination
                and np.any(
                    vaccinated_population_form["Initial Vaccinated Proportion"]
                    > vaccinated_population_form["Target Vaccinated Proportion"]
                ),
                f"""
Error: The age-specific vaccinated proportions form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains rows where the initial vaccinated proportion is greater than the
target vaccinated proportion. As such, the target proportion will already be
met, and no new vaccinations will occur for the age groups specified by these
rows.

Please make one of the following changes:

- Remove all rows of the Age-Specific Vaccinated Population Parameters form in
:primary-badge[:material/vaccines: Vaccination] that have the initial
proportion higher than the target proportion.
- Decrease the Initial Vaccinated Population column in
:primary-badge[:material/vaccines: Vaccination] to always be lower than the
target proportion.
- Increase the Target Vaccinated Population column in
:primary-badge[:material/vaccines: Vaccination] to always be higher than the
initial proportion.
                """,
                True,
            )

    # Primary Vaccine Parameters
    with st.expander(
        "Vaccine-Derived Immunity",
        key=f"vaccine_immunity_container{scenario_id}",
        on_change="rerun",
    ) as vaccine_immunity_container:
        if vaccine_immunity_container.open:
            # Describe primary vaccines
            st.markdown("""
These parameters control the properties of the main schedule of vaccines that
will be administered to individuals within the simulation.
            """)

            # Single vs multi-dose vaccine
            if advanced:
                load_key("use_multiple_doses", scenario_id, False)
                use_multiple_doses = st.toggle(
                    "Multiple Vaccine Doses",
                    value=False,
                    on_change=save_key,
                    args=["use_multiple_doses", scenario_id],
                    key=f"_use_multiple_doses{scenario_id}",
                    help="""
Toggle whether vaccines in the simulation should require multiple doses for
each individual.
        """,
                )
            else:
                use_multiple_doses = False

            if use_multiple_doses:
                # Multiple doses
                load_key("primary_dose_count", scenario_id, 2)
                primary_dose_count = st.slider(
                    "Number of Vaccine Doses",
                    min_value=2,
                    max_value=5,
                    value=2,
                    key=f"_primary_dose_count{scenario_id}",
                    on_change=save_key,
                    args=["primary_dose_count", scenario_id],
                    disabled=not use_vaccines,
                    help="""
The number of times each individual in the simulation will be administered a
vaccine for the pathogen, excluding booster vaccines.
                    """,
                )
                load_key("time_between_primary_doses", scenario_id, 3)
                st.slider(
                    "Time Between Vaccine Doses (Months)",
                    min_value=1,
                    max_value=12,
                    value=3,
                    disabled=not use_vaccines,
                    on_change=save_key,
                    args=["time_between_primary_doses", scenario_id],
                    key=f"_time_between_primary_doses{scenario_id}",
                    help="""
The number of months after an individual receives a vaccine dose before they
are able to receive another, where a month is 30 days.
                    """,
                )

                # Waning parameters
                load_key("vaccine_waning_toggle", scenario_id, False)
                waning_toggle = st.toggle(
                    "Enable Vaccine-Derived Immunity Waning",
                    value=False,
                    on_change=save_key,
                    args=["vaccine_waning_toggle", scenario_id],
                    key=f"_vaccine_waning_toggle{scenario_id}",
                    help="""
Toggle whether or not immunity gained from being vaccinated will wane over
time. If this is enabled, individuals in the simulation can be infected if it
has been a sufficiently long time since they received their final vaccine dose.
                    """,
                )
                if waning_toggle:
                    load_key("primary_waning_delay", scenario_id, 6)
                    st.slider(
                        "Vaccine-Derived Immunity Waning Delay (Months)",
                        min_value=1,
                        max_value=12,
                        value=6,
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waning_delay", scenario_id],
                        key=f"_primary_waning_delay{scenario_id}",
                        help="""
The number of months after an individual receives their final vaccine dose
before they begin losing their immunity, where a month is 30 days.
                        """,
                    )
                    load_key("primary_waning_duration", scenario_id, 12)
                    st.slider(
                        "Vaccine Waning Duration (Months)",
                        min_value=1,
                        max_value=12,
                        value=6,
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waning_duration", scenario_id],
                        key=f"_primary_waning_duration{scenario_id}",
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

Here you can set the {"initial " if waning_toggle else ""}efficacy of each
vaccine dose in the schedule separately. Note that changing the "Number of
Vaccine Doses" parameter will affect how many sections are present here.
                """)
                for i in range(primary_dose_count):
                    with st.container(border=True):
                        st.markdown(f"#### {ORDINALS[i+1]} Vaccine Dose")
                        load_key("primary_initial_efficacy", scenario_id, 0.5, f"-{i}")
                        # Store efficacy between 0-100 for form compatibility
                        initial_dose_efficacy = round(
                            st.slider(
                                (
                                    "Initial Dose Efficacy (Probability)"
                                    if waning_toggle
                                    else "Dose Efficacy (Probability)"
                                ),
                                min_value=0.0,
                                max_value=1.0,
                                value=0.5,
                                format="percent",
                                disabled=not use_vaccines,
                                on_change=save_key,
                                args=["primary_initial_efficacy", scenario_id, f"-{i}"],
                                key=f"_primary_initial_efficacy{scenario_id}-{i}",
                                help=f"""
The {"initial " if waning_toggle else ""}efficacy of this vaccine dose,
represented as the probability that an individual that has received the dose
will remain healthy when exposed to the pathogen.
                            """,
                            )
                            * 100,
                            6,
                        )

                        # Age-Specific Primary Efficacy Field
                        st.markdown(
                            (
                                "##### Age-Specific Initial Efficacy"
                                if waning_toggle
                                else "##### Age-Specific Efficacy"
                            ),
                            help=f"""
This section allows unique {"initial " if waning_toggle else ""}efficacy values
for this dose to be defined for individual age groups in the simulation,
overriding the global efficacy value for this dose defined above.
                            """,
                        )
                        if use_vaccines:
                            st.markdown(
                                "Double-click a cell in this table to edit its value."
                            )
                        load_key(
                            "vaccine_initial_efficacy_age_form",
                            scenario_id,
                            pd.DataFrame(
                                {
                                    "Age Group": [None],
                                    "Initial Dose Efficacy": [initial_dose_efficacy],
                                },
                            ),
                            f"-{i}",
                            dataframe=True,
                        )
                        vaccine_initial_efficacy_age_form = st.data_editor(
                            session[
                                f"vaccine_initial_efficacy_age_form{scenario_id}-{i}"
                            ],
                            height="content",
                            num_rows="dynamic",
                            key=f"_vaccine_initial_efficacy_age_form{scenario_id}-{i}",
                            on_change=save_key,
                            args=[
                                "vaccine_initial_efficacy_age_form",
                                scenario_id,
                                f"-{i}",
                            ],
                            kwargs={"dataframe": True},
                            disabled=not use_vaccines,
                            placeholder=(
                                "Enter a value" if use_vaccines else "Disabled"
                            ),
                            column_config={
                                "Age Group": st.column_config.SelectboxColumn(
                                    "Age Group",
                                    required=True,
                                    options=AGE_GROUP_KEYS,
                                    format_func=age_display,
                                    help=f"""
An age group that will have a specific
{"initial " if waning_toggle else ""}efficacy value defined for this vaccine
dose, overriding the base value.
                                    """,
                                ),
                                "Initial Dose Efficacy": st.column_config.NumberColumn(
                                    (
                                        "Initial Dose Efficacy (Probability)"
                                        if waning_toggle
                                        else "Dose Efficacy (Probability)"
                                    ),
                                    required=True,
                                    default=initial_dose_efficacy,
                                    min_value=0.0,
                                    max_value=100.0,
                                    format="%0.5g%%",
                                    help=f"""
The {"initial " if waning_toggle else ""}efficacy of this vaccine dose for this
age group, represented as the probability that a vaccinated individual in this
age group will remain healthy when exposed to the pathogen.
                                    """,
                                ),
                            },
                        )
                        param_error(
                            f"vaccine_initial_efficacy_duplicates{i}",
                            scenario_id,
                            lambda: has_duplicates(vaccine_initial_efficacy_age_form),
                            f"""
Error: The age-specific {"initial" if waning_toggle else "dose"} efficacy form
used for the {ORDINALS[i+1].lower()} vaccine dose by the
{'baseline scenario' if scenario_id == 0 else f'scenario named "{session.scenario_names[scenario_id]}"'}
contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific
{"Initial " if waning_toggle else ""}Efficacy form in the {ORDINALS[i+1]}
Vaccine Dose section of :primary-badge[:material/vaccines: Vaccination] that
use the same age group as another row.
                            """,
                            True,
                        )

                # Efficacy After Waning
                if waning_toggle:
                    load_key("primary_waned_efficacy", scenario_id, 0.0)
                    primary_waned_efficacy = st.slider(
                        "Minimum Dose Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.0,
                        format="percent",
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waned_efficacy", scenario_id],
                        key=f"_primary_waned_efficacy{scenario_id}",
                        help="""
The efficacy of a vaccinated individual's immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                        """,
                    )
                    percent_waned_efficacy = round(primary_waned_efficacy * 100, 6)
                    # Last efficacy value is all that's cared about
                    # for error checking purposes
                    final_dose = primary_dose_count - 1
                    final_initial_efficacy = id_get(
                        "primary_initial_efficacy", scenario_id, 0.5, f"-{final_dose}"
                    )
                    param_error(
                        "waned_efficacy_above_initial",
                        scenario_id,
                        lambda: use_vaccines
                        and primary_waned_efficacy > final_initial_efficacy,
                        f"""
Error: The initial vaccine efficacy for the final vaccine dose in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {100 * final_initial_efficacy:0.3g}%, but the minimum efficacy is
{100 * primary_waned_efficacy:0.3g}%. As such, a vaccinated person's immunity
to the pathogen will get stronger over time instead of weaker.

Please make one of the following changes:

- Increase Initial Dose Efficacy for the final dose in :primary-badge[:material/vaccines: Vaccination]
to be greater than {100 * primary_waned_efficacy:0.3g}%.
- Decrease Minimum Dose Efficacy in :primary-badge[:material/vaccines: Vaccination]
to be lower than {100 * final_initial_efficacy:0.3g}%.
                        """,
                        True,
                    )

                    # Age-Specific Waned Efficacy Field
                    st.markdown(
                        "### Age-Specific Minimum Efficacy",
                        help="""
This table allows for unique minimum efficacy values to be defined for
individual age groups in the simulation, overriding the global waned efficacy
defined above.
                        """,
                    )
                    if use_vaccines:
                        st.markdown(
                            "Double-click a cell in this table to edit its value."
                        )
                    load_key(
                        "vaccine_waning_age_form",
                        scenario_id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Dose Efficacy After Waning": [percent_waned_efficacy],
                            },
                        ),
                        dataframe=True,
                    )
                    vaccine_waning_age_form = st.data_editor(
                        session[f"vaccine_waning_age_form{scenario_id}"],
                        height="content",
                        num_rows="dynamic",
                        key=f"_vaccine_waning_age_form{scenario_id}",
                        on_change=save_key,
                        args=["vaccine_waning_age_form", scenario_id],
                        kwargs={"dataframe": True},
                        disabled=not use_vaccines,
                        placeholder=("Enter a value" if use_vaccines else "Disabled"),
                        column_config={
                            "Age Group": st.column_config.SelectboxColumn(
                                "Age Group",
                                required=True,
                                options=AGE_GROUP_KEYS,
                                format_func=age_display,
                                help="""
An age group that will have a specific final efficacy value after immunity
waning defined for it, overriding the base value.
                                """,
                            ),
                            "Dose Efficacy After Waning": st.column_config.NumberColumn(
                                "Minimum Dose Efficacy (Probability)",
                                required=True,
                                default=percent_waned_efficacy,
                                min_value=0.0,
                                max_value=99.999999,
                                format="%0.5g%%",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age
group after the full waning duration, represented as the probability that they
will remain healthy when exposed to the pathogen.
                        """,
                            ),
                        },
                    )
                    param_error(
                        "vaccine_waning_duplicates",
                        scenario_id,
                        lambda: has_duplicates(vaccine_waning_age_form),
                        f"""
Error: The age-specific minimum efficacy form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Minimum Efficacy form in
the Vaccine-Derived Immunity section of :primary-badge[:material/vaccines: Vaccination]
that use the same age group as another row.
                        """,
                        True,
                    )
                    # TODO: Have these errors highlight specific ages
                    final_initial_efficacy_age_form = id_get(
                        "vaccine_initial_efficacy_age_form",
                        scenario_id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [
                                    round(
                                        id_get(
                                            "primary_initial_efficacy",
                                            scenario_id,
                                            0.5,
                                            f"-{final_dose}",
                                        )
                                        * 100,
                                        6,
                                    )
                                ],
                            },
                        ),
                        f"-{final_dose}",
                    )
                    combined_efficacies = pd.merge(
                        final_initial_efficacy_age_form,
                        vaccine_waning_age_form,
                        how="inner",
                        on="Age Group",
                    )
                    # TODO: make data_editor error messages name the row
                    # (and not break on dupes)
                    param_error(
                        "age_vaccine_waning_duplicates",
                        scenario_id,
                        lambda: np.any(
                            combined_efficacies["Initial Dose Efficacy"]
                            < combined_efficacies["Dose Efficacy After Waning"]
                        ),
                        f"""
Error: The vaccine age-specific efficacy forms used for the final vaccine dose
by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains rows where the initial vaccine efficacy is greater than the minimum
efficacy. As such, the immunity to the pathogen conferred by the vaccine will
get stronger over time instead of weaker for the age groups specified by these
rows.

Please modify the Age-Specific Initial Efficacy form for the final vaccine dose
alongside the Age-Specific Minimum Efficacy form in 
:primary-badge[:material/vaccines: Vaccination]
such that no age group has its initial efficacy lower than its waned efficacy.
                        """,
                        True,
                    )

            else:
                # Single-dose vaccines

                # Waning parameters (only if advanced parameters are enabled)
                if advanced:
                    load_key("vaccine_waning_toggle", scenario_id, False)
                    waning_toggle = st.toggle(
                        "Enable Vaccine-Derived Immunity Waning",
                        value=False,
                        on_change=save_key,
                        args=["vaccine_waning_toggle", scenario_id],
                        key=f"_vaccine_waning_toggle{scenario_id}",
                        help="""
Toggle whether or not immunity gained from being vaccinated will wane over
time. If this is enabled, individuals in the simulation can be infected if it
has been a sufficiently long time since they were vaccinated.
                        """,
                    )
                else:
                    waning_toggle = False

                # Vaccine Efficacy for All Doses
                load_key("primary_single_dose_initial_efficacy", scenario_id, 0.5)
                single_dose_initial_efficacy = st.slider(
                    f"{"Initial " if waning_toggle else ""}Vaccine Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    format="percent",
                    disabled=not use_vaccines,
                    on_change=save_key,
                    args=["primary_single_dose_initial_efficacy", scenario_id],
                    key=f"_primary_single_dose_initial_efficacy{scenario_id}",
                    help=f"""
The {"initial " if waning_toggle else ""}efficacy of the vaccine, represented
as the probability that an individual that has recently received a dose will
remain healthy when exposed to the pathogen.
                    """,
                )

                if waning_toggle:
                    load_key("primary_waned_efficacy", scenario_id, 0.0)
                    primary_waned_efficacy = st.slider(
                        "Minimum Vaccine Efficacy (Probability)",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.0,
                        format="percent",
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waned_efficacy", scenario_id],
                        key=f"_primary_waned_efficacy{scenario_id}",
                        help="""
The efficacy of a vaccinated individual's immunity after the full waning
duration, represented as the probability that they will remain healthy when
exposed to the pathogen.
                        """,
                    )
                    # TODO: Should disabling waning be a listed fix for the error?
                    param_error(
                        "single_waned_efficacy_above_initial",
                        scenario_id,
                        lambda: use_vaccines
                        and primary_waned_efficacy > single_dose_initial_efficacy,
                        f"""
Error: The initial vaccine efficacy in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {100 * single_dose_initial_efficacy:0.3g}%, but the efficacy after waning is
{100 * primary_waned_efficacy:0.3g}%. As such, a vaccinated person's immunity
to the pathogen will get stronger over time instead of weaker.

Please make one of the following changes:

- Increase Initial Vaccine Efficacy in :primary-badge[:material/vaccines: Vaccination]
to be greater than {100 * primary_waned_efficacy:0.3g}%.
- Decrease Minimum Vaccine Efficacy in :primary-badge[:material/vaccines: Vaccination]
to be lower than {100 * single_dose_initial_efficacy:0.3g}%.
                        """,
                        True,
                    )
                    load_key("primary_waning_delay", scenario_id, 6)
                    st.slider(
                        "Vaccine-Derived Immunity Waning Delay (Months)",
                        min_value=1,
                        max_value=12,
                        value=6,
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waning_delay", scenario_id],
                        key=f"_primary_waning_delay{scenario_id}",
                        help="""
The number of months after an individual receives the vaccine before they begin
losing their immunity, where a month is 30 days.
                        """,
                    )
                    load_key("primary_waning_duration", scenario_id, 12)
                    st.slider(
                        "Vaccine Waning Duration (Months)",
                        min_value=1,
                        max_value=12,
                        value=6,
                        disabled=not use_vaccines,
                        on_change=save_key,
                        args=["primary_waning_duration", scenario_id],
                        key=f"_primary_waning_duration{scenario_id}",
                        help="""
The number of months after a vaccinated individual begins losing their immunity
before their resistance to the pathogen reaches its lowest point, where a month
is 30 days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                        """,
                    )
                else:
                    primary_waned_efficacy = 0.0

                # Scale to 0-100 for form compatibility
                percent_single_dose_initial_efficacy = round(
                    single_dose_initial_efficacy * 100, 6
                )
                percent_waned_efficacy = round(primary_waned_efficacy * 100, 6)

                # Age-Specific Primary Efficacy Field
                st.markdown(
                    f"### Age-Specific Vaccine Efficacy",
                    help=f"""
This section allows unique vaccine efficacy values to be defined for individual
age groups in the simulation, overriding the efficacy defined above.
                    """,
                )
                if use_vaccines:
                    st.markdown("Double-click a cell in this table to edit its value.")

                load_key(
                    "single_vaccine_efficacy_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [percent_single_dose_initial_efficacy],
                            "Vaccine Efficacy After Waning": [percent_waned_efficacy],
                        },
                    ),
                    dataframe=True,
                )
                # Set N/A values from hidden columns to the current default
                if waning_toggle:
                    session[f"single_vaccine_efficacy_age_form{scenario_id}"] = (
                        replace_table_na(
                            session[f"single_vaccine_efficacy_age_form{scenario_id}"],
                            {"Vaccine Efficacy After Waning": percent_waned_efficacy},
                        )
                    )
                single_vaccine_efficacy_age_form = st.data_editor(
                    session[f"single_vaccine_efficacy_age_form{scenario_id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_single_vaccine_efficacy_age_form{scenario_id}",
                    on_change=save_key,
                    args=["single_vaccine_efficacy_age_form", scenario_id],
                    kwargs={"dataframe": True},
                    disabled=not use_vaccines,
                    placeholder=("Enter a value" if use_vaccines else "Disabled"),
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have a specific vaccine efficacy value defined for it,
overriding the base value.
                            """,
                        ),
                        "Vaccine Efficacy": st.column_config.NumberColumn(
                            f"{"Initial " if waning_toggle else ""}Vaccine Efficacy (Probability)",
                            required=True,
                            default=percent_single_dose_initial_efficacy,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help=f"""
The {"initial " if waning_toggle else ""}efficacy of each vaccine dose for this
age group, represented as the probability that a recently vaccinated individual
in this age group will remain healthy when exposed to the pathogen.
                            """,
                        ),
                        "Vaccine Efficacy After Waning": (
                            None
                            if not waning_toggle
                            else st.column_config.NumberColumn(
                                "Minimum Vaccine Efficacy (Probability)",
                                required=True,
                                default=percent_waned_efficacy,
                                min_value=0.0,
                                max_value=99.999999,
                                format="%0.5g%%",
                                help="""
The efficacy of the immunity possessed by a vaccinated individual in this age
group after the full waning duration, represented as the probability that they
will remain healthy when exposed to the pathogen.
                        """,
                            )
                        ),
                    },
                )
                param_error(
                    "single_vaccine_efficacy_duplicates",
                    scenario_id,
                    lambda: has_duplicates(single_vaccine_efficacy_age_form),
                    f"""
Error: The age-specific vaccine efficacy form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Vaccine Efficacy form in
:primary-badge[:material/vaccines: Vaccination] that use the same age group as
another row.
                    """,
                    True,
                )
                param_error(
                    "single_dose_waned_above_initial",
                    scenario_id,
                    lambda: waning_toggle
                    and np.any(
                        single_vaccine_efficacy_age_form["Vaccine Efficacy"]
                        < single_vaccine_efficacy_age_form[
                            "Vaccine Efficacy After Waning"
                        ]
                    ),
                    f"""
Error: The age-specific vaccine efficacy form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains rows where the minimum vaccine efficacy is greater than the initial
efficacy. As such, the immunity to the pathogen conferred by the vaccine will
get stronger over time instead of weaker for the age groups specified by these
rows.

Please make one of the following changes:

- Remove all rows of the Age-Specific Vaccine Efficacy form in
:primary-badge[:material/vaccines: Vaccination] that have the initial efficacy
lower than the minimum efficacy.
- Increase the Initial Vaccine Efficacy column in
:primary-badge[:material/vaccines: Vaccination] to always be higher than the
minimum efficacy.
- Decrease the Minimum Vaccine Efficacy column in
:primary-badge[:material/vaccines: Vaccination] to always be lower than the
initial efficacy.
                    """,
                    True,
                )

    # Booster Parameters (if advanced parameters are enabled)
    # TODO: This is a wall of sliders; see if layout can be broken up somehow
    if advanced:
        with st.expander(
            "Booster Vaccines",
            key=f"booster_vaccine_container{scenario_id}",
            on_change="rerun",
        ) as booster_vaccine_container:
            if booster_vaccine_container.open:
                # Describe booster vaccines
                st.markdown("""
These parameters control the properties of booster vaccines, additional doses
of a vaccine only administered to individuals who have already received all
vaccines in the initial schedule. Unlike the main vaccine doses defined above,
all booster vaccine doses share the same efficacy values. Booster vaccines are
primarily used with diseases like COVID-19, meningococcal disease and
diphtheria to preserve an individual's immunity to the pathogen as it wanes
over time.
                """)

                # Universal booster parameters
                load_key("booster_vaccine_toggle", scenario_id, False)
                use_booster_vaccines = st.toggle(
                    "Enable Booster Vaccines",
                    value=False,
                    key=f"_booster_vaccine_toggle{scenario_id}",
                    on_change=save_key,
                    args=["booster_vaccine_toggle", scenario_id],
                    disabled=not use_vaccines,
                    help="""
Toggle whether or not booster vaccines are administered in the simulation,
overriding other booster-related parameters.
                    """,
                )
                left_column, right_column = st.columns(2)
                load_key("booster_dose_count", scenario_id, 3)
                booster_dose_count = left_column.slider(
                    "Number of Booster Doses",
                    min_value=1,
                    max_value=10,
                    value=3,
                    key=f"_booster_dose_count{scenario_id}",
                    disabled=not use_vaccines or not use_booster_vaccines,
                    on_change=save_key,
                    args=["booster_dose_count", scenario_id],
                    help="""
The number of times each individual in the simulation will be administered a
booster vaccine.
                    """,
                )
                load_key("time_between_booster_doses", scenario_id, 3)
                time_between_booster_doses = right_column.slider(
                    "Time Between Booster Doses (Months)",
                    min_value=1,
                    max_value=12,
                    value=3,
                    disabled=not use_vaccines
                    or not use_booster_vaccines
                    or booster_dose_count == 1,
                    on_change=save_key,
                    args=["time_between_booster_doses", scenario_id],
                    key=f"_time_between_booster_doses{scenario_id}",
                    help="""
The number of months after an individual receives one booster vaccine dose
before they are able to receive another, where a month is 30 days.
                    """,
                )
                load_key("booster_waning_delay", scenario_id, 4)
                booster_waning_delay = left_column.slider(
                    "Booster Immunity Waning Delay (Months)",
                    min_value=1,
                    max_value=12,
                    value=4,
                    disabled=not use_vaccines or not use_booster_vaccines,
                    on_change=save_key,
                    args=["booster_waning_delay", scenario_id],
                    key=f"_booster_waning_delay{scenario_id}",
                    help="""
The number of months after an individual receives a booster vaccine dose before
they begin losing their immunity, where a month is 30 days.
                    """,
                )
                load_key("booster_waning_duration", scenario_id, 6)
                right_column.slider(
                    "Booster Waning Duration (Months)",
                    min_value=0,
                    max_value=12,
                    value=6,
                    disabled=not use_vaccines or not use_booster_vaccines,
                    on_change=save_key,
                    args=["booster_waning_duration", scenario_id],
                    key=f"_booster_waning_duration{scenario_id}",
                    help="""
The number of months after a booster-vaccinated individual begins losing their
immunity before their resistance to the pathogen reaches its lowest point,
where a month is 30 days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                        """,
                )
                param_error(
                    "booster_wanes_too_fast",
                    scenario_id,
                    lambda: use_vaccines
                    and use_booster_vaccines
                    and time_between_booster_doses > booster_waning_delay,
                    f"""
Error: The time between booster vaccine doses used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is longer than the time before a booster vaccine's efficacy begins to wane.
As such, the booster vaccines will begin waning before all doses have been
received.

Please make one of the following changes:

- Increase Booster Immunity Waning Delay in :primary-badge[:material/vaccines: Vaccination]
to be greater than {time_between_booster_doses}.
- Decrease Time Between Booster Doses in :primary-badge[:material/vaccines: Vaccination]
to be lower than {booster_waning_delay}.
                    """,
                    True,
                )
                load_key("booster_initial_efficacy", scenario_id, 0.9)
                booster_initial_efficacy = left_column.slider(
                    "Initial Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    format="percent",
                    key=f"_booster_initial_efficacy{scenario_id}",
                    disabled=not use_vaccines or not use_booster_vaccines,
                    on_change=save_key,
                    args=["booster_initial_efficacy", scenario_id],
                    help="""
The initial efficacy of each booster vaccine, represented as the probability
that an individual that has recently received the booster will remain healthy
when exposed to the pathogen.
                    """,
                )
                load_key("booster_waned_efficacy", scenario_id, 0.6)
                booster_waned_efficacy = right_column.slider(
                    "Minimum Booster Efficacy (Probability)",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.6,
                    format="percent",
                    key=f"_booster_waned_efficacy{scenario_id}",
                    disabled=not use_vaccines or not use_booster_vaccines,
                    on_change=save_key,
                    args=["booster_waned_efficacy", scenario_id],
                    help="""
The efficacy of a booster-vaccinated individual's immunity after the full
waning duration, represented as the probability that they will remain healthy
when exposed to the pathogen.
                        """,
                )

                # Show error if waned efficacy is above initial
                param_error(
                    "booster_waned_efficacy_above_initial",
                    scenario_id,
                    lambda: use_vaccines
                    and use_booster_vaccines
                    and booster_waned_efficacy > booster_initial_efficacy,
                    f"""
Error: The initial booster vaccine efficacy in the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} is {100 * booster_initial_efficacy:0.3g}%, but the minimum booster efficacy
is {100 * booster_waned_efficacy:0.3g}%. As such, a vaccinated person's
immunity to the pathogen will get stronger over time instead of weaker.

Please make one of the following changes:

- Increase Initial Booster Efficacy in :primary-badge[:material/vaccines: Vaccination]
to be greater than {100 * booster_waned_efficacy:0.3g}%.
- Decrease Minimum Booster Efficacy in :primary-badge[:material/vaccines: Vaccination]
to be lower than {100 * booster_initial_efficacy:0.3g}%.
                    """,
                    True,
                )

                # Scale to 0-100 for form compatibility
                booster_initial_percent = round(booster_initial_efficacy * 100, 6)
                booster_waned_percent = round(booster_waned_efficacy * 100, 6)

                # Modifiable-length field for age-specific efficacy
                st.markdown(
                    "### Age-Specific Booster Efficacy",
                    help="""
This table allows for unique booster efficacy values (both initial and minimum)
to be defined for individual age groups in the simulation, overriding the
global booster efficacy values defined above.
                    """,
                )
                if use_vaccines and use_booster_vaccines:
                    st.markdown("Double-click a cell in this table to edit its value.")
                load_key(
                    "booster_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Initial Booster Efficacy": [booster_initial_percent],
                            "Booster Efficacy After Waning": [booster_waned_percent],
                        },
                    ),
                    dataframe=True,
                )
                booster_age_form = st.data_editor(
                    session[f"booster_age_form{scenario_id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_booster_age_form{scenario_id}",
                    on_change=save_key,
                    args=["booster_age_form", scenario_id],
                    kwargs={"dataframe": True},
                    disabled=not use_vaccines or not use_booster_vaccines,
                    placeholder=(
                        "Enter a value"
                        if use_vaccines and use_booster_vaccines
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
                            default=booster_initial_percent,
                            min_value=0.0,
                            max_value=100.0,
                            format="%0.5g%%",
                            help="""
The initial efficacy of each booster vaccine for this age group, represented
as the probability that a recently vaccinated individual in this age group will
remain healthy when exposed to the pathogen.
                            """,
                        ),
                        "Booster Efficacy After Waning": st.column_config.NumberColumn(
                            "Minimum Booster Efficacy (Probability)",
                            required=True,
                            default=booster_waned_percent,
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
                    "booster_duplicates",
                    scenario_id,
                    lambda: has_duplicates(booster_age_form),
                    f"""
Error: The booster vaccine age-specific efficacy form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Booster Efficacy form in
:primary-badge[:material/vaccines: Vaccination] that use the same age group as
another row.
                    """,
                    True,
                )
                # TODO: make data_editor error messages name the row
                param_error(
                    "booster_age_waned_efficacy_above_initial",
                    scenario_id,
                    lambda: np.any(
                        booster_age_form["Initial Booster Efficacy"]
                        < booster_age_form["Booster Efficacy After Waning"]
                    ),
                    f"""
Error: The booster vaccine age-specific efficacy form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains rows where the initial booster efficacy is greater than the minimum
booster efficacy. As such, the immunity to the pathogen conferred by the
booster will get stronger over time instead of weaker for the age groups
specified by these rows.

Please make one of the following changes:

- Remove all rows of the Age-Specific Booster Efficacy form in
:primary-badge[:material/vaccines: Vaccination] that have the initial efficacy
higher than the efficacy after waning.
- Increase the Initial Booster Efficacy column in :primary-badge[:material/vaccines: Vaccination]
to always be higher than the efficacy after waning.
- Decrease the Minimum Booster Efficacy column in :primary-badge[:material/vaccines: Vaccination]
to always be lower than the initial efficacy.
                    """,
                    True,
                )
    # TODO: Reintegrate trigger thresholds when vaccines care about them


def vaccine_save_schema(
    schema: Parameters,
    scenario_id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    include_dashboard: bool = False,
) -> bool:
    """
    Function to populate the Pydantic model schema with vaccination parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to show more complex parameters like
            individual vaccine dose efficacies.

        baseline (Parameters, optional): A Pydantic model representing the
            parameters set for the baseline scenario. When `id` is not 0, this
            will be used to omit parameters that are already set in the
            baseline from the final scenario.

        include_dashboard (bool): Set to `True` to include the
            dashboard-exclusive vaccine distribution parameter.

    Returns:
        bool: `True` if vaccines were used in the scenario, permitting
            direct vs. indirect protection calculations.
    """

    # TODO: Make code clearer (split up advanced section if needed)
    # TODO: Avoid saving default row values to schema (or loading them)

    # Load reused parameters immediately to save time
    vaccine_toggle = id_get("vaccine_toggle", scenario_id, False)
    use_multiple_doses = (
        id_get("use_multiple_doses", scenario_id, False) if advanced else False
    )
    waning_toggle = (
        id_get("vaccine_waning_toggle", scenario_id, False) if advanced else False
    )
    booster_vaccine_toggle = (
        id_get("booster_vaccine_toggle", scenario_id, False) if advanced else False
    )
    age_names = list(AGE_GROUP_KEYS)
    sim_length = session.get("cycle_count", 360) * 2
    initial_vaccinated_proportion = round(
        id_get("initial_vaccinated_population", scenario_id, 0.0) / 100, 6
    )
    target_vaccinated_proportion = round(
        id_get("target_vaccinated_population", scenario_id, 80.0) / 100, 6
    )
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        if vaccine_toggle:
            # Vaccination Coverage
            use_live_distribution = (
                False
                if not advanced
                else id_get("vaccine_distribution", scenario_id, "Static Proportions")
                == "Live Distribution"
            )
            if include_dashboard:
                dashboard_params = DashboardParameters()
                dashboard_params.live_vaccine_distribution = use_live_distribution
                if scenario_id > 0 and baseline is not None:
                    schema_remove_baseline(
                        dashboard_params, baseline.Dashboard_Parameter
                    )
                schema_update(schema, "Dashboard_Parameter", dashboard_params)

            vaccinated_population_form = id_get(
                "vaccinated_population_form",
                scenario_id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Vaccinated Proportion": [
                            initial_vaccinated_proportion
                        ],
                        "Target Vaccinated Proportion": [target_vaccinated_proportion],
                    },
                ),
            ).copy()
            proportion_columns = [
                "Initial Vaccinated Proportion",
                "Target Vaccinated Proportion",
            ]
            vaccinated_population_form[proportion_columns] = (
                vaccinated_population_form[proportion_columns].div(100.0).round(6)
            )
            # TODO: Scenario coverage with Age=None doesn't overwrite baseline coverage;
            # either add explicit entries for each age or modify the toolbox
            schema.Scenario_VaccineCoverage = [
                VaccineCoverage(
                    Age=None,
                    Initial=initial_vaccinated_proportion,
                    Target=(
                        target_vaccinated_proportion
                        if use_live_distribution
                        else initial_vaccinated_proportion
                    ),
                )
            ] + [
                VaccineCoverage(
                    Age=age,
                    Initial=initial,
                    Target=target if use_live_distribution else initial,
                )
                for age, initial, target in zip(
                    vaccinated_population_form["Age Group"],
                    vaccinated_population_form["Initial Vaccinated Proportion"],
                    vaccinated_population_form["Target Vaccinated Proportion"],
                )
                if age
            ]

            # Scenario Parameters
            scenario_params = GeneralParameters()

            # TODO: See if these can be reintegrated onto the dashboard
            scenario_params.vaccination_delay = 0
            scenario_params.vaccination_duration = 2500
            scenario_params.vaccination_trigger = TRIGGER_KEY_CONVERTER["Timed"]
            scenario_params.vaccination_relaxation = TRIGGER_KEY_CONVERTER["Always"]

            # Ensure doses do not exceed the integer limit
            scenario_params.vaccine_doses = (
                min(id_get("maximum_vaccine_doses", scenario_id, 0), 2000000000)
                if use_live_distribution
                and id_get("use_limited_doses", scenario_id, False)
                else 99999999
            )
            scenario_params.vaccination_first_dose_rate = (
                min(id_get("first_dose_rate", scenario_id, 300), 2000000000)
                if use_live_distribution
                else 99999999
            )

            if scenario_id > 0 and baseline is not None:
                schema_remove_baseline(scenario_params, baseline.Scenario_Parameter)
            schema_update(schema, "Scenario_Parameter", scenario_params)

            # Vaccine Doses and Efficacy
            if use_multiple_doses:
                primary_dose_count = id_get("primary_dose_count", scenario_id, 2)

                # Individual Dose Efficacy Parameters
                primary_initial_efficacy = [
                    id_get("primary_initial_efficacy", scenario_id, 0.5, f"-{i}")
                    for i in range(primary_dose_count)
                ]
                # Waned is 0 if disabled since it doesn't matter
                primary_waned_efficacy = (
                    id_get("primary_waned_efficacy", scenario_id, 0.0)
                    if waning_toggle
                    else 0.0
                )

                # Base Primary Efficacy Values
                efficacy_params = [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=primary_waned_efficacy,
                        Efficacy=primary_initial_efficacy,
                    )
                ]
                # Age-Specific Primary Efficacy Values
                vaccine_initial_efficacy_age_forms = [
                    id_get(
                        "vaccine_initial_efficacy_age_form",
                        scenario_id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Initial Dose Efficacy": [
                                    round(primary_initial_efficacy[i] * 100, 6)
                                ],
                            },
                        ),
                        f"-{i}",
                    ).copy()
                    for i in range(primary_dose_count)
                ]
                for form in vaccine_initial_efficacy_age_forms:
                    form["Initial Dose Efficacy"] = (
                        form["Initial Dose Efficacy"].div(100.0).round(6)
                    )
                age_initial_efficacy = {
                    age: [
                        next(
                            iter(df["Initial Dose Efficacy"][df["Age Group"] == age]),
                            default,
                        )
                        for df, default in zip(
                            vaccine_initial_efficacy_age_forms, primary_initial_efficacy
                        )
                    ]
                    for age in age_names
                }
                age_waned_efficacy = {age: primary_waned_efficacy for age in age_names}
                vaccine_waning_age_form = (
                    id_get(
                        "vaccine_waning_age_form",
                        scenario_id,
                        pd.DataFrame(
                            {
                                "Age Group": [None],
                                "Dose Efficacy After Waning": [
                                    round(primary_waned_efficacy * 100, 6)
                                ],
                            },
                        ),
                    )
                    .copy()
                    .dropna()
                )
                vaccine_waning_age_form["Dose Efficacy After Waning"] = (
                    vaccine_waning_age_form["Dose Efficacy After Waning"]
                    .div(100.0)
                    .round(6)
                )
                age_waned_efficacy.update(
                    vaccine_waning_age_form.set_index("Age Group")[
                        "Dose Efficacy After Waning"
                    ].to_dict()
                )

                efficacy_params += [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=age,
                        Efficacy=age_initial_efficacy[age],
                        WanedEfficacy=age_waned_efficacy[age],
                    )
                    for age in age_names
                    if age_initial_efficacy[age] != primary_initial_efficacy
                    or age_waned_efficacy[age] != primary_waned_efficacy
                ]

                # Dose Parameters
                primary_waning_duration = (
                    id_get("primary_waning_duration", scenario_id, 12) * 60
                )
                dose_params = [
                    VaccineDose(
                        DoseType="primary",
                        Count=primary_dose_count,
                        DoseSpacingCycles=id_get(
                            "time_between_primary_doses", scenario_id, 3
                        )
                        * 60,
                        WaningDelay=(
                            id_get("primary_waning_delay", scenario_id, 6) * 60
                            if waning_toggle
                            else sim_length
                        ),
                        WaningRatePerCycle=(
                            0.0
                            if not waning_toggle
                            else (
                                1.0
                                if primary_waning_duration == 0
                                else (
                                    primary_initial_efficacy[-1]
                                    - primary_waned_efficacy
                                )
                                / primary_waning_duration
                            )
                        ),
                    )
                ]
            else:
                # Single Efficacy Parameters
                single_dose_initial_efficacy = id_get(
                    "primary_single_dose_initial_efficacy", scenario_id, 0.5
                )
                single_dose_waned_efficacy = (
                    id_get("primary_waned_efficacy", scenario_id, 0.0)
                    if waning_toggle
                    else 0.0
                )
                single_dose_efficacy_age_form = id_get(
                    "single_vaccine_efficacy_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Vaccine Efficacy": [
                                round(single_dose_initial_efficacy * 100, 6)
                            ],
                            "Vaccine Efficacy After Waning": [
                                round(single_dose_waned_efficacy * 100, 6)
                            ],
                        },
                    ),
                ).copy()
                efficacy_columns = ["Vaccine Efficacy", "Vaccine Efficacy After Waning"]
                single_dose_efficacy_age_form[efficacy_columns] = (
                    single_dose_efficacy_age_form[efficacy_columns].div(100.0).round(6)
                )

                efficacy_params = [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=None,
                        WanedEfficacy=single_dose_waned_efficacy,
                        Efficacy=[single_dose_initial_efficacy],
                    )
                ] + [
                    VaccineEfficacy(
                        DoseType="primary",
                        Age=age,
                        WanedEfficacy=waned if waning_toggle else 0.0,
                        Efficacy=[initial],
                    )
                    for age, initial, waned in zip(
                        single_dose_efficacy_age_form["Age Group"],
                        single_dose_efficacy_age_form["Vaccine Efficacy"],
                        single_dose_efficacy_age_form["Vaccine Efficacy After Waning"],
                    )
                    if age
                ]

                # Dose Parameters
                primary_waning_duration = (
                    id_get("primary_waning_duration", scenario_id, 12) * 60
                )
                dose_params = [
                    VaccineDose(
                        DoseType="primary",
                        Count=1,
                        DoseSpacingCycles=id_get(
                            "time_between_primary_doses", scenario_id, 3
                        )
                        * 60,
                        WaningDelay=(
                            id_get("primary_waning_delay", scenario_id, 6) * 60
                            if waning_toggle
                            else sim_length
                        ),
                        WaningRatePerCycle=(
                            0.0
                            if not waning_toggle
                            else (
                                1.0
                                if primary_waning_duration == 0
                                else (
                                    single_dose_initial_efficacy
                                    - single_dose_waned_efficacy
                                )
                                / primary_waning_duration
                            )
                        ),
                    )
                ]

            # Booster Efficacy Values
            if booster_vaccine_toggle:
                booster_initial_efficacy = id_get(
                    "booster_initial_efficacy", scenario_id, 0.9
                )
                booster_waned_efficacy = id_get(
                    "booster_waned_efficacy", scenario_id, 0.6
                )
                booster_age_form = id_get(
                    "booster_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Initial Booster Efficacy": [
                                round(booster_initial_efficacy * 100, 6)
                            ],
                            "Booster Efficacy After Waning": [
                                round(booster_waned_efficacy * 100, 6)
                            ],
                        },
                    ),
                ).copy()
                booster_columns = [
                    "Initial Booster Efficacy",
                    "Booster Efficacy After Waning",
                ]
                booster_age_form[booster_columns] = (
                    booster_age_form[booster_columns].div(100.0).round(6)
                )
                efficacy_params += [
                    VaccineEfficacy(
                        DoseType="booster",
                        Age=None,
                        Efficacy=booster_initial_efficacy,
                        WanedEfficacy=booster_waned_efficacy,
                    )
                ] + [
                    VaccineEfficacy(
                        DoseType="booster",
                        Age=age,
                        Efficacy=initial,
                        WanedEfficacy=waned,
                    )
                    for age, initial, waned in zip(
                        booster_age_form["Age Group"],
                        booster_age_form["Initial Booster Efficacy"],
                        booster_age_form["Booster Efficacy After Waning"],
                    )
                    if age
                ]

                booster_waning_duration = (
                    id_get("booster_waning_duration", scenario_id, 6) * 60
                )
                dose_params += [
                    VaccineDose(
                        DoseType="booster",
                        Count=id_get("booster_dose_count", scenario_id, 3),
                        DoseSpacingCycles=id_get(
                            "time_between_booster_doses", scenario_id, 3
                        )
                        * 60,
                        WaningDelay=id_get("booster_waning_delay", scenario_id, 4) * 60,
                        WaningRatePerCycle=(
                            1.0
                            if booster_waning_duration == 0
                            else (booster_initial_efficacy - booster_waned_efficacy)
                            / booster_waning_duration
                        ),
                    )
                ]

            # Save efficacy and dose parameters
            # TODO: Rework baseline deduplication to make it feasible to do for vaccines
            schema.Scenario_VaccineDoseEfficacy = efficacy_params
            schema.Scenario_VaccineDose = dose_params
    except (ValueError, ValidationError) as e:
        vaccine_log.error(
            f"[vaccine_save_schema] Encountered {type(e).__name__} while validating parameters for scenario {scenario_id}: {e}"
        )
        raise e
    return vaccine_toggle


def vaccine_load_schema(schema: Parameters, scenario_id: int = 0):
    """
    Function to read vaccination parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters
            in different instances of the tab by adding a number to the
            Streamlit session state variables. A value of 0 means that this is
            the baseline scenario and will be treated accordingly.
    """

    # Keep track of whether vaccines/boosters have showed up
    # TODO: Distinguish between scenario with vaccines disabled and
    # scenario with no changes to vaccines (only relevant once
    # scenarios are more efficient with less baseline duplication)
    use_vaccines, use_multiple_doses, use_boosters = False, False, False

    # Load vaccine parameters
    schema_dose = schema.Scenario_VaccineDose
    schema_efficacy = schema.Scenario_VaccineDoseEfficacy
    schema_coverage = schema.Scenario_VaccineCoverage
    schema_dashboard = schema.Dashboard_Parameter
    missing_parameters = (
        params is None for params in (schema_dose, schema_efficacy, schema_coverage)
    )
    if scenario_id == 0 and any(missing_parameters) and not all(missing_parameters):
        raise AssertionError(
            "Vaccination parameters were only partially "
            "defined for the baseline scenario"
        )

    # Dashboard Parameters
    if schema_dashboard is not None:
        use_live_distribution = schema_dashboard.live_vaccine_distribution
        if use_live_distribution is not None:
            update_param_from_schema(
                "vaccine_distribution",
                "Live Distribution" if use_live_distribution else "Static Proportions",
                scenario_id,
            )
    elif scenario_id == 0:
        raise AssertionError(
            "Schema does not include vaccination distribution "
            "information for the baseline scenario"
        )
    else:
        use_live_distribution = (
            id_get("vaccine_distribution", 0, "Static Proportions")
            == "Live Distribution"
        )

    # Vaccine Coverage Parameters
    if schema_coverage is not None:
        use_vaccines = True
        coverage_table = pd.DataFrame(
            columns=(
                "Age Group",
                "Initial Vaccinated Proportion",
                "Target Vaccinated Proportion",
            )
        )
        # Get the global values (age=None) first
        schema_coverage.sort(key=lambda x: AGE_ORDER.get(x.Age, 99))
        if len(schema_coverage) > 0 and schema_coverage[0].Age is None:
            baseline_coverage = schema_coverage.pop(0)
            baseline_initial_coverage = (
                0.0
                if baseline_coverage.Initial is None
                else round(baseline_coverage.Initial * 100, 6)
            )
            update_param_from_schema(
                "initial_vaccinated_population", baseline_initial_coverage, scenario_id
            )
            baseline_target_coverage = round(baseline_coverage.Target * 100, 6)
            update_param_from_schema(
                "target_vaccinated_population", baseline_target_coverage, scenario_id
            )
        elif scenario_id == 0:
            raise AssertionError(
                "Schema does not include general vaccine "
                "coverage proportions for the baseline scenario"
            )
        else:
            baseline_initial_coverage = id_get("initial_vaccinated_population", 0, 0.0)
            baseline_target_coverage = id_get("target_vaccinated_population", 0, 80.0)

        # Iterate over each coverage age
        for coverage in schema_coverage:
            age, initial, target = coverage.Age, coverage.Initial, coverage.Target
            if age is not None:
                coverage_table.loc[coverage_table.shape[0]] = [
                    age,
                    (
                        baseline_initial_coverage
                        if initial is None
                        else round(initial * 100, 6)
                    ),
                    round(target * 100, 6),
                ]
        update_table_from_schema(
            "vaccinated_population_form",
            coverage_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Initial Vaccinated Proportion": [baseline_initial_coverage],
                    "Target Vaccinated Proportion": [baseline_target_coverage],
                },
            ),
        )

    # Placeholders for attributes that may not be defined
    # TODO: See which of these can become None to avoid
    # propagating values not in the schema itself
    dose_count_defined = False
    primary_dose_count = id_get("primary_dose_count", 0, 2)
    booster_dose_count = id_get("booster_dose_count", 0, 3)
    primary_rate_per_cycle = id_get("primary_waning_duration", 0, 12)
    booster_rate_per_cycle = id_get("booster_waning_duration", 0, 6)
    initial_efficacies = [
        id_get("primary_initial_efficacy", 0, 0.5, f"-{primary_dose_count - 1}")
    ]
    waned_efficacy = id_get("primary_waned_efficacy", 0, 0.0)
    booster_initial_efficacy = id_get("booster_initial_efficacy", 0, 0.9)
    booster_waned_efficacy = id_get("booster_waned_efficacy", 0, 0.6)

    # Vaccine Dosage Parameters
    if schema_dose is not None:
        use_vaccines = True

        # Primary vaccines
        if any(dose.DoseType == "primary" for dose in schema_dose):
            primary_dose = [dose for dose in schema_dose if dose.DoseType == "primary"][
                0
            ]
            primary_dose_count = primary_dose.Count
            use_multiple_doses = bool(primary_dose_count != 1)
            dose_count_defined = True
            if use_multiple_doses:
                update_param_from_schema(
                    "primary_dose_count", primary_dose_count, scenario_id
                )
            update_param_from_schema(
                "time_between_primary_doses",
                primary_dose.DoseSpacingCycles // 60,
                scenario_id,
            )
            waning_delay = primary_dose.WaningDelay
            update_param_from_schema(
                "primary_waning_delay", waning_delay // 60, scenario_id
            )
            # Efficacy needs to be logged so that waning rate per cycle
            # can be calculated
            primary_rate_per_cycle = primary_dose.WaningRatePerCycle
            update_param_from_schema(
                "vaccine_waning_toggle", bool(primary_rate_per_cycle), scenario_id
            )
        elif scenario_id == 0:
            raise AssertionError(
                "Primary vaccine dose properties were not defined for the "
                "baseline scenario, despite booster properties being defined"
            )

        # Booster Vaccines
        if any(dose.DoseType == "booster" for dose in schema_dose):
            booster_dose = [dose for dose in schema_dose if dose.DoseType == "booster"][
                0
            ]
            use_boosters = True
            booster_dose_count = booster_dose.Count
            update_param_from_schema(
                "booster_dose_count", booster_dose_count, scenario_id
            )
            update_param_from_schema(
                "time_between_booster_doses",
                booster_dose.DoseSpacingCycles // 60,
                scenario_id,
            )
            update_param_from_schema(
                "booster_waning_delay", booster_dose.WaningDelay // 60, scenario_id
            )
            # Efficacy needs to be logged so that waning rate per cycle
            # can be calculated
            booster_rate_per_cycle = booster_dose.WaningRatePerCycle

    # Vaccine Efficacy Parameters
    if schema_efficacy is not None:
        use_vaccines = True

        # Primary Vaccines
        primary_efficacy_schema = [
            dose for dose in schema_efficacy if dose.DoseType == "primary"
        ]
        # Get the global values (age=None) first
        primary_efficacy_schema.sort(key=lambda x: AGE_ORDER.get(x.Age, 99))
        if len(primary_efficacy_schema) > 0 and primary_efficacy_schema[0].Age is None:
            global_efficacy = primary_efficacy_schema.pop(0)
            if not isinstance(global_efficacy.Efficacy, list):
                initial_efficacies = [global_efficacy.Efficacy]
            else:
                initial_efficacies = global_efficacy.Efficacy
            if dose_count_defined and len(initial_efficacies) != primary_dose_count:
                # Throw error if dose and efficacy disagree on dose count
                raise AssertionError(
                    "Vaccine dose count is inconsistent between "
                    "dose and efficacy parameters for the "
                    + (
                        "baseline scenario"
                        if scenario_id == 0
                        else f"scenario named {session.scenario_names[scenario_id]}"
                    )
                )
            primary_dose_count = len(initial_efficacies)
            use_multiple_doses = use_multiple_doses or primary_dose_count > 1
            update_param_from_schema(
                "primary_single_dose_initial_efficacy",
                initial_efficacies[0],
                scenario_id,
            )
            for index, value in enumerate(initial_efficacies):
                update_param_from_schema(
                    "primary_initial_efficacy", value, scenario_id, f"-{index}"
                )
            waned_efficacy = global_efficacy.WanedEfficacy
            update_param_from_schema(
                "primary_waned_efficacy", waned_efficacy, scenario_id
            )
        elif scenario_id == 0:
            raise AssertionError(
                "Schema does not include general primary vaccine "
                "efficacy proportions for the baseline scenario"
            )
        else:
            initial_efficacies = [
                id_get("primary_initial_efficacy", 0, 0.5, f"-{i}")
                for i in range(primary_dose_count)
            ]
            waned_efficacy = id_get("primary_waned_efficacy", 0, 0.0)

        # Iterate over each efficacy age
        primary_initial_efficacy_tables = [
            pd.DataFrame(columns=("Age Group", "Initial Dose Efficacy"))
            for _ in range(primary_dose_count)
        ]
        primary_waned_efficacy_tables = pd.DataFrame(
            columns=("Age Group", "Dose Efficacy After Waning")
        )
        primary_single_efficacy_table = pd.DataFrame(
            columns=("Age Group", "Vaccine Efficacy", "Vaccine Efficacy After Waning")
        )
        for prim in primary_efficacy_schema:
            age, base, waned = prim.Age, prim.Efficacy, prim.WanedEfficacy
            if not isinstance(base, list):
                base = [base]
            # Assume correct number of efficacies are used
            # since the schema should error before now otherwise
            if age is not None:
                if waned != waned_efficacy:
                    primary_waned_efficacy_tables.loc[
                        primary_waned_efficacy_tables.shape[0]
                    ] = [age, waned]
                    primary_single_efficacy_table.loc[
                        primary_single_efficacy_table.shape[0]
                    ] = [age, base[0], waned]
                elif base[0] != initial_efficacies[0]:
                    # Use first dose for single table
                    primary_single_efficacy_table.loc[
                        primary_single_efficacy_table.shape[0]
                    ] = [age, base[0], waned]
                for index, value in enumerate(base):
                    if value != initial_efficacies[index]:
                        current_table = primary_initial_efficacy_tables[index]
                        current_table.loc[current_table.shape[0]] = [age, value]

        # Save the tables
        for index, table in enumerate(primary_initial_efficacy_tables):
            if not table.empty:
                table["Initial Dose Efficacy"] = (
                    table["Initial Dose Efficacy"].mul(100.0).round(6)
                )
            update_table_from_schema(
                "vaccine_initial_efficacy_age_form",
                table,
                scenario_id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Initial Dose Efficacy": [
                            round(initial_efficacies[index] * 100, 6)
                        ],
                    },
                ),
                extra=f"-{index}",
            )
        if not primary_waned_efficacy_tables.empty:
            primary_waned_efficacy_tables["Dose Efficacy After Waning"] = (
                primary_waned_efficacy_tables["Dose Efficacy After Waning"]
                .mul(100.0)
                .round(6)
            )
        update_table_from_schema(
            "vaccine_waning_age_form",
            primary_waned_efficacy_tables,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Dose Efficacy After Waning": [round(waned_efficacy * 100, 6)],
                },
            ),
        )
        if not primary_single_efficacy_table.empty:
            efficacy_columns = [
                "Vaccine Efficacy",
                "Vaccine Efficacy After Waning",
            ]
            primary_single_efficacy_table[efficacy_columns] = (
                primary_single_efficacy_table[efficacy_columns].mul(100.0).round(6)
            )
        update_table_from_schema(
            "single_vaccine_efficacy_age_form",
            primary_single_efficacy_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Vaccine Efficacy": [round(initial_efficacies[0] * 100, 6)],
                    "Vaccine Efficacy After Waning": [round(waned_efficacy * 100, 6)],
                },
            ),
        )

        # Booster Vaccines
        booster_efficacy_schema = [
            dose for dose in schema_efficacy if dose.DoseType == "booster"
        ]
        if len(booster_efficacy_schema) > 0:
            if scenario_id == 0 and not use_boosters:
                # Throw error if baseline has efficacy params but no dose params
                raise AssertionError(
                    "Booster vaccine parameters were only "
                    "partially defined for the baseline scenario"
                )
            use_boosters = True
        # Get the global values (age=None) first
        booster_efficacy_schema.sort(key=lambda x: AGE_ORDER.get(x.Age, 99))
        if len(booster_efficacy_schema) > 0 and booster_efficacy_schema[0].Age is None:
            global_booster_efficacy = booster_efficacy_schema.pop(0)
            booster_initial_efficacy = global_booster_efficacy.Efficacy
            assert not isinstance(
                booster_initial_efficacy, list
            ), "Booster efficacy was list"
            update_param_from_schema(
                "booster_initial_efficacy", booster_initial_efficacy, scenario_id
            )
            booster_waned_efficacy = global_booster_efficacy.WanedEfficacy
            update_param_from_schema(
                "booster_waned_efficacy", booster_waned_efficacy, scenario_id
            )
        elif use_boosters and scenario_id == 0:
            raise AssertionError(
                "Schema does not include general booster vaccine "
                "efficacy proportions for the baseline scenario"
            )
        else:
            booster_initial_efficacy = id_get("booster_initial_efficacy", 0, 0.9)
            booster_waned_efficacy = id_get("booster_waned_efficacy", 0, 0.6)

        # Iterate over each efficacy age
        booster_efficacy_table = pd.DataFrame(
            columns=(
                "Age Group",
                "Initial Booster Efficacy",
                "Booster Efficacy After Waning",
            )
        )
        for boost in booster_efficacy_schema:
            age, base, waned = boost.Age, boost.Efficacy, boost.WanedEfficacy
            assert not isinstance(base, list), "Booster efficacy was list"
            if age is not None:
                booster_efficacy_table.loc[booster_efficacy_table.shape[0]] = [
                    age,
                    base,
                    waned,
                ]
        if not booster_efficacy_table.empty:
            booster_columns = [
                "Initial Booster Efficacy",
                "Booster Efficacy After Waning",
            ]
            booster_efficacy_table[booster_columns] = (
                booster_efficacy_table[booster_columns].mul(100.0).round(6)
            )
        update_table_from_schema(
            "booster_age_form",
            booster_efficacy_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Initial Booster Efficacy": [
                        round(booster_initial_efficacy * 100, 6)
                    ],
                    "Booster Efficacy After Waning": [
                        round(booster_waned_efficacy * 100, 6)
                    ],
                },
            ),
        )

    # Final Toggles
    # TODO: Ensure that toggles being disabled is distinguishable from
    # parameters being unchanged from baselines
    update_param_from_schema("vaccine_toggle", use_vaccines, scenario_id)
    update_param_from_schema("booster_vaccine_toggle", use_boosters, scenario_id)
    update_param_from_schema("use_multiple_doses", use_multiple_doses, scenario_id)

    # Come back to waning duration since it needs both efficacy and dose
    if primary_rate_per_cycle:
        update_param_from_schema(
            "primary_waning_duration",
            (
                0
                if primary_rate_per_cycle == 1.0
                else (initial_efficacies[-1] - waned_efficacy)
                // (primary_rate_per_cycle * 60)
            ),
            scenario_id,
        )
    if booster_rate_per_cycle:
        update_param_from_schema(
            "booster_waning_duration",
            (
                0
                if booster_rate_per_cycle == 1.0
                else (booster_initial_efficacy - booster_waned_efficacy)
                // (booster_rate_per_cycle * 60)
            ),
            scenario_id,
        )

    # General Scenario Parameters
    # TODO: Make sure unset values are not used
    schema_parameters = schema.Scenario_Parameter
    if schema_parameters is not None:
        # TODO: Add other vaccine stuff if it's made configurable on the dashboard

        # Dose Rate
        if use_live_distribution:
            first_dose_rate = schema_parameters.vaccination_first_dose_rate
            dose_count = schema_parameters.vaccine_doses
            if dose_count is not None:
                update_param_from_schema(
                    "use_limited_doses", dose_count != 99999999, scenario_id
                )
                update_param_from_schema(
                    "maximum_vaccine_doses", dose_count, scenario_id
                )
            if first_dose_rate is not None:
                update_param_from_schema(
                    "first_dose_rate", first_dose_rate, scenario_id
                )
