# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where disease parameters can be modified

# Imports
import logging

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    dayCount,
    dualError,
    dynamicScaleChange,
    hasDuplicates,
    idGet,
    loadKey,
    paramError,
    saveKey,
    saveWithRerun,
)
from ClientResources.ModelSchema import (
    Parameters,
    ageScenarioParameters,
    scenarioParameters,
    strainParameters,
)
from ClientResources.SharedResources import ageTimeDict, backgroundColour

# Logging
diseaseLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.fragment
def buildDiseaseTab(id: int):
    """
    Function to generate the parameters for the disease in a specified
    container with scenario differentiation

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.
    """
    # Initialise session variables needed by the disease forms
    # sessionParameters = {
    #   f"transRowCount{id}": 0,
    #   f"seedPeriodError{id}": 0,
    #   f"deathRowCount{id}": 0}
    # }
    # for parameter, default in sessionParameters.items():
    # session[parameter] = session.get(parameter, default)

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    # ageGroupSets = {
    #    f"transRemainingAgeGroups{id}": (f"transRowCount{id}", f"transAgeGroup{id}-"),
    #    f"deathRemainingAgeGroups{id}": (f"deathRowCount{id}", f"deathAgeGroup{id}-")
    # }

    # Use function to recalculate remaining group parameters
    # getRemainingGroups(ageGroupSets, ageCategories.keys())

    # Tab Content
    st.header("Disease-Related Parameters")
    st.markdown(
        """
        This tab contains parameters relating to the disease itself, including
        the rate of infectious individuals entering the modelled community, the
        rate at which the disease spreads and how long infection lasts before
        recovery.
    """
    )

    # Seeding Parameters
    simLength = session.get("cycleCount", 360)
    with st.expander("Infection Seeding"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control how infected individuals
            are directly seeded into the community. Seeding is
            typically used to kickstart the initial epidemic by
            ensuring a steady number of people are infected
            daily.
        """
        )
        loadKey("seedRate", id, 0.25)
        st.select_slider(
            "Infection Seeding Rate (Average Individuals per Cycle)",
            np.linspace(0.025, 5.0, 200),
            0.25,
            key=f"_seedRate{id}",
            on_change=saveWithRerun,
            args=["seedRate", id],  # type: ignore
            format_func=lambda x: f"{x:0.4g}",
            help="""
                The average number of individuals that will be
                infected directly via infection seeding each cycle.
                Note that each day of the simulation is 2 cycles.
            """,
        )
        # TODO: Notify users if dynamic parameters are changed
        loadKey("seedPeriod", id, (1, 30))
        st.slider(
            "Infection Seeding Time Period (Days)",
            min_value=1,
            max_value=simLength,
            value=(1, 30),
            format="Day %i",
            on_change=dynamicScaleChange,
            args=["seedPeriod", "seedTimeForm", id],
            key=f"_seedPeriod{id}",
            help="""
                The time period during which infection seeding will
                occur in the simulation. The first value is the day
                on which seeding will begin (where Day 1 is the
                first day of the simulation), and the second value
                is the day on which it will stop.

                Note that if you modify this value, the update
                points for infection seeding defined in
                :primary-badge[:material/manage_history: Dynamic] may have
                their values altered. For instance, if you go from seeding
                ending on Day 60 to Day 30, an update point set to affect
                the value on Day 45 will be changed to affect it on Day 30 instead.
            """,
        )

    # Transmission Parameters
    with st.expander("Disease Transmission"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control the likelihood that the
            disease will spread when an infected individual
            interacts with others.

            The probability that an interaction between an infected
            individual $I_i$ and an uninfected, non-immune
            individual $I_s$ will result in the infection of $I_s$
            is calculated with the following formula
            [[1](https://www.doi.org/10.1371/journal.pone.0004005)]:

            $$
            P_{trans}(I_i, I_s) = 1 - \\exp{(-\\beta \\times
            sym(I_i) \\times inf(I_i) \\times susc(I_s) \\times
            \\kappa)}
            $$

            In this formula:
            - $\\beta$ (beta) is the basic transmission parameter
            for the disease
            - $sym(I_i)$ is a parameter based on whether or not the
            infected individual has shown symptoms
            - $inf(I_i)$ is the infectiousness parameter for the
            infected individual
            - $susc(I_s)$ is the susceptibility parameter for the
            uninfected individual
            - $\\kappa$ is the location parameter for the area the
            interaction is occurring in

            The parameters in this section will control the values
            of each of these parameters under various conditions.
        """
        )

        # Beta and symptom multipliers
        # Previous default was 0.11
        loadKey("beta", id, 0.0616)
        st.number_input(
            "Basic Transmission Parameter (β)",
            min_value=0.00001,
            max_value=1.0,
            value=0.0616,
            step=0.00001,
            format="%0.5g",
            key=f"_beta{id}",
            on_change=saveKey,
            args=["beta", id],
            help="""
                The value of the basic transmission parameter
                $\\beta$, the base constant used to calculate the
                probability of an individual being infected with
                the disease upon interacting with an infected
                individual. The higher this value is, the more
                likely it is for uninfected individuals to contract
                the disease in any interaction with infected
                individuals.
            """,
        )
        leftCol, rightCol = st.columns(2)
        loadKey("betaAsymptomatic", id, 0.55)
        leftCol.number_input(
            "Asymptomatic Transmission Multiplier",
            min_value=0.00001,
            max_value=1.0,
            value=0.55,
            step=0.00001,
            format="%0.5g",
            on_change=saveKey,
            args=["betaAsymptomatic", id],
            key=f"_betaAsymptomatic{id}",
            help="""
                The value of the transmissibility modifier
                $sym(I_i)$ when the infected individual in an
                interaction ($I_i$) is asymptomatic (i.e. has not
                shown any symptoms of the disease despite being
                infectious). This applies to both individuals who
                are too early in the disease's lifespan to show
                symptoms as well as individuals who never show
                symptoms throughout their infectious period. The
                lower this value is, the less likely it is for
                uninfected individuals to contract the disease when
                interacting with asymptomatic individuals.
            """,
        )
        loadKey("betaPostSymptomatic", id, 0.55)
        rightCol.number_input(
            "Post-Symptomatic Transmission Multiplier",
            min_value=0.00001,
            max_value=1.0,
            value=0.55,
            step=0.00001,
            format="%0.5g",
            on_change=saveKey,
            args=["betaPostSymptomatic", id],
            key=f"_betaPostSymptomatic{id}",
            help="""
                The value of the transmissibility modifier
                $sym(I_i)$ when the infected individual in an
                interaction ($I_i$) is post-symptomatic (i.e.
                previously showed symptoms of the disease, but no
                longer does). The lower this value is, the less
                likely it is for uninfected individuals to contract
                the disease when interacting with post-symptomatic
                individuals.
            """,
        )
        loadKey("schoolKappa", id, 1.0)
        leftCol.number_input(
            "School Transmission Multiplier",
            min_value=0.00001,
            max_value=10.0,
            value=1.0,
            step=0.00001,
            format="%0.5g",
            key=f"_schoolKappa{id}",
            on_change=saveKey,
            args=["schoolKappa", id],
            help="""
                The value of the transmissibility modifier
                $\\kappa$ when an interaction takes place in a
                school. The higher this value is, the more
                likely it is for uninfected individuals to contract
                the disease when interacting with infected
                individuals in schools.
                """,
        )
        loadKey("workKappa", id, 1.0)
        rightCol.number_input(
            "Workplace Transmission Multiplier",
            min_value=0.00001,
            max_value=10.0,
            value=1.0,
            step=0.00001,
            format="%0.5g",
            key=f"_workKappa{id}",
            on_change=saveKey,
            args=["workKappa", id],
            help="""
                The value of the transmissibility modifier
                $\\kappa$ when an interaction takes place in a
                workplace. The higher this value is, the more
                likely it is for uninfected individuals to contract
                the disease when interacting with infected
                individuals in workplaces.
                """,
        )
        loadKey("householdKappa", id, 2.2)
        leftCol.number_input(
            "Household Transmission Multiplier",
            min_value=0.00001,
            max_value=10.0,
            value=2.2,
            step=0.00001,
            format="%0.5g",
            key=f"_householdKappa{id}",
            on_change=saveKey,
            args=["householdKappa", id],
            help="""
                The value of the transmissibility modifier
                $\\kappa$ when an interaction takes place in a
                household. The higher this value is, the more
                likely it is for uninfected individuals to contract
                the disease when interacting with infected
                individuals in households.
                """,
        )
        loadKey("backgroundKappa", id, 1.0)
        rightCol.number_input(
            "Background Contact Transmission Multiplier",
            min_value=0.00001,
            max_value=10.0,
            value=1.0,
            step=0.00001,
            format="%0.5g",
            key=f"_backgroundKappa{id}",
            on_change=saveKey,
            args=["backgroundKappa", id],
            help="""
                The value of the transmissibility modifier
                $\\kappa$ when an interaction takes place during the
                model's background phase (i.e. outside of simulated
                locations). The higher this value is, the more
                likely it is for uninfected individuals to contract
                the disease during the background phase.
                """,
        )

        # Dataframe for age-based transmissibility modifiers
        st.markdown(
            "### Age-Specific Infectiousness/Susceptibility",
            help="""
This table allows for unique values of $inf(I_i)$ and $susc(I_s)$ to be
defined for each age group, modifying the probability of infection for
interactions involving individuals in said age groups. These parameters
will assume a default value of 1 (i.e. no change in probability) if they
are not specified for a specific age group.
            """,
        )
        st.markdown("Double-click a cell in this table to edit its value.")
        loadKey(
            "transAgeForm",
            id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Infectiousness": [1.0],
                    "Susceptibility": [1.0],
                },
            ),
            dataframe=True,
        )
        transAgeForm = st.data_editor(
            session[f"transAgeForm{id}"],
            height="content",
            num_rows="dynamic",
            key=f"_transAgeForm{id}",
            on_change=saveKey,
            args=["transAgeForm", id],
            kwargs={"dataframe": True},
            placeholder="Enter a value",
            column_config={
                "Age Group": st.column_config.SelectboxColumn(
                    "Age Group",
                    required=True,
                    options=ageTimeDict.keys(),
                    format_func=lambda x: ageTimeDict[x],  # type: ignore
                    help="""
An age group that will have specific infectiousness and susceptibility
parameters defined for it, modifying the base transmission probability for
interactions involving individuals in that age group.
                    """,
                ),
                "Infectiousness": st.column_config.NumberColumn(
                    "Infectiousness",
                    required=True,
                    default=1.0,
                    min_value=0.0,
                    help="""
The value of the infectiousness parameter $inf(I_i)$ when the infected
individual in an interaction ($I_i$) is a member of this age group. The lower
this value is, the less likely it is for uninfected individuals to contract
the disease when interacting with infected individuals in this age group.
                    """,
                ),
                "Susceptibility": st.column_config.NumberColumn(
                    "Susceptibility",
                    required=True,
                    default=1.0,
                    min_value=0.0,
                    help="""
The value of the susceptibility parameter $susc(I_s)$ when the uninfected
individual in an interaction ($I_s$) is a member of this age group. The lower
this value is, the less likely it is for uninfected individuals in this age
group to contract the disease when interacting with infected individuals.
                    """,
                ),
            },
        )
        paramError(
            "transmissionAgeFormDuplicates",
            id,
            lambda: hasDuplicates(transAgeForm),
            f"""
                Error: The age-specific infectiousness/susceptibility
                form used by the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{session[f'scenarioName{id}']}"'
                } contains duplicate age group rows. Each age group
                should only be used in a single row of the form.

                Please remove or change any rows of the Age-Specific
                Infectiousness/Susceptibility form in
                :primary-badge[:material/coronavirus: Disease]
                that use the same age group as another row.
            """,
            True,
        )

        # Old variable-length form
        oldVarLengthForm = '''# Save relevant params as variables to avoid lookups
        transRowCount = session[f"transRowCount{id}"]
        transRemainingGroups = session[f"transRemainingAgeGroups{id}"]
        transAgeContainer = st.container()
        for i in range(transRowCount):
            (
                transGroupColumn,
                transInfectColumn,  # transSusceptColumn,
                transRemoveColumn,
            ) = transAgeContainer.columns(
                (0.25, 0.55, 0.2), vertical_alignment="center"
            )
            transCurrentGroup = session.get(f"transAgeGroup{id}-{i}")

            # Age group column
            loadKey(
                "transAgeGroup",
                id,
                transCurrentGroup if transCurrentGroup else transRemainingGroups[0],
                f"-{i}",
            )
            with transGroupColumn:
                st.selectbox(
                    "Age Group",
                    key=f"_transAgeGroup{id}-{i}",
                    options=(
                        # Set age group options such that only ages
                        # that haven't been selected yet can be selected
                        [transCurrentGroup]
                        + [
                            group
                            for group in transRemainingGroups
                            if group != transCurrentGroup
                        ]
                        if transCurrentGroup
                        else transRemainingGroups
                    ),
                    on_change=saveKey,
                    args=["transAgeGroup", id, f"-{i}"],  # type: ignore
                    disabled=not transRowCount < 10,
                    help="""
                    An age group that will have specific
                    infectiousness and susceptibility parameters
                    defined for it, modifying the base transmission
                    probability for interactions involving
                    individuals in that age group.

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
            # Infectiousness column
            loadKey("transInfect", id, 1.0, f"-{i}")
            with transInfectColumn:
                st.select_slider(
                    "Infectiousness",
                    np.linspace(0.0, 3.0, 301),
                    1.0,
                    key=f"_transInfect{id}-{i}",
                    on_change=saveKey,
                    args=["transInfect", id, f"-{i}"],  # type: ignore
                    format_func=lambda x: f"{x:0.3g}",
                    help="""
                    The value of the infectiousness parameter
                    $inf(I_i)$ when the infected individual in an
                    interaction ($I_i$) is a member of this age
                    group. The lower this value is, the less likely
                    it is for uninfected individuals to contract
                    the disease when interacting with infected
                    individuals in this age group.
                """,
                )
            # Susceptibility column
            loadKey("transSuscept", id, 1.0, f"-{i}")
            with transInfectColumn:
                st.select_slider(
                    "Susceptibility",
                    np.linspace(0.0, 3.0, 301),
                    1.0,
                    key=f"_transSuscept{id}-{i}",
                    on_change=saveKey,
                    args=["transSuscept", id, f"-{i}"],  # type: ignore
                    format_func=lambda x: f"{x:0.3g}",
                    help="""
                    The value of the susceptibility parameter
                    $susc(I_s)$ when the uninfected individual in
                    an interaction ($I_s$) is a member of this age
                    group. The lower this value is, the less likely
                    it is for uninfected individuals in this age
                    group to contract the disease when interacting
                    with infected individuals.
                """,
                )
            # Delete button column
            with transRemoveColumn:
                st.button(
                    label="Remove Age Group",
                    icon=":material/delete:",
                    key=f"transRemove{id}-{i}",
                    on_click=deleteFormRow,
                    args=(
                        i,
                        f"transRowCount{id}",
                        {
                            f"transAgeGroup{id}-",
                            f"transInfect{id}-",
                            f"transSuscept{id}-",
                        },
                    ),
                    help="""
                    Remove this row of the form and remove these
                    age-specific transmission parameters from the
                    simulation.
                """,
                )
        # Button to add another row for age specific params
        transAgeContainer.button(
            label="Add Age Group",
            icon=":material/add:",
            on_click=addFormRow,
            key=f"transAdd{id}",
            args=(
                f"transRowCount{id}",
                {
                    f"transAgeGroup{id}-{transRowCount}": (
                        transRemainingGroups[0] if transRemainingGroups else None
                    ),
                    f"transInfect{id}-{transRowCount}": 1.0,
                    f"transSuscept{id}-{transRowCount}": 1.0,
                },
            ),
            disabled=not transRowCount < 10,
            help=(
                """
                Add another row to this form, where you can select
                an additional age group to have unique transmission
                parameters.
            """
                if transRowCount <= 9
                else """
                All age groups have been given unique transmission
                parameters, so a new age group cannot be added.
            """
            ),
        )'''

    # Life Cycle Parameters
    with st.expander("Disease Life Cycle"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control the disease's life cycle,
            including how long individuals are infectious for and
            the likelihood of developing symptoms.
        """
        )

        # Asymptomatic params
        loadKey("asymptomaticChild", id, 0.35)
        st.select_slider(
            "Probability of Young (0-24) Asymptomatic Case",
            np.linspace(0.0, 1.0, 201),
            0.35,
            format_func=lambda x: f"{100 * x:0.3g}%",
            on_change=saveKey,
            args=["asymptomaticChild", id],  # type: ignore
            key=f"_asymptomaticChild{id}",
            help="""
                The probability that an infected young person
                (defined as 0-24 years old) in the simulation will
                be asymptomatic (i.e. they never show any symptoms
                of the disease despite being infectious).
            """,
        )
        loadKey("asymptomaticAdult", id, 0.35)
        st.select_slider(
            "Probability of Adult (24+) Asymptomatic Case",
            np.linspace(0.0, 1.0, 201),
            0.35,
            format_func=lambda x: f"{100 * x:0.3g}%",
            on_change=saveKey,
            args=["asymptomaticAdult", id],  # type: ignore
            key=f"_asymptomaticAdult{id}",
            help="""
                The probability that an infected adult (defined as
                24+ years old) in the simulation will be
                asymptomatic (i.e. they never show any symptoms of
                the disease despite being infectious).
            """,
        )

        # Duration Parameters
        st.markdown(
            """
            ### Disease Life Stages

            Diseases in the simulation have 5 distinct stages in
            their life cycle:

            1. Latent: The disease is still developing in the body
            of the infected individual; they do not yet show
            symptoms and are not infectious.
            2. Pre-Symptomatic: The disease has developed further
            and the infected individual can now spread the disease
            to others, but they still do not show any symptoms.
            3. Symptomatic: The disease is now showing symptoms in
            the infected individual, and thus can now be diagnosed.
            4. Post-Symptomatic: The infected individual's
            condition has improved enough that they no longer show
            symptoms of the disease, but they are still infectious.
            5. Recovered: The individual is no longer infectious
            and has gained an immunity to the disease.

            If an infected individual is asymptomatic, their
            infection will not progress into the symptomatic stage;
            they will remain in the pre-symptomatic stage without
            symptoms for the disease's entire duration.

            The following parameters configure the length of each
            stage in the disease's life cycle.
        """
        )
        loadKey("latencyPeriod", id, 0.5)
        # Previous default was 10
        latencyPeriod = st.slider(
            "Latency Period Length (Days)",
            min_value=0.0,
            max_value=14.0,
            value=0.5,
            step=0.5,
            format="%f Days",
            on_change=saveKey,
            args=["latencyPeriod", id],  # type: ignore
            key=f"_latencyPeriod{id}",
            help="""
                The length in days of the disease's latency period,
                i.e. the length of time between an individual
                initially being infected by the disease and said
                individual becoming infectious themselves.
            """,
        )
        loadKey("preSymptomPeriod", id, 1.0)
        # Previous default was 2
        preSymptomPeriod = st.slider(
            "Pre-Symptomatic Period Length (Days)",
            min_value=0.0,
            max_value=14.0,
            value=1.0,
            step=0.5,
            format="%f Days",
            key=f"_preSymptomPeriod{id}",
            on_change=saveKey,
            args=["preSymptomPeriod", id],  # type: ignore
            help="""
                The length in days of the disease's pre-symptomatic
                period, i.e. the length of time between an
                infected individual becoming capable of infecting
                others with the disease and said individual
                beginning to show symptoms.
            """,
        )
        loadKey("symptomPeriod", id, 2.0)
        # Previous default was 7
        symptomPeriod = st.slider(
            "Symptomatic Period Length (Days)",
            min_value=0.0,
            max_value=14.0,
            value=2.0,
            step=0.5,
            format="%f Days",
            on_change=saveKey,
            args=["symptomPeriod", id],  # type: ignore
            key=f"_symptomPeriod{id}",
            help="""
                The length in days of the disease's symptomatic
                period, i.e. the length of time during which an
                infected individual will show symptoms of the
                disease.
            """,
        )
        loadKey("postSymptomPeriod", id, 2.5)
        # Previous default was 1
        postSymptomPeriod = st.slider(
            "Post-Symptomatic Period Length (Days)",
            min_value=0.0,
            max_value=14.0,
            value=2.5,
            step=0.5,
            format="%f Days",
            key=f"_postSymptomPeriod{id}",
            on_change=saveKey,
            args=["postSymptomPeriod", id],  # type: ignore
            help="""
                The length in days of the disease's
                post-symptomatic period, i.e. the length of time
                between an individual ceasing to show symptoms of
                the disease and said individual being fully
                recovered/no longer infectious.
            """,
        )
        dualError(
            "noInfectiousPeriod",
            id,
            lambda: preSymptomPeriod + symptomPeriod + postSymptomPeriod == 0,
            lambda: symptomPeriod == 0,
            f"""
                Error: The disease life cycle used by the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{session[f'scenarioName{id}']}"'
                } has pre-symptomatic, symptomatic and post-symptomatic
                periods all set to have a length of 0 days. As such,
                there is no point where the disease is infectious, and
                it cannot spread.

                Please increase either Pre-Symptomatic Period Length,
                Symptomatic Period Length or Post-Symptomatic Period
                Length in :primary-badge[:material/coronavirus: Disease]
                to be greater than 0.
            """,
            f"""
                Error: The disease life cycle used by the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{session[f'scenarioName{id}']}"'
                } has its symptomatic period set to have a length of 0 days.
                As such, there is no point where the disease shows symptoms.

                Please increase Symptomatic Period Length in
                :primary-badge[:material/coronavirus: Disease]
                to be greater than 0.
            """,
        )

        # Display duration lengths via Cool Bar Graph Thing™
        stageNames = ["Latent", "Pre-Symptomatic", "Symptomatic", "Post-Symptomatic"]
        data = pd.DataFrame(
            {
                "Life Stage": stageNames,
                "Length (Days)": [
                    latencyPeriod,
                    preSymptomPeriod,
                    symptomPeriod,
                    postSymptomPeriod,
                ],
            }
        )
        data["end"] = data["Length (Days)"].cumsum()
        data["start"] = data["end"].shift(fill_value=0)
        data["tooltip"] = data["Life Stage"] + ": " + data["Length (Days)"].astype(str)
        chart = (
            alt.Chart(data, title="Current Disease Life Cycle")
            .mark_bar(stroke=backgroundColour(), strokeWidth=1)
            .encode(
                x=alt.X(
                    "start:Q",
                    title="Length (Days)",
                    axis=alt.Axis(format=".1~f", tickMinStep=0.5),
                    scale=alt.Scale(
                        domain=[
                            0,
                            (
                                latencyPeriod
                                + preSymptomPeriod
                                + symptomPeriod
                                + postSymptomPeriod
                            ),
                        ]
                    ),
                ),
                x2="end:Q",
                y=alt.value(0),
                color=alt.Color(
                    "Life Stage:N", sort=stageNames, scale=alt.Scale(scheme="inferno")
                ),
                tooltip=["Life Stage", "Length (Days)"],
            )
            .properties(width="container", height=200)
        )
        st.altair_chart(chart)

        # Written period lengths
        st.markdown(
            """
            With the parameters defined above, the following time
            periods can be defined:
        """
        )
        totalCol, incubationCol, infectiousCol = st.columns(
            (0.33333, 0.33333, 0.33333), vertical_alignment="center"
        )
        totalCol.metric(
            "Total Length of Infection",
            dayCount(
                latencyPeriod + preSymptomPeriod + symptomPeriod + postSymptomPeriod
            ),
            help="""
                The length in days of the disease's total lifespan,
                i.e. the length of time between an individual
                initially being infected by the disease and said
                individual being fully recovered/no longer
                infectious.
            """,
        )
        incubationCol.metric(
            "Incubation Period",
            dayCount(latencyPeriod + preSymptomPeriod),
            help="""
                The length in days of the disease's incubation
                period, i.e. the length of time between an
                individual initially being infected by the disease
                and said individual beginning to show symptoms.
            """,
        )
        infectiousCol.metric(
            "Infectious Period",
            dayCount(preSymptomPeriod + symptomPeriod + postSymptomPeriod),
            help="""
                The length in days of the disease's infectious
                period, i.e. the length of time during which an
                infected individual is capable of spreading the
                disease to others.
            """,
        )

    # Health Burden Outcome Parameters
    with st.expander("Health Burden Outcomes"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control how likely different health
            burden outcomes (such as hospitalisation and death) are
            to occur as a result of the disease. These parameters
            are primarily used in the simulation's post-processing
            phase; most of these outcomes are not simulated
            directly, but the probabilities defined here are used
            in combination with the data from the simulation to
            generate statistics on how many people were affected by
            each outcome.

            Note that none of these health burden outcomes are
            capable of occurring in asymptomatic individuals; the
            probabilities defined here will only apply to people
            who are symptomatic.
        """
        )

        # Health Burden Outcomes
        # TODO: Consider having these be just infected proportion rather than
        # infected symptomatic proportion (which one is easier for
        # researchers to calculate?)
        # TODO: Note how scientific notation works in the description or something
        loadKey("caseRatio", id, 0.5)
        st.number_input(
            "Diagnosed Case Rate (Proportion of Population)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.00001,
            format="%0.5g",
            key=f"_caseRatio{id}",
            on_change=saveKey,
            args=["caseRatio", id],
            help="""
                The proportion of infected, symptomatic
                individuals who will be formally diagnosed as a
                confirmed case of the disease.
            """,
        )
        loadKey("gpRatio", id, 0.17)
        st.number_input(
            "GP Visit Rate (Proportion of Population)",
            min_value=0.0,
            max_value=1.0,
            value=0.17,
            step=0.00001,
            format="%0.5g",
            key=f"_gpRatio{id}",
            on_change=saveKey,
            args=["gpRatio", id],
            help="""
                The proportion of infected, symptomatic
                individuals who will visit their general practitioner
                (GP) as a result of the disease.
            """,
        )
        loadKey("hospitalRatio", id, 0.01374491)
        st.number_input(
            "Hospitalisation Rate (Proportion of Population)",
            min_value=0.0,
            max_value=1.0,
            value=0.01374491,
            step=0.00001,
            format="%0.5e",
            key=f"_hospitalRatio{id}",
            on_change=saveKey,
            args=["hospitalRatio", id],
            help="""
                The proportion of infected, symptomatic
                individuals who will be admitted to a hospital as a
                result of the disease.
            """,
        )
        loadKey("icuRatio", id, 0.00274898)
        st.number_input(
            "ICU Visit Rate (Proportion of Population)",
            min_value=0.0,
            max_value=1.0,
            value=0.00274898,
            step=0.00001,
            format="%0.5e",
            key=f"_icuRatio{id}",
            on_change=saveKey,
            args=["icuRatio", id],
            help="""
                The proportion of infected, symptomatic
                individuals who will be admitted to a hospital's
                intensive care unit (ICU) as a result of the
                disease.
            """,
        )
        loadKey("deathRatio", id, 0.00050034)
        deathRate = st.number_input(
            "Mortality Rate (Proportion of Population)",
            min_value=0.0,
            max_value=1.0,
            value=0.00050034,
            step=0.00001,
            format="%0.5e",
            key=f"_deathRatio{id}",
            on_change=saveKey,
            args=["deathRatio", id],
            help="""
                The base proportion of infected, symptomatic
                individuals who will die as a direct result of the
                disease.
            """,
        )

        # Dataframe for age-based mortality
        st.markdown(
            "### Age-Specific Mortality Rate",
            help="""
This table allows for unique likelihoods of death to be defined for
each age group, overriding the global rate defined above.
            """,
        )
        st.markdown("Double-click a cell in this table to edit its value.")
        loadKey(
            "mortAgeForm",
            id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Mortality Rate": [deathRate],
                },
            ),
            dataframe=True,
        )
        mortAgeForm = st.data_editor(
            session[f"mortAgeForm{id}"],
            height="content",
            num_rows="dynamic",
            key=f"_mortAgeForm{id}",
            on_change=saveKey,
            args=["mortAgeForm", id],
            kwargs={"dataframe": True},
            placeholder="Enter a value",
            column_config={
                "Age Group": st.column_config.SelectboxColumn(
                    "Age Group",
                    required=True,
                    options=ageTimeDict.keys(),
                    format_func=lambda x: ageTimeDict[x],  # type: ignore
                    help="""
An age group that will have a specific mortality rate defined for it,
overriding the base proportion.
                    """,
                ),
                "Mortality Rate": st.column_config.NumberColumn(
                    "Mortality Rate (Proportion of Population)",
                    required=True,
                    default=deathRate,
                    min_value=0.0,
                    max_value=1.0,
                    format="%0.5e",
                    help="""
The proportion of infected, symptomatic individuals in this age
group who will die as a direct result of the disease.
                    """,
                ),
            },
        )
        paramError(
            "mortalityAgeFormDuplicates",
            id,
            lambda: hasDuplicates(mortAgeForm),
            f"""
                Error: The age-specific mortality rate form used by the {
                    'baseline scenario' if id == 0
                    else f'scenario named "{session[f'scenarioName{id}']}"'
                } contains duplicate age group rows. Each age group
                should only be used in a single row of the form.

                Please remove or change any rows of the Age-Specific
                Mortality Rate form in
                :primary-badge[:material/coronavirus: Disease]
                that use the same age group as another row.
            """,
            True,
        )

        oldVarLengthForm = '''
        # Save relevant params as variables to avoid lookups
        deathRowCount = session[f"deathRowCount{id}"]
        deathRemainingGroups = session[f"deathRemainingAgeGroups{id}"]
        deathAgeContainer = st.container()
        for i in range(deathRowCount):
            (deathGroupColumn, deathRateColumn, deathRemoveColumn) = (
                deathAgeContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment="center"
                )
            )
            deathCurrentGroup = session.get(f"deathAgeGroup{id}-{i}")

            # Age group column
            loadKey(
                "deathAgeGroup",
                id,
                deathCurrentGroup if deathCurrentGroup else deathRemainingGroups[0],
                f"-{i}",
            )
            with deathGroupColumn:
                st.selectbox(
                    "Age Group",
                    key=f"_deathAgeGroup{id}-{i}",
                    # Set age group options such that only ages
                    # that haven't been selected yet can be selected
                    options=(
                        [deathCurrentGroup]
                        + [
                            group
                            for group in deathRemainingGroups
                            if group != deathCurrentGroup
                        ]
                        if deathCurrentGroup
                        else deathRemainingGroups
                    ),
                    on_change=saveKey,
                    args=["deathAgeGroup", id, f"-{i}"],  # type: ignore
                    disabled=not deathRowCount < 10,
                    help="""
                    An age group that will have specific mortality
                    rates defined for it, overriding the base
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
            # Mortality column
            loadKey("deathRatio", id, 0.00050034, f"-{i}")
            with deathRateColumn:
                st.select_slider(
                    "Mortality Rate (Probability)",
                    np.linspace(0.0, 1.0, 201),
                    0.00050034,
                    key=f"_deathRatio{id}-{i}",
                    on_change=saveKey,
                    args=["deathRatio", id, f"-{i}"],  # type: ignore
                    format_func=lambda x: f"{100 * x:0.3g}%",
                    help="""
                    The probability that an infected, symptomatic
                    individual in this age group will die as a
                    direct result of the disease.
                """,
                )
            # Delete button column
            with deathRemoveColumn:
                st.button(
                    label="Remove Age Group",
                    icon=":material/delete:",
                    key=f"deathRemove{id}-{i}",
                    on_click=deleteFormRow,
                    args=(
                        i,
                        f"deathRowCount{id}",
                        {f"deathAgeGroup{id}-", f"deathRate{id}-"},
                    ),
                    help="""
                    Remove this row of the form and remove these
                    age-specific mortality rates from the
                    simulation.
                """,
                )
        # Button to add another row for age specific params
        deathAgeContainer.button(
            label="Add Age Group",
            icon=":material/add:",
            on_click=addFormRow,
            key=f"deathAdd{id}",
            args=(
                f"deathRowCount{id}",
                {
                    f"deathAgeGroup{id}-{deathRowCount}": (
                        deathRemainingGroups[0] if deathRemainingGroups else None
                    ),
                    f"deathRatio{id}-{deathRowCount}": deathRate,
                },
            ),
            disabled=not deathRowCount < 10,
            help=(
                """
                Add another row to this form, where you can select
                an additional age group to have a unique mortality
                rate.
            """
                if deathRowCount <= 9
                else """
                All age groups have been given unique mortality
                rates, so a new age group cannot be added.
            """
            ),
        )'''

    # Waning Immunity Parameters
    # TODO: Allow fully disabling immunity waning
    with st.expander("Immunity Waning"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control how immunity to the disease
            conferred by having been infected by it in the past
            will become less effective over time. Note that
            individuals in the simulation are assumed to be
            completely immune to the disease immediately after
            recovering from it; the efficacy before waning is 100%.

            Note that these parameters do not affect immunity to
            the disease that is obtained from vaccination. This
            type of immunity can be configured using the parameters
            in the "Vaccinations and NPIs" tab.
        """
        )

        # Waning immunity
        loadKey("naturalImmunityDuration", id, 2)
        st.slider(
            "Natural Immunity Waning Delay (Months)",
            1,
            36,
            2,
            on_change=saveKey,
            args=["naturalImmunityDuration", id],  # type: ignore
            key=f"_naturalImmunityDuration{id}",
            help="""
                The number of months after an individual fully
                recovers from the disease before the immunity
                conferred by having been infected begins to
                diminish, where a month is 30 days.
            """,
        )
        loadKey("naturalWanedEfficacy", id, 0.5)
        st.select_slider(
            "Natural Immunity After Waning (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.5,
            key=f"_naturalWanedEfficacy{id}",
            on_change=saveKey,
            args=["naturalWanedEfficacy", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The final efficacy value that an individual's
                natural immunity after recovering from the disease
                will approach as it begins to diminish, represented
                as the probability that the individual will remain
                healthy when exposed to the disease after their
                immunity is fully waned.
            """,
        )
        loadKey("naturalWaningRate", id, 6)
        st.slider(
            "Natural Immunity Waning Duration (Months)",
            0,
            36,
            6,
            on_change=saveKey,
            args=["naturalWaningRate", id],  # type: ignore
            key=f"_naturalWaningRate{id}",
            help="""
                The number of months after the immunity from having
                fully recovered from the disease begins waning
                before the efficacy of the immunity stabilises,
                where a month is 30 days. Natural immunity in the
                *Flusim* simulation will wane at a linear rate, so
                this parameter represents how long it takes for the
                immunity level to decrease from 100% immunity to
                the final immunity probability defined above.

                If this parameter is set to 0, the immunity
                provided by recovering from the disease will never
                diminish.
            """,
        )


