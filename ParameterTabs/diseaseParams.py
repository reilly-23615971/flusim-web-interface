# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where disease parameters can be modified

# Imports
import logging
from typing import Any, Optional, cast

import altair as alt
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    age_display,
    age_sort,
    age_sort_series,
    background_colour,
    day_count,
    dual_error,
    param_error,
    plural,
    schema_remove_baseline,
    schema_update,
)
from ClientResources.ModelSchema import (
    AllAgesParameters,
    DashboardParameters,
    GeneralParameters,
    Parameters,
    PatchParameters,
    StrainParameters,
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
    AGE_KEY_CONVERTER,
    COMMUNITIES,
    AgeGroupKey,
)

# Logging
disease_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# @st.fragment
def build_disease_tab(scenario_id: int, advanced: bool = False):
    """
    Function to generate the parameters for the pathogen in a specified
    container with scenario differentiation

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables.

        advanced (bool): Set to True to show more complex parameters like
            location-specific transmission modifiers.
    """
    # Tab Content
    st.header("Pathogen-Related Parameters")
    st.markdown("""
This tab contains parameters relating to the pathogen itself, including the
rate of infectious individuals entering the modelled community, the rate at
which the pathogen spreads and how long infection lasts before recovery.
    """)

    # Transmission Parameters
    with st.expander(
        "Infection Transmission",
        key=f"transmission_container{scenario_id}",
        on_change="rerun",
    ) as transmission_container:
        if transmission_container.open:
            st.markdown("""
These parameters control the likelihood that the pathogen will spread when an
infected individual interacts with others.

The probability that an interaction between an infected individual $I_i$ and a
healthy individual $I_s$ with no immunity to the disease will result in the
infection of $I_s$ is calculated with the following formula
[[1](https://www.doi.org/10.1371/journal.pone.0004005)]:

$$
P_{trans}(I_i, I_s) = 1 - \\exp{(-\\beta \\times sym(I_i) \\times inf(I_i)
\\times susc(I_s) \\times \\kappa)}
$$

In this formula:
- $\\beta$ is the basic transmission probability, which determines the
likelihood that any interaction with a healthy individual will result in a new
infection. It is analogous to the basic reproduction number ($R_0$), acting as
a representation of how often an infected individual will spread the disease to
others.
- $sym(I_i)$ is equal to 1 when the infected individual is showing symptoms of
the infection, but reduces the likelihood of infection if they are not showing
symptoms. Common respiratory infection symptoms like sneezing and coughing are
effective in spreading the infection to others, so individuals who do not
display these symptoms will be less likely to transmit the infection.
- $inf(I_i)$ is infectiousness, which modifies the likelihood of infection
based on how old the infected individual is. People of different ages may be
more or less likely to spread the disease; for instance, young children may
have less concern for hygiene, resulting in them spreading the infection more
often.
- $susc(I_s)$ is susceptibility, which modifies the likelihood of infection
based on how old the healthy individual is. A person's age may affect how
likely they are to catch the infection from others; for instance, seniors often
have weaker immune systems that make them more likely to be infected.
- $\\kappa$ modifies the likelihood of infection based on whether the
interaction takes place in a household, school, workplace or other location.
The location of interactions may affect the probability of transmission; for
instance, infections typically spread more often in households since they are
more enclosed than other locations.
            """)
            # TODO: Mention that kappa changes are advanced-only?

            # Beta and symptom multipliers
            # Previous default for beta was 0.11
            load_key("beta", scenario_id, 0.0616)
            st.number_input(
                "Basic Transmission Parameter (β)",
                min_value=0.00001,
                max_value=1.0,
                value=0.0616,
                step=0.001,
                format="%0.5g",
                key=f"_beta{scenario_id}",
                on_change=save_key,
                args=["beta", scenario_id],
                help="""
The value of the basic transmission parameter $\\beta$, the base probability of
a person being infected when interacting with someone who is already infected.
The higher this value is, the more likely it is for uninfected individuals to
contract the pathogen in any interaction with infected individuals.
                """,
            )
            left_column, right_column = st.columns(2)
            load_key("beta_asymptomatic", scenario_id, 0.55)
            left_column.number_input(
                "Asymptomatic Transmission ($sym(I_i)$)",
                min_value=0.00001,
                max_value=1.0,
                value=0.55,
                step=0.01,
                format="%0.5g",
                on_change=save_key,
                args=["beta_asymptomatic", scenario_id],
                key=f"_beta_asymptomatic{scenario_id}",
                help="""
The value of the transmissibility modifier $sym(I_i)$ when the infected
individual in an interaction ($I_i$) is asymptomatic (i.e. has not shown any
symptoms of the pathogen despite being infectious). This applies to both
individuals who are too early in the pathogen's lifespan to show symptoms as
well as individuals who never show symptoms throughout their infectious period.
The lower this value is, the less likely it is for uninfected individuals to
contract the pathogen when interacting with asymptomatic individuals.
                """,
            )
            load_key("beta_post_symptomatic", scenario_id, 0.55)
            right_column.number_input(
                "Post-Symptomatic Transmission ($sym(I_i)$)",
                min_value=0.00001,
                max_value=1.0,
                value=0.55,
                step=0.01,
                format="%0.5g",
                on_change=save_key,
                args=["beta_post_symptomatic", scenario_id],
                key=f"_beta_post_symptomatic{scenario_id}",
                help="""
The value of the transmissibility modifier $sym(I_i)$ when the infected
individual in an interaction ($I_i$) is post-symptomatic (i.e. previously
showed symptoms of the pathogen, but no longer does). The lower this value is,
the less likely it is for uninfected individuals to contract the pathogen when
interacting with post-symptomatic individuals.
                """,
            )
            # Transmission multipliers (only if advanced params are enabled)
            if advanced:
                load_key("school_kappa", scenario_id, 1.0)
                left_column.number_input(
                    "School Transmission ($\\kappa$)",
                    min_value=0.00001,
                    max_value=10.0,
                    value=1.0,
                    step=0.01,
                    format="%0.5g",
                    key=f"_school_kappa{scenario_id}",
                    on_change=save_key,
                    args=["school_kappa", scenario_id],
                    help="""
The value of the transmissibility modifier $\\kappa$ when an interaction takes
place in a school. The higher this value is, the more likely it is for
uninfected individuals to contract the pathogen when interacting with infected
individuals in schools.
                    """,
                )
                load_key("work_kappa", scenario_id, 1.0)
                right_column.number_input(
                    "Workplace Transmission ($\\kappa$)",
                    min_value=0.00001,
                    max_value=10.0,
                    value=1.0,
                    step=0.01,
                    format="%0.5g",
                    key=f"_work_kappa{scenario_id}",
                    on_change=save_key,
                    args=["work_kappa", scenario_id],
                    help="""
The value of the transmissibility modifier $\\kappa$ when an interaction takes
place in a workplace. The higher this value is, the more likely it is for
uninfected individuals to contract the pathogen when interacting with infected
individuals in workplaces.
                    """,
                )
                load_key("household_kappa", scenario_id, 2.2)
                left_column.number_input(
                    "Household Transmission ($\\kappa$)",
                    min_value=0.00001,
                    max_value=10.0,
                    value=2.2,
                    step=0.01,
                    format="%0.5g",
                    key=f"_household_kappa{scenario_id}",
                    on_change=save_key,
                    args=["household_kappa", scenario_id],
                    help="""
The value of the transmissibility modifier $\\kappa$ when an interaction takes
place in a household. The higher this value is, the more likely it is for
uninfected individuals to contract the pathogen when interacting with infected
individuals in households.
                    """,
                )
                load_key("background_kappa", scenario_id, 1.0)
                right_column.number_input(
                    "Background Contact Transmission ($\\kappa$)",
                    min_value=0.00001,
                    max_value=10.0,
                    value=1.0,
                    step=0.01,
                    format="%0.5g",
                    key=f"_background_kappa{scenario_id}",
                    on_change=save_key,
                    args=["background_kappa", scenario_id],
                    help="""
The value of the transmissibility modifier $\\kappa$ when an interaction takes
place outside of the previous 3 locations (during the simulation's background
phase). The higher this value is, the more likely it is for uninfected
individuals to contract the pathogen during the background phase.
                    """,
                )

            # Dataframe for age-based transmissibility modifiers
            st.markdown(
                "### Age-Specific Infectiousness/Susceptibility",
                help="""
This table allows for unique values of $inf(I_i)$ and $susc(I_s)$ to be defined
for each age group, modifying the probability of infection for interactions
involving individuals in said age groups. These parameters will assume a
default value of 1 (i.e. no change in probability) if they are not specified
for a specific age group.
                """,
            )
            st.markdown("""
Double-click a cell in this table to edit its value. Note that any ages not
added to this form will use values of $inf(I_i)$ and $susc(I_s)$ equal to 1.
            """)
            load_key(
                "transmission_age_form",
                scenario_id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Infectiousness": [1.0],
                        "Susceptibility": [1.0],
                    },
                ),
                dataframe=True,
            )
            transmission_age_form = st.data_editor(
                session[f"transmission_age_form{scenario_id}"],
                height="content",
                num_rows="dynamic",
                key=f"_transmission_age_form{scenario_id}",
                on_change=save_key,
                args=["transmission_age_form", scenario_id],
                kwargs={"dataframe": True},
                placeholder="Enter a value",
                column_config={
                    "Age Group": st.column_config.SelectboxColumn(
                        "Age Group",
                        required=True,
                        options=AGE_GROUP_KEYS,
                        format_func=age_display,
                        help="""
The age group whose infectiousness and susceptibility will be modified.
                        """,
                    ),
                    "Infectiousness": st.column_config.NumberColumn(
                        "Infectiousness (inf(I\u1d62))",
                        required=True,
                        default=1.0,
                        min_value=0.0,
                        help="""
The value of the infectiousness parameter $inf(I_i)$ when the infected
individual in an interaction ($I_i$) is a member of this age group. The lower
this value is, the less likely it is for uninfected individuals to contract
the pathogen when interacting with infected individuals in this age group.
                        """,
                    ),
                    "Susceptibility": st.column_config.NumberColumn(
                        "Susceptibility (susc(I\u209b))",
                        required=True,
                        default=1.0,
                        min_value=0.0,
                        help="""
The value of the susceptibility parameter $susc(I_s)$ when the uninfected
individual in an interaction ($I_s$) is a member of this age group. The lower
this value is, the less likely it is for uninfected individuals in this age
group to contract the pathogen when interacting with infected individuals.
                        """,
                    ),
                },
            )
            param_error(
                "transmission_duplicates",
                scenario_id,
                lambda: has_duplicates(transmission_age_form),
                f"""
Error: The age-specific infectiousness/susceptibility form used by the {
    'baseline scenario' if scenario_id == 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Infectiousness/Susceptibility
form in :primary-badge[:material/coronavirus: Pathogen] that use the same age
group as another row.
                """,
                True,
            )

    # Life Cycle Parameters
    with st.expander(
        "Infection Life Cycle",
        key=f"life_cycle_container{scenario_id}",
        on_change="rerun",
    ) as life_cycle_container:
        if life_cycle_container.open:
            # Describe what sort of parameters are here
            st.markdown("""
These parameters control the pathogen's life cycle, including how long
individuals are infectious for and the likelihood of developing symptoms.
            """)

            # Duration Parameters
            st.subheader("Infection Life Stages", divider="grey")
            st.markdown("""
When an individual in the simulation is infected with a pathogen, the infection
does not remain static; it progresses through multiple life stages that affect
its transmissibility before the individual recovers. The pathogen in the
simulation has 5 distinct stages in its life cycle:

1. Latent: The pathogen is still developing in the body of the infected
individual; they do not show symptoms and cannot spread the pathogen.
2. Pre-Symptomatic: The pathogen has developed further and the infected
individual can now spread the pathogen to others, but they still do not show
any symptoms and thus have a reduced transmission rate.
3. Symptomatic: The infected individual has begun showing symptoms, resulting
in a high transmission rate and allowing them to be diagnosed with the pathogen.
4. Post-Symptomatic: The infected individual's condition has improved enough
that they no longer show symptoms of the pathogen, but they can still spread
the infection at a reduced transmission rate.
5. Recovered: The individual has recovered from the pathogen and can no longer
spread the infection.

The following parameters configure the length of each stage in the pathogen's
life cycle.
            """)
            load_key("latency_period", scenario_id, 0.5)
            # Previous default was 10
            latency_period = st.slider(
                "Latent Period Length (Days)",
                min_value=0.0,
                max_value=14.0,
                value=0.5,
                step=0.5,
                format="%f Day(s)",
                on_change=save_key,
                args=["latency_period", scenario_id],
                key=f"_latency_period{scenario_id}",
                help="""
The length in days of the pathogen's latent period, i.e. the length of time
between a person initially being infected by the pathogen and becoming
infectious themselves.
                """,
            )
            load_key("pre_symptom_period", scenario_id, 1.0)
            # Previous default was 2
            pre_symptom_period = st.slider(
                "Pre-Symptomatic Period Length (Days)",
                min_value=0.0,
                max_value=14.0,
                value=1.0,
                step=0.5,
                format="%f Day(s)",
                key=f"_pre_symptom_period{scenario_id}",
                on_change=save_key,
                args=["pre_symptom_period", scenario_id],
                help="""
The length in days of the pathogen's pre-symptomatic period, i.e. the length of
time between a person becoming infectious and beginning to show symptoms.
                """,
            )
            load_key("symptom_period", scenario_id, 2.0)
            # Previous default was 7
            symptom_period = st.slider(
                "Symptomatic Period Length (Days)",
                min_value=0.0,
                max_value=14.0,
                value=2.0,
                step=0.5,
                format="%f Day(s)",
                on_change=save_key,
                args=["symptom_period", scenario_id],
                key=f"_symptom_period{scenario_id}",
                help="""
The length in days of the pathogen's symptomatic period, i.e. the length of
time during which an infected individual will show symptoms of the pathogen.
                """,
            )
            load_key("post_symptom_period", scenario_id, 2.5)
            # Previous default was 1
            post_symptom_period = st.slider(
                "Post-Symptomatic Period Length (Days)",
                min_value=0.0,
                max_value=14.0,
                value=2.5,
                step=0.5,
                format="%f Day(s)",
                key=f"_post_symptom_period{scenario_id}",
                on_change=save_key,
                args=["post_symptom_period", scenario_id],
                help="""
The length in days of the pathogen's post-symptomatic period, i.e. the length
of time between a person ceasing to show symptoms of the pathogen and being
fully recovered/no longer infectious.
                """,
            )
            dual_error(
                "no_infectious_period",
                scenario_id,
                lambda: pre_symptom_period + symptom_period + post_symptom_period == 0,
                lambda: symptom_period == 0,
                f"""
Error: The infection life cycle used by the {
    'baseline scenario' if scenario_id== 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} has pre-symptomatic, symptomatic and post-symptomatic periods all set to have
a length of 0 days. As such, there is no point where the pathogen is
infectious, and it cannot spread.

Please increase either Pre-Symptomatic Period Length, Symptomatic Period Length
or Post-Symptomatic Period Length in
:primary-badge[:material/coronavirus: Pathogen] to be greater than 0.
                """,
                f"""
Warning: The infection life cycle used by the {
    'baseline scenario' if scenario_id== 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} has its symptomatic period set to have a length of 0 days. As such, there is
no point where the pathogen shows symptoms.

Please increase Symptomatic Period Length in
:primary-badge[:material/coronavirus: Pathogen] to be greater than 0.
                """,
            )

            # Display duration lengths via Cool Bar Graph Thing (tm)
            stage_names = [
                "Latent",
                "Pre-Symptomatic",
                "Symptomatic",
                "Post-Symptomatic",
            ]
            stage_data = pd.DataFrame(
                {
                    "Life Stage": stage_names,
                    "Length (Days)": [
                        latency_period,
                        pre_symptom_period,
                        symptom_period,
                        post_symptom_period,
                    ],
                }
            )
            # Filter out zero values and define chart values
            stage_data = stage_data[stage_data["Length (Days)"] > 0].reset_index(
                drop=True
            )
            stage_data["end"] = stage_data["Length (Days)"].cumsum()
            stage_data["start"] = stage_data["end"].shift(fill_value=0)
            stage_data["tooltip"] = (
                stage_data["Life Stage"]
                + ": "
                + stage_data["Length (Days)"].astype(str)
            )
            chart = (
                alt.Chart(stage_data, title="Current Infection Life Cycle")
                .mark_bar(size=30, stroke=background_colour(), strokeWidth=1)
                .encode(
                    x=alt.X(
                        "start:Q",
                        title="Length (Days)",
                        axis=alt.Axis(format=".1~f", tickMinStep=0.5),
                        scale=alt.Scale(
                            domain=[
                                0,
                                (
                                    latency_period
                                    + pre_symptom_period
                                    + symptom_period
                                    + post_symptom_period
                                ),
                            ]
                        ),
                    ),
                    x2="end:Q",
                    y=alt.value(0),
                    color=alt.Color(
                        "Life Stage:N",
                        sort=stage_names,
                        scale=alt.Scale(
                            scheme="inferno", domain=list(stage_data["Life Stage"])
                        ),
                    ),
                    tooltip=["Life Stage", "Length (Days)"],
                )
                .properties(width="container", height=205)
            )
            st.altair_chart(chart)

            # Written period lengths
            st.markdown("""
In addition to these life stages, the infection's life cycle may also be
described using the following time periods:
            """)
            total_column, incubation_column, infectious_column = st.columns(3)
            total_column.metric(
                "Total Length of Infection",
                day_count(
                    latency_period
                    + pre_symptom_period
                    + symptom_period
                    + post_symptom_period
                ),
                delta_description="from infection to recovery",
                help="""
The length in days of the pathogen's total lifespan, i.e. the length of time
between a person initially being infected by the pathogen and said person being
fully recovered/no longer infectious.
                """,
            )
            incubation_column.metric(
                "Incubation Period",
                day_count(latency_period + pre_symptom_period),
                delta_description="from infection to symptoms",
                help="""
The length in days of the pathogen's incubation period, i.e. the length of time
between a person being infected and beginning to show symptoms.
                """,
            )
            infectious_column.metric(
                "Infectious Period",
                day_count(pre_symptom_period + symptom_period + post_symptom_period),
                delta_description="where others may be infected",
                help="""
The length in days of the pathogen's infectious period, i.e. the length of time
during which an infected individual is capable of spreading the pathogen to others.
                """,
            )

            # Asymptomatic params (age-separated if advanced params are enabled)
            st.subheader("Asymptomatic Likelihood", divider="grey")
            st.markdown("""
Whenever an individual is infected with the pathogen, there is a chance that
their infection will be asymptomatic. An asymptomatic infection lasts for the
same amount of time as a regular infection, but the infected individual will
never show symptoms. Since an asymptomatic individual can still spread the
infection (albeit at a reduced transmission rate due to the lack of symptoms),
this allows the pathogen to continue spreading even when symptomatic
individuals take steps to avoid spreading the disease.
            """)
            if advanced:
                load_key("asymptomatic_child", scenario_id, 0.35)
                st.slider(
                    "Probability of Young (0-24) Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=save_key,
                    args=["asymptomatic_child", scenario_id],
                    key=f"_asymptomatic_child{scenario_id}",
                    help="""
The probability that an infected young person (less than 24 years old) in the
simulation will be asymptomatic (i.e. they never show any symptoms of the
pathogen despite being infectious).
                    """,
                )
                load_key("asymptomatic_adult", scenario_id, 0.35)
                st.slider(
                    "Probability of Adult (24+) Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=save_key,
                    args=["asymptomatic_adult", scenario_id],
                    key=f"_asymptomatic_adult{scenario_id}",
                    help="""
The probability that an infected adult (over 24 years old) in the simulation
will be asymptomatic (i.e. they never show any symptoms of the pathogen despite
being infectious).
                    """,
                )
            else:
                load_key("asymptomatic_adult", scenario_id, 0.35)
                st.slider(
                    "Probability of Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=save_key,
                    args=["asymptomatic_adult", scenario_id],
                    key=f"_asymptomatic_adult{scenario_id}",
                    help="""
The probability that an infected individual in the simulation will be
asymptomatic (i.e. they never show any symptoms of the pathogen despite being
infectious).
                    """,
                )

    # Seeding Parameters
    sim_length = session.get("cycle_count", 360)
    with st.expander(
        "Infection Seeding", key=f"seeding_container{scenario_id}", on_change="rerun"
    ) as seeding_container:
        if seeding_container.open:
            st.markdown("""
These parameters control how infected individuals are directly seeded into the
community. When a simulation experiment begins, everyone within the simulation
is healthy. Infection seeding is used to kickstart the spread of the pathogen
by randomly selecting individuals to infect. The process of infection seeding
represents the introduction of infected individuals from outside the population
(e.g. tourists). Additionally, the random nature of infection seeding
introduces stochasticity into the model and allows for variance between
different experiment runs using the same parameters.
        
During each cycle of the simulation (i.e. twice per day) within the specified
seeding period, infection seeding will directly infect a number of people equal
to the seeding rate. If the seeding rate is a decimal, the number of infections
is chosen randomly each cycle such that it averages out to the desired rate.
            """)
            load_key("seeding_rate", scenario_id, 0.25)
            # TODO: Elaborate on decimal seeding rate mechanics?
            st.slider(
                "Infection Seeding Rate (Average Individuals per Cycle)",
                min_value=0.05,
                max_value=5.0,
                value=0.25,
                step=0.05,
                key=f"_seeding_rate{scenario_id}",
                on_change=save_key,
                args=["seeding_rate", scenario_id],
                format="%0.4g",
                help="""
The average number of individuals that will be infected directly via infection
seeding each cycle. Note that each day of the simulation is 2 cycles.

If this number is a decimal, the simulation will randomly decide between the
two closest integers every cycle such that the average number of people seeded
is the desired rate. For instance, if the seeding rate is 3.2, the simulation
will infect 3 people 80% of the time and 4 people 20% of the time.
                """,
            )
            load_key("seeding_period", scenario_id, (1, 30))
            st.slider(
                "Infection Seeding Time Period (Days)",
                min_value=1,
                max_value=sim_length,
                value=(1, 30),
                format="Day %i",
                on_change=dynamic_scale_change,
                args=[
                    "seeding_period",
                    "seed_rate_dynamic_form",
                    "Infection Seeding Time Period",
                    scenario_id,
                ],
                key=f"_seeding_period{scenario_id}",
                help="""
The time period during which infection seeding will occur in the simulation.
The first value is the day on which seeding will begin (where Day 1 is the
first day of the simulation), and the second value is the day on which it will
stop.

Note that if you modify this value, the update points for infection seeding
defined in :primary-badge[:material/manage_history: Dynamic] may have their
values altered. For instance, if you go from seeding ending on Day 60 to Day
30, an update point set to affect the value on Day 45 will be changed to affect
it on Day 30 instead.
                """,
            )
            # Patch-Specific Seeding
            if advanced:
                community = COMMUNITIES[session.get("community", "newcastle")]
                patches = community.patches
                st.markdown("""
### Location-Specific Infection Seeding

This table allows for different locations in the simulated community to be
seeded with infections more frequently. The higher a location's seeding weight
is, the more likely it is that seeded infections will target an individual in
that location.
                """)
                st.markdown("Double-click a cell in this table to edit its value.")
                load_key(
                    "seeding_patch_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Location": [None],
                            "Seeding Weight": [1.0],
                        },
                    ),
                    dataframe=True,
                )
                # TODO: Reset this when community changes (and warn the user)
                seeding_patch_form = st.data_editor(
                    session[f"seeding_patch_form{scenario_id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_seeding_patch_form{scenario_id}",
                    on_change=save_key,
                    args=["seeding_patch_form", scenario_id],
                    kwargs={"dataframe": True},
                    placeholder="Enter a value",
                    column_config={
                        "Location": st.column_config.SelectboxColumn(
                            "Location",
                            required=True,
                            options=patches,
                            help=f"""
A location within the simulated community (currently {community.name}).
                            """,
                        ),
                        "Seeding Weight": st.column_config.NumberColumn(
                            "Seeding Weight",
                            required=True,
                            default=1.0,
                            min_value=0.0,
                            max_value=100.0,
                            format="localized",
                            help="""
The relative likelihood of infections being seeded into individuals in this
location. Higher values will result in infections being seeded here more often
(e.g. setting this to 2.0 will make this location be seeded into twice as often
as other locations) and vice versa. If this is set to 0, no infections will
ever be seeded into individuals in this location (though they may still
contract the infection via contact with individuals in other locations)
                            """,
                        ),
                    },
                )
                param_error(
                    "seeding_duplicates",
                    scenario_id,
                    lambda: has_duplicates(seeding_patch_form, column="Location"),
                    f"""
Error: The location-specific infection seeding form used by the {
    'baseline scenario' if scenario_id== 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate location rows. Each location should only be used in a
single row of the form.

Please remove or change any rows of the Location-Specific Infection Seeding
form in :primary-badge[:material/coronavirus: Pathogen] that use the same age
group as another row.
                    """,
                    True,
                )

    # Health Burden Outcome Parameters
    with st.expander(
        "Health Burden Outcomes",
        key=f"health_burden_container{scenario_id}",
        on_change="rerun",
    ) as burden_container:
        if burden_container.open:
            st.markdown("""
These parameters control how likely different health burden outcomes are to
occur as a result of the pathogen. Health burden outcomes are adverse
consequences that may result from an infection, such as hospitalisation or
death. These outcomes are not simulated directly, but are calculated using the
infection counts obtained once the simulation is complete. Generally, each
health burden outcome follows from the previous outcomes; of all individuals
who are diagnosed, only a subset of them will be hospitalised, and only a
subset of those who are hospitalised will die. Only symptomatic infections can
result in health burden outcomes.
        
The health burden outcomes that the dashboard can simulate are as follows:

1. Diagnosis: The individual has been formally diagnosed with the pathogen. Not
all individuals who show symptoms will be diagnosed, since some people will not
mention their infection to any sources that record infection data.

2. GP Visits: The individual has consulted their general practitioner (GP)
regarding the symptoms of the infection.

3. Hospitalisation: The individual has been admitted to a hospital as a result
of the infection.

4. ICU Visits: The individual has been admitted to the Intensive Care Unit
(ICU) of a hospital.

5. Mortality: The individual has died as a direct result of the infection.
            """)
            st.info(
                """
Note that due to the difference in scale between these health burden outcomes,
their occurrence rates are represented in different ways: 

- Diagnosis and GP Visits are represented as percentages of the infected,
symptomatic population.
- Hospitalisations and Mortality are represented as the number of occurrences
for every 100,000 infected, symptomatic individuals in the population.
- ICU Visits are represented as percentages of the hospitalised population.
                """,
                icon=":material/decimal_increase:",
            )

            # Health Burden Outcomes
            # TODO: Can the percents be turned into sliders?
            left_column, right_column = st.columns(2)
            load_key("case_ratio", scenario_id, 50.0)
            left_column.number_input(
                "Diagnosis Rate (% Percentage of Cases)",
                min_value=0.0,
                max_value=100.0,
                value=50.0,
                step=1.0,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_case_ratio{scenario_id}",
                on_change=save_key,
                args=["case_ratio", scenario_id],
                help="""
The percentage of infected, symptomatic individuals who will be formally
diagnosed as a confirmed case of the pathogen.
                """,
            )
            load_key("gp_ratio", scenario_id, 17.0)
            right_column.number_input(
                "GP Visit Rate (% Percentage of Cases)",
                min_value=0.0,
                max_value=100.0,
                value=17.0,
                step=1.0,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_gp_ratio{scenario_id}",
                on_change=save_key,
                args=["gp_ratio", scenario_id],
                help="""
The percentage of infected, symptomatic individuals who will visit their
general practitioner (GP) as a result of the pathogen.
                """,
            )
            load_key("hospital_ratio", scenario_id, 320.0)
            hospital_rate = left_column.number_input(
                "Hospitalisation Rate (per 100,000 Cases)",
                min_value=0.0,
                max_value=100000.0,
                value=320.0,
                step=1.0,
                format="%0.5g",
                placeholder="Enter a number between 0 and 100000",
                key=f"_hospital_ratio{scenario_id}",
                on_change=save_key,
                args=["hospital_ratio", scenario_id],
                help="""
The average number of infected individuals who will be admitted to a hospital
for every 100,000 symptomatic cases of the pathogen.
                """,
            )
            load_key("icu_ratio", scenario_id, 20.0)
            right_column.number_input(
                "ICU Visit Rate (% Percentage of Hospitalisations)",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
                step=1.0,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_icu_ratio{scenario_id}",
                on_change=save_key,
                args=["icu_ratio", scenario_id],
                help="""
The percentage of infected, hospitalised individuals who will be admitted to
a hospital's intensive care unit (ICU) as a result of the pathogen.
                """,
            )
            load_key("death_ratio", scenario_id, 12.0)
            death_rate = st.number_input(
                "Mortality Rate (per 100,000 Cases)",
                min_value=0.0,
                max_value=100000.0,
                value=12.0,
                step=0.1,
                format="%0.5g",
                placeholder="Enter a number between 0 and 100000",
                key=f"_death_ratio{scenario_id}",
                on_change=save_key,
                args=["death_ratio", scenario_id],
                help="""
The average number of infected individuals who will die for every 100,000
symptomatic cases of the pathogen.
                """,
            )

            # Dataframe for age-based burdens (if advanced params are enabled)
            if advanced:
                st.markdown(
                    "### Age-Specific Health Burdens",
                    help="""
This table allows for unique likelihoods of death or hospitalisation to be
defined for each age group, overriding the global rates defined above.
                    """,
                )
                st.markdown("Double-click a cell in this table to edit its value.")
                load_key(
                    "health_burden_age_form",
                    scenario_id,
                    pd.DataFrame(
                        {
                            "Age Group": [None],
                            "Hospitalisation Rate": [hospital_rate],
                            "Mortality Rate": [death_rate],
                        },
                    ),
                    dataframe=True,
                )
                health_burden_age_form = st.data_editor(
                    session[f"health_burden_age_form{scenario_id}"],
                    height="content",
                    num_rows="dynamic",
                    key=f"_health_burden_age_form{scenario_id}",
                    on_change=save_key,
                    args=["health_burden_age_form", scenario_id],
                    kwargs={"dataframe": True},
                    placeholder="Enter a value",
                    column_config={
                        "Age Group": st.column_config.SelectboxColumn(
                            "Age Group",
                            required=True,
                            options=AGE_GROUP_KEYS,
                            format_func=age_display,
                            help="""
An age group that will have specific health burden outcome rates defined for
it, overriding the base rates.
                            """,
                        ),
                        "Hospitalisation Rate": st.column_config.NumberColumn(
                            "Hospitalisation Rate (per 100,000 Cases)",
                            required=True,
                            default=hospital_rate,
                            min_value=0.0,
                            max_value=100000.0,
                            format="localized",
                            help="""
The average number of infected individuals who will be admitted to a hospital
for every 100,000 cases of the pathogen in this age group.
                            """,
                        ),
                        "Mortality Rate": st.column_config.NumberColumn(
                            "Mortality Rate (per 100,000 Cases)",
                            required=True,
                            default=death_rate,
                            min_value=0.0,
                            max_value=100000.0,
                            format="localized",
                            help="""
The average number of infected individuals who will die for every 100,000 cases
of the pathogen in this age group.
                            """,
                        ),
                    },
                )
                param_error(
                    "health_burden_duplicates",
                    scenario_id,
                    lambda: has_duplicates(health_burden_age_form),
                    f"""
Error: The age-specific health burden rate form used by the {
    'baseline scenario' if scenario_id== 0
    else f'scenario named "{session.scenario_names[scenario_id]}"'
} contains duplicate age group rows. Each age group should only be used in a
single row of the form.

Please remove or change any rows of the Age-Specific Health Burdens form in
:primary-badge[:material/coronavirus: Pathogen] that use the same age group as
another row.
                    """,
                    True,
                )

    # Waning Immunity Parameters (if advanced parameters are enabled)
    if advanced:
        with st.expander(
            "Immunity Waning", key=f"waning_container{scenario_id}", on_change="rerun"
        ) as waning_container:
            if waning_container.open:
                # Describe what sort of parameters are here
                st.markdown("""
Individuals in the simulation are able to become immune to the pathogen in two
different ways: by recovering from the infection, or by receiving a vaccine.
These parameters control immunity from recovering from the infection, also
referred to as natural immunity. Immunity from receiving a vaccine can be
configured using the parameters in :primary-badge[:material/vaccines: Vaccination].

The efficacy of an individual's natural immunity is represented as the
probability that they will remain healthy in the event that they would be
infected. The efficacy of natural immunity begins at 100% (where the individual
will never be infected) and stays at full effectiveness for the specified
waning delay period. Once this period has elapsed, the efficacy linearly
decreases to its minimum value over the specified waning duration. If an
individual with waned natural immunity is infected again, their immunity will
begin waning from 100% again once they recover.

                """)
                load_key("natural_waning_toggle", scenario_id, False)
                waning_toggle = st.toggle(
                    "Enable Natural Immunity Waning",
                    value=False,
                    on_change=save_key,
                    args=["natural_waning_toggle", scenario_id],
                    key=f"_natural_waning_toggle{scenario_id}",
                    help="""
Toggle whether or not immunity gained from being infected by the pathogen will
wane over time. If this is enabled, individuals in the simulation can be
infected again after recovering from a previous infection.
                    """,
                )
                # TODO: No more months
                load_key("natural_immunity_duration", scenario_id, 2)
                st.slider(
                    "Natural Immunity Waning Delay (Months)",
                    min_value=0,
                    max_value=12,
                    value=2,
                    disabled=not waning_toggle,
                    on_change=save_key,
                    args=["natural_immunity_duration", scenario_id],
                    key=f"_natural_immunity_duration{scenario_id}",
                    help="""
The number of months after an individual fully recovers from the pathogen
before they begin losing their immunity, where a month is 30 days.

If this parameter is set to 0, an individual's natural immunity will begin to
diminish immediately after they recover from the disease.
                    """,
                )
                load_key("natural_waning_rate", scenario_id, 6)
                st.slider(
                    "Natural Immunity Waning Duration (Months)",
                    min_value=0,
                    max_value=12,
                    value=6,
                    disabled=not waning_toggle,
                    on_change=save_key,
                    args=["natural_waning_rate", scenario_id],
                    key=f"_natural_waning_rate{scenario_id}",
                    help="""
The number of months after an individual begins losing their immunity before
their resistance to the pathogen reaches its lowest point, where a month is 30
days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                    """,
                )
                load_key("natural_waned_efficacy", scenario_id, 0.5)
                st.slider(
                    "Natural Immunity Minimum Efficacy (Probability)",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.5,
                    format="percent",
                    disabled=not waning_toggle,
                    key=f"_natural_waned_efficacy{scenario_id}",
                    on_change=save_key,
                    args=["natural_waned_efficacy", scenario_id],
                    help="""
The efficacy of an individual's natural immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                    """,
                )


def disease_describe(scenario_id: int = 0, advanced: bool = False):
    """
    Function to describe the current pathogen parameters in natural language.

    Parameters:
        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to describe more complex parameters like
            location-specific transmission modifiers.
    """

    # Transmission
    st.subheader("Infection Transmission")
    st.markdown(f"""
The probability that an interaction between an infected individual $I_i$ and a
healthy individual $I_s$ with no immunity to the disease will result in the
infection of $I_s$ is calculated with the following formula
[[1](https://www.doi.org/10.1371/journal.pone.0004005)]:
    """)
    st.latex(r"""
        P_{trans}(I_i, I_s) = 1 - \exp{(-\beta \times
        sym(I_i) \times inf(I_i) \times susc(I_s) \times
        \kappa)}
    """)
    # Get infectiousness/susceptibility values
    transmission_values, susceptibility_values = {}, {}
    transmission_age_form = id_get(
        "transmission_age_form",
        scenario_id,
        pd.DataFrame(
            {
                "Age Group": [None],
                "Infectiousness": [1.0],
                "Susceptibility": [1.0],
            },
        ),
    )
    for age, trans, susc in zip(
        transmission_age_form["Age Group"],
        transmission_age_form["Infectiousness"],
        transmission_age_form["Susceptibility"],
    ):
        if age:
            if trans != 1.0:
                transmission_values[age] = trans
            if susc != 1.0:
                susceptibility_values[age] = susc

    match len(transmission_values):
        case 0:
            transmission_string = """
  The simulation does not currently give any age groups unique values of
$inf(I_i)$; its value is always equal to 1.
            """
        case 1:
            ((age, value),) = transmission_values.items()
            transmission_string = f"""
  When the infected individual $I_i$ belongs to the age group
"{AGE_KEY_CONVERTER[age]}", $inf(I_i)$ will be equal to {value:.5g}. For all
other age groups, $inf(I_i)$ will be equal to 1.
            """
        case _:
            transmission_string = """
  The value of $inf(I_i)$ will be one of the following values, depending on
which age group the infected individual $I_i$ belongs to:
            """
            for age, value in sorted(transmission_values.items(), key=age_sort):
                transmission_string += f"\n  - {AGE_KEY_CONVERTER[age]}: {value:.5g}"
            if len(transmission_values) < 10:
                transmission_string += (
                    "\n\n  For all other age groups, $inf(I_i)$ will be equal to 1."
                )
    match len(susceptibility_values):
        case 0:
            susceptibility_string = """
  The simulation does not currently give any age groups unique values of
$susc(I_s)$; its value is always equal to 1.
            """
        case 1:
            ((age, value),) = susceptibility_values.items()
            susceptibility_string = f"""
  When the healthy individual $I_s$ belongs to the age group
"{AGE_KEY_CONVERTER[age]}", $susc(I_s)$ will be equal to {value:.5g}. For all
other age groups, $susc(I_s)$ will be equal to 1.
            """
        case _:
            susceptibility_string = """
  The value of $susc(I_s)$ will be one of the following values, depending on
which age group the healthy individual $I_s$ belongs to:
            """
            for age, value in sorted(susceptibility_values.items(), key=age_sort):
                susceptibility_string += f"\n  - {AGE_KEY_CONVERTER[age]}: {value:.5g}"
            if len(susceptibility_values) < 10:
                susceptibility_string += (
                    "\n\n  For all other age groups, $susc(I_s)$ will be equal to 1."
                )

    st.markdown(
        """
The meanings of the variables used in this formula are as follows:

- $\\beta$ is the basic transmission probability, which determines
the likelihood that any interaction with a healthy individual will result
in a new infection. It is analogous to the basic reproduction number
($R_0$), acting as a representation of how often an infected individual
will spread the disease to others.

  The current value of $\\beta$ used by the simulation is {beta:.6g}. The
ability to calculate the value of $\\beta$ needed to replicate a given
basic reproduction number will be added in a future version of the dashboard.

- $sym(I_i)$ is used to represent whether the infected individual is
showing symptoms. Common respiratory infection symptoms like sneezing
and coughing are effective in spreading the infection to others, so
individuals who do not display these symptoms will be less likely to
transmit the infection.

  When the infected individual $I_i$ either was infected too recently to
show symptoms or has an asymptomatic infection, $sym(I_i)$ will be equal
to {asym:.5g}. Similarly, if the infected individual's infection has progressed
enough that they no longer show symptoms but are still infectious,
$sym(I_i)$ will be equal to {post_sym:.5g}. However, when the infected
individual is showing symptoms normally, $sym(I_i)$ will be equal to 1.

- $inf(I_i)$ is used to represent how old the infected individual is.
People of different ages may be more or less likely to spread the disease;
for instance, young children may have less concern for hygiene, resulting
in them spreading the infection more often.

  {trans}

- $susc(I_s)$ is used to represent how old the healthy individual is. A
person's age may affect how likely they are to catch the infection from
others; for instance, seniors often have weaker immune systems that make
them more likely to be infected.

  {susc}

- $\\kappa$ is used to represent the location the interaction takes place
in. The location of interactions may affect the probability of transmission;
for instance, infections typically spread more often in households since
they are more enclosed than other locations.

  When an interaction takes place inside a household, $\\kappa$ will be
equal to {household:.5g}. Interactions in schools use a value of {school:.5g},
while interactions in workplaces use a value of {workplace:.5g}. For
interactions that occur during the background phase (i.e. outside of the
previous three locations), $\\kappa$ will be equal to {background:.5g}.
    """.format(
            beta=id_get("beta", scenario_id, 0.0616),
            asym=id_get("beta_asymptomatic", scenario_id, 0.55),
            post_sym=id_get("beta_post_symptomatic", scenario_id, 0.55),
            trans=transmission_string,
            susc=susceptibility_string,
            household=id_get("household_kappa", scenario_id, 2.2),
            workplace=id_get("work_kappa", scenario_id, 1.0),
            school=id_get("school_kappa", scenario_id, 1.0),
            background=id_get("background_kappa", scenario_id, 1.0),
        )
    )

    # Life Cycle
    st.subheader("Infection Life Cycle")
    latent_period = id_get("latency_period", scenario_id, 0.5)
    pre_symptom_period = id_get("pre_symptom_period", scenario_id, 1.0)
    symptom_period = id_get("symptom_period", scenario_id, 2.0)
    post_symptom_period = id_get("post_symptom_period", scenario_id, 2.5)
    st.markdown(
        """
When an individual in the simulation is infected with a pathogen, the
infection does not remain static; it progresses through multiple life
stages that affect its transmissibility before the individual recovers.
The pathogen in the simulation has 5 distinct stages in its life cycle:

1. Latent: The pathogen is still developing in the body of the infected
individual; they do not show symptoms and cannot spread the pathogen.

  The latent stage lasts for {latent}.

2. Pre-Symptomatic: The pathogen has developed further and the infected
individual can now spread the pathogen to others, but they still do not
show any symptoms and thus have a reduced transmission rate.

  The pre-symptomatic stage lasts for {pre_sym}.

3. Symptomatic: The infected individual has begun showing symptoms,
resulting in a high transmission rate and allowing them to be diagnosed
with the pathogen.

  The symptomatic stage lasts for {sym}.

4. Post-Symptomatic: The infected individual's condition has improved
enough that they no longer show symptoms of the pathogen, but they can
still spread the infection at a reduced transmission rate.

  The post-symptomatic stage lasts for {post_sym}.

5. Recovered: The individual has recovered from the pathogen and can no
longer spread the infection.

When combining the durations of each life cycle stage, the total length
of the infection is {total}. Additionally, the length of the
disease's incubation period (the time period from initial infection to
the beginning of symptoms) is {incubation}, while the length of its
infectious period (the period in which an infected individual can spread
the disease) is {infectious}.

Whenever an individual is infected with the pathogen, there is a chance
that their infection will be asymptomatic. An asymptomatic infection lasts
for the same amount of time as a regular infection, but the infected
individual will never show symptoms. Since an asymptomatic individual can
still spread the infection (albeit at a reduced transmission rate due to
the lack of symptoms), this allows the pathogen to continue spreading even
when symptomatic individuals take steps to avoid spreading the disease.

The probability of an infection being asymptomatic is {young_asym:.0%} for
individuals who are 24 years old or younger, and {old_asym:.0%} for individuals
who are more than 24 years old.
    """.format(
            latent=day_count(latent_period).lower(),
            pre_sym=day_count(pre_symptom_period).lower(),
            sym=day_count(symptom_period).lower(),
            post_sym=day_count(post_symptom_period).lower(),
            total=day_count(
                latent_period
                + pre_symptom_period
                + symptom_period
                + post_symptom_period
            ).lower(),
            incubation=day_count(latent_period + pre_symptom_period).lower(),
            infectious=day_count(
                pre_symptom_period + symptom_period + post_symptom_period
            ).lower(),
            young_asym=id_get("asymptomatic_child", scenario_id, 0.35),
            old_asym=id_get("asymptomatic_adult", scenario_id, 0.35),
        )
    )

    # Seeding
    # TODO: Add the patch seeding stuff here
    st.subheader("Infection Seeding")
    seeding_rate = id_get("seeding_rate", scenario_id, 0.25)
    if seeding_rate.is_integer():
        seeding_string = f"""
During each cycle of the simulation (i.e. twice per day), infection seeding
will infect {seeding_rate:.0g} random {"person" if seeding_rate == 1 else "people"}.
        """
    else:
        seeding_minimum, seeding_maximum = int(seeding_rate), -(-seeding_rate // 1)
        seeding_string = f"""
During each cycle of the simulation (i.e. twice per day), infection seeding
will infect an average of {seeding_rate:.3g} random people. The number of
infections will always be either {seeding_minimum:.0g} or {seeding_maximum:.0g}
each cycle; there is a {seeding_rate % 1:.0%} chance that there will be
{seeding_maximum:.0g} seeded infection{plural(seeding_maximum)}.
        """
    start_day, end_day = id_get("seeding_period", scenario_id, (1, 30))
    st.markdown("""
When a simulation experiment begins, everyone within the simulation is healthy.
Infection seeding is used to kickstart the spread of the pathogen by randomly
selecting individuals to infect every cycle. The process of infection seeding
represents the introduction of infected individuals from outside the population
(e.g. tourists). Additionally, the random nature of infection seeding
introduces stochasticity into the model and allows for variance between
different experiment runs using the same parameters.

{seeding_rate} Infection seeding occurs from Day {start} to Day {end} of each
simulation.
    """.format(seeding_rate=seeding_string, start=start_day, end=end_day))

    # Health Burdens
    st.subheader("Health Burden Outcomes")
    hospital_rate = id_get("hospital_ratio", scenario_id, 320.0)
    death_rate = id_get("death_ratio", scenario_id, 12.0)
    st.markdown(
        """
Health burden outcomes are adverse consequences that may result from an
infection, such as hospitalisation or death. These outcomes are not
simulated directly, but are calculated using the infection counts obtained
once the simulation is complete. Generally, each health burden outcome
follows from the previous outcomes; of all individuals who are diagnosed,
only a subset of them will be hospitalised, and only a subset of those who
are hospitalised will die. Only symptomatic infections can result in health
burden outcomes.

The health burden outcomes that the dashboard can simulate are as follows:

1. Diagnosis: The individual has been formally diagnosed with the pathogen.
Not all individuals who show symptoms will be diagnosed, since some people
will not mention their infection to any sources that record infection data.

  Every symptomatic individual in the simulation has a {diagnosis:.6g}%
chance of being diagnosed.

2. GP Visits: The individual has consulted their general practitioner (GP)
regarding the symptoms of the infection.

  Every symptomatic individual in the simulation has a {gp:.6g}% chance
of visiting their GP.

3. Hospitalisation: The individual has been admitted to a hospital as a
result of the infection.

  For every 100,000 symptomatic individuals in the simulation, an average
of {hospitalisation:.10g} individual(s) will be hospitalised.

4. ICU Visits: The individual has been admitted to the Intensive Care Unit
(ICU) of a hospital.

  ICU visits are defined as a subset of hospitalisations; every
hospitalised individual in the simulation has a {icu:.6g}% chance of
visiting the ICU.

5. Mortality: The individual has died as a direct result of the infection.

  For every 100,000 symptomatic individuals in the simulation, an average
of {death:.10g} individual(s) will die.
    """.format(
            diagnosis=id_get("case_ratio", scenario_id, 50.0),
            gp=id_get("gp_ratio", scenario_id, 17.0),
            hospitalisation=hospital_rate,
            icu=id_get("icu_ratio", scenario_id, 20.0),
            death=death_rate,
        )
    )
    health_burden_age_form = (
        id_get(
            "health_burden_age_form",
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Hospitalisation Rate": [hospital_rate],
                    "Mortality Rate": [death_rate],
                },
            ),
        )
        .dropna()
        .sort_values("Age Group", key=age_sort_series)
    )
    health_burden_age_form["Age Group"] = health_burden_age_form["Age Group"].map(
        age_display
    )
    if advanced and not health_burden_age_form.empty:
        st.markdown("""
Additionally, the following age groups use different hospitalisation/mortality
rates:
        """)
        # TODO: Sort the table beforehand
        st.dataframe(
            health_burden_age_form,
            hide_index=True,
            column_config={
                "Age Group": "Age Group",
                "Hospitalisation Rate": st.column_config.NumberColumn(
                    "Hospitalisation Rate (per 100,000 Cases)",
                    format="localized",
                ),
                "Mortality Rate": st.column_config.NumberColumn(
                    "Mortality Rate (per 100,000 Cases)",
                    format="localized",
                ),
            },
        )

    # Waning
    # TODO: Come up with a more readable way of generating this description
    st.subheader("Natural Immunity")
    if not (advanced and id_get("natural_waning_toggle", scenario_id, False)):
        waning_string = """
Currently, natural immunity in the simulation lasts indefinitely; once an
individual has recovered from the disease, they cannot be infected again for
the remainder of the simulation.
        """
    else:
        waning_delay = id_get("natural_immunity_duration", scenario_id, 2)
        waning_duration = id_get("natural_waning_rate", scenario_id, 6)
        waned_efficacy = id_get("natural_waned_efficacy", scenario_id, 0.5)
        if waning_delay == 0 and waning_duration == 0:
            if waned_efficacy == 0:
                # No immunity
                waning_string = """
Currently, individuals in the simulation have no natural immunity; they can be
infected again immediately after recovering from a previous infection.
                """
            else:
                # Constant lesser immunity
                waning_string = f"""
When an individual in the simulation recovers from the disease, their natural
immunity has an efficacy of {waned_efficacy:.0%}. This means that if the
individual would be infected at any point, there is only a {waned_efficacy:.0%}
chance that they will remain healthy; {1 - waned_efficacy:.0%} of the time,
they will successfully be infected.
                """
        else:
            # Construct description using relevant elements
            waning_string = """
When an individual in the simulation recovers from the disease, they initially
have full natural immunity and cannot be infected again. However, """
            if waning_duration == 0:
                if waned_efficacy == 0:
                    # Lose all immunity all at once
                    waning_string += f"""{waning_delay}
month{plural(waning_delay)} ({day_count(waning_delay * 30).lower()}) after the
initial recovery, their natural immunity will disappear, and they will be able
to be infected again. An individual who is infected a second time will regain
their natural immunity once they recover.
                    """
                else:
                    # Drop to lower immunity all at once
                    waning_string += f"""{waning_delay}
month{plural(waning_delay)} ({day_count(waning_delay * 30).lower()}) after the
initial recovery, their natural immunity will wane, become less effective.

The efficacy of an individual's natural immunity once it wanes is equal to
{waned_efficacy:.0%}. This means that if they would be infected, there is only
a {waned_efficacy:.0%} chance that they will remain healthy;
{1 - waned_efficacy:.0%} of the time, they will successfully be infected. If an
individual with waned natural immunity is infected again, their immunity will
begin waning from 100% again once they recover.
                    """
            elif waning_delay == 0:
                # Immediate waning
                waning_string += f"""their natural immunity will immediately
begin to wane, becoming less effective over time. The individual will gradually
become more susceptible to infection over a period of {waning_duration}
month{plural(waning_duration)} ({day_count(waning_duration * 30).lower()}),
after which """
                if waned_efficacy == 0:
                    waning_string += f"""they will have lost their immunity
entirely.

The efficacy of natural immunity linearly decreases from 100% to 0% over the
individual's {waning_duration} month waning period. This means that their
immunity's efficacy will be at 50% halfway through this period; if they were to
be infected at this point, there is a 50% chance for them to remain healthy. If
an individual with waned natural immunity is infected again, their immunity
will begin waning from 100% again once they recover.
                    """
                else:
                    waning_string += f"""their natural immunity will be at its
weakest.

The efficacy of an individual's natural immunity at its weakest point is equal
to {waned_efficacy:.0%}. This means that if they would be infected, there is
only a {waned_efficacy:.0%} chance that they will remain healthy;
{1 - waned_efficacy:.0%} of the time, they will successfully be infected. The
efficacy of natural immunity linearly decreases from 100% to
{waned_efficacy:.0%} over the individual's {waning_duration} month waning
period. If an individual with waned natural immunity is infected again, their
immunity will begin waning from 100% again once they recover.
                    """
            else:
                waning_string += f"""{waning_delay} month{plural(waning_delay)}
({day_count(waning_delay * 30).lower()}) after the initial recovery, their
natural immunity will begin to wane, becoming less effective over time. The
individual will gradually become more susceptible to infection for
{waning_duration} month{plural(waning_duration)}
({day_count(waning_duration * 30).lower()}), after which """
                if waned_efficacy == 0:
                    waning_string += f"""they will have lost their immunity
entirely.

The efficacy of natural immunity linearly decreases from 100% to 0% over the
individual's {waning_duration} month waning period. This means that their
immunity's efficacy will be at 50% halfway through this period; if they were to
be infected at this point, there is a 50% chance for them to remain healthy. If
an individual with waned natural immunity is infected again, their immunity
will begin waning from 100% again once they recover.
                    """
                else:
                    waning_string += f"""their natural immunity will be at its
weakest.

The efficacy of an individual's natural immunity at its weakest point is equal
to {waned_efficacy:.0%}. This means that if they would be infected, there is
only a {waned_efficacy:.0%} chance that they will remain healthy;
{1 - waned_efficacy:.0%} of the time, they will successfully be infected. The
efficacy of natural immunity linearly decreases from 100% to
{waned_efficacy:.0%} over the individual's {waning_duration} month waning
period. If an individual with waned natural immunity is infected again, their
immunity will begin waning from 100% again once they recover.
                    """

    st.markdown(f"""
Individuals in the simulation are able to become immune to the pathogen
in two different ways: by recovering from the infection, or by receiving
a vaccine. The immunity conferred by recovering from infection is known
as natural immunity.
        
{waning_string}
    """)


