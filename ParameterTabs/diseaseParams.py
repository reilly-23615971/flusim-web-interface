# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where disease parameters can be modified

# Imports
import logging
from typing import Literal, Optional

import altair as alt
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    ageSort,
    backgroundColour,
    dayCount,
    dualError,
    paramError,
    plural,
    schemaRemoveBaseline,
)
from ClientResources.ModelSchema import (
    Parameters,
    ageScenarioParameters,
    dashboardParameters,
    scenarioParameters,
    strainParameters,
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
from ClientResources.SharedResources import ageTimeDict

# Logging
diseaseLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


def asymptomaticSave(
    key: str,
    scenarioID: int,
    direction: Literal["simpleToAdvanced", "advancedToSimple"],
):
    """
    Wrapper for `saveKey` that keeps asymptomatic probabilities synced.

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int): The integer representing the scenario the widget
            is part of.

        direction (str): Either "simpleToAdvanced" or "advancedToSimple", used to
            determine which parameters to propagate values to.
    """
    saveKey(key, scenarioID)
    match direction:
        case "simpleToAdvanced":
            simpleProb = idGet(key, scenarioID, 0.35)
            session[f"asymptomaticChild{scenarioID}"] = simpleProb
            session[f"asymptomaticAdult{scenarioID}"] = simpleProb
        case "advancedToSimple":
            session[f"asymptomaticBoth{scenarioID}"] = idGet(key, scenarioID, 0.35)


@st.fragment
def buildDiseaseTab(id: int, advanced: bool = False):
    """
    Function to generate the parameters for the pathogen in a specified
    container with scenario differentiation

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.

        advanced (bool): Set to True to show more complex parameters like
            location-specific transmission modifiers.
    """
    # Initialise session variables needed by the pathogen forms
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
    st.header("Pathogen-Related Parameters")
    st.markdown("""
        This tab contains parameters relating to the pathogen itself, including
        the rate of infectious individuals entering the modelled community, the
        rate at which the pathogen spreads and how long infection lasts before
        recovery.
    """)

    # Transmission Parameters
    with st.expander(
        "Infection Transmission", key=f"transmissionContainer{id}", on_change="rerun"
    ) as transmissionContainer:
        if transmissionContainer.open:
            st.markdown("""
                These parameters control the likelihood that the
                pathogen will spread when an infected individual
                interacts with others.

                The probability that an interaction between an infected
                individual $I_i$ and a healthy individual $I_s$ with
                no immunity to the disease will result in the infection of $I_s$
                is calculated with the following formula
                [[1](https://www.doi.org/10.1371/journal.pone.0004005)]:

                $$
                P_{trans}(I_i, I_s) = 1 - \\exp{(-\\beta \\times
                sym(I_i) \\times inf(I_i) \\times susc(I_s) \\times
                \\kappa)}
                $$

                In this formula:
                - $\\beta$ is the basic transmission probability, which determines
                the likelihood that any interaction with a healthy individual will
                result in a new infection. It is analogous to the basic reproduction
                number ($R_0$), acting as a representation of how often an infected
                individual will spread the disease to others.
                - $sym(I_i)$ is equal to 1 when the infected individual is showing
                symptoms of the infection, but reduces the likelihood of infection
                if they are not showing symptoms. Common respiratory infection
                symptoms like sneezing and coughing are effective in spreading
                the infection to others, so individuals who do not display these
                symptoms will be less likely to transmit the infection.
                - $inf(I_i)$ is infectiousness, which modifies the likelihood of
                infection based on how old the infected individual is. People of
                different ages may be more or less likely to spread the disease;
                for instance, young children may have less concern for hygiene,
                resulting in them spreading the infection more often.
                - $susc(I_s)$ is susceptibility, which modifies the likelihood of
                infection based on how old the healthy individual is. A person's
                age may affect how likely they are to catch the infection from
                others; for instance, seniors often have weaker immune systems
                that make them more likely to be infected.
                - $\\kappa$ modifies the likelihood of infection based on whether
                the interaction takes place in a household, school, workplace or
                other location. The location of interactions may affect the
                probability of transmission; for instance, infections typically
                spread more often in households since they are more enclosed than
                other locations.
            """)
            # TODO: Mention that kappa changes are advanced-only?

            # Beta and symptom multipliers
            # Previous default for beta was 0.11
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
$\\beta$, the base probability of a person being infected
when interacting with someone who is already infected.
The higher this value is, the more
likely it is for uninfected individuals to contract
the pathogen in any interaction with infected individuals.
                """,
            )
            leftCol, rightCol = st.columns(2)
            loadKey("betaAsymptomatic", id, 0.55)
            leftCol.number_input(
                "Asymptomatic Transmission ($sym(I_i)$)",
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
shown any symptoms of the pathogen despite being
infectious). This applies to both individuals who
are too early in the pathogen's lifespan to show
symptoms as well as individuals who never show
symptoms throughout their infectious period. The
lower this value is, the less likely it is for
uninfected individuals to contract the pathogen when
interacting with asymptomatic individuals.
                """,
            )
            loadKey("betaPostSymptomatic", id, 0.55)
            rightCol.number_input(
                "Post-Symptomatic Transmission ($sym(I_i)$)",
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
previously showed symptoms of the pathogen, but no
longer does). The lower this value is, the less
likely it is for uninfected individuals to contract
the pathogen when interacting with post-symptomatic
individuals.
                """,
            )
            # Transmission multipliers (only if advanced params are enabled)
            if advanced:
                loadKey("schoolKappa", id, 1.0)
                leftCol.number_input(
                    "School Transmission ($\\kappa$)",
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
the pathogen when interacting with infected
individuals in schools.
                    """,
                )
                loadKey("workKappa", id, 1.0)
                rightCol.number_input(
                    "Workplace Transmission ($\\kappa$)",
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
the pathogen when interacting with infected
individuals in workplaces.
                        """,
                )
                loadKey("householdKappa", id, 2.2)
                leftCol.number_input(
                    "Household Transmission ($\\kappa$)",
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
the pathogen when interacting with infected
individuals in households.
                        """,
                )
                loadKey("backgroundKappa", id, 1.0)
                rightCol.number_input(
                    "Background Contact Transmission ($\\kappa$)",
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
$\\kappa$ when an interaction takes place outside of the previous 3
locations (during the simulation's background phase).
The higher this value is, the more
likely it is for uninfected individuals to contract
the pathogen during the background phase.
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
            st.markdown("""
                Double-click a cell in this table to edit its value. Note that
                any ages not added to this form will use values of $inf(I_i)$
                and $susc(I_s)$ equal to 1.
            """)
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
                    :primary-badge[:material/coronavirus: Pathogen]
                    that use the same age group as another row.
                """,
                True,
            )

            # Old variable-length form
            '''# Save relevant params as variables to avoid lookups
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
                        args=["transAgeGroup", id, f"-{i}"],
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
                        args=["transInfect", id, f"-{i}"],
                        format_func=lambda x: f"{x:0.3g}",
                        help="""
                        The value of the infectiousness parameter
                        $inf(I_i)$ when the infected individual in an
                        interaction ($I_i$) is a member of this age
                        group. The lower this value is, the less likely
                        it is for uninfected individuals to contract
                        the pathogen when interacting with infected
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
                        args=["transSuscept", id, f"-{i}"],
                        format_func=lambda x: f"{x:0.3g}",
                        help="""
                        The value of the susceptibility parameter
                        $susc(I_s)$ when the uninfected individual in
                        an interaction ($I_s$) is a member of this age
                        group. The lower this value is, the less likely
                        it is for uninfected individuals in this age
                        group to contract the pathogen when interacting
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
    with st.expander(
        "Infection Life Cycle", key=f"lifeCycleContainer{id}", on_change="rerun"
    ) as lifeCycleContainer:
        if lifeCycleContainer.open:
            # Describe what sort of parameters are here
            st.markdown("""
                These parameters control the pathogen's life cycle,
                including how long individuals are infectious for and
                the likelihood of developing symptoms.
            """)

            # Duration Parameters
            st.subheader("Infection Life Stages", divider="grey")
            st.markdown("""
                When an individual in the simulation is infected with a pathogen,
                the infection does not remain static; it progresses through multiple
                life stages that affect its transmissibility before the individual
                recovers. The pathogen in the simulation has 5 distinct stages
                in its life cycle:

                1. Latent: The pathogen is still developing in the body of the
                infected individual; they do not show symptoms and cannot spread
                the pathogen.
                2. Pre-Symptomatic: The pathogen has developed further and the
                infected individual can now spread the pathogen to others, but
                they still do not show any symptoms and thus have a reduced
                transmission rate.
                3. Symptomatic: The infected individual has begun showing symptoms,
                resulting in a high transmission rate and allowing them to be
                diagnosed with the pathogen.
                4. Post-Symptomatic: The infected individual's condition has
                improved enough that they no longer show symptoms of the pathogen,
                but they can still spread the infection at a reduced transmission
                rate.
                5. Recovered: The individual has recovered from the pathogen and
                can no longer spread the infection.

                The following parameters configure the length of each
                stage in the pathogen's life cycle.
            """)
            loadKey("latencyPeriod", id, 0.5)
            # Previous default was 10
            latencyPeriod = st.slider(
                "Latent Period Length (Days)",
                min_value=0.0,
                max_value=14.0,
                value=0.5,
                step=0.5,
                format="%f Day(s)",
                on_change=saveKey,
                args=["latencyPeriod", id],
                key=f"_latencyPeriod{id}",
                help="""
The length in days of the pathogen's latent period,
i.e. the length of time between a person
initially being infected by the pathogen and becoming infectious themselves.
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
                format="%f Day(s)",
                key=f"_preSymptomPeriod{id}",
                on_change=saveKey,
                args=["preSymptomPeriod", id],
                help="""
The length in days of the pathogen's pre-symptomatic
period, i.e. the length of time between a person becoming
infectious and beginning to show symptoms.
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
                format="%f Day(s)",
                on_change=saveKey,
                args=["symptomPeriod", id],
                key=f"_symptomPeriod{id}",
                help="""
The length in days of the pathogen's symptomatic
period, i.e. the length of time during which an
infected individual will show symptoms of the pathogen.
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
                format="%f Day(s)",
                key=f"_postSymptomPeriod{id}",
                on_change=saveKey,
                args=["postSymptomPeriod", id],
                help="""
The length in days of the pathogen's
post-symptomatic period, i.e. the length of time
between a person ceasing to show symptoms of
the pathogen and being fully recovered/no longer infectious.
                """,
            )
            dualError(
                "noInfectiousPeriod",
                id,
                lambda: preSymptomPeriod + symptomPeriod + postSymptomPeriod == 0,
                lambda: symptomPeriod == 0,
                f"""
                    Error: The infection life cycle used by the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{session[f'scenarioName{id}']}"'
                    } has pre-symptomatic, symptomatic and post-symptomatic
                    periods all set to have a length of 0 days. As such,
                    there is no point where the pathogen is infectious, and
                    it cannot spread.

                    Please increase either Pre-Symptomatic Period Length,
                    Symptomatic Period Length or Post-Symptomatic Period
                    Length in :primary-badge[:material/coronavirus: Pathogen]
                    to be greater than 0.
                """,
                f"""
                    Warning: The infection life cycle used by the {
                        'baseline scenario' if id == 0
                        else f'scenario named "{session[f'scenarioName{id}']}"'
                    } has its symptomatic period set to have a length of 0 days.
                    As such, there is no point where the pathogen shows symptoms.

                    Please increase Symptomatic Period Length in
                    :primary-badge[:material/coronavirus: Pathogen]
                    to be greater than 0.
                """,
            )

            # Display duration lengths via Cool Bar Graph Thing (tm)
            stageNames = [
                "Latent",
                "Pre-Symptomatic",
                "Symptomatic",
                "Post-Symptomatic",
            ]
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
            # Filter out zero values and define chart values
            data = data[data["Length (Days)"] > 0].reset_index(drop=True)
            data["end"] = data["Length (Days)"].cumsum()
            data["start"] = data["end"].shift(fill_value=0)
            data["tooltip"] = (
                data["Life Stage"] + ": " + data["Length (Days)"].astype(str)
            )
            chart = (
                alt.Chart(data, title="Current Infection Life Cycle")
                .mark_bar(size=30, stroke=backgroundColour(), strokeWidth=1)
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
                        "Life Stage:N",
                        sort=stageNames,
                        scale=alt.Scale(
                            scheme="inferno", domain=list(data["Life Stage"])
                        ),
                    ),
                    tooltip=["Life Stage", "Length (Days)"],
                )
                .properties(width="container", height=205)
            )
            st.altair_chart(chart)

            # Written period lengths
            st.markdown("""
                In addition to these life stages, the infection's life cycle may
                also be described using the following time periods:
            """)
            totalCol, incubationCol, infectiousCol = st.columns(3)
            totalCol.metric(
                "Total Length of Infection",
                dayCount(
                    latencyPeriod + preSymptomPeriod + symptomPeriod + postSymptomPeriod
                ),
                delta_description="from infection to recovery",
                help="""
The length in days of the pathogen's total lifespan,
i.e. the length of time between a person
initially being infected by the pathogen and said
person being fully recovered/no longer infectious.
                """,
            )
            incubationCol.metric(
                "Incubation Period",
                dayCount(latencyPeriod + preSymptomPeriod),
                delta_description="from infection to symptoms",
                help="""
The length in days of the pathogen's incubation
period, i.e. the length of time between a person
being infected and beginning to show symptoms.
                """,
            )
            infectiousCol.metric(
                "Infectious Period",
                dayCount(preSymptomPeriod + symptomPeriod + postSymptomPeriod),
                delta_description="where others may be infected",
                help="""
The length in days of the pathogen's infectious
period, i.e. the length of time during which an
infected individual is capable of spreading the
pathogen to others.
                """,
            )

            # Asymptomatic params (age-separated if advanced params are enabled)
            st.subheader("Asymptomatic Likelihood", divider="grey")
            st.markdown("""
                Whenever an individual is infected with the pathogen, there is
                a chance that their infection will be asymptomatic. An asymptomatic
                infection lasts for the same amount of time as a regular infection,
                but the infected individual will never show symptoms. Since an
                asymptomatic individual can still spread the infection (albeit at
                a reduced transmission rate due to the lack of symptoms), this
                allows the pathogen to continue spreading even when symptomatic
                individuals take steps to avoid spreading the disease.
            """)
            if advanced:
                loadKey("asymptomaticChild", id, 0.35)
                st.slider(
                    "Probability of Young (0-24) Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=saveKey,
                    args=["asymptomaticChild", id],
                    key=f"_asymptomaticChild{id}",
                    help="""
The probability that an infected young person (less than 24 years old) in
the simulation will be asymptomatic (i.e. they never show any symptoms of the
pathogen despite being infectious).
                    """,
                )
                loadKey("asymptomaticAdult", id, 0.35)
                st.slider(
                    "Probability of Adult (24+) Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=asymptomaticSave,
                    args=["asymptomaticAdult", id, "advancedToSimple"],
                    key=f"_asymptomaticAdult{id}",
                    help="""
The probability that an infected adult (over 24 years old) in the
simulation will be asymptomatic (i.e. they never show any symptoms of the
pathogen despite being infectious).
                    """,
                )
            else:
                loadKey("asymptomaticBoth", id, 0.35)
                st.slider(
                    "Probability of Asymptomatic Case",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    format="percent",
                    on_change=asymptomaticSave,
                    args=["asymptomaticBoth", id, "simpleToAdvanced"],
                    key=f"_asymptomaticBoth{id}",
                    help="""
The probability that an infected individual in the simulation will be
asymptomatic (i.e. they never show any symptoms of the pathogen despite
being infectious).
                    """,
                )

    # Seeding Parameters
    simLength = session.get("cycleCount", 360)
    with st.expander(
        "Infection Seeding", key=f"infectionSeedingContainer{id}", on_change="rerun"
    ) as seedingContainer:
        if seedingContainer.open:
            st.markdown("""
                These parameters control how infected individuals are directly
                seeded into the community. When a simulation experiment begins,
                everyone within the simulation is healthy. Infection seeding is
                used to kickstart the spread of the pathogen by randomly selecting
                individuals to infect. The process of infection seeding
                represents the introduction of infected individuals from outside
                the population (e.g. tourists). Additionally, the random nature
                of infection seeding introduces stochasticity into the model and
                allows for variance between different experiment runs using the
                same parameters.
                        
                During each cycle of the simulation (i.e. twice per day) within
                the specified seeding period, infection seeding will directly
                infect a number of people equal to the seeding rate. If the seeding
                rate is a decimal, the number of infections is chosen randomly
                each cycle such that it averages out to the desired rate.
            """)
            loadKey("seedRate", id, 0.25)
            # TODO: Elaborate on decimal seeding rate mechanics?
            st.slider(
                "Infection Seeding Rate (Average Individuals per Cycle)",
                0.05,
                5.0,
                value=0.25,
                step=0.05,
                key=f"_seedRate{id}",
                on_change=saveKey,
                args=["seedRate", id],
                format="%0.4g",
                help="""
The average number of individuals that will be infected directly via infection
seeding each cycle. Note that each day of the simulation is 2 cycles.

If this number is a decimal, the simulation will randomly decide between the two
closest integers every cycle such that the average number of people seeded is the
desired rate. For instance, if the seeding rate is 3.2, the simulation will infect
3 people 80% of the time and 4 people 20% of the time.
                """,
            )
            loadKey("seedPeriod", id, (1, 30))
            st.slider(
                "Infection Seeding Time Period (Days)",
                min_value=1,
                max_value=simLength,
                value=(1, 30),
                format="Day %i",
                on_change=dynamicScaleChange,
                args=[
                    "seedPeriod",
                    "seedTimeForm",
                    "Infection Seeding Time Period",
                    id,
                ],
                key=f"_seedPeriod{id}",
                help="""
The time period during which infection seeding will occur in the simulation.
The first value is the day on which seeding will begin (where Day 1 is the
first day of the simulation), and the second value is the day on which it will stop.

Note that if you modify this value, the update points for infection seeding defined in
:primary-badge[:material/manage_history: Dynamic] may have their values altered.
For instance, if you go from seeding ending on Day 60 to Day 30, an update point
set to affect the value on Day 45 will be changed to affect it on Day 30 instead.
                """,
            )

    # Health Burden Outcome Parameters
    with st.expander(
        "Health Burden Outcomes",
        key=f"healthBurdenContainer{id}",
        on_change="rerun",
    ) as burdenContainer:
        if burdenContainer.open:
            st.markdown("""
                These parameters control how likely different health burden outcomes
                are to occur as a result of the pathogen. Health burden outcomes
                are adverse consequences that may result from an infection, such
                as hospitalisation or death. These outcomes are not simulated
                directly, but are calculated using the infection counts obtained
                once the simulation is complete. Generally, each health burden
                outcome follows from the previous outcomes; of all individuals
                who are diagnosed, only a subset of them will be hospitalised,
                and only a subset of those who are hospitalised will die. Only
                symptomatic infections can result in health burden outcomes.
                        
                The health burden outcomes that the dashboard can simulate are as follows:

                1. Diagnosis: The individual has been formally diagnosed with the
                pathogen. Not all individuals who show symptoms will be diagnosed,
                since some people will not mention their infection to any sources
                that record infection data.

                2. GP Visits: The individual has consulted their general practitioner
                (GP) regarding the symptoms of the infection.

                3. Hospitalisation: The individual has been admitted to a hospital
                as a result of the infection.

                4. ICU Visits: The individual has been admitted to the Intensive
                Care Unit (ICU) of a hospital.

                5. Mortality: The individual has died as a direct result of the
                infection.
            """)
            st.info(
                """
                    Note that due to the difference in scale between these health
                    burden outcomes, their occurrence rates are represented in
                    different ways: 
                    
                    - Diagnosis and GP Visits are represented as percentages of
                    the infected, symptomatic population.
                    - Hospitalisations and Mortality are represented as the number
                    of occurrences for every 100,000 infected, symptomatic
                    individuals in the population.
                    - ICU Visits are represented as percentages of the hospitalised
                    population.
                """,
                icon=":material/decimal_increase:",
            )

            # Health Burden Outcomes
            loadKey("caseRatio", id, 50.0)
            st.number_input(
                "Diagnosis Rate (% Percentage of Cases)",
                min_value=0.0,
                max_value=100.0,
                value=50.0,
                step=0.1,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_caseRatio{id}",
                on_change=saveKey,
                args=["caseRatio", id],
                help="""
The percentage of infected, symptomatic individuals who will be formally
diagnosed as a confirmed case of the pathogen.
                """,
            )
            loadKey("gpRatio", id, 17.0)
            st.number_input(
                "GP Visit Rate (% Percentage of Cases)",
                min_value=0.0,
                max_value=100.0,
                value=17.0,
                step=0.1,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_gpRatio{id}",
                on_change=saveKey,
                args=["gpRatio", id],
                help="""
The percentage of infected, symptomatic individuals who will visit their
general practitioner (GP) as a result of the pathogen.
                """,
            )
            loadKey("hospitalRatio", id, 320.0)
            st.number_input(
                "Hospitalisation Rate (Hospitalisations per 100,000 Cases)",
                min_value=0.0,
                max_value=100000.0,
                value=320.0,
                step=0.01,
                format="%0.5g",
                placeholder="Enter a number between 0 and 100000",
                key=f"_hospitalRatio{id}",
                on_change=saveKey,
                args=["hospitalRatio", id],
                help="""
The average number of infected individuals who will be admitted to a hospital
for every 100,000 symptomatic cases of the pathogen.
                """,
            )
            loadKey("icuRatio", id, 20.0)
            st.number_input(
                "ICU Visit Rate (% Percentage of Hospitalisations)",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
                step=0.1,
                format="%0.3g",
                placeholder="Enter a percentage between 0 and 100",
                key=f"_icuRatio{id}",
                on_change=saveKey,
                args=["icuRatio", id],
                help="""
The percentage of infected, hospitalised individuals who will be admitted to
a hospital's intensive care unit (ICU) as a result of the pathogen.
                """,
            )
            loadKey("deathRatio", id, 12.0)
            deathRate = st.number_input(
                "Mortality Rate (Deaths per 100,000 Cases)",
                min_value=0.0,
                max_value=100000.0,
                value=12.0,
                step=0.01,
                format="%0.5g",
                placeholder="Enter a number between 0 and 100000",
                key=f"_deathRatio{id}",
                on_change=saveKey,
                args=["deathRatio", id],
                help="""
The average number of infected individuals who will die for every 100,000
symptomatic cases of the pathogen.
                """,
            )

            # Dataframe for age-based mortality (if advanced params are enabled)
            # TODO: Add thousands separators/ban scientific notation from all tables
            if advanced:
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
overriding the base rate.
                            """,
                        ),
                        "Mortality Rate": st.column_config.NumberColumn(
                            "Mortality Rate (Deaths per 100,000 Cases)",
                            required=True,
                            default=deathRate,
                            min_value=0.0,
                            max_value=100000.0,
                            format="%0.8g",
                            help="""
