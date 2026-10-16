# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for creating and downloading files (e.g. parameter schema files)

# Imports
import logging
import time
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from typing import Optional

import streamlit as st
from pydantic import ValidationError

from ClientResources.InterfaceFunctions import unique_name, validation_error_formatting
from ClientResources.ModelSchema import (
    CommandArgument,
    CommunityOverride,
    DashboardParameters,
    GeneralParameters,
    ModelGuideFile,
    OverrideParams,
    Parameters,
    Simulation,
    SimulationSet,
)
from ClientResources.ParameterFunctions import id_get
from ClientResources.Types import COMMUNITY_NAMES
from ParameterTabs.communityParams import (
    build_community_tab,
    community_load_schema,
    community_save_schema,
)
from ParameterTabs.diseaseParams import (
    build_disease_tab,
    disease_load_schema,
    disease_save_schema,
)
from ParameterTabs.dynamicParams import (
    build_dynamic_tab,
    dynamic_load_schema,
    dynamic_save_schema,
)
from ParameterTabs.npiParams import (
    build_npi_tab,
    npi_load_schema,
    npi_save_schema,
)
from ParameterTabs.vaccinationParams import (
    build_vaccination_tab,
    vaccine_load_schema,
    vaccine_save_schema,
)

# Logging
download_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


def upload_download_bar():
    """
    Wrapper to create buttons for downloading and uploading parameters
    """
    download, upload = st.columns(2)
    with download:
        parameter_download()
    with upload:
        st.button(
            label="Upload Parameters from File",
            width="stretch",
            on_click=parameter_upload,
            icon=":material/upload_file:",
            help="""
Upload a JSON file containing parameter settings for the simulation. These
files can be downloaded from the dashboard; they should be named
"FlusimParameterSettings_[timestamp].json". Note that any parameters currently
set on the dashboard (including baseline parameters, scenario parameters and
simulation engine settings) will be replaced with the values in the uploaded file.
            """,
        )