def disease_save_schema(
    schema: Parameters,
    scenario_id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    include_dashboard: bool = False,
):
    """
    Function to populate the Pydantic model schema with pathogen parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to account for more complex parameters
            like location-specific transmission modifiers.

        baseline (Parameters, optional): A Pydantic model representing the
            parameters set for the baseline scenario. When `id` is not 0, this
            will be used to omit parameters that are already set in the
            baseline from the final scenario.

        include_dashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like GP rate in the generated schema.
    """
    try:
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Load reused parameters immediately to save time
        seeding_period = id_get("seeding_period", scenario_id, (1, 30))
        latency_period = id_get("latency_period", scenario_id, 0.5)
        pre_symptom_period = id_get("pre_symptom_period", scenario_id, 1.0)
        symptom_period = id_get("symptom_period", scenario_id, 2.0)
        post_symptom_period = id_get("post_symptom_period", scenario_id, 2.5)
        global_hospital_rate = round(
            id_get("hospital_ratio", scenario_id, 320.0) / 100000, 10
        )
        global_death_rate = round(id_get("death_ratio", scenario_id, 12.0) / 100000, 10)
        health_burden_age_form = id_get(
            "health_burden_age_form",
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Hospitalisation Rate": [global_hospital_rate],
                    "Mortality Rate": [global_death_rate],
                },
            ),
        )

        # Strain Parameters
        beta = id_get("beta", scenario_id, 0.0616)
        baseline_beta = (
            baseline.Scenario_Strain[0].Beta
            if baseline is not None and baseline.Scenario_Strain is not None
            else None
        )
        if baseline_beta is None or baseline_beta != beta:
            schema.Scenario_Strain = [
                StrainParameters(StrainId=0, Beta=id_get("beta", scenario_id, 0.0616))
            ]

        # Patch Parameters
        if advanced:
            seeding_patch_form: pd.DataFrame = id_get(
                "seeding_patch_form",
                scenario_id,
                pd.DataFrame(
                    {
                        "Location": [None],
                        "Seeding Weight": [1.0],
                    },
                ),
            )
            schema.Scenario_Patch = [
                PatchParameters(
                    Patch=patch,
                    SeedingWeight=seed,
                )
                for patch, seed in zip(
                    seeding_patch_form["Location"],
                    seeding_patch_form["Seeding Weight"],
                )
                if patch
            ]

        # Scenario Parameters With Age Prefix
        age_scenario_params = AllAgesParameters()
        age_scenario_params.mort = global_death_rate

        # Scenario Parameters
        scenario_params = GeneralParameters()

        # Advanced parameter differences
        if advanced:
            scenario_params.prob_asymptomatic_young = id_get(
                "asymptomatic_child", scenario_id, 0.35
            )
            scenario_params.prob_asymptomatic = id_get(
                "asymptomatic_adult", scenario_id, 0.35
            )
            scenario_params.kappa_household = id_get(
                "household_kappa", scenario_id, 2.2
            )
            scenario_params.kappa_child_education = id_get(
                "school_kappa", scenario_id, 1.0
            )
            scenario_params.kappa_workplace = id_get("work_kappa", scenario_id, 1.0)
            scenario_params.kappa_background = id_get(
                "background_kappa", scenario_id, 1.0
            )

            mortality_rates = health_burden_age_form["Mortality Rate"]
            for age in AGE_GROUP_KEYS:
                if age in health_burden_age_form["Age Group"].values:
                    mort = mortality_rates[
                        health_burden_age_form["Age Group"] == age
                    ].item()
                    setattr(scenario_params, f"{age}_mort", round(mort / 100000, 10))
                else:
                    setattr(scenario_params, f"{age}_mort", global_death_rate)
        else:
            prob_asymptomatic = id_get("asymptomatic_adult", scenario_id, 0.35)
            scenario_params.prob_asymptomatic_young = prob_asymptomatic
            scenario_params.prob_asymptomatic = prob_asymptomatic

        # Immunity Waning
        if advanced and id_get("natural_waning_toggle", scenario_id, False):
            waned_efficacy = id_get("natural_waned_efficacy", scenario_id, 0.5)
            waning_rate = id_get("natural_waning_rate", scenario_id, 6) * 60
            scenario_params.infection_waning_cycle_delay = (
                id_get("natural_immunity_duration", scenario_id, 2) * 60
            )
            scenario_params.infection_waned_protection = waned_efficacy
            scenario_params.infection_waning_rate_per_cycle = (
                1.0 if waning_rate == 0 else (1.0 - waned_efficacy) / waning_rate
            )
        else:
            # Set rate to 0
            scenario_params.infection_waning_rate_per_cycle = 0
        # Infection Seeding
        scenario_params.seed_rate = id_get("seeding_rate", scenario_id, 0.25)
        scenario_params.seeding_start_cycle = (seeding_period[0] - 1) * 2
        scenario_params.seeding_duration = (
            seeding_period[1] - seeding_period[0] + 1
        ) * 2
        # Transmission
        scenario_params.beta_asymptomatic = id_get(
            "beta_asymptomatic", scenario_id, 0.55
        )
        scenario_params.beta_post_symptomatic = id_get(
            "beta_post_symptomatic", scenario_id, 0.55
        )
        # Life Cycle
        scenario_params.transmissibility_delay = int(latency_period * 2)
        scenario_params.symptom_latency = int((latency_period + pre_symptom_period) * 2)
        scenario_params.generation_time = int(
            (latency_period + pre_symptom_period + symptom_period) * 2
        )
        scenario_params.infection_duration = int(
            (latency_period + pre_symptom_period + symptom_period + post_symptom_period)
            * 2
        )
        # Health Burden Outcomes
        scenario_params.prob_diagnosis = round(
            id_get("case_ratio", scenario_id, 50.0) / 100, 6
        )
        hospital_rate = id_get("hospital_ratio", scenario_id, 320.0) / 100000
        scenario_params.prob_hospitalisation = round(hospital_rate, 10)
        # Age-Specific Parameters
        transmission_age_form = id_get(
            "transmission_age_form",
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Infectiousness": [1.0],
                    "Susceptibility": [1.0],
                },
            ),
        )
        # TODO: Make sure there's no chance of this getting duplicate rows
        for age in AGE_GROUP_KEYS:
            if age in transmission_age_form["Age Group"].values:
                age_row = transmission_age_form.loc[
                    transmission_age_form["Age Group"] == age
                ]
                setattr(
                    scenario_params, f"{age}_trans", age_row["Infectiousness"].item()
                )
                setattr(
                    scenario_params, f"{age}_susc", age_row["Susceptibility"].item()
                )
            else:
                setattr(scenario_params, f"{age}_trans", 1.0)
                setattr(scenario_params, f"{age}_susc", 1.0)

        # Save the updated parameters, removing redundant baseline values
        # TODO: Find a better way to prevent needing to include every table age
        # (maybe omit all ages if they're empty/unchanged from baseline?)
        transmission_table_params = set().union(
            *[{f"{age}_trans", f"{age}_susc", f"{age}_mort"} for age in AGE_GROUP_KEYS]
        )
        if baseline is not None and scenario_id > 0:
            schema_remove_baseline(
                age_scenario_params, baseline.Scenario_ParameterWithAgePrefix
            )
            schema_remove_baseline(
                scenario_params,
                baseline.Scenario_Parameter,
                ignore=transmission_table_params,
            )
        schema_update(schema, "Scenario_ParameterWithAgePrefix", age_scenario_params)
        schema_update(schema, "Scenario_Parameter", scenario_params)

        # Dashboard Parameters
        if include_dashboard:
            dashboard_params = DashboardParameters()
            dashboard_params.prob_gp = round(
                id_get("gp_ratio", scenario_id, 17.0) / 100, 6
            )
            dashboard_params.prob_icu = round(
                id_get("icu_ratio", scenario_id, 20.0) / 100, 6
            )
            hospitalisation_rates = health_burden_age_form["Hospitalisation Rate"]
            for age in AGE_GROUP_KEYS:
                if age in health_burden_age_form["Age Group"].values:
                    hosp = hospitalisation_rates[
                        health_burden_age_form["Age Group"] == age
                    ].item()
                    setattr(dashboard_params, f"{age}_hosp", round(hosp / 100000, 10))
                else:
                    setattr(dashboard_params, f"{age}_hosp", global_hospital_rate)

            if scenario_id > 0 and baseline is not None:
                schema_remove_baseline(
                    dashboard_params,
                    baseline.Dashboard_Parameter,
                    ignore={f"{age}_hosp" for age in AGE_GROUP_KEYS},
                )
            schema_update(schema, "Dashboard_Parameter", dashboard_params)
    except (ValueError, ValidationError) as e:
        disease_log.error(
            f"[disease_save_schema] Encountered {type(e).__name__} while validating parameters for scenario {scenario_id}: {e}"
        )
        raise e