The average number of infected individuals in this age group who will die
for every 100,000 cases of the pathogen.
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
                        :primary-badge[:material/coronavirus: Pathogen]
                        that use the same age group as another row.
                    """,
                    True,
                )

                '''
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
                    loadKey("deathRatio", id, 0.000115077, f"-{i}")
                    with deathRateColumn:
                        st.select_slider(
                            "Mortality Rate (Probability)",
                            np.linspace(0.0, 1.0, 201),
                            0.000115077,
                            key=f"_deathRatio{id}-{i}",
                            on_change=saveKey,
                            args=["deathRatio", id, f"-{i}"],  # type: ignore
                            format_func=lambda x: f"{100 * x:0.3g}%",
                            help="""
                            The probability that an infected, symptomatic
                            individual in this age group will die as a
                            direct result of the pathogen.
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

    # Waning Immunity Parameters (if advanced parameters are enabled)
    if advanced:
        with st.expander(
            "Immunity Waning", key=f"naturalWaningContainer{id}", on_change="rerun"
        ) as waningContainer:
            if waningContainer.open:
                # Describe what sort of parameters are here
                st.markdown("""
                    Individuals in the simulation are able to become immune to
                    the pathogen in two different ways: by recovering from the
                    infection, or by receiving a vaccine. These parameters control
                    immunity from recovering from the infection, also referred to
                    as natural immunity. Immunity from receiving a vaccine can be
                    configured using the parameters in
                    :primary-badge[:material/vaccines: Vaccination].
                    
                    The efficacy of an individual's natural immunity is represented
                    as the probability that they will remain healthy in the event
                    that they would be infected. The efficacy of natural immunity
                    begins at 100% (where the individual will never be infected)
                    and stays at full effectiveness for the specified waning delay
                    period. Once this period has elapsed, the efficacy linearly
                    decreases to its minimum value over the specified waning duration.
                    If an individual with waned natural immunity is infected again,
                    their immunity will begin waning from 100% again once they recover.

                """)
                loadKey("naturalWaningToggle", id, False)
                waningToggle = st.toggle(
                    "Enable Natural Immunity Waning",
                    value=False,
                    on_change=saveKey,
                    args=["naturalWaningToggle", id],
                    key=f"_naturalWaningToggle{id}",
                    help="""
Toggle whether or not immunity gained from being infected by the pathogen will
wane over time. If this is enabled, individuals in the simulation can be
infected again after recovering from a previous infection.
                    """,
                )
                # TODO: No more months
                loadKey("naturalImmunityDuration", id, 2)
                st.slider(
                    "Natural Immunity Waning Delay (Months)",
                    0,
                    12,
                    2,
                    disabled=not waningToggle,
                    on_change=saveKey,
                    args=["naturalImmunityDuration", id],
                    key=f"_naturalImmunityDuration{id}",
                    help="""
The number of months after an individual fully recovers from the pathogen
before they begin losing their immunity, where a month is 30 days.

If this parameter is set to 0, an individual's natural immunity will begin to diminish immediately after they recover from the disease.
                    """,
                )
                """
The number of months after an individual fully recovers from the pathogen
before the immunity conferred by having been infected begins to diminish,
where a month is 30 days.
                """
                loadKey("naturalWaningRate", id, 6)
                st.slider(
                    "Natural Immunity Waning Duration (Months)",
                    0,
                    12,
                    6,
                    disabled=not waningToggle,
                    on_change=saveKey,
                    args=["naturalWaningRate", id],
                    key=f"_naturalWaningRate{id}",
                    help="""
The number of months after an individual begins losing their immunity before
their resistance to the pathogen reaches its lowest point, where a month is 30
days.

If this parameter is set to 0, individuals will lose their immunity to the
pathogen all at once.
                    """,
                )
                """
The number of months after the immunity from having
fully recovered from the pathogen begins waning
before the efficacy of the immunity stabilises,
where a month is 30 days. Natural immunity in the
*Flusim* simulation will wane at a linear rate, so
this parameter represents how long it takes for the
immunity level to decrease from 100% immunity to
the final immunity probability defined above.

If this parameter is set to 0, the immunity
provided by recovering from the pathogen will never diminish.
                """
                loadKey("naturalWanedEfficacy", id, 0.5)
                st.slider(
                    "Natural Immunity Minimum Efficacy (Probability)",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.5,
                    format="percent",
                    disabled=not waningToggle,
                    key=f"_naturalWanedEfficacy{id}",
                    on_change=saveKey,
                    args=["naturalWanedEfficacy", id],
                    help="""
The efficacy of an individual's natural immunity after the full waning duration,
represented as the probability that they will remain healthy when exposed to
the pathogen.
                    """,
                )
                """
The final efficacy value that an individual's natural immunity after recovering
from the pathogen will approach as it begins to diminish, represented as the
probability that the individual will remain healthy when exposed to the pathogen
after their immunity is fully waned.
                """


