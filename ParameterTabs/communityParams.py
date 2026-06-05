# Flusim Web Interface Application
# Developed by Reilly Evans
# Functionised tab where community parameters can be modified

# Imports
import logging
from typing import Optional

import numpy as np
import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import (
    plural,
    schemaRemoveBaseline,
    schemaUpdate,
)
from ClientResources.ModelSchema import Parameters, scenarioParameters
from ClientResources.ParameterFunctions import (
    idGet,
    loadKey,
    saveKey,
    updateParamFromSchema,
)

# Logging
communityLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


@st.fragment
def buildCommunityTab(id: int, advanced: bool = False):
    """
    Function to generate the parameters for the simulation environment in a
    specified container with scenario differentiation.

    Parameters:
        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables.

        advanced (bool): Set to `True` to show more complex parameters like
            child supervision rate.
    """

    # Tab Content
    st.header("Community-Related Parameters")
    st.markdown("""
        This tab contains parameters relating to the community that
        is simulated by the model, including the likelihood of
        different health burden outcomes, how individuals react to
        the pathogen, and the size of groups that individuals form
        in different locations.
    """)

    # Withdrawal and BCC
    '''with st.expander("Withdrawals and Diagnosis"):
        # Describe what sort of parameters are here
        st.markdown(
            """
            These parameters control how individuals in the
            community will react to symptoms of the pathogen,
            including how likely they are to withdraw from
            work/school and how long it takes until they have their
            infection officially diagnosed as a case.

            Note that this section does not contain parameters
            related to social distancing and other programs
            implemented by the government to reduce the spread of
            the pathogen. These interventions can be configured
            using the parameters in :primary-badge[:material/medical_mask: NPIs].
        """
        )'''
    st.subheader("Withdrawals and Contact", divider="grey")

    # The parameters in question
    loadKey("withdrawalWork", id, 0.5)
    st.slider(
        "Work Withdrawal Rate (Probability)",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        format="percent",
        on_change=saveKey,
        args=["withdrawalWork", id],
        key=f"_withdrawalWork{id}",
        help="""
The probability of an infected individual in the
simulation not going to work after
becoming symptomatic.
        """,
    )
    loadKey("withdrawalSchool", id, 0.9)
    st.slider(
        "School Withdrawal Rate (Probability)",
        min_value=0.0,
        max_value=1.0,
        value=0.9,
        format="percent",
        on_change=saveKey,
        args=["withdrawalSchool", id],
        key=f"_withdrawalSchool{id}",
        help="""
The probability of an infected individual in the
simulation not going to school
after becoming symptomatic.
        """,
    )
    loadKey("bccRate", id, 4.0)
    # Note that this is daily, not once per cycle
    st.slider(
        "Background Contact Count (Interactions per Person per Day)",
        min_value=0.0,
        max_value=10.0,
        value=4.0,
        step=0.25,
        key=f"_bccRate{id}",
        on_change=saveKey,
        args=["bccRate", id],
        help="""
The average number of other people each individual will contact in the
background phase of each day in the simulation. This is used to emulate
interactions that occur in locations not modelled in the simulation, such
as public transport.
        """,
    )

    if advanced:
        # Other Community Parameters
        st.subheader("Advanced Community Settings", divider="grey")

        # TODO: Default to 0
        loadKey("diagnosisDelay", id, 0)
        st.slider(
            "Case Diagnosis Delay (Days)",
            min_value=0.0,
            max_value=14.0,
            value=0.0,
            step=0.5,
            format="%f Day(s)",
            on_change=saveKey,
            args=["diagnosisDelay", id],
            key=f"_diagnosisDelay{id}",
            help="""
The number of days after an individual begins showing symptoms of the pathogen
before their infection can be formally diagnosed as a confirmed case. This may
affect non-pharmaceutical interventions that use case numbers to choose when to
come into effect.
            """,
        )

        loadKey("childSupervision", id, 1.0)
        st.slider(
            "Child Supervision Rate (Probability)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            format="percent",
            key=f"_childSupervision{id}",
            on_change=saveKey,
            args=["childSupervision", id],
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
            format="%f Person(s)",
            on_change=saveKey,
            args=["maxClassSize", id],
            help="""
The maximum size of classes within schools in the simulation.
            """,
            # TODO: if childcare becomes relevant again mention it in the tooltip
        )

        '''loadKey("maxClassCount", id, 1)
        st.slider(
            "Number of School Class Subgroups",
            1,
            5,
            1,
            on_change=saveKey,
            args=["maxClassCount", id],
            key=f"_maxClassCount{id}",
            help="""
The maximum number of subgroups that may exist
within a single school class in the simulation.
Subgroups are defined as sets of individuals that
regularly interact with each other but not with the
rest of the class.
            """,
        )'''
        loadKey("maxWorkGroupSize", id, 10)
        st.slider(
            "Maximum Work Group Size (Number of People)",
            0,
            25,
            10,
            format="%f Person(s)",
            key=f"_maxWorkGroupSize{id}",
            on_change=saveKey,
            args=["maxWorkGroupSize", id],
            help="""
The maximum size of groups within workplaces in the simulation.
            """,
        )