def diseaseSchema(schema: Parameters, id: int = 0):
    """
    Function to populate the Pydantic model schema with the parameters in
    this tab with scenario differentiation

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

        # Load reused parameters immediately to save time
        seedPeriod = idGet("seedPeriod", id, (1, 30))
        latencyPeriod = idGet("latencyPeriod", id, 0.5)
        preSymptomPeriod = idGet("preSymptomPeriod", id, 1.0)
        symptomPeriod = idGet("symptomPeriod", id, 2.0)
        postSymptomPeriod = idGet("postSymptomPeriod", id, 2.5)

        # Strain Parameters
        schema.Scenario_Strain = [
            strainParameters(StrainId=0, Beta=idGet("beta", id, 0.0616))
        ]

        # Scenario Parameters With Age Prefix
        ageScenarioParams = (
            schema.Scenario_ParameterWithAgePrefix
            if schema.Scenario_ParameterWithAgePrefix
            else ageScenarioParameters()
        )
        deathRate = idGet("deathRatio", id, 0.00050034)
        ageScenarioParams.mort = deathRate
        schema.Scenario_ParameterWithAgePrefix = ageScenarioParams

        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter
            if schema.Scenario_Parameter
            else scenarioParameters()
        )
        # Infection Seeding
        scenarioParams.seed_rate = idGet("seedRate", id, 0.25)
        scenarioParams.seeding_start_cycle = (seedPeriod[0] - 1) * 2
        scenarioParams.seeding_duration = (seedPeriod[1] - seedPeriod[0] + 1) * 2
        # Transmission
        scenarioParams.beta_asymptomatic = idGet("betaAsymptomatic", id, 0.55)
        scenarioParams.beta_post_symptomatic = idGet("betaPostSymptomatic", id, 0.55)
        scenarioParams.prob_asymptomatic_young = idGet("asymptomaticChild", id, 0.35)
        scenarioParams.prob_asymptomatic = idGet("asymptomaticAdult", id, 0.35)
        scenarioParams.kappa_household = idGet("householdKappa", id, 2.2)
        scenarioParams.kappa_child_education = idGet("schoolKappa", id, 1.0)
        scenarioParams.kappa_workplace = idGet("workKappa", id, 1.0)
        scenarioParams.kappa_background = idGet("backgroundKappa", id, 1.0)
        # Life Cycle
        scenarioParams.transmissibility_delay = latencyPeriod * 2
        scenarioParams.symptom_latency = (latencyPeriod + preSymptomPeriod) * 2
        scenarioParams.generation_time = (
            latencyPeriod + preSymptomPeriod + symptomPeriod
        ) * 2
        scenarioParams.infection_duration = (
            latencyPeriod + preSymptomPeriod + symptomPeriod + postSymptomPeriod
        ) * 2
        # Health Burden Outcomes
        scenarioParams.prob_diagnosis = idGet("caseRatio", id, 0.5)
        scenarioParams.prob_hospitalisation = idGet("hospitalRatio", id, 0.01374491)
        scenarioParams.prob_withdrawal = idGet("withdrawalWork", id, 0.5)
        scenarioParams.prob_school_withdrawal = idGet("withdrawalSchool", id, 0.9)
        # Immunity Waning
        scenarioParams.infection_waning_cycle_delay = (
            idGet("naturalImmunityDuration", id, 2) * 60
        )
        scenarioParams.infection_waned_protection = idGet(
            "naturalWanedEfficacy", id, 0.5
        )
        scenarioParams.infection_waning_rate_per_cycle = idGet(
            "naturalWaningRate", id, 6
        )
        # Age-Specific Parameters
        transAgeForm = idGet(
            "transAgeForm",
            id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Infectiousness": [1.0],
                    "Susceptibility": [1.0],
                },
            ),
        )
        for age, trans, susc in zip(
            transAgeForm["Age Group"],
            transAgeForm["Infectiousness"],
            transAgeForm["Susceptibility"],
        ):
            if age:
                setattr(scenarioParams, f"{age}_trans", trans)
                setattr(scenarioParams, f"{age}_susc", susc)
        mortAgeForm = idGet(
            "mortAgeForm",
            id,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Mortality Rate": [deathRate],
                },
            ),
        )
        for age, mort in zip(
            mortAgeForm["Age Group"],
            mortAgeForm["Mortality Rate"],
        ):
            if age:
                setattr(scenarioParams, f"{age}_mort", mort)
        oldVarLengthForm = """
        for i in range(session.get(f"transRowCount{id}", 0)):
            varAgeGroup = ageCategories[session[f"transAgeGroup{id}-{i}"]]
            setattr(
                scenarioParams,
                f"{varAgeGroup}_trans",
                idGet("transInfect", id, 1, f"-{i}"),
            )
            setattr(
                scenarioParams,
                f"{varAgeGroup}_susc",
                idGet("transSuscept", id, 1, f"-{i}"),
            )
        for i in range(session.get(f"deathRowCount{id}", 0)):
            setattr(
                scenarioParams,
                f"{ageCategories[session[f'deathAgeGroup{id}-{i}']]}_mort",
                idGet("deathRatio", id, deathRate, f"-{i}"),
            )"""
        # Save the updated parameters
        schema.Scenario_Parameter = scenarioParams
    except (ValueError, ValidationError) as e:
        diseaseLog.error(
            (
                f"[diseaseParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e