def disease_load_schema(schema: Parameters, scenario_id: int = 0):
    """
    Function to read pathogen parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        scenario_id (int): An integer that will be used to differentiate the
            parameters in different instances of the tab by adding a number to
            the Streamlit session state variables. A value of 0 means that this
            is the baseline scenario and will be treated accordingly.

    Raises:
        ValidationError: If some but not all of the parameters needed to
            define natural immunity waning/infection seeding/infection life
            cycle periods are included in a baseline schema, or if patches are
            defined for the wrong community.
    """
    # Dashboard Parameters
    schema_dashboard = schema.Dashboard_Parameter
    if schema_dashboard is not None:
        if schema_dashboard.prob_gp is not None:
            update_param_from_schema(
                "gp_ratio", round(schema_dashboard.prob_gp * 100, 6), scenario_id
            )
        raw_hospitalisation_params = {
            p.removesuffix("_hosp"): v
            for p, v in schema_dashboard.model_dump(
                exclude_unset=True, exclude_none=True
            ).items()
            if p.endswith("_hosp")
        }
    else:
        raw_hospitalisation_params = {}

    # Patch Parameters
    valid_patches = set(COMMUNITIES[session.community].patches)
    schema_patch = schema.Scenario_Patch
    if schema_patch is not None:
        patch_table = pd.DataFrame(columns=("Location", "Seeding Weight"))
        for patch in schema_patch:
            name, weight = patch.Patch, patch.SeedingWeight
            if name not in valid_patches:
                raise AssertionError("""
Seeding weights were defined for locations that are not in the selected community
                """)
            patch_table.loc[patch_table.shape[0]] = [
                name,
                round(weight if weight else 1.0, 6),
            ]
        update_table_from_schema(
            "seeding_patch_form",
            patch_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Location": [None],
                    "Seeding Weight": [1.0],
                },
            ),
        )

    # Strain Parameters
    schema_strain = schema.Scenario_Strain
    if schema_strain is not None:
        update_param_from_schema("beta", schema_strain[0].Beta, scenario_id)

    # Global Age Parameters
    schema_age = schema.Scenario_ParameterWithAgePrefix
    if schema_age is not None and schema_age.mort is not None:
        global_death_rate = round(schema_age.mort * 100000, 6)
        update_param_from_schema("death_ratio", global_death_rate, scenario_id)
    else:
        global_death_rate = id_get("death_ratio", 0, 12.0)

    # General Scenario Parameters
    schema_parameters = schema.Scenario_Parameter
    if schema_parameters is not None:
        sim_length = session.get("cycle_count", 360)
        param_dict = schema_parameters.model_dump(exclude_unset=True, exclude_none=True)

        # Use dictionary to convert schema parameters into dashboard values
        param_converter = {
            "seed_rate": ("seeding_rate", lambda x: x),
            "beta_asymptomatic": ("beta_asymptomatic", lambda x: x),
            "beta_post_symptomatic": ("beta_post_symptomatic", lambda x: x),
            "kappa_household": ("household_kappa", lambda x: x),
            "kappa_child_education": ("school_kappa", lambda x: x),
            "kappa_workplace": ("work_kappa", lambda x: x),
            "kappa_background": ("background_kappa", lambda x: x),
            "prob_asymptomatic": ("asymptomatic_adult", lambda x: x),
            "prob_asymptomatic_young": ("asymptomatic_child", lambda x: x),
            "prob_diagnosis": ("case_ratio", lambda x: round(x * 100, 6)),
            "prob_hospitalisation": ("hospital_ratio", lambda x: round(x * 100000, 6)),
            "infection_waning_cycle_delay": (
                "natural_immunity_duration",
                lambda x: x // 60 if x != 9999 else None,
            ),
        }
        simple_params = {p: v for p, v in param_converter.items() if p in param_dict}
        for parameter, (key, format_func) in simple_params.items():
            update_param_from_schema(
                key, format_func(param_dict[parameter]), scenario_id
            )

        # Natural immunity waning
        if "infection_waning_rate_per_cycle" in param_dict:
            use_waning = param_dict["infection_waning_rate_per_cycle"] > 0
            update_param_from_schema("natural_waning_toggle", use_waning, scenario_id)
        else:
            use_waning = id_get("natural_waning_toggle", 0, False)

        # Period definitions
        # TODO: Handle baseline validation errors better
        # TODO: There might be some issues here; check to see if
        # decimals are getting ignored by the strict sliders
        if use_waning and {
            "infection_waned_protection",
            "infection_waning_rate_per_cycle",
        }.intersection(param_dict):
            # Waning immunity (if not disabled)
            # Ensure baseline has all values
            waned_efficacy = schema_parameters.infection_waned_protection
            waning_rate = schema_parameters.infection_waning_rate_per_cycle
            if None in {waned_efficacy, waning_rate} and scenario_id == 0:
                raise AssertionError("""
Waning efficacy parameters were only partially defined for the baseline scenario
                """)

            # Use baseline values to plug None gaps
            base_waned_efficacy = id_get("natural_waned_efficacy", 0, 0.5)
            base_waning_duration = id_get("natural_waning_rate", 0, 6)
            if waned_efficacy is None:
                waned_efficacy = base_waned_efficacy
            if waning_rate is None:
                waning_rate = (
                    1.0
                    if base_waning_duration == 0
                    else (1.0 - base_waned_efficacy) / (base_waning_duration * 60)
                )

            # Calculate efficacy waning duration
            update_param_from_schema(
                "natural_waned_efficacy", waned_efficacy, scenario_id
            )
            if waning_rate in {0.0, 1.0}:
                update_param_from_schema("natural_waning_rate", 0, scenario_id)
            else:
                update_param_from_schema(
                    "natural_waning_rate",
                    int((1.0 - waned_efficacy) / (waning_rate * 60)),
                    scenario_id,
                )

        if {"seeding_start_cycle", "seeding_duration"}.intersection(param_dict):
            # Seeding period
            # Ensure baseline has all values
            seeding_start = schema_parameters.seeding_start_cycle
            seeding_length = schema_parameters.seeding_duration
            if None in {seeding_start, seeding_length} and scenario_id == 0:
                raise AssertionError("""
Infection seeding period parameters were only partially defined for the
baseline scenario
                """)

            # Use baseline values to plug None gaps
            baseline_period_start, baseline_period_end = id_get(
                "seeding_period", 0, (1, 30)
            )
            if seeding_start is None:
                seeding_start = (baseline_period_start - 1) * 2
            if seeding_length is None:
                seeding_length = (baseline_period_end - baseline_period_start + 1) * 2

            # Calculate seeding period
            seeding_period_start = (seeding_start // 2) + 1
            seeding_period_end = min(sim_length, (seeding_start + seeding_length) // 2)
            update_param_from_schema(
                "seeding_period",
                (seeding_period_start, seeding_period_end),
                scenario_id,
            )

        if {
            "transmissibility_delay",
            "symptom_latency",
            "generation_time",
            "infection_duration",
        }.intersection(param_dict):
            # Infection life cycle periods
            # Ensure baseline has all values
            transmissibility_delay = schema_parameters.transmissibility_delay
            symptom_latency = schema_parameters.symptom_latency
            generation_time = schema_parameters.generation_time
            infection_duration = schema_parameters.infection_duration
            if (
                None
                in {
                    transmissibility_delay,
                    symptom_latency,
                    generation_time,
                    infection_duration,
                }
                and scenario_id == 0
            ):
                raise AssertionError("""
Infection life cycle parameters were only partially defined for the baseline
scenario
                """)

            # Use baseline values to plug None gaps
            baseline_latency = id_get("latency_period", 0, 0.5)
            baseline_pre_symptomatic = id_get("pre_symptom_period", 0, 1.0)
            baseline_symptomatic = id_get("symptom_period", 0, 2.0)
            baseline_post_symptomatic = id_get("post_symptom_period", 0, 2.5)
            if transmissibility_delay is None:
                transmissibility_delay = baseline_latency * 2
            if symptom_latency is None:
                symptom_latency = (baseline_latency + baseline_pre_symptomatic) * 2
            if generation_time is None:
                generation_time = (
                    baseline_latency + baseline_pre_symptomatic + baseline_symptomatic
                ) * 2
            if infection_duration is None:
                infection_duration = (
                    baseline_latency
                    + baseline_pre_symptomatic
                    + baseline_symptomatic
                    + baseline_post_symptomatic
                ) * 2

            update_param_from_schema(
                "latency_period", transmissibility_delay / 2, scenario_id
            )
            update_param_from_schema(
                "pre_symptom_period",
                (symptom_latency - transmissibility_delay) / 2,
                scenario_id,
            )
            update_param_from_schema(
                "symptom_period",
                (generation_time - symptom_latency) / 2,
                scenario_id,
            )
            update_param_from_schema(
                "post_symptom_period",
                (infection_duration - generation_time) / 2,
                scenario_id,
            )

        # Tables

        # Age-specific transmission
        transmission_table = pd.DataFrame(
            columns=("Age Group", "Infectiousness", "Susceptibility")
        )
        transmission_params: dict[AgeGroupKey, Any] = {
            cast(AgeGroupKey, p.removesuffix("_trans")): v
            for p, v in param_dict.items()
            if p.endswith("_trans") and v != 1.0
        }
        susceptibility_params: dict[AgeGroupKey, Any] = {
            cast(AgeGroupKey, p.removesuffix("_susc")): v
            for p, v in param_dict.items()
            if p.endswith("_susc") and v != 1.0
        }
        # TODO: Leave table to inherit baseline if ages are unchanged
        transmission_ages = sorted(
            set(transmission_params.keys()) | set(susceptibility_params.keys()),
            key=lambda x: AGE_GROUP_KEYS.index(x),
        )
        for age in transmission_ages:
            transmission_value = transmission_params.get(age, 1.0)
            susceptibility_value = susceptibility_params.get(age, 1.0)
            transmission_table.loc[transmission_table.shape[0]] = [
                age,
                transmission_value,
                susceptibility_value,
            ]
        update_table_from_schema(
            "transmission_age_form",
            transmission_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Infectiousness": [1.0],
                    "Susceptibility": [1.0],
                },
            ),
        )

        # Age-specific health burdens
        global_hospital_rate = param_dict.get(
            "prob_hospitalisation", id_get("hospital_ratio", 0, 320.0)
        )
        burden_table = pd.DataFrame(
            columns=("Age Group", "Hospitalisation Rate", "Mortality Rate")
        )
        hospitalisation_params: dict[AgeGroupKey, Any] = {
            cast(AgeGroupKey, p): round(v * 100000, 6)
            for p, v in raw_hospitalisation_params.items()
            if v != global_hospital_rate
        }
        mortality_params: dict[AgeGroupKey, Any] = {
            cast(AgeGroupKey, p.removesuffix("_mort")): (
                round(v * 100000, 6) if v is not None else None
            )
            for p, v in param_dict.items()
            if p.endswith("_mort") and v != global_death_rate
        }
        burden_ages = sorted(
            set(hospitalisation_params.keys()) | set(mortality_params.keys()),
            key=lambda x: AGE_GROUP_KEYS.index(x),
        )
        for age in burden_ages:
            hospitalisation_value = hospitalisation_params.get(
                age, global_hospital_rate
            )
            mortality_value = mortality_params.get(age, global_death_rate)
            burden_table.loc[burden_table.shape[0]] = [
                age,
                hospitalisation_value,
                mortality_value,
            ]
        update_table_from_schema(
            "health_burden_age_form",
            burden_table,
            scenario_id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Hospitalisation Rate": [
                        id_get("hospital_ratio", scenario_id, 320.0)
                    ],
                    "Mortality Rate": [id_get("death_ratio", scenario_id, 12.0)],
                },
            ),
        )
