# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where community parameters can be modified

# Imports
import logging

import numpy as np
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    dayCount,
    idGet,
    loadKey,
    saveKey,
)
from ClientResources.ModelSchema import Parameters, scenarioParameters

# Logging
communityLog = logging.getLogger(__name__)


@st.fragment
def buildCommunityTab(id: int):
    """
    Function to generate the parameters for the simulation environment in a
    specified container with scenario differentiation

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.
    """
    # Initialise session variables needed by the disease forms
    # sessionParameters = {f"deathRowCount{id}": 0}
    # for parameter, default in sessionParameters.items():
    # st.session_state[parameter] = st.session_state.get(parameter, default)

    # Ensure age selections only give possible parameters
    # Dictionary format: 'remaining groups variable': (
    #   'number of rows variable', 'group row variable prefix'
    # )
    # ageGroupSets = {
    # f"deathRemainingAgeGroups{id}": (f"deathRowCount{id}", f"deathAgeGroup{id}-")
    # }

    # Use function to recalculate remaining group parameters
    # getRemainingGroups(ageGroupSets, ageCategories.keys())

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


def communitySchema(schema: Parameters, id: int = 0):
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

        # Scenario Parameters
        scenarioParams = (
            schema.Scenario_Parameter
            if schema.Scenario_Parameter
            else scenarioParameters()
        )
        scenarioParams.diagnosis_delay = idGet("diagnosisDelay", id, 1) * 2
        scenarioParams.background_contact_count = idGet("bccRate", id, 4.0)
        scenarioParams.prob_child_supervision = idGet("childSupervision", id, 1.0)
        scenarioParams.max_class_count = idGet("maxClassCount", id, 1)
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