def diseaseDescribe(scenarioID: int = 0, advanced: bool = False):
    """
    Function to describe the current pathogen parameters in natural language.

    Parameters:
        scenarioID (int): An integer that will be used to differentiate the parameters
            in different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to describe more complex parameters like
            location-specific transmission modifiers.
    """

    # Transmission
    st.subheader("Infection Transmission")
    st.markdown(f"""
        The probability that an interaction between an infected
        individual $I_i$ and a healthy individual $I_s$ with
        no immunity to the disease will result in the infection of $I_s$
        is calculated with the following formula
        [[1](https://www.doi.org/10.1371/journal.pone.0004005)]:
    """)
    st.latex(r"""
        P_{trans}(I_i, I_s) = 1 - \exp{(-\beta \times
        sym(I_i) \times inf(I_i) \times susc(I_s) \times
        \kappa)}
    """)
    # Get infectiousness/susceptibility values
    transValues, suscValues = {}, {}
    transAgeForm = idGet(
        "transAgeForm",
        scenarioID,
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
            if trans != 1.0:
                transValues[age] = trans
            if susc != 1.0:
                suscValues[age] = susc

    match len(transValues):
        case 0:
            transString = """
          The simulation does not currently give any
        age groups unique values of $inf(I_i)$;
        its value is always equal to 1.
            """
        case 1:
            ((age, value),) = transValues.items()
            transString = f"""
          When the infected individual $I_i$ belongs to
        the age group "{ageTimeDict[age]}", $inf(I_i)$ will be equal to {value:.5g}.
        For all other age groups, $inf(I_i)$ will be equal to 1.
            """
        case _:
            transString = """
          The value of $inf(I_i)$ will be one of the following values,
        depending on which age group the infected
        individual $I_i$ belongs to:
            """
            for age, value in sorted(transValues.items(), key=ageSort):
                transString += f"""\n
          - {ageTimeDict[age]}: {value:.5g}
                """
            if len(transValues) < 10:
                transString += """\n
          For all other age groups, $inf(I_i)$ will be equal to 1.
                """
    match len(suscValues):
        case 0:
            suscString = """
          The simulation does not currently give any
        age groups unique values of $susc(I_s)$;
        its value is always equal to 1.
            """
        case 1:
            ((age, value),) = suscValues.items()
            suscString = f"""
          When the healthy individual $I_s$ belongs to
        the age group "{ageTimeDict[age]}", $susc(I_s)$ will be equal to {value:.5g}.
        For all other age groups, $susc(I_s)$ will be equal to 1.
            """
        case _:
            suscString = """
          The value of $susc(I_s)$ will be one of the following values,
        depending on which age group the healthy
        individual $I_s$ belongs to:
            """
            for age, value in sorted(suscValues.items(), key=ageSort):
                suscString += f"""\n
          - {ageTimeDict[age]}: {value:.5g}
                """
            if len(suscValues) < 10:
                suscString += """\n
          For all other age groups, $susc(I_s)$ will be equal to 1.
                """

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
        $sym(I_i)$ will be equal to {postsym:.5g}. However, when the infected
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
            beta=idGet("beta", scenarioID, 0.0616),
            asym=idGet("betaAsymptomatic", scenarioID, 0.55),
            postsym=idGet("betaPostSymptomatic", scenarioID, 0.55),
            trans=transString,
            susc=suscString,
            household=idGet("householdKappa", scenarioID, 2.2),
            workplace=idGet("workKappa", scenarioID, 1.0),
            school=idGet("schoolKappa", scenarioID, 1.0),
            background=idGet("backgroundKappa", scenarioID, 1.0),
        )
    )

    # Life Cycle
    st.subheader("Infection Life Cycle")
    latentPeriod = idGet("latencyPeriod", scenarioID, 0.5)
    preSymptomPeriod = idGet("preSymptomPeriod", scenarioID, 1.0)
    symptomPeriod = idGet("symptomPeriod", scenarioID, 2.0)
    postSymptomPeriod = idGet("postSymptomPeriod", scenarioID, 2.5)
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
        
           The pre-symptomatic stage lasts for {preSym}.
        
        3. Symptomatic: The infected individual has begun showing symptoms,
        resulting in a high transmission rate and allowing them to be diagnosed
        with the pathogen.
        
           The symptomatic stage lasts for {sym}.
        
        4. Post-Symptomatic: The infected individual's condition has improved
        enough that they no longer show symptoms of the pathogen, but they can
        still spread the infection at a reduced transmission rate.
        
           The post-symptomatic stage lasts for {postSym}.
        
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
        
        The probability of an infection being asymptomatic is {youngAsym:.0%} for
        individuals who are 24 years old or younger, and {oldAsym:.0%} for individuals
        who are more than 24 years old.
    """.format(
            latent=dayCount(latentPeriod).lower(),
            preSym=dayCount(preSymptomPeriod).lower(),
            sym=dayCount(symptomPeriod).lower(),
            postSym=dayCount(postSymptomPeriod).lower(),
            total=dayCount(
                latentPeriod + preSymptomPeriod + symptomPeriod + postSymptomPeriod
            ).lower(),
            incubation=dayCount(latentPeriod + preSymptomPeriod).lower(),
            infectious=dayCount(
                preSymptomPeriod + symptomPeriod + postSymptomPeriod
            ).lower(),
            youngAsym=idGet("asymptomaticChild", scenarioID, 0.35),
            oldAsym=idGet("asymptomaticAdult", scenarioID, 0.35),
        )
    )

    # Seeding
    st.subheader("Infection Seeding")
    seedRate = idGet("seedRate", scenarioID, 0.25)
    if seedRate.is_integer():
        seedString = f"""
        During each cycle of the simulation (i.e. twice per day), infection
        seeding will infect {seedRate:.0g} random
        {"person" if seedRate == 1 else "people"}.
        """
    else:
        lowSeed, highSeed = int(seedRate), -(-seedRate // 1)
        seedString = f"""
        During each cycle of the simulation (i.e. twice per day), infection
        seeding will infect an average of {seedRate:.3g} random people. The
        number of infections will always be either {lowSeed:.0g} or
        {highSeed:.0g} each cycle; there is a {seedRate % 1:.0%} chance that
        there will be {highSeed:.0g} seeded infection{plural(highSeed)}.
        """
    startDay, endDay = idGet("seedPeriod", scenarioID, (1, 30))
    st.markdown("""
        When a simulation experiment begins, everyone within the simulation is
        healthy. Infection seeding is used to kickstart the spread of the pathogen
        by randomly selecting individuals to infect every cycle. The process of
        infection seeding represents the introduction of infected individuals from
        outside the population (e.g. tourists). Additionally, the random nature
        of infection seeding introduces stochasticity into the model and allows
        for variance between different experiment runs using the same parameters.

        {seedRate} Infection seeding occurs from Day {start} to Day {end} of each simulation.
    """.format(seedRate=seedString, start=startDay, end=endDay))

    # Health Burdens
    st.subheader("Health Burden Outcomes")
    # Get age-specific mortality values
    transValues, suscValues = {}, {}
    deathRate = idGet("deathRatio", scenarioID, 12.0)
    mortString = f"""
           For every 100,000 symptomatic individuals in the simulation, an average
        of {deathRate:.10g} individual{plural(deathRate)} will die.
    """
    if advanced:
        mortAgeForm = idGet(
            "mortAgeForm",
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Mortality Rate": [deathRate],
                },
            ),
        )
        mortValues = {
            age: mort
            for age, mort in zip(
                mortAgeForm["Age Group"],
                mortAgeForm["Mortality Rate"],
            )
            if age and mort != deathRate
        }
    else:
        mortValues = {}
    match len(mortValues):
        case 0:
            mortString += """
           The dashboard also possesses the ability to define separate mortality
        rates for different age groups; however, currently there are no age groups
        whose mortality rate differs from the above value.
            """
        case 1:
            ((age, value),) = mortValues.items()
            mortString += f"""
           The age group "{ageTimeDict[age]}" uses a different mortality rate;
        for every 100,000 symptomatic individuals who are in the age group
        "{ageTimeDict[age]}", an average of {value:.10g} individual{plural(value)}
        will die.
            """
        case 10:
            mortString = """
           Each age group in the simulation has its own mortality rate,
        defining the average number of deaths for every 100,000 symptomatic
        individuals in that age group. These mortality rates are listed below:
            """
            for age, value in sorted(mortValues.items(), key=ageSort):
                mortString += f"""\n
           - {ageTimeDict[age]}: {value:.10g} death{plural(value)} per 100,000 cases
                """
        case _:
            mortString += """
           Additionally, the following age groups use different mortality rates:
            """
            for age, value in sorted(mortValues.items(), key=ageSort):
                mortString += f"""\n
           - {ageTimeDict[age]}: {value:.10g} death{plural(value)} per 100,000 cases
                """
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
        of {hospitalisation:.10g} individuals will be hospitalised.

        4. ICU Visits: The individual has been admitted to the Intensive Care Unit
        (ICU) of a hospital.
        
           ICU visits are defined as a subset of hospitalisations; every
        hospitalised individual in the simulation has a {icu:.6g}% chance of
        visiting the ICU.

        5. Mortality: The individual has died as a direct result of the infection.
        
           {death}
    """.format(
            diagnosis=idGet("caseRatio", scenarioID, 50.0),
            gp=idGet("gpRatio", scenarioID, 17.0),
            hospitalisation=idGet("hospitalRatio", scenarioID, 320.0),
            icu=idGet("icuRatio", scenarioID, 20.0),
            death=mortString,
        )
    )

    # Waning
    # TODO: Come up with a more readable way of generating this description
    st.subheader("Natural Immunity")
    if not (advanced and idGet("naturalWaningToggle", scenarioID, False)):
        waningString = """
        Currently, natural immunity in the simulation lasts indefinitely; once an
        individual has recovered from the disease, they cannot be infected again
        for the remainder of the simulation.
        """
    else:
        waningDelay = idGet("naturalImmunityDuration", scenarioID, 2)
        waningDuration = idGet("naturalWaningRate", scenarioID, 6)
        wanedEfficacy = idGet("naturalWanedEfficacy", scenarioID, 0.5)
        if waningDelay == 0 and waningDuration == 0:
            if wanedEfficacy == 0:
                # No immunity
                waningString = """
        Currently, individuals in the simulation have no natural immunity; they
        can be infected again immediately after recovering from a previous infection.
                """
            else:
                # Constant lesser immunity
                waningString = f"""
        When an individual in the simulation recovers from the disease, their
        natural immunity has an efficacy of {wanedEfficacy:.0%}. This means that
        if the individual would be infected at any point, there is only a
        {wanedEfficacy:.0%} chance that they will remain healthy;
        {1 - wanedEfficacy:.0%} of the time, they will successfully be infected.
                """
        else:
            # Construct description using relevant elements
            waningString = """
        When an individual in the simulation recovers from the disease, they initially have full natural immunity and cannot be infected again. However, """
            if waningDuration == 0:
                if wanedEfficacy == 0:
                    # Lose all immunity all at once
                    waningString += f"""{waningDelay} month{plural(waningDelay)} ({dayCount(waningDelay * 30).lower()}) after the initial recovery, their natural immunity will disappear, and they will be able to be infected again. An individual who is infected a second time will regain their natural immunity once they recover.
                    """
                else:
                    # Drop to lower immunity all at once
                    waningString += f"""{waningDelay} month{plural(waningDelay)} ({dayCount(waningDelay * 30).lower()}) after the initial recovery, their natural immunity will wane, become less effective.

        The efficacy of an individual's natural immunity once it wanes is equal to {wanedEfficacy:.0%}. This means that if they would be infected, there is only a {wanedEfficacy:.0%} chance that they will remain healthy; {1 - wanedEfficacy:.0%} of the time, they will successfully be infected. If an individual with waned natural immunity is infected again, their immunity will begin waning
        from 100% again once they recover.
                    """
            elif waningDelay == 0:
                # Immediate waning
                waningString += f"""their natural immunity will immediately begin to wane, becoming less effective over time. The individual will gradually become more susceptible to infection over a period of {waningDuration} month{plural(waningDuration)} ({dayCount(waningDuration * 30).lower()}), after which """
                if wanedEfficacy == 0:
                    waningString += f"""they will have lost their immunity entirely.

        The efficacy of natural immunity linearly decreases from 100% to 0% over the individual's {waningDuration} month waning period. This means that their immunity's efficacy will be at 50% halfway through this period; if they were to be infected at this point, there is a 50% chance for them to remain healthy. If an individual with waned natural immunity is infected again, their immunity will begin waning from 100% again once they recover.
                    """
                else:
                    waningString += f"""their natural immunity will be at its weakest.

        The efficacy of an individual's natural immunity at its weakest point is equal to {wanedEfficacy:.0%}. This means that if they would be infected, there is only a {wanedEfficacy:.0%} chance that they will remain healthy; {1 - wanedEfficacy:.0%} of the time, they will successfully be infected. The efficacy of natural immunity linearly decreases from 100% to {wanedEfficacy:.0%} over the individual's {waningDuration} month waning period. If an individual with waned natural immunity is infected again, their immunity will begin waning from 100% again once they recover.
                    """
            else:
                waningString += f"""{waningDelay} month{plural(waningDelay)} ({dayCount(waningDelay * 30).lower()}) after the initial recovery, their natural immunity will begin to wane, becoming less effective over time. The individual will gradually become more susceptible to infection for {waningDuration} month{plural(waningDuration)} ({dayCount(waningDuration * 30).lower()}), after which """
                if wanedEfficacy == 0:
                    waningString += f"""they will have lost their immunity entirely.

        The efficacy of natural immunity linearly decreases from 100% to 0% over the individual's {waningDuration} month waning period. This means that their immunity's efficacy will be at 50% halfway through this period; if they were to be infected at this point, there is a 50% chance for them to remain healthy. If an individual with waned natural immunity is infected again, their immunity will begin waning from 100% again once they recover.
                    """
                else:
                    waningString += f"""their natural immunity will be at its weakest.

        The efficacy of an individual's natural immunity at its weakest point is equal to {wanedEfficacy:.0%}. This means that if they would be infected, there is only a {wanedEfficacy:.0%} chance that they will remain healthy; {1 - wanedEfficacy:.0%} of the time, they will successfully be infected. The efficacy of natural immunity linearly decreases from 100% to {wanedEfficacy:.0%} over the individual's {waningDuration} month waning period. If an individual with waned natural immunity is infected again, their immunity will begin waning from 100% again once they recover.
                    """

    st.markdown(f"""
        Individuals in the simulation are able to become immune to the pathogen
        in two different ways: by recovering from the infection, or by receiving
        a vaccine. The immunity conferred by recovering from infection is known
        as natural immunity.
                
        {waningString}
    """)


