# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for creating and downloading files (e.g. parameter schema)

# Imports
import logging
import time
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from typing import Optional

import streamlit as st
from pydantic import ValidationError

# Reload streamlit_notify if it fails the first time
try:
    import streamlit_notify as stn
except ImportError:
    import importlib

    time.sleep(0.01)
    importlib.reload(importlib.import_module("streamlit_notify"))
    import streamlit_notify as stn  # type: ignore

from ClientResources.InterfaceFunctions import uniqueName, validationErrorFormatting
from ClientResources.ModelSchema import (
    Parameters,
    commandArgument,
    communityOverride,
    dashboardParameters,
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
from ParameterTabs.npiParams import (
    buildNPITab,
    npiLoadSchema,
    npiSaveSchema,
)
from ParameterTabs.vaccinationParams import (
    buildVaccinationTab,
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
    # TODO: Check if there's errors
    # TODO: See if occasional page-blanking bugs can be fixed
    # TODO: Popover is a bit finicky; consider trying dialog or expander again
    with st.popover(
        "Download Parameters to File",
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
            st.markdown("""
                Would you like to download the currently selected parameter settings
                as a JSON file? This will allow you to load the settings onto the
                dashboard at a later date instead of manually setting them again.
            """)
            st.download_button(
                "Confirm",
                createConfig(
                    session.get("scenarioCount", 0) + 1, includeDashboard=True
                ).model_dump_json(indent=4, exclude_unset=True),
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
    # TODO: This still blanks the page occasionally (sometimes displays the following:)
    # Life Stage	Pre-Symptomatic
    # Length (Days)	1
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


def createConfig(scenarioCount: int, includeDashboard: bool = False) -> modelGuideFile:
    """
    Function to generate a JSON config file using the selected parameters.

    Parameters:
        scenarioCount (int): The number of scenarios to define in the config.

        includeDashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like scaling population in the generated schema.

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
    # TODO: Add setting that forces tables to have baseline duplicates removed
    # (for sending to the server, not for downloading)
    useVaccines = False
    useAdvanced = session.get("showAdvanced", False)

    for id, scenario in enumerate(scenarioParams):
        baseline = scenarioParams[0] if id != 0 else None
        diseaseSaveSchema(scenario, id, useAdvanced, baseline, includeDashboard)
        communitySaveSchema(scenario, id, useAdvanced, baseline)
        useVaccines = vaccineSaveSchema(scenario, id, useAdvanced) or useVaccines
        npiSaveSchema(scenario, id, useAdvanced, baseline, includeDashboard)
        if useAdvanced:
            dynamicSaveSchema(scenario, id)

    # Use middle joint to control options
    middleJoint = "-dashboard"
    if useVaccines:
        middleJoint += "+vaccines"

    # Set up engine parameters
    community = session.get("community", "newcastle")
    engineParams = Parameters(
        Command_Argument=commandArgument(
            n_runs=session.get("runCount", 24),
            n_cycles=session.get("cycleCount", 360) * 2,
        )
    )
    if includeDashboard:
        dashboardParams = dashboardParameters(show_advanced_parameters=useAdvanced)
        if useAdvanced:
            dashboardParams.scaling_population = session.get(
                "scalingPopulation", communityPopulation[community]
            )
        engineParams.Dashboard_Parameter = dashboardParams
    if useAdvanced:
        startDay = session.get("startDay", "Random")
        if startDay != "Random":
            engineParams.Scenario_Parameter = scenarioParameters(
                start_day_of_week=(
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                ).index(startDay)
            )
    sessionID = int(datetime.now().timestamp())

    # Create config object
    return modelGuideFile(
        name="Flusim Web Dashboard Simulation",
        description=str(sessionID),
        output_folder="./results/",
        middle_joint=middleJoint,
        community_used=[community],
        # Community overrides are global parameters e.g. number of runs
        community_overrides=[
            communityOverride(
                name=session.get("community", "newcastle"),
                parameters=engineParams,
            )
        ],
        # Shared overrides are baseline parameters
        shared_overrides=overrideParams(parameters=scenarioParams[0]),
        # TODO: Omit override_setting from scenarios with identical params to baseline
        simulation_sets=[
            simulationSet(
                name="Dashboard Simulation Set",
                version=sessionID,
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


def loadConfig(file: BytesIO | str):
    """
    Function to read a JSON config file and set the dashboard's parameters
    to correspond to it.

    Parameters:
        file (BytesIO or str): The JSON file containing the parameter settings.
            A string representation of the JSON will also be accepted.
    """
    try:
        if isinstance(file, str):
            schema = modelGuideFile.model_validate_json(file)
        else:
            schema = modelGuideFile.model_validate_json(file.read())
    except ValidationError as e:
        validationErrorFormatting(e)
        return

    # Save a backup of st.session_state to ensure changes aren't left unfinished
    backupSession = deepcopy(dict(session))

    # TODO: More error checks for parameter values allowed by the
    # simulation engine but not the dashboard
    try:
        # Simulation engine settings
        if len(schema.community_used) > 1:
            raise AssertionError("""
                The selected parameter schema includes multiple
                communities in `community_used`. The dashboard currently only
                supports simulating a single community at a time; please
                remove any excess communities from the JSON file.
            """)
        if schema.community_used[0] not in communityPopulation:
            raise AssertionError(f"""
                The selected parameter schema uses the community
                "{schema.community_used[0]}". The dashboard currently only
                supports `newcastle` and `cairns` as communities; please
                change the value in the JSON file's `community_used` field to
                one of these.
            """)
        if schema.community_overrides:
            if len(schema.community_overrides) > 1:
                raise AssertionError("""
                    The selected parameter schema includes multiple
                    `community_overrides` sections. The dashboard currently only
                    supports simulating a single community at a time; please
                    remove any excess community override sections from the JSON file.
                """)
            engineSettings = schema.community_overrides[0]
            session.community = engineSettings.name

            dashboardSettings = engineSettings.parameters.Dashboard_Parameter
            if dashboardSettings is not None:
                session.showAdvanced = bool(dashboardSettings.show_advanced_parameters)
                session.scalingPopulation = (
                    dashboardSettings.scaling_population
                    if dashboardSettings.scaling_population is not None
                    else communityPopulation[engineSettings.name]
                )

            engineParams = engineSettings.parameters.Scenario_Parameter
            if engineParams is not None:
                session.startDay = (
                    (
                        "Sunday",
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                    )[engineParams.start_day_of_week]
                    if engineParams.start_day_of_week is not None
                    else "Random"
                )

            commandArgs = engineSettings.parameters.Command_Argument
            if commandArgs is not None:
                # TODO: Make sure these don't mess with the sliders when None
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
            npiLoadSchema(baselineParams, 0)
            dynamicLoadSchema(baselineParams, 0)

        # Scenario parameters
        if len(schema.simulation_sets) > 1:
            raise AssertionError("""
                The selected parameter schema includes multiple
                `simulation_sets` objects. Parameter files for the dashboard
                put all scenarios in a single set, such that there should
                be only one `simulation_sets` object. Please modify the
                JSON file so that there is only one `simulation_sets` object.
            """)
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
                # TODO: Make sure names are unique (either here or in the schema)
                updateParamFromSchema("scenarioName", scenario.name, scenarioID)
                if scenario.override_setting:
                    scenarioParams = scenario.override_setting.parameters
                    diseaseLoadSchema(scenarioParams, scenarioID)
                    communityLoadSchema(scenarioParams, scenarioID)
                    vaccineLoadSchema(scenarioParams, scenarioID)
                    npiLoadSchema(scenarioParams, scenarioID)
                    dynamicLoadSchema(scenarioParams, scenarioID)
        # Load tabs briefly to initialise errors
        useAdvanced = session.get("showAdvanced", False)
        placeholderContainer = st.empty()
        for testID in range(scenarioCount + 1):
            # TODO: Find a less hacky way to initialise errors
            with placeholderContainer.popover(
                "Loading parameters...", icon="spinner", disabled=True
            ):
                buildDiseaseTab(testID, useAdvanced)
                buildCommunityTab(testID, useAdvanced)
                buildVaccinationTab(testID, useAdvanced)
                buildNPITab(testID, useAdvanced)
                buildDynamicTab(testID)

    except AssertionError as e:
        # TODO: Give the errors icons and titles once updated to Streamlit 1.57
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


def createTemplate(
    scenarioID: int, includeInterventions: bool = True, includeDashboard: bool = False
) -> Parameters:
    """
    Function to generate a JSON config object from a single scenario's parameters.

    Parameters:
        scenarioID (int): The ID representing the scenario to make a template from.

        includeInterventions (bool): Set to True to not include any vaccination or
            NPI parameters in the template, such as when performing R0 analysis.

        includeDashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like GP rate in the generated schema.

    Returns:
        Parameters: A Pydantic object storing the template parameters
            in a format that can be loaded easily.
    """

    # Set up schema objects
    session = st.session_state
    useAdvanced = session.get("showAdvanced", False)
    template = Parameters()
    baseline = (
        createTemplate(0, includeInterventions, includeDashboard)
        if scenarioID > 0
        else None
    )

    diseaseSaveSchema(template, scenarioID, useAdvanced, baseline, includeDashboard)
    communitySaveSchema(template, scenarioID, useAdvanced, baseline)
    if includeInterventions:
        vaccineSaveSchema(template, scenarioID, useAdvanced)
        npiSaveSchema(template, scenarioID, useAdvanced, baseline, includeDashboard)
    if useAdvanced:
        dynamicSaveSchema(template, scenarioID)
    return template


def loadTemplate(
    scenarioID: int, template: Parameters | str, templateName: Optional[str] = None
):
    """
    Function to set a single scenario's parameters to match a given template.

    Parameters:
        scenarioID (int): The ID representing the scenario to make a template from.

        template (Parameters or str): Either the object containing the parameters
            to initialise in the selected scenario, or the path to the file
            containing said parameters.

        templateName (str, optional): The name of the template being applied.
    """
    if not isinstance(template, Parameters):
        try:
            with open(template, "r") as file:
                templateData = Parameters.model_validate_json(file.read())
        except FileNotFoundError as e:
            downloadLog.error(f"[loadTemplate] Template file not found: {e}")
            raise e
        except ValidationError as e:
            downloadLog.error(
                f"[loadTemplate] Template file had validation errors: {e}"
            )
            raise e
    else:
        templateData = template

    # Save a backup of st.session_state to ensure changes aren't left unfinished
    backupSession = deepcopy(dict(session))

    try:
        # Load the parameters
        if scenarioID != 0:
            resetScenario(scenarioID, loud=False)
        diseaseLoadSchema(templateData, scenarioID)
        communityLoadSchema(templateData, scenarioID)
        vaccineLoadSchema(templateData, scenarioID)
        npiLoadSchema(templateData, scenarioID)
        dynamicLoadSchema(templateData, scenarioID)

        # Load tabs briefly to initialise errors
        # TODO: Find a less hacky way to initialise errors
        useAdvanced = session.get("showAdvanced", False)
        placeholderContainer = st.empty()
        with placeholderContainer.popover(
            "Loading parameters...", icon="spinner", disabled=True
        ):
            buildDiseaseTab(scenarioID, useAdvanced)
            buildCommunityTab(scenarioID, useAdvanced)
            buildVaccinationTab(scenarioID, useAdvanced)
            buildNPITab(scenarioID, useAdvanced)
            buildDynamicTab(scenarioID)
            if scenarioID == 0:
                for testID in range(1, session.get("scenarioCount", 0) + 1):
                    buildDiseaseTab(testID, useAdvanced)
                    buildCommunityTab(testID, useAdvanced)
                    buildVaccinationTab(testID, useAdvanced)
                    buildNPITab(testID, useAdvanced)
                    buildDynamicTab(testID)

    except AssertionError as e:
        st.error(body=e, icon=":material/error:")

        # Restore session state
        # TODO: Make sure this can't overrule simulation results or other changes
        # that may occur between starting the upload process and an error occurring
        session.clear()
        session.update(backupSession)
        return

    stn.toast(
        body="Template successfully loaded!",
        icon=":material/list_alt_check:",
        duration="short",
    )
    st.rerun()


# Scenario management functions
def addScenario(openTab: Optional[str] = None):
    """
    Simple function to initialise an empty scenario.

    Parameters:
        openTab (str, optional): The scenario's tab, to be opened immediately.
    """
    newCount = session["scenarioCount"] + 1
    session["scenarioCount"] = newCount
    session["scenarioSetParams"][newCount] = set()
    session["scenarioSetParamsExtra"][newCount] = set()
    session["activeErrors"][newCount] = {}

    # Ensure new name is unique
    newName = uniqueName(
        "New Scenario",
        {session.get(f"scenarioName{i}", "New Scenario") for i in range(1, newCount)},
    )
    session[f"scenarioName{newCount}"] = newName
    if openTab is not None:
        session[openTab] = f"**#{newCount}** {newName}"
        session.tabReloader = not session.get("tabReloader", False)
        stn.toast("Scenario added!", icon=":material/add:")


def deleteScenario(scenarioID: int, openTab: Optional[str] = None):
    """
    Function that removes a scenario from the dashboard, shifting up other
    scenario values if necessary.

    Parameters:
        scenarioID (int): The ID representing the scenario to be deleted.

        openTab (str, optional): The scenario's tab, to open the next scenario.
    """
    # Get set of saved params
    scenarioCount = session.get("scenarioCount", 0)
    savedParams = session["scenarioSetParams"]
    savedExtraParams = session["scenarioSetParamsExtra"]

    # Shift existing values down
    for s in range(scenarioID, scenarioCount):
        paramsToConsider = savedParams[s] | savedParams[s + 1] | {"scenarioName"}
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
    for param in savedParams[scenarioCount] | {"scenarioName"}:
        del session[f"{param}{scenarioCount}"]
    for param, extra in savedExtraParams[scenarioCount]:
        del session[f"{param}{scenarioCount}{extra}"]
    del session["scenarioSetParams"][scenarioCount]
    del session["scenarioSetParamsExtra"][scenarioCount]
    del session["activeErrors"][scenarioCount]

    # Update selected scenarios for R0 calculation
    for widget in {"rCalibrateScenario", "calibSavedScenarioID", "rCalculateScenario"}:
        currentIndex = session.get(widget)
        if currentIndex == scenarioID:
            del session[widget]
        elif currentIndex is not None and currentIndex > scenarioID:
            session[widget] -= 1

    # Update scenario count
    session["scenarioCount"] -= 1

    # Open the scenario taking the deleted one's place
    # TODO: If programmatic anchor tags are possible (append to URL?),
    # move user to the top of the tab container
    if openTab is not None:
        if scenarioCount > 1:
            openCount = scenarioID if scenarioID < scenarioCount else scenarioCount - 1
            session[openTab] = f"**#{openCount}** {session[f"scenarioName{openCount}"]}"
            session.tabReloader = not session.get("tabReloader", False)
        stn.toast("Scenario removed!", icon=":material/delete:")


def resetScenario(scenarioID: int, loud: bool = True):
    """
    Function that resets all parameters in a scenario to their baseline values.

    Parameters:
        scenarioID (int): The ID representing the scenario to be reset.

        loud (bool): Set to true to show a notification upon resetting.
    """
    # Delete scenario parameters (excluding the name)
    for param in session["scenarioSetParams"][scenarioID] - {"scenarioName"}:
        del session[f"{param}{scenarioID}"]
    for param, extra in session["scenarioSetParamsExtra"][scenarioID]:
        del session[f"{param}{scenarioID}{extra}"]
    session["scenarioSetParams"][scenarioID] = set()
    session["scenarioSetParamsExtra"][scenarioID] = set()
    session["activeErrors"][scenarioID] = session["activeErrors"][0]
    if loud:
        stn.toast("Scenario reset!", icon=":material/settings_backup_restore:")
