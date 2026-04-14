# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for creating and downloading files (e.g. parameter schema)

# Imports
import logging
import time
from copy import deepcopy
from io import BytesIO

import streamlit as st
import streamlit_notify as stn  # type: ignore
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
from ClientResources.ParameterFunctions import idGet, updateParamFromSchema
from ClientResources.SharedResources import communityPopulation
from ParameterTabs.communityParams import (
    buildCommunityTab,
    communityLoadSchema,
    communitySaveSchema,
)
from ParameterTabs.diseaseParams import (
    buildDiseaseTab,
    diseaseLoadSchema,
    diseaseSaveSchema,
)
from ParameterTabs.dynamicParams import (
    buildDynamicTab,
    dynamicLoadSchema,
    dynamicSaveSchema,
)
from ParameterTabs.vaccinationNPIParams import (
    buildVaccinationNPITab,
    vaccineLoadSchema,
    vaccineSaveSchema,
)

# Logging
downloadLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


def uploadDownloadBar():
    """
    Wrapper to create buttons for downloading and uploading parameters
    """
    download, upload = st.columns(2)
    with download:
        parameterDownload()
    with upload:
        st.button(
            label="Upload Parameters from File",
            width="stretch",
            on_click=parameterUpload,
            key="_uploadParamsButton",
            icon=":material/upload_file:",
            help="""
Upload a JSON file containing parameter settings for the simulation. These
files can be downloaded from the dashboard; they should be named
"FlusimParameterSettings_[timestamp].json". Note that any parameters currently
set on the dashboard (including baseline parameters, scenario parameters and
simulation engine settings) will be replaced with the values in the uploaded file.
            """,
        )


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
        width="stretch",
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
    uploadPending = bool(session.get("parameterUpload") is not None)
    st.info(
        body="""
            Loading parameters from a file wil overwrite any parameters that have
            been manually set using the dashboard, including scenario parameters
            and simulation engine settings. Are you sure you would like to upload
            parameters from a file?
        """,
        icon=":material/database_off:",
    )
    if session.simulationInProgress:
        st.warning(
            """
            Uploading new parameters from a file will not affect the simulation
            that is currently running.
        """,
            icon=":material/av_timer:",
        )
    uploadedParameters = st.file_uploader(
        "Upload Parameters from File",
        type="json",
        key="parameterUpload",
        disabled=uploadPending,
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
        diseaseSaveSchema(scenario, id, useAdvanced)
        communitySaveSchema(scenario, id, useAdvanced)
        useVaccines = vaccineSaveSchema(scenario, id, useAdvanced) or useVaccines
        if useAdvanced:
            dynamicSaveSchema(scenario, id)

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
    try:
        schema = modelGuideFile.model_validate_json(file.read())
    except ValidationError as e:
        # TODO: Process the full message to show the issues with the loaded file
        st.error(
            body="""
                The selected file does not contain valid
                parameter settings. Please only upload parameter files
                downloaded from the dashboard, and avoid editing parameter
                files after downloading them.
            """,
            icon=":material/unknown_document:",
        )
        st.header("Full Error Message")
        st.error(e, icon=":material/breaking_news:")
        return

    # Save a backup of st.session_state to ensure changes aren't left unfinished
    backupSession = deepcopy(dict(session))

    # Simulation engine settings
    # TODO: More error checks for parameter values allowed by the
    # simulation engine but not the dashboard
    try:
        if len(schema.community_used) > 1:
            raise ValidationError(
                """
                The selected parameter schema includes multiple
                communities in `community_used`. The dashboard currently only
                supports simulating a single community at a time; please
                remove any excess communities from the JSON file.
                """
            )
        if schema.community_used[0] not in communityPopulation:
            raise ValidationError(
                f"""
                The selected parameter schema uses the community
                "{schema.community_used[0]}". The dashboard currently only
                supports `newcastle` and `cairns` as communities; please
                change the value in the JSON file's `community_used` field to
                one of these.
                """
            )
        if schema.community_overrides:
            if len(schema.community_overrides) > 1:
                raise ValidationError(
                    """
                    The selected parameter schema includes multiple
                    `community_overrides` sections. The dashboard currently only
                    supports simulating a single community at a time; please
                    remove any excess community override sections from the JSON file.
                    """
                )
            engineSettings = schema.community_overrides[0]
            session.community = engineSettings.name

            engineParams = engineSettings.parameters.Scenario_Parameter
            if engineParams is not None and engineParams.start_day_of_week is not None:
                session.startDay = (
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                )[engineParams.start_day_of_week]
            commandArgs = engineSettings.parameters.Command_Argument
            if commandArgs is not None:
                session.runCount = commandArgs.n_runs
                session.cycleCount = (
                    commandArgs.n_cycles // 2
                    if commandArgs.n_cycles is not None
                    else None
                )

        # Baseline parameters
        # TODO: Improve robustness of LoadSchema functions with invalid data
        if schema.shared_overrides is not None:
            baselineParams = schema.shared_overrides.parameters
            diseaseLoadSchema(baselineParams, 0)
            communityLoadSchema(baselineParams, 0)
            vaccineLoadSchema(baselineParams, 0)
            dynamicLoadSchema(baselineParams, 0)

        # Scenario parameters
        if len(schema.simulation_sets) > 1:
            raise ValidationError(
                """
                    The selected parameter schema includes multiple
                    `simulation_sets` objects. Parameter files for the dashboard
                    put all scenarios in a single set, such that there should
                    be only one `simulation_sets` object. Please modify the
                    JSON file so that there is only one `simulation_sets` object.
                    """
            )
        simulationList = schema.simulation_sets[0].simulations
        scenarioCount = session.get("scenarioCount", 0)
        # Delete current scenarios in order to start fresh
        while scenarioCount > 0:
            deleteScenario(scenarioCount)
            scenarioCount = session.get("scenarioCount", 0)
        # Populate new scenarios
        for scenarioID, scenario in enumerate(simulationList):
            if scenarioID != 0:
                addScenario()
                updateParamFromSchema("scenarioName", scenario.name, scenarioID)
                if scenario.override_setting:
                    scenarioParams = scenario.override_setting.parameters
                    diseaseLoadSchema(scenarioParams, scenarioID)
                    communityLoadSchema(scenarioParams, scenarioID)
                    vaccineLoadSchema(scenarioParams, scenarioID)
                    dynamicLoadSchema(scenarioParams, scenarioID)
        # Load tabs briefly to initialise errors
        placeholderContainer = st.empty()
        for testID in range(scenarioCount + 1):
            # TODO: Find a less hacky way to initialise errors
            with placeholderContainer.popover(
                "Loading parameters...", icon="spinner", disabled=True
            ):
                buildDiseaseTab(testID, True)
                buildCommunityTab(testID, True)
                buildVaccinationNPITab(testID, True)
                buildDynamicTab(testID)

    except ValidationError as e:
        # TODO: See if it's possible/worthwhile to give
        # different errors different icons
        st.error(body=e, icon=":material/error:")

        # Restore session state
        # TODO: Make sure this can't overrule simulation results or other changes
        # that may occur between starting the upload process and an error occurring
        session.clear()
        session.update(backupSession)
        return

    stn.toast(
        "Parameters successfully uploaded!",
        icon=":material/download_done:",
        duration="short",
    )
    st.rerun()


# Scenario management functions
def addScenario():
    """
    Simple function to initialise an empty scenario.
    """
    newCount = session["scenarioCount"] + 1
    session["scenarioCount"] = newCount
    session[f"scenarioName{newCount}"] = f"Scenario #{newCount}"
    session["scenarioSetParams"][newCount] = set()
    session["scenarioSetParamsExtra"][newCount] = set()
    session["activeErrors"][newCount] = {}


def deleteScenario(scenarioID: int):
    """
    Function that removes a scenario from the dashboard, shifting up other
    scenario values if necessary.

    Parameters:
        scenarioID (int): The ID representing the scenario to be deleted.
    """
    # Get set of saved params
    scenarioCount = session.get("scenarioCount", 0)
    savedParams = session["scenarioSetParams"]
    savedExtraParams = session["scenarioSetParamsExtra"]

    # Shift existing values down
    for s in range(scenarioID, scenarioCount):
        paramsToConsider = savedParams[s] | savedParams[s + 1]
        for param in paramsToConsider:
            newValue = idGet(param, s + 1, None)
            if newValue is None:
                del session[f"{param}{s}"]
            else:
                session[f"{param}{s}"] = newValue
        extraParamsToConsider = savedExtraParams[s] | savedExtraParams[s + 1]
        for param, extra in extraParamsToConsider:
            newValue = idGet(param, s + 1, None, extra=extra)
            if newValue is None:
                del session[f"{param}{s}{extra}"]
            else:
                session[f"{param}{s}{extra}"] = newValue
        session["scenarioSetParams"][s] = savedParams[s + 1]
        session["scenarioSetParamsExtra"][s] = savedExtraParams[s + 1]
        session["activeErrors"][s] = session["activeErrors"][s + 1]

    # Delete duplicated end scenario params
    for param in savedParams[scenarioCount]:
        del session[f"{param}{scenarioCount}"]
    for param, extra in savedExtraParams[scenarioCount]:
        del session[f"{param}{scenarioCount}{extra}"]
    del session["scenarioSetParams"][scenarioCount]
    del session["scenarioSetParamsExtra"][scenarioCount]
    del session["activeErrors"][scenarioCount]

    # Update scenario count
    session["scenarioCount"] -= 1
