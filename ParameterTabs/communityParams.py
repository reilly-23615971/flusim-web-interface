# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where community parameters can be modified

# Imports
import logging
import numpy as np
import streamlit as st
from pydantic import ValidationError
from ClientResources.InterfaceFunctions import (
    addFormRow,
    deleteFormRow,
    saveKey,
    loadKey,
    idGet,
    getRemainingGroups,
    dayCount,
)
from ClientResources.SharedResources import ageCategories
from ClientResources.ModelSchema import (
    Parameters,
    scenarioParameters,
    ageScenarioParameters,
)

# Logging
communityLog = logging.getLogger(__name__)

"""
Function to generate the parameters for the simulation environment in a
specified container with scenario differentiation

Parameters:
    id: An integer that will be used to differentiate the parameters in
    different instances of the tab by adding a number to the Streamlit
    session state variables.
"""


@st.fragment
def buildCommunityTab(id):
    # Initialise session variables needed by the disease forms
    sessionParameters = {f"deathRowCount{id}": 0}
    for parameter, default in sessionParameters.items():
        st.session_state[parameter] = st.session_state.get(parameter, default)

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    ageGroupSets = {
        f"deathRemainingAgeGroups{id}": (f"deathRowCount{id}", f"deathAgeGroup{id}-")
    }

    # Use function to recalculate remaining group parameters
    getRemainingGroups(ageGroupSets, ageCategories.keys())

    # Tab Content
    st.header("Community Parameters")
    st.markdown(
        """
        This tab contains parameters relating to the community that
        is simulated by the model, including the likelihood of
        different health burden outcomes, how individuals react to
        the disease, and the size of groups that individuals form
        in different locations.
    """
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
        # TODO: Move these to Disease tab
        # TODO: Make default values more realistic
        loadKey("caseRatio", id, 0.5)
        st.select_slider(
            "Diagnosed Case Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.5,
            key=f"_caseRatio{id}",
            on_change=saveKey,
            args=["caseRatio", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The probability that an infected, symptomatic
                individual will be formally diagnosed as a
                confirmed case of the disease.
            """,
        )
        loadKey("gpRatio", id, 0.35)
        st.select_slider(
            "GP Visit Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.35,
            key=f"_gpRatio{id}",
            on_change=saveKey,
            args=["gpRatio", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The probability that an infected, symptomatic
                individual will visit their general practitioner
                (GP) as a result of the disease.
            """,
        )
        loadKey("hospitalRatio", id, 0.25)
        st.select_slider(
            "Hospitalisation Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.25,
            key=f"_hospitalRatio{id}",
            on_change=saveKey,
            args=["hospitalRatio", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The probability that an infected, symptomatic
                individual will be admitted to a hospital as a
                result of the disease.
            """,
        )
        loadKey("icuRatio", id, 0.1)
        st.select_slider(
            "ICU Visit Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.1,
            key=f"_icuRatio{id}",
            on_change=saveKey,
            args=["icuRatio", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The probability that an infected, symptomatic
                individual will be admitted to a hospital's
                intensive care unit (ICU) as a result of the
                disease.
            """,
        )
        loadKey("deathRatio", id, 0.05)
        deathRate = st.select_slider(
            "Mortality Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.05,
            key=f"_deathRatio{id}",
            on_change=saveKey,
            args=["deathRatio", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The base probability that an infected, symptomatic
                individual will die as a direct result of the
                disease.
            """,
        )

        # Age-based Mortality
        st.markdown(
            """
            ### Age-Specific Mortality Rate

            This section allows for unique likelihoods of death to
            be defined for each age group, overriding the global
            rate defined above.
        """
        )
        # Save relevant params as variables to avoid lookups
        deathRowCount = st.session_state[f"deathRowCount{id}"]
        deathRemainingGroups = st.session_state[f"deathRemainingAgeGroups{id}"]
        deathAgeContainer = st.container()
        for i in range(deathRowCount):
            (deathGroupColumn, deathRateColumn, deathRemoveColumn) = (
                deathAgeContainer.columns(
                    (0.25, 0.55, 0.2), vertical_alignment="center"
                )
            )
            deathCurrentGroup = st.session_state.get(f"deathAgeGroup{id}-{i}")

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
            loadKey("deathRatio", id, 0.05, f"-{i}")
            with deathRateColumn:
                st.select_slider(
                    "Mortality Rate (Probability)",
                    np.linspace(0.0, 1.0, 201),
                    0.05,
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
        )

    # Disease Response Parameters
    with st.expander("Withdrawals and Diagnosis"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control how individuals in the
            community will react to symptoms of the disease,
            including how likely they are to withdraw from
            work/school and how long it takes until they have their
            infection officially diagnosed as a case.

            Note that this section does not contain parameters
            related to social distancing and other programs
            implemented by the government to reduce the spread of
            the disease. These interventions can be configured
            using the parameters in the "Vaccinations and NPIs" tab.
        """
        )

        # The parameters in question
        loadKey("withdrawalWork", id, 0.5)
        st.select_slider(
            "Work Withdrawal Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.5,
            format_func=lambda x: f"{100 * x:0.3g}%",
            on_change=saveKey,
            args=["withdrawalWork", id],  # type: ignore
            key=f"_withdrawalWork{id}",
            help="""
                The probability of an infected individual in the
                simulation voluntarily withdrawing from work after
                becoming symptomatic.
            """,
        )
        loadKey("withdrawalSchool", id, 0.9)
        st.select_slider(
            "School Withdrawal Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            0.9,
            format_func=lambda x: f"{100 * x:0.3g}%",
            on_change=saveKey,
            args=["withdrawalSchool", id],  # type: ignore
            key=f"_withdrawalSchool{id}",
            help="""
                The probability of an infected individual in the
                simulation voluntarily withdrawing from school
                after becoming symptomatic.
            """,
        )
        loadKey("diagnosisDelay", id, 1)
        st.select_slider(
            "Case Diagnosis Delay (Days)",
            range(15),
            1,
            on_change=saveKey,
            args=["diagnosisDelay", id],  # type: ignore
            format_func=dayCount,
            key=f"_diagnosisDelay{id}",
            help="""
                The number of days after an individual begins
                showing symptoms of the disease before their
                infection can be formally diagnosed as a confirmed
                case.
            """,
        )

    # Behaviour Parameters
    with st.expander("Population Behaviours"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control various aspects of how
            individuals behave in the simulation, including the
            size of groups that they form and how many people they
            interact with each day.
        """
        )

        # BCC and Child Supervision
        loadKey("bccRate", id, 4.0)
        st.slider(
            (
                (
                    "Background Contact Count (Average "
                    "Number of Interactions per Person per Day)"
                )
            ),
            0.0,
            8.0,
            4.0,
            key=f"_bccRate{id}",
            on_change=saveKey,
            args=["bccRate", id],  # type: ignore
            help="""
                The average number of other people each individual
                will interact with in the background phase of each
                day in the simulation. These interactions emulate
                interactions outside of locations simulated by the
                model.
            """,
        )
        loadKey("childSupervision", id, 1.0)
        st.select_slider(
            "Child Supervision Rate (Probability)",
            np.linspace(0.0, 1.0, 201),
            1.0,
            key=f"_childSupervision{id}",
            on_change=saveKey,
            args=["childSupervision", id],  # type: ignore
            format_func=lambda x: f"{100 * x:0.3g}%",
            help="""
                The probability that an adult in the simulation
                will remain at their household if there is at least
                one child present and no other adults are at home.
            """,
        )

        # Group Sizes
        loadKey("maxClassSize", id, 10)
        st.slider(
            "Maximum School Class Size (Number of People)",
            0,
            25,
            10,
            key=f"_maxClassSize{id}",
            on_change=saveKey,
            args=["maxClassSize", id],  # type: ignore
            help="""
                The maximum size of school classes within
                schools and childcare facilities in the simulation.
            """,
        )
        # TODO: Triple check if this affects the simulation
        loadKey("maxClassCount", id, 1)
        st.slider(
            "Number of School Class Subgroups",
            1,
            5,
            1,
            on_change=saveKey,
            args=["maxClassCount", id],  # type: ignore
            key=f"_maxClassCount{id}",
            help="""
                The maximum number of subgroups that may exist
                within a single school class in the simulation.
                Subgroups are defined as sets of individuals that
                regularly interact with each other but not with the
                rest of the class.
            """,
        )
        loadKey("maxWorkGroupSize", id, 10)
        st.slider(
            "Maximum Work Group Size (Number of People)",
            0,
            25,
            10,
            key=f"_maxWorkGroupSize{id}",
            on_change=saveKey,
            args=["maxWorkGroupSize", id],  # type: ignore
            help="""
                The maximum size of groups within workplaces in the
                simulation.
            """,
        )


"""
Function to populate the Pydantic model schema with the parameters in
this tab with scenario differentiation

Parameters:
    schema: The Pydantic model (specifically an object in the
    Parameters class) that the parameters will be populated into.

    id: An integer that will be used to differentiate the parameters in
    different instances of the tab by adding a number to the Streamlit
    session state variables. A value of 0 means that this is the
    baseline scenario and will be treated accordingly.
"""


def communitySchema(schema, id=0):
    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Scenario Parameters With Age Prefix
        ageScenarioParams = (
            schema.Scenario_ParameterWithAgePrefix
            if schema.Scenario_ParameterWithAgePrefix
            else ageScenarioParameters()
        )
        deathRate = idGet("deathRatio", id, 0.05)
        ageScenarioParams.mort = deathRate
        schema.Scenario_ParameterWithAgePrefix = ageScenarioParams

        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter
            if schema.Scenario_Parameter
            else scenarioParameters()
        )
        scenarioParams.prob_diagnosis = idGet("caseRatio", id, 0.5)
        scenarioParams.prob_hospitalisation = idGet("hospitalRatio", id, 0.25)
        scenarioParams.prob_withdrawal = idGet("withdrawalWork", id, 0.5)
        scenarioParams.prob_school_withdrawal = idGet("withdrawalSchool", id, 0.9)
        scenarioParams.diagnosis_delay = idGet("diagnosisDelay", id, 1) * 2
        scenarioParams.background_contact_count = idGet("bccRate", id, 4.0)
        scenarioParams.prob_child_supervision = idGet("childSupervision", id, 1.0)
        # scenarioParams.max_class_count = idGet('maxClassCount', id, 1)
        scenarioParams.max_class_size = idGet("maxClassSize", id, 10)
        scenarioParams.max_workgroup_size = idGet("maxWorkGroupSize", id, 10)
        """
        scenarioParams.max_adult_class_size = idGet("maxAdultClassSize", id, 10)
        scenarioParams.max_neighbourgroup_size = idGet(
            'maxNeighborGroupSize', id, 10
        )
        scenarioParams.max_churchgroup_size = idGet(
            'maxChurchGroupSize', id, 10
        )
        """
        # Procedural Scenario Parameters (age specific)
        for i in range(st.session_state.get(f"deathRowCount{id}", 0)):
            setattr(
                scenarioParams,
                f"{ageCategories[st.session_state[f'deathAgeGroup{id}-{i}']]}_mort",
                idGet("deathRatio", id, deathRate, f"-{i}"),
            )
        # Save the updated params
        schema.Scenario_Parameter = scenarioParams
    except (ValueError, ValidationError) as e:
        communityLog.error(
            (
                f"[communityParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e