def parameter_download():
    """
    Function to create a button that downloads the JSON of the current
    parameter set when clicked. Uses a `st.popover` container due to
    `st.dialog` not working well with `st.download_button`.
    """
    # TODO: Check if there's errors before downloading
    # TODO: See if occasional page-blanking bugs can be fixed
    # TODO: Popover is a bit finicky; consider trying dialog or expander again
    with st.popover(
        "Download Parameters to File",
        icon=":material/download:",
        width="stretch",
        key="parameter_download_container",
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
Would you like to download the currently selected parameter settings as a JSON
file? This will allow you to load the settings onto the dashboard at a later
date instead of manually setting them again.
            """)
            st.download_button(
                "Confirm",
                create_config(
                    session.get("scenario_count", 0) + 1, include_dashboard=True
                ).model_dump_json(indent=4, exclude_unset=True),
                f"FlusimParameterSettings_{time.strftime('%Y.%m.%d_%I.%M.%S%p')}.json",
                mime="application/json",
                on_click=lambda: session.update(
                    {"parameter_download_container": False}
                ),
            )


@st.dialog("Upload Parameters from File", width="large", icon=":material/upload_file:")
def parameter_upload():
    """
    Dialog wrapper function to upload parameter settings from a JSON file.
    """
    uploaded_file = session.get("parameter_upload")
    st.info(
        body="""
Loading parameters from a file wil overwrite any parameters that have been
manually set using the dashboard, including scenario parameters and simulation
engine settings. Are you sure you would like to upload parameters from a file?
        """,
        icon=":material/database_off:",
    )
    if session.simulation_in_progress:
        st.warning(
            """
Uploading new parameters from a file will not affect the simulation that is
currently running.
        """,
            icon=":material/av_timer:",
        )
    st.file_uploader(
        "Upload Parameters from File",
        type="json",
        key="parameter_upload",
        disabled=uploaded_file is not None,
        help="""
Upload a JSON file containing parameter settings for the simulation. These
files can be downloaded from the dashboard; they should be named
"FlusimParameterSettings_[timestamp].json". Note that any parameters currently
set on the dashboard (including baseline parameters, scenario parameters and
simulation engine settings) will be replaced with the values in the uploaded file.
        """,
    )
    if uploaded_file is not None:
        load_config(uploaded_file)


def create_config(
    scenario_count: int, include_dashboard: bool = False
) -> ModelGuideFile:
    """
    Function to generate a JSON config file using the selected parameters.

    Parameters:
        scenario_count (int): The number of scenarios to define in the config.

        include_dashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like scaling population in the generated schema.

    Returns:
        ModelGuideFile: A Pydantic object storing the selected parameters
            in a format that can be converted into JSON easily.
    """

    # Set up schema objects
    session = st.session_state
    scenario_params = [Parameters() for _ in range(scenario_count)]

    # Populate parameters with session_state values
    # TODO: Add setting that forces tables to have baseline duplicates removed
    # (for sending to the server, not for downloading)
    use_vaccines = False
    use_advanced = session.get("show_advanced", False)

    for id, scenario in enumerate(scenario_params):
        baseline = scenario_params[0] if id != 0 else None
        disease_save_schema(scenario, id, use_advanced, baseline, include_dashboard)
        community_save_schema(scenario, id, use_advanced, baseline)
        use_vaccines = (
            vaccine_save_schema(scenario, id, use_advanced, baseline, include_dashboard)
            or use_vaccines
        )
        npi_save_schema(scenario, id, use_advanced, baseline, include_dashboard)
        if use_advanced:
            dynamic_save_schema(scenario, id)

    # Use middle joint to control options
    middle_joint = "-dashboard"
    if use_vaccines:
        middle_joint += "+vaccines"

    # Set up engine parameters
    community = session.get("community", "newcastle")
    engine_params = Parameters(
        Command_Argument=CommandArgument(
            n_runs=session.get("run_count", 24),
            n_cycles=session.get("cycle_count", 360) * 2,
        )
    )
    if include_dashboard:
        dashboard_params = DashboardParameters(show_advanced_parameters=use_advanced)
        if use_advanced:
            dashboard_params.scaling_population = session.get("scaling_population")
        engine_params.Dashboard_Parameter = dashboard_params
    if use_advanced:
        start_day = session.get("start_day", "Random")
        if start_day != "Random":
            engine_params.Scenario_Parameter = GeneralParameters(
                start_day_of_week=(
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                ).index(start_day)
            )
    session_id = int(datetime.now().timestamp())

    # Create config object
    return ModelGuideFile(
        name="Flusim Web Dashboard Simulation",
        description=str(session_id),
        output_folder="./results/",
        middle_joint=middle_joint,
        community_used=[community],
        # Community overrides are global parameters e.g. number of runs
        community_overrides=[
            CommunityOverride(
                name=session.get("community", "newcastle"),
                parameters=engine_params,
            )
        ],
        # Shared overrides are baseline parameters
        shared_overrides=OverrideParams(parameters=scenario_params[0]),
        # TODO: Omit override_setting from scenarios with identical params to baseline
        simulation_sets=[
            SimulationSet(
                name="Dashboard Simulation Set",
                version=session_id,
                simulations=[Simulation(name="Baseline")]
                + [
                    Simulation(
                        name=session.scenario_names[i],
                        override_setting=OverrideParams(parameters=scenario_params[i]),
                    )
                    for i in range(1, scenario_count)
                ],
            )
        ],
    )


def load_config(file: BytesIO | str, loud: bool = True) -> bool:
    """
    Function to read a JSON config file and set the dashboard's parameters
    to correspond to it.

    Parameters:
        file (BytesIO or str): The JSON file containing the parameter settings.
            A string representation of the JSON will also be accepted.

        loud (bool): Set to `True` to notify the user of the updated parameters.

    Returns:
        bool: `False` if the parameters were loaded successfully,
            `True` if an error occurred.
    """
    try:
        if isinstance(file, str):
            schema = ModelGuideFile.model_validate_json(file)
        else:
            schema = ModelGuideFile.model_validate_json(file.read())
    except ValidationError as e:
        validation_error_formatting(e)
        return True

    # Save a backup of st.session_state to ensure changes aren't left unfinished
    backup_session = deepcopy(dict(session))

    # TODO: More error checks for parameter values allowed by the
    # simulation engine but not the dashboard
    try:
        # Simulation engine settings
        if len(schema.community_used) > 1:
            raise AssertionError("""
The selected parameter schema includes multiple communities in `community_used`.
The dashboard currently only supports simulating a single community at a time;
please remove any excess communities from the JSON file.
            """)
        if schema.community_used[0] not in COMMUNITY_NAMES:
            raise AssertionError(f"""
The selected parameter schema uses the community "{schema.community_used[0]}".
The dashboard currently only supports `newcastle`, `cairns` and `albany` as
communities; please change the value in the JSON file's `community_used` field
to one of these.
            """)
        if schema.community_overrides:
            if len(schema.community_overrides) > 1:
                raise AssertionError("""
The selected parameter schema includes multiple `community_overrides` sections.
The dashboard currently only supports simulating a single community at a time;
please remove any excess community override sections from the JSON file.
                """)
            engine_settings = schema.community_overrides[0]
            session.community = engine_settings.name

            dashboard_settings = engine_settings.parameters.Dashboard_Parameter
            if dashboard_settings is not None:
                session.show_advanced = bool(
                    dashboard_settings.show_advanced_parameters
                )
                if dashboard_settings.scaling_population is not None:
                    session.scaling_population = dashboard_settings.scaling_population

            engine_params = engine_settings.parameters.Scenario_Parameter
            if engine_params is not None:
                session.start_day = (
                    (
                        "Sunday",
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                    )[engine_params.start_day_of_week]
                    if engine_params.start_day_of_week is not None
                    else "Random"
                )

            command_args = engine_settings.parameters.Command_Argument
            if command_args is not None:
                # TODO: Make sure these don't mess with the sliders when None
                session.run_count = command_args.n_runs
                session.cycle_count = (
                    command_args.n_cycles // 2
                    if command_args.n_cycles is not None
                    else None
                )

        # Baseline parameters
        # TODO: Improve robustness of LoadSchema functions with invalid data
        if schema.shared_overrides is not None:
            baseline_params = schema.shared_overrides.parameters
            disease_load_schema(baseline_params, 0)
            community_load_schema(baseline_params, 0)
            vaccine_load_schema(baseline_params, 0)
            npi_load_schema(baseline_params, 0)
            dynamic_load_schema(baseline_params, 0)

        # Scenario parameters
        if len(schema.simulation_sets) > 1:
            raise AssertionError("""
The selected parameter schema includes multiple `simulation_sets` objects.
Parameter files for the dashboard put all scenarios in a single set, such that
there should be only one `simulation_sets` object. Please modify the JSON file
so that there is only one `simulation_sets` object.
            """)
        simulation_list = schema.simulation_sets[0].simulations
        scenario_count = session.get("scenario_count", 0)
        # Delete current scenarios in order to start fresh
        while scenario_count > 0:
            delete_scenario(scenario_count)
            scenario_count = session.get("scenario_count", 0)
        # Populate new scenarios
        for scenario_id, scenario in enumerate(simulation_list):
            if scenario_id != 0:
                add_scenario()
                session.scenario_names[scenario_id] = scenario.name
                if scenario.override_setting:
                    scenario_params = scenario.override_setting.parameters
                    disease_load_schema(scenario_params, scenario_id)
                    community_load_schema(scenario_params, scenario_id)
                    vaccine_load_schema(scenario_params, scenario_id)
                    npi_load_schema(scenario_params, scenario_id)
                    dynamic_load_schema(scenario_params, scenario_id)
        # Load tabs briefly to initialise errors
        use_advanced = session.get("show_advanced", False)
        placeholder_container = st.empty()
        for test_id in range(scenario_count + 1):
            # TODO: Find a less hacky way to initialise errors
            with placeholder_container.popover(
                "Loading parameters...", icon="spinner", disabled=True
            ):
                build_disease_tab(test_id, use_advanced)
                build_community_tab(test_id, use_advanced)
                build_vaccination_tab(test_id, use_advanced)
                build_npi_tab(test_id, use_advanced)
                build_dynamic_tab(test_id)

    except AssertionError as e:
        # TODO: Give the errors icons and titles once updated to Streamlit 1.57
        st.error(body=e, icon=":material/error:")

        # Restore session state
        # TODO: Make sure this can't overrule simulation results or other changes
        # that may occur between starting the upload process and an error occurring
        session.clear()
        session.update(backup_session)
        return True
    if loud:
        st.toast(
            "Parameters successfully uploaded!",
            icon=":material/download_done:",
            duration="short",
        )
        st.rerun()
    return False


def create_template(
    scenario_id: int,
    include_interventions: bool = True,
    include_dashboard: bool = False,
) -> Parameters:
    """
    Function to generate a JSON config object from a single scenario's parameters.

    Parameters:
        scenario_id (int): The ID representing the scenario to make a template from.

        include_interventions (bool): Set to True to not include any vaccination or
            NPI parameters in the template, such as when performing R0 analysis.

        include_dashboard (bool): Set to `True` to include dashboard-exclusive
            parameters like GP rate in the generated schema.

    Returns:
        Parameters: A Pydantic object storing the template parameters
            in a format that can be loaded easily.
    """

    # Set up schema objects
    session = st.session_state
    use_advanced = session.get("show_advanced", False)
    template = Parameters()
    baseline = (
        create_template(0, include_interventions, include_dashboard)
        if scenario_id > 0
        else None
    )

    disease_save_schema(
        template, scenario_id, use_advanced, baseline, include_dashboard
    )
    community_save_schema(template, scenario_id, use_advanced, baseline)
    if include_interventions:
        vaccine_save_schema(
            template, scenario_id, use_advanced, baseline, include_dashboard
        )
        npi_save_schema(
            template, scenario_id, use_advanced, baseline, include_dashboard
        )
    if use_advanced:
        dynamic_save_schema(template, scenario_id)
    return template


def load_template(
    scenario_id: int, template: Parameters | str, template_name: Optional[str] = None
):
    """
    Function to set a single scenario's parameters to match a given template.

    Parameters:
        scenario_id (int): The ID representing the scenario to make a template from.

        template (Parameters or str): Either the object containing the parameters
            to initialise in the selected scenario, or the path to the file
            containing said parameters.

        template_name (str, optional): The name of the template being applied.
    """
    if not isinstance(template, Parameters):
        try:
            with open(template, "r") as file:
                template_data = Parameters.model_validate_json(file.read())
        except FileNotFoundError as e:
            download_log.error(f"[load_template] Template file not found: {e}")
            raise e
        except ValidationError as e:
            download_log.error(
                f"[load_template] Template file had validation errors: {e}"
            )
            raise e
    else:
        template_data = template

    # Save a backup of st.session_state to ensure changes aren't left unfinished
    backup_session = deepcopy(dict(session))

    try:
        # Load the parameters
        if scenario_id != 0:
            reset_scenario(scenario_id, loud=False)
        disease_load_schema(template_data, scenario_id)
        community_load_schema(template_data, scenario_id)
        vaccine_load_schema(template_data, scenario_id)
        npi_load_schema(template_data, scenario_id)
        dynamic_load_schema(template_data, scenario_id)

        # Load tabs briefly to initialise errors
        # TODO: Find a less hacky way to initialise errors
        use_advanced = session.get("show_advanced", False)
        placeholder_container = st.empty()
        with placeholder_container.popover(
            "Loading parameters...", icon="spinner", disabled=True
        ):
            build_disease_tab(scenario_id, use_advanced)
            build_community_tab(scenario_id, use_advanced)
            build_vaccination_tab(scenario_id, use_advanced)
            build_npi_tab(scenario_id, use_advanced)
            build_dynamic_tab(scenario_id)
            if scenario_id == 0:
                for test_id in range(1, session.get("scenario_count", 0) + 1):
                    build_disease_tab(test_id, use_advanced)
                    build_community_tab(test_id, use_advanced)
                    build_vaccination_tab(test_id, use_advanced)
                    build_npi_tab(test_id, use_advanced)
                    build_dynamic_tab(test_id)

    except AssertionError as e:
        st.error(body=e, icon=":material/error:")

        # Restore session state
        # TODO: Make sure this can't overrule simulation results or other changes
        # that may occur between starting the upload process and an error occurring
        session.clear()
        session.update(backup_session)
    else:
        st.toast(
            body="Template successfully loaded!",
            icon=":material/list_alt_check:",
            duration="short",
        )
        st.rerun()


# Scenario management functions
def add_scenario(open_tab: Optional[str] = None):
    """
    Simple function to initialise an empty scenario.

    Parameters:
        open_tab (str, optional): The scenario's tab, to be opened immediately.
    """
    updated_count = session["scenario_count"] + 1
    session["scenario_count"] = updated_count
    session["scenario_set_params"][updated_count] = set()
    session["scenario_extra_params"][updated_count] = set()
    session["active_errors"][updated_count] = {}

    # Ensure new name is unique
    new_name = unique_name("New Scenario", set(session.scenario_names))
    session.scenario_names.append(new_name)
    if open_tab is not None:
        session[open_tab] = f"**#{updated_count}** {new_name}"
        session.tab_reloader = not session.get("tab_reloader", False)
        st.toast("Scenario added!", icon=":material/add:")


def delete_scenario(scenario_id: int, open_tab: Optional[str] = None):
    """
    Function that removes a scenario from the dashboard, shifting up other
    scenario values if necessary.

    Parameters:
        scenario_id (int): The ID representing the scenario to be deleted.

        open_tab (str, optional): The scenario's tab, to open the next scenario.
    """
    # Get set of saved params
    scenario_count = session.get("scenario_count", 0)
    saved_params = session.scenario_set_params
    saved_extra_params = session.scenario_extra_params

    # Shift existing values down
    for s in range(scenario_id, scenario_count):
        relevant_params = saved_params[s] | saved_params[s + 1]
        for param in relevant_params:
            new_value = id_get(param, s + 1, None)
            if new_value is None:
                del session[f"{param}{s}"]
            else:
                session[f"{param}{s}"] = new_value
        relevant_extra_params = saved_extra_params[s] | saved_extra_params[s + 1]
        for param, extra in relevant_extra_params:
            new_value = id_get(param, s + 1, None, extra=extra)
            if new_value is None:
                del session[f"{param}{s}{extra}"]
            else:
                session[f"{param}{s}{extra}"] = new_value
        session.scenario_set_params[s] = saved_params[s + 1]
        session.scenario_extra_params[s] = saved_extra_params[s + 1]
        session.active_errors[s] = session.active_errors[s + 1]
        session.scenario_names[s] = session.scenario_names[s + 1]

    # Delete duplicated end scenario params
    for param in saved_params[scenario_count]:
        del session[f"{param}{scenario_count}"]
    for param, extra in saved_extra_params[scenario_count]:
        del session[f"{param}{scenario_count}{extra}"]
    del session.scenario_set_params[scenario_count]
    del session.scenario_extra_params[scenario_count]
    del session.active_errors[scenario_count]
    session.scenario_names.pop()

    # Update selected scenarios for R0 calculation
    for widget in {"r_calibrate_scenario", "calib_saved_id", "r_calculate_scenario"}:
        current_index = session.get(widget)
        if current_index == scenario_id:
            del session[widget]
        elif current_index is not None and current_index > scenario_id:
            session[widget] -= 1

    # Update scenario count
    session["scenario_count"] -= 1

    # Open the scenario taking the deleted one's place
    # TODO: If programmatic anchor tags are possible (append to URL?),
    # move user to the top of the tab container
    if open_tab is not None:
        if scenario_count > 1:
            open_count = (
                scenario_id if scenario_id < scenario_count else scenario_count - 1
            )
            session[open_tab] = (
                f"**#{open_count}** {session.scenario_names[open_count]}"
            )
            session.tab_reloader = not session.get("tab_reloader", False)
        st.toast("Scenario removed!", icon=":material/delete:")


def reset_scenario(scenario_id: int, loud: bool = True):
    """
    Function that resets all parameters in a scenario to their baseline values.

    Parameters:
        scenario_id (int): The ID representing the scenario to be reset.

        loud (bool): Set to true to show a notification upon resetting.
    """
    # Delete scenario parameters (excluding the name)
    for param in session["scenario_set_params"][scenario_id]:
        del session[f"{param}{scenario_id}"]
    for param, extra in session["scenario_extra_params"][scenario_id]:
        del session[f"{param}{scenario_id}{extra}"]
    session["scenario_set_params"][scenario_id] = set()
    session["scenario_extra_params"][scenario_id] = set()
    session["active_errors"][scenario_id] = session["active_errors"][0]
    if loud:
        st.toast("Scenario reset!", icon=":material/settings_backup_restore:")