def communityDescribe(scenarioID: int = 0, advanced: bool = False):
    """
    Function to describe the current community parameters in natural language.

    Parameters:
        scenarioID (int): An integer that will be used to differentiate the parameters
            in different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to describe more complex parameters like
            child supervision rate.
    """

    # Withdrawal
    st.subheader("Withdrawal Rates")
    st.markdown(
        """
        Most individuals in the simulation will attend a school or workplace every
        day from Monday to Friday. However, if an individual shows symptoms of
        the pathogen, they may instead remain at home to avoid infecting others.
        
        Children attending schools have a {child:.0%} chance of staying home if
        they are symptomatic. Adults (and adolescents) attending work have a
        {adult:.0%} chance of staying home if they are symptomatic.
        """.format(
            child=idGet("withdrawalSchool", scenarioID, 0.9),
            adult=idGet("withdrawalWork", scenarioID, 0.5),
        )
    )

    # BCC and Group Size
    st.subheader("Contact Between Individuals")
    bccRate = idGet("bccRate", scenarioID, 4.0)
    if bccRate.is_integer():
        bccString = f"""
        During the simulation's background phase (i.e. once per day), every
        individual who did not stay at home that day will interact with
        {bccRate:.0g} random {"person" if bccRate == 1 else "people"}.
        """
    else:
        lowBCC, highBCC = int(bccRate), -(-bccRate // 1)
        bccString = f"""
        During the simulation's background phase (i.e. once per day), every
        individual who did not stay at home that day will interact with an
        average of {bccRate:.3g} random people. The number of interactions will
        always be either {lowBCC:.0g} or {highBCC:.0g} for each individual;
        there is a {bccRate % 1:.0%} chance that an individual will interact
        with {highBCC:.0g} {"person" if bccRate == 1 else "people"}.
        """
    st.markdown(
        """
        To give the pathogen opportunities to spread, the model simulates
        interactions between individuals in the same location every cycle.
        However, in real life, a person may only regularly interact with a small
        group of people at a given location; for instance, children in schools
        may only interact with their close friends, while employees may not
        interact with people in other departments even if they work in the same
        building. To recreate this behaviour in the simulation, the people in
        each location are divided into several subgroups who can only interact
        with other members of their subgroup.

        Children in schools can form groups with up to {school} people; actual
        classes in the school may have more people, but students will not interact
        with more than {school} people within their class enough to spread the
        disease. Individuals in workplaces can form work groups with up to {work}
        people.
        
        In addition to interacting with people in the same location as them,
        individuals will also interact with random people anywhere in the simulation.
        These background contacts account for any interactions outside of the
        locations that are built into the simulation, such as those that occur
        on public transport or in shopping centres.
                
        {bcc}
        """.format(
            school=idGet("maxClassSize", scenarioID, 10) if advanced else 10,
            work=idGet("maxWorkGroupSize", scenarioID, 10) if advanced else 10,
            bcc=bccString,
        )
    )

    # Other Community Parameters
    st.subheader("Other Community Parameters")
    diagnosisDelay = idGet("diagnosisDelay", scenarioID, 0) if advanced else 0
    if diagnosisDelay > 0:
        # TODO: Note that delay may affect deployment of NPIs if they exist
        diagnosisString = f"""
        When an individual begins to show symptoms of the pathogen, they will not
        be diagnosed immediately. The individual will only be counted as a
        diagnosed case of the infection {diagnosisDelay}
        day{plural(diagnosisDelay)} after they begin to show symptoms. This
        means that non-pharmaceutical interventions that come into effect based
        on the number of diagnosed cases will take longer to start than if there
        was no delay.
        """
    else:
        diagnosisString = f"""
        When an individual begins to show symptoms of the pathogen, they will
        immediately be counted as a diagnosed case of the infection. The model
        possesses the ability to add a delay between the onset of symptoms and
        official diagnosis; however, currently this delay is set to 0 days.
        """
    childSupervision = idGet("childSupervision", scenarioID, 1.0)
    if childSupervision == 1:
        supervisionString = """
        While the locations that individuals go to are mostly determined independently
        of other people, an exception is made when a child would be left alone
        in a household. If every adult in a household is going to another location
        but a child in the same household is staying at home, one of the adults
        will also stay at home to ensure the child is not unsupervised.
        """
    elif childSupervision > 0:
        supervisionString = f"""
        While the locations that individuals go to are mostly determined independently
        of other people, an exception is made when a child would be left alone
        in a household. If every adult in a household is going to another location
        but a child in the same household is staying at home, there is a
        {childSupervision:.0%} chance that one of the adults will also stay at
        home to ensure the child is not unsupervised.
        """
    else:
        supervisionString = f"""
        The locations that individuals go to are determined independently of other
        people in the simulation. The model possesses the ability to allow adults
        to stay home if children would be left unsupervised in their household;
        however, currently the chance of this occurring is set to 0%.
        """
    st.markdown(
        """
        {diagnosis}

        {supervision}
        """.format(
            diagnosis=diagnosisString,
            supervision=supervisionString,
        )
    )


def communitySaveSchema(
    schema: Parameters,
    id: int = 0,
    advanced: bool = False,
    baseline: Optional[Parameters] = None,
):
    """
    Function to populate the Pydantic model schema with community parameters
    using scenario differentiation.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be populated into.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.

        advanced (bool): Set to `True` to show more complex parameters like
            child supervision rate.

        baseline (Parameters, optional): A Pydantic model representing the parameters
            set for the baseline scenario. When `id` is not 0, this will be used
            to omit parameters that are already set in the baseline from the final
            scenario.
    """

    try:
        # Validate parameters
        if not isinstance(schema, Parameters):
            raise ValueError("schema should be a Parameters object")

        # Scenario Parameters
        scenarioParams = scenarioParameters()

        # Withdrawals and Contact
        scenarioParams.prob_withdrawal = idGet("withdrawalWork", id, 0.5)
        scenarioParams.prob_school_withdrawal = idGet("withdrawalSchool", id, 0.9)
        scenarioParams.background_contact_count = idGet("bccRate", id, 4.0)

        # The Rest
        if advanced:
            scenarioParams.diagnosis_delay = idGet("diagnosisDelay", id, 0) * 2
            scenarioParams.prob_child_supervision = idGet("childSupervision", id, 1.0)
            # scenarioParams.max_class_count = idGet("maxClassCount", id, 1)
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
        # Save the updated parameters, removing redundant baseline values
        if id > 0 and baseline is not None:
            schemaRemoveBaseline(scenarioParams, baseline.Scenario_Parameter)
        schemaUpdate(schema, "Scenario_Parameter", scenarioParams)

    except (ValueError, ValidationError) as e:
        communityLog.error(
            (
                f"[communityParams] Encountered {type(e).__name__} "
                f"while validating parameters for scenario {id}: {e}"
            )
        )
        raise e


def communityLoadSchema(schema: Parameters, scenarioID: int = 0):
    """
    Function to read community parameters from a schema and set the
    dashboard's widgets to the specified values.

    Parameters:
        schema (Parameters): The Pydantic model (specifically an object in the
            Parameters class) that the parameters will be read from.

        id (int): An integer that will be used to differentiate the parameters in
            different instances of the tab by adding a number to the Streamlit
            session state variables. A value of 0 means that this is the
            baseline scenario and will be treated accordingly.
    """
    schemaParameters = schema.Scenario_Parameter
    if schemaParameters is None:
        return
    # Use dictionary to convert schema parameters into dashboard values
    paramConvert = {
        "prob_withdrawal": ("withdrawalWork", lambda x: x),
        "prob_school_withdrawal": ("withdrawalSchool", lambda x: x),
        "background_contact_count": ("bccRate", lambda x: x),
        "diagnosis_delay": ("diagnosisDelay", lambda x: round(x / 2, 1)),
        "prob_child_supervision": ("childSupervision", lambda x: x),
        "max_class_size": ("maxClassSize", lambda x: x),
        "max_workgroup_size": ("maxWorkGroupSize", lambda x: x),
    }
    # Only include non-None params that fit this tab
    validParams = {
        p: v
        for p, v in schemaParameters.model_dump(
            exclude_unset=True, exclude_none=True
        ).items()
        if p in paramConvert.keys()
    }
    for parameter, value in validParams.items():
        key, formatFunc = paramConvert[parameter]
        updateParamFromSchema(key, formatFunc(value), scenarioID)
