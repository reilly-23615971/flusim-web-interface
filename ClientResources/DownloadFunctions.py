# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for creating and downloading files (e.g. parameter schema)

# Imports
import logging
import time
from io import BytesIO

import streamlit as st
from pydantic import ValidationError

from ClientResources.ModelSchema import (
    Parameters,
    commandArgument,
    communityOverride,
    modelGuideFile,
    overrideParams,
    scenarioParameters,
    simulation,
    simulationSet,
)
from ParameterTabs.communityParams import communitySchema
from ParameterTabs.diseaseParams import diseaseSchema
from ParameterTabs.dynamicParams import dynamicSchema
from ParameterTabs.vaccinationNPIParams import vaccineSchema

# Logging
downloadLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


def parameterDownload():
    """
    Function to create a button that downloads the JSON of the current
    parameter set when clicked. Uses a `st.popover` container due to
    `st.dialog` not working well with `st.download_button`.
    """
    # TODO: Check if there's errors and don't allow downloading if there are
    # TODO: See if occasional page-blanking bugs can be fixed
    # TODO: Popover is a bit finicky; consider trying dialog or expander again
    with st.popover(
        "Download Parameter Settings",
        icon=":material/download:",
        key="parameterDownloadContainer",
        on_change="rerun",
        help="""
Download the currently selected parameters as a JSON file that can
be uploaded to the dashboard at a later date. Note that the baseline
parameters, scenario parameters and simulation engine settings are all
included in this file.
        """,
    ) as pop:
        if pop.open:
            st.markdown(
                """
                Would you like to download the currently selected parameter settings
                as a JSON file? This will allow you to load the settings onto the
                dashboard at a later date instead of manually setting them again.
            """
            )
            st.download_button(
                "Confirm",
                createConfig(session.get("scenarioCount", 0) + 1).model_dump_json(
                    indent=4, exclude_unset=True
                ),
                f"FlusimParameterSettings_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.json",
                mime="application/json",
                key="parameterDownloadConfirm",
                on_click=lambda: session.update({"parameterDownloadContainer": False}),
            )


@st.dialog("Upload Parameters from File", width="large", icon=":material/upload_file:")
def parameterUpload():
    """
    Dialog wrapper function to upload parameter settings from a JSON file.
    """
    # TODO: See if upload can be disabled while file is being processed
    # uploadPending = bool(session.get("parameterUpload") is not None)
    st.info(
        body="""
            Loading parameters from a file wil overwrite any parameters that have
            been manually set using the dashboard, including scenario parameters
            and simulation engine settings. Are you sure you would like to upload
            parameters from a file?
        """,
        icon=":material/database_off:",
    )
    uploadedParameters = st.file_uploader(
        "Upload Parameters from File",
        type="json",
        key="parameterUpload",
        # disabled = uploadPending,
        help="""
Upload a JSON file containing parameter settings for the simulation. These
files can be downloaded from the dashboard; they should be named
"FlusimParameterSettings_[timestamp].json". Note that any parameters currently
set on the dashboard (including baseline parameters, scenario parameters and
simulation engine settings) will be replaced with the values in the uploaded file.
        """,
    )
    if uploadedParameters is not None:
        loadConfig(uploadedParameters)


def createConfig(scenarioCount: int) -> modelGuideFile:
    """
    Function to generate a JSON config file using the selected parameters.

    Parameters:
        scenarioCount (int): The number of scenarios to define in the config.

    Returns:
        modelGuideFile: A Pydantic object storing the selected parameters
            in a format that can be converted into JSON easily.
    """
    # Set up schema objects
    session = st.session_state
    scenarioParams = [Parameters() for _ in range(scenarioCount)]

    # Populate parameters with session_state values
    # TODO: Make sure scenario parameters don't include baseline defaults
    # (particularly with variable-length forms)
    useVaccines = False
    useAdvanced = session.get("showAdvanced", False)
    for id, scenario in enumerate(scenarioParams):
        diseaseSchema(scenario, id, useAdvanced)
        communitySchema(scenario, id, useAdvanced)
        useVaccines = vaccineSchema(scenario, id, useAdvanced) or useVaccines
        if useAdvanced:
            dynamicSchema(scenario, id)

    # Use middle joint to control options
    # TODO: Account for more conditionals
    middleJoint = "-dashboard"
    if useVaccines:
        middleJoint += "+vaccines"

    # Create config object
    return modelGuideFile(
        name="Flusim Dashboard Simulation",
        description=str(session.sessionID),
        output_folder="./results/",
        middle_joint=middleJoint,
        community_used=[session.get("community", "newcastle")],
        # Community overrides are global parameters e.g. number of runs
        community_overrides=[
            communityOverride(
                name=session.get("community", "newcastle"),
                parameters=Parameters(
                    Command_Argument=commandArgument(
                        n_runs=session.get("runCount", 24),
                        n_cycles=session.get("cycleCount", 360) * 2,
                    ),
                    Scenario_Parameter=scenarioParameters(
                        start_day_of_week=(
                            "Sunday",
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                        ).index(session.get("startDay", "Monday"))
                    ),
                ),
            )
        ],
        # Shared overrides are baseline parameters
        shared_overrides=overrideParams(parameters=scenarioParams[0]),
        simulation_sets=[
            simulationSet(
                name="Dashboard Simulation Set",
                version=session.sessionID,
                simulations=[simulation(name="Baseline")]
                + [
                    simulation(
                        name=session[f"scenarioName{i}"],
                        override_setting=overrideParams(parameters=scenarioParams[i]),
                    )
                    for i in range(1, scenarioCount)
                ],
            )
        ],
    )


def loadConfig(file: BytesIO):
    """
    Function to read a JSON config file and set the dashboard's parameters
    to correspond to it [in progress].

    Parameters:
        file (bytes): The JSON file containing the parameter settings.
    """
    # TODO: Finish me
    try:
        schema = modelGuideFile.model_validate_json(file.read())
    except ValidationError as e:
        # TODO: Refine error to state the issues with the loaded file
        st.error(
            body="""
                The selected file does not contain valid
                parameter settings. Please only upload parameter files
                downloaded from the dashboard, and avoid editing parameter
                files after downloading them.
            """,
            icon=":material/unknown_document:",
        )
        # TODO: Debug
        st.header("Full Error Message")
        st.error(e, icon=":material/breaking_news:")
        return
    # TODO: Load parameters from schema

    # Simulation engine settings
    engineSettings = schema.community_overrides
    if engineSettings is not None:
        pass
        # TODO: Throw error if there isn't exactly  one community override

    st.write(schema)
    pass