def diseaseSaveSchema(
    schema: Parameters,
    id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
    includeDashboard: bool = False,
):
    """
    Function to populate the Pydantic model schema with pathogen parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to account for more complex parameters like
            location-specific transmission modifiers.

        baseline (Parameters, optional): A Pydantic model representing the parameters
            set for the baseline scenario. When `id` is not 0, this will be used
            to omit parameters that are already set in the baseline from the final
            scenario.

        includeDashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like GP rate in the generated schema.
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
        globalDeathRate = round(idGet("deathRatio", id, 12.0) / 100000, 10)
        ageScenarioParams.mort = globalDeathRate

        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter
            if schema.Scenario_Parameter
            else scenarioParameters()
        )

        # Advanced parameter differences
        if advanced:
            scenarioParams.prob_asymptomatic_young = idGet(
                "asymptomaticChild", id, 0.35
            )
            scenarioParams.prob_asymptomatic = idGet("asymptomaticAdult", id, 0.35)
            scenarioParams.kappa_household = idGet("householdKappa", id, 2.2)
            scenarioParams.kappa_child_education = idGet("schoolKappa", id, 1.0)
            scenarioParams.kappa_workplace = idGet("workKappa", id, 1.0)
            scenarioParams.kappa_background = idGet("backgroundKappa", id, 1.0)
            mortAgeForm = idGet(
                "mortAgeForm",
                id,
                pd.DataFrame(
                    {
                        "Age Group": [None],
                        "Mortality Rate": [globalDeathRate],
                    },
                ),
            )
            for age, mort in zip(
                mortAgeForm["Age Group"],
                mortAgeForm["Mortality Rate"],
            ):
                roundedMort = round(mort / 100000, 10)
                if age and roundedMort != globalDeathRate:
                    setattr(scenarioParams, f"{age}_mort", roundedMort)
        else:
            probAsymptomatic = idGet("asymptomaticBoth", id, 0.35)
            scenarioParams.prob_asymptomatic_young = probAsymptomatic
            scenarioParams.prob_asymptomatic = probAsymptomatic

        # Immunity Waning
        if advanced and idGet("naturalWaningToggle", id, False):
            wanedEfficacy = idGet("naturalWanedEfficacy", id, 0.5)
            waningRate = idGet("naturalWaningRate", id, 6) * 60
            scenarioParams.infection_waning_cycle_delay = (
                idGet("naturalImmunityDuration", id, 2) * 60
            )
            scenarioParams.infection_waned_protection = wanedEfficacy
            scenarioParams.infection_waning_rate_per_cycle = (
                1.0 if waningRate == 0 else (1.0 - wanedEfficacy) / waningRate
            )
        else:
            # Set immunity delay to 99999, effectively disabling it
            # TODO: Make sure simulation accepts delays this high
            scenarioParams.infection_waning_cycle_delay = 99999
        # Infection Seeding
        scenarioParams.seed_rate = idGet("seedRate", id, 0.25)
        scenarioParams.seeding_start_cycle = (seedPeriod[0] - 1) * 2
        scenarioParams.seeding_duration = (seedPeriod[1] - seedPeriod[0] + 1) * 2
        # Transmission
        scenarioParams.beta_asymptomatic = idGet("betaAsymptomatic", id, 0.55)
        scenarioParams.beta_post_symptomatic = idGet("betaPostSymptomatic", id, 0.55)
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
        scenarioParams.prob_diagnosis = round(idGet("caseRatio", id, 50.0) / 100, 6)
        hospitalRate = idGet("hospitalRatio", id, 320.0) / 100000
        scenarioParams.prob_hospitalisation = round(hospitalRate, 10)
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
                if trans != 1.0:
                    setattr(scenarioParams, f"{age}_trans", trans)
                if susc != 1.0:
                    setattr(scenarioParams, f"{age}_susc", susc)
        """
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
                idGet("deathRatio", id, globalDeathRate, f"-{i}"),
            )"""

        # Save the updated parameters, removing redundant baseline values
        ageTableParams = set().union(
            *[{f"{age}_trans", f"{age}_susc", f"{age}_mort"} for age in ageTimeDict]
        )
        if id > 0 and baseline is not None:
            schemaRemoveBaseline(
                ageScenarioParams, baseline.Scenario_ParameterWithAgePrefix
            )
            schemaRemoveBaseline(
                scenarioParams, baseline.Scenario_Parameter, ignore=ageTableParams
            )

        if ageScenarioParams:
            schema.Scenario_ParameterWithAgePrefix = ageScenarioParams
        if scenarioParams:
            schema.Scenario_Parameter = scenarioParams

        # Dashboard Parameters
        dashboardParams = (
            schema.Dashboard_Parameter
            if schema.Dashboard_Parameter
            else dashboardParameters()
        )
        if includeDashboard:
            dashboardParams.prob_gp = round(idGet("gpRatio", id, 17.0) / 100, 6)
            dashboardParams.prob_icu = round(
                hospitalRate * idGet("icuRatio", id, 20.0) / 100, 10
            )
            if id > 0 and baseline is not None:
                schemaRemoveBaseline(dashboardParams, baseline.Dashboard_Parameter)
            if dashboardParams:
                schema.Dashboard_Parameter = dashboardParams
    except (ValueError, ValidationError) as e:
        diseaseLog.error(
            (
                f"[diseaseParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e


def diseaseLoadSchema(schema: Parameters, scenarioID: int = 0):
    """
    Function to read pathogen parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

    Raises:
        ValidationError: If some but not all of the parameters needed to
            define natural immunity waning/infection seeding/infection life
            cycle periods are included in a baseline schema.
    """
    # Strain Parameters
    schemaStrain = schema.Scenario_Strain
    if schemaStrain is not None:
        updateParamFromSchema("beta", schemaStrain[0].Beta, scenarioID)

    # Global Age Parameters
    schemaAge = schema.Scenario_ParameterWithAgePrefix
    if schemaAge is not None and schemaAge.mort is not None:
        updateParamFromSchema(
            "deathRatio", round(schemaAge.mort * 100000, 6), scenarioID
        )

    # Dashboard Parameters
    schemaDash = schema.Dashboard_Parameter
    if schemaDash is not None:
        if schemaDash.prob_gp is not None:
            updateParamFromSchema(
                "gpRatio", round(schemaDash.prob_gp * 100, 6), scenarioID
            )
        icuRate = schemaDash.prob_icu
    else:
        icuRate = None

    # General Scenario Parameters
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is not None:
        simLength = session.get("cycleCount", 360)
        paramDict = {p: v for p, v in vars(schemaParameters).items() if v is not None}

        # Use dictionary to convert schema parameters into dashboard values
        paramConvert = {
            "seed_rate": ("seedRate", lambda x: x),
            "beta_asymptomatic": ("betaAsymptomatic", lambda x: x),
            "beta_post_symptomatic": ("betaPostSymptomatic", lambda x: x),
            "kappa_household": ("householdKappa", lambda x: x),
            "kappa_child_education": ("schoolKappa", lambda x: x),
            "kappa_workplace": ("workKappa", lambda x: x),
            "kappa_background": ("backgroundKappa", lambda x: x),
            "prob_asymptomatic": ("asymptomaticAdult", lambda x: x),
            "prob_asymptomatic_young": ("asymptomaticChild", lambda x: x),
            "prob_diagnosis": ("caseRatio", lambda x: round(x * 100, 6)),
            "infection_waning_cycle_delay": (
                "naturalImmunityDuration",
                lambda x: x // 60,
            ),
        }
        simpleParams = {p: v for p, v in paramConvert.items() if p in paramDict}
        for parameter, (key, formatFunc) in simpleParams.items():
            updateParamFromSchema(key, formatFunc(paramDict[parameter]), scenarioID)

        # Hospitalisation and ICU ratio
        if "prob_hospitalisation" in paramDict or icuRate is not None:
            hospitalRate = paramDict["prob_hospitalisation"]
            if None in {hospitalRate, icuRate} and scenarioID == 0:
                raise AssertionError(
                    "Hospitalisation and ICU rate parameters were only partially "
                    "defined for the baseline scenario"
                )

            # Use baseline values to plug None gaps
            baseHospitalRate = idGet("hospitalRatio", 0, 320.0)
            baseICUProb = idGet("icuRatio", 0, 20.0)
            if hospitalRate is None:
                hospitalRate = baseHospitalRate / 100000
            if icuRate is None:
                icuRate = hospitalRate * baseICUProb / 100

            # Calculate ICU proportion
            updateParamFromSchema(
                "hospitalRatio", round(hospitalRate * 100000, 6), scenarioID
            )
            updateParamFromSchema(
                "icuRatio",
                round(icuRate * 100 / hospitalRate, 6) if hospitalRate > 0.0 else 0.0,
                scenarioID,
            )

        # Advanced parameter differences
        if "prob_asymptomatic" in paramDict:
            updateParamFromSchema(
                "asymptomaticBoth", schemaParameters.prob_asymptomatic, scenarioID
            )
        """if (
            paramDict.get("infection_waning_cycle_delay", 99999)
            < simLength
        ):
            updateParamFromSchema("naturalWaningToggle", True, scenarioID)"""

        # Natural immunity waning
        if "infection_waning_cycle_delay" in paramDict:
            useWaning = paramDict["infection_waning_cycle_delay"] != 99999
        else:
            useWaning = idGet("naturalWaningToggle", 0, False)
        updateParamFromSchema("naturalWaningToggle", useWaning, scenarioID)

        # Period definitions
        # TODO: Handle baseline validation errors better
        # TODO: There might be some issues here; check to see if
        # decimals are getting ignored by the strict sliders
        if useWaning and {
            "infection_waned_protection",
            "infection_waning_rate_per_cycle",
        }.intersection(paramDict):
            # Waning immunity (if not disabled)
            # Ensure baseline has all values
            wanedEfficacy = schemaParameters.infection_waned_protection
            waningRate = schemaParameters.infection_waning_rate_per_cycle
            if None in {wanedEfficacy, waningRate} and scenarioID == 0:
                raise AssertionError(
                    "Waning efficacy parameters were only partially "
                    "defined for the baseline scenario"
                )

            # Use baseline values to plug None gaps
            baseWanedEfficacy = idGet("naturalWanedEfficacy", 0, 0.5)
            baseWaningDuration = idGet("naturalWaningRate", 0, 6)
            if wanedEfficacy is None:
                wanedEfficacy = baseWanedEfficacy
            if waningRate is None:
                waningRate = (
                    1.0
                    if baseWaningDuration == 0
                    else (1.0 - baseWanedEfficacy) / (baseWaningDuration * 60)
                )

            # Calculate efficacy waning duration
            updateParamFromSchema("naturalWaningEfficacy", wanedEfficacy, scenarioID)
            if waningRate in {0.0, 1.0}:
                updateParamFromSchema("naturalWaningRate", 0, scenarioID)
            else:
                updateParamFromSchema(
                    "naturalWaningRate",
                    int((1.0 - wanedEfficacy) / (waningRate * 60)),
                    scenarioID,
                )

        if {"seeding_start_cycle", "seeding_duration"}.intersection(paramDict):
            # Seeding period
            # Ensure baseline has all values
            seedStart = schemaParameters.seeding_start_cycle
            seedLength = schemaParameters.seeding_duration
            if None in {seedStart, seedLength} and scenarioID == 0:
                raise AssertionError(
                    "Infection seeding period parameters were only partially "
                    "defined for the baseline scenario"
                )

            # Use baseline values to plug None gaps
            basePeriodStart, basePeriodEnd = idGet("seedPeriod", 0, (1, 30))
            if seedStart is None:
                seedStart = (basePeriodStart - 1) * 2
            if seedLength is None:
                seedLength = (basePeriodEnd - basePeriodStart + 1) * 2

            # Calculate seeding period
            seedPeriodStart = (seedStart // 2) + 1
            seedPeriodEnd = min(simLength, (seedStart + seedLength) // 2)
            updateParamFromSchema(
                "seedPeriod", (seedPeriodStart, seedPeriodEnd), scenarioID
            )

        if {
            "transmissibility_delay",
            "symptom_latency",
            "generation_time",
            "infection_duration",
        }.intersection(paramDict):
            # Infection life cycle periods
            # Ensure baseline has all values
            transmissibilityDelay = schemaParameters.transmissibility_delay
            symptomLatency = schemaParameters.symptom_latency
            generationTime = schemaParameters.generation_time
            infectionDuration = schemaParameters.infection_duration
            if (
                None
                in {
                    transmissibilityDelay,
                    symptomLatency,
                    generationTime,
                    infectionDuration,
                }
                and scenarioID == 0
            ):
                raise AssertionError(
                    "Infection life cycle parameters were only partially "
                    "defined for the baseline scenario"
                )

            # Use baseline values to plug None gaps
            baseLatency = idGet("latencyPeriod", 0, 0.5)
            basePreSymptom = idGet("preSymptomPeriod", 0, 1.0)
            baseSymptom = idGet("symptomPeriod", 0, 2.0)
            basePostSymptom = idGet("postSymptomPeriod", 0, 2.5)
            if transmissibilityDelay is None:
                transmissibilityDelay = baseLatency * 2
            if symptomLatency is None:
                symptomLatency = (baseLatency + basePreSymptom) * 2
            if generationTime is None:
                generationTime = (baseLatency + basePreSymptom + baseSymptom) * 2
            if infectionDuration is None:
                infectionDuration = (
                    baseLatency + basePreSymptom + baseSymptom + basePostSymptom
                ) * 2

            updateParamFromSchema(
                "latencyPeriod", transmissibilityDelay / 2, scenarioID
            )
            updateParamFromSchema(
                "preSymptomPeriod",
                (symptomLatency - transmissibilityDelay) / 2,
                scenarioID,
            )
            updateParamFromSchema(
                "symptomPeriod",
                (generationTime - symptomLatency) / 2,
                scenarioID,
            )
            updateParamFromSchema(
                "postSymptomPeriod",
                (infectionDuration - generationTime) / 2,
                scenarioID,
            )

        # Tables

        # Age-specific transmission
        transTable = pd.DataFrame(
            columns=("Age Group", "Infectiousness", "Susceptibility")
        )
        transParams = {
            p.removesuffix("_trans"): v
            for p, v in paramDict.items()
            if p.endswith("_trans")
        }
        suscParams = {
            p.removesuffix("_susc"): v
            for p, v in paramDict.items()
            if p.endswith("_susc")
        }
        transAges = sorted(
            set(transParams.keys()) | set(suscParams.keys()),
            key=lambda x: list(ageTimeDict).index(x),
        )
        for age in transAges:
            transValue = transParams.get(age, 1.0)
            suscValue = suscParams.get(age, 1.0)
            if transValue != 1.0 or suscValue != 1.0:
                transTable.loc[transTable.shape[0]] = [age, transValue, suscValue]
        updateTableFromSchema(
            "transAgeForm",
            transTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Infectiousness": [1.0],
                    "Susceptibility": [1.0],
                },
            ),
        )

        # Age-specific mortality
        mortTable = pd.DataFrame(columns=("Age Group", "Mortality Rate"))
        mortParams = {
            p.removesuffix("_mort"): round(v * 100000, 6) if v is not None else None
            for p, v in paramDict.items()
            if p.endswith("_mort")
        }
        for param, value in mortParams.items():
            mortTable.loc[mortTable.shape[0]] = [param, value]
        updateTableFromSchema(
            "mortAgeForm",
            mortTable,
            scenarioID,
            pd.DataFrame(
                {
                    "Age Group": [None],
                    "Mortality Rate": [idGet("deathRatio", scenarioID, 12.0)],
                },
            ),
        )
