# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where the simulation can be ran (and non-scenario parameters are changed)

# Imports
from datetime import datetime
from threading import Event

import pandas as pd
import streamlit as st

from resources.constants import PRESET_R0_PATH, USE_PRESET_PARAMS
from resources.download import create_template
from resources.interface import error_checker
from resources.model_schema import CommunityOverride, OverrideTemplate, Parameters
from resources.parameter import community_change, load_key, save_key
from resources.server import task_wrapper
from resources.types import (
    COMMUNITY_NAMES,
    R0_CALCULATION_STATUS,
    R0_CALIBRATION_STATUS,
)

# Store st.session_state as variable for efficiency
session = st.session_state
calibration_in_progress = session.calibration_in_progress
calculation_in_progress = session.calculation_in_progress
calibration_cancel_flag = Event()
calculation_cancel_flag = Event()


@st.dialog("Calibrate $R_0$", width="large", icon=":material/partner_exchange:")
def calibrate_r0_button() -> None:
    """
    Callback function for the Calibrate R0 button, opening a dialog window
    before performing the calibration.
    """
    # Disable button if it's taking a while to run
    calibration_pending = bool(session.get("confirm_calibration_button"))

    # Get scenario to calculate
    scenario_id = session.get("r_calibrate_scenario", 0)
    scenario_name = session.scenario_names[scenario_id]
    target_reproduction_number = session.get("target_reproduction_number", 1.5)

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severe_errors_found = error_checker(scenario_id, f"Errors in {scenario_name}")
    if severe_errors_found:
        st.error(
            """
The basic reproduction number cannot be calibrated due to the errors displayed
above. Please correct these errors before calibrating $R_0$.
            """,
            icon=":material/error:",
        )
    else:
        # TODO: Estimate calibration runtime
        st.markdown(f"""
Are you sure you want to calibrate the basic reproduction
number to a value of {target_reproduction_number} for
{"the baseline scenario" if scenario_id == 0 else scenario_name}?
        """)
        # TODO: Should precision be a parameter on the dashboard?
        st.info(
            f"""
Due to the iterative methods used to calibrate $R_0$, the basic reproduction
number achieved after calibration may differ from the target value
({target_reproduction_number}) by ±0.02.
        """,
            icon=":material/target:",
        )
        if USE_PRESET_PARAMS:
            st.warning(
                """
The debug settings of the dashboard are set such that $R_0$ calibration uses
preset parameters instead of those set on the dashboard. The calibrated $R_0$
will not match the parameters for the selected scenario, and may not respect
the "Include Vaccinations and NPIs" toggle.
                """,
                icon=":material/bug_report:",
            )
        st.button(
            "Confirm",
            key="confirm_calibration_button",
            icon="spinner" if calibration_pending else None,
            disabled=calibration_pending,
        )
        if calibration_pending:
            # Set params indicating model is simulating
            session.calibration_in_progress = True
            session.calibration_start_time = datetime.now()
            calibration_cancel_flag.clear()

            # Get relevant settings from session
            show_advanced = session.get("show_advanced", False)
            use_interventions = (
                session.get("r_calculate_interventions", False)
                if show_advanced
                else False
            )
            community = session.get("community", "newcastle")

            # Load JSON
            if USE_PRESET_PARAMS:
                with open(PRESET_R0_PATH, "r") as f:
                    params = Parameters.model_validate_json(f.read())
            else:
                params = create_template(
                    scenario_id,
                    include_interventions=use_interventions,
                    include_dashboard=False,
                )
            schema = OverrideTemplate(
                name=community,
                description=str(target_reproduction_number),
                parameters=params,
            ).model_dump_json(indent=4, exclude_unset=True)
            # TODO: Just save ID instead of name?
            session.calib_scenario_name = scenario_name
            session.calib_saved_id = scenario_id

            # Prepare model call parameters
            status_params = {
                "result_type": "json",
                "status_decoder": {
                    "start": (0.01, "Initialising parameters..."),
                    "generating_toolbox": (0.02, "Preparing simulation engine..."),
                    "generating_config": (0.05, "Calibrating $R_0$..."),
                    "completed": (1.0, "$R_0$ calibrated!"),
                    "error": (-1.0, "Calibration halted due to error"),
                    "shutdown": (
                        -1.0,
                        "Server shut down before calibration could finish",
                    ),
                },
                "request_queue": R0_CALIBRATION_STATUS,
            }

            # Clear the status queue
            R0_CALIBRATION_STATUS.progress.append(0.0)
            R0_CALIBRATION_STATUS.tasks.clear()
            R0_CALIBRATION_STATUS.tasks.append("Connecting to server...")
            session["calibration_error"] = None

            # Make the model call
            session.calibration_in_progress = True
            task_wrapper(
                "R0 Calibration",
                "r0/calibrate",
                schema,
                calibration_cancel_flag,
                status_params,
            )

            # Generate popup to let the user know it's pending
            st.toast(
                "Calibrating $R_0$. Please wait...",
                icon=":material/partner_exchange:",
            )
            st.rerun()


@st.dialog("Cancel $R_0$ Calibration", width="large", icon=":material/stop_circle:")
def stop_calibration_button():
    """
    Callback function for the Calibrate R0 button, opening a dialog window
    before cancelling the currently pending analysis.
    """

    # Disable button if it's taking a while to run
    cancel_pending = bool(session.get("confirm_calibration_cancel_button"))

    st.warning(
        "Are you sure you want to stop calibrating $R_0$?",
        icon=":material/warning:",
    )
    st.button(
        "Confirm",
        key="confirm_calibration_cancel_button",
        icon="spinner" if cancel_pending else None,
        disabled=cancel_pending,
    )
    if cancel_pending:
        # Exit immediately if there's nothing to stop
        if not session.calibration_in_progress:
            st.toast(
                "$R_0$ is not currently being calibrated; there's nothing to cancel.",
                icon=":material/stop:",
            )
            st.rerun()

        # Display as error on the progress bar
        session["calibration_error"] = (
            "Calibration cancelled",
            "The calibration was manually cancelled by the user.",
            "stop_circle",
            None,
        )
        R0_CALIBRATION_STATUS.progress.append(-1.0)

        # Stop the run_model thread
        calibration_cancel_flag.set()
        session.calibration_in_progress = False
        session.show_calibration_progress = True

        # Generate popup to let the user know it's cancelled
        st.toast(
            "The calibration has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


@st.dialog("Calculate $R_0$", width="large", icon=":material/calculate:")
def calculate_r0_button() -> None:
    """
    Callback function for the Calculate R0 button, opening a dialog window
    before running the calculation.
    """
    # Disable button if it's taking a while to run
    calculation_pending = bool(session.get("confirm_calculation_button"))

    # Get scenario to calculate
    scenario_id = session.get("r_calculate_scenario", 0)
    scenario_name = session.scenario_names[scenario_id]

    # Display any errors
    # TODO: Hide scenario errors that are copies of baseline errors
    severe_errors_found = error_checker(scenario_id, f"Errors in {scenario_name}")
    if severe_errors_found:
        st.error(
            """
The basic reproduction number cannot be calculated due to the errors displayed
above. Please correct these errors before calculating $R_0$.
            """,
            icon=":material/error:",
        )
    else:
        # TODO: Estimate calculation runtime
        st.markdown(f"""
Are you sure you want to calculate the basic reproduction number for
{"the baseline scenario" if scenario_id == 0 else scenario_name}?
        """)
        if USE_PRESET_PARAMS:
            st.warning(
                """
The debug settings of the dashboard are set such that $R_0$ calculation uses
preset parameters instead of those set on the dashboard. The calculated $R_0$
will not match the parameters for the selected scenario, and may not respect
the "Include Vaccinations and NPIs" toggle.
                """,
                icon=":material/bug_report:",
            )
        st.button(
            "Confirm",
            key="confirm_calculation_button",
            icon="spinner" if calculation_pending else None,
            disabled=calculation_pending,
        )
        if calculation_pending:
            # Set params indicating model is simulating
            session.calculation_in_progress = True
            session.calculation_start_time = datetime.now()
            calculation_cancel_flag.clear()

            # Get relevant settings from session
            show_advanced = session.get("show_advanced", False)
            use_interventions = (
                session.get("r_calculate_interventions", False)
                if show_advanced
                else False
            )
            community = session.get("community", "newcastle")

            # Load JSON
            if USE_PRESET_PARAMS:
                with open(PRESET_R0_PATH, "r") as f:
                    params = Parameters.model_validate_json(f.read())
            else:
                params = create_template(
                    scenario_id,
                    include_interventions=use_interventions,
                    include_dashboard=False,
                )
            schema = CommunityOverride(
                name=community, parameters=params
            ).model_dump_json(indent=4, exclude_unset=True)
            session.calculation_scenario_name = scenario_name

            # Prepare model call parameters
            status_params = {
                "result_type": "json",
                "status_decoder": {
                    "start": (0.01, "Initialising parameters..."),
                    "generating_toolbox": (0.02, "Preparing simulation engine..."),
                    "generating_config": (0.1, "Calculating $R_0$..."),
                    "completed": (1.0, "$R_0$ calculated!"),
                    "error": (-1.0, "Calculation halted due to error"),
                    "shutdown": (
                        -1.0,
                        "Server shut down before calculation could finish",
                    ),
                },
                "result_queue": R0_CALCULATION_STATUS,
            }

            # Clear the status queue
            R0_CALCULATION_STATUS.progress.append(0.0)
            R0_CALCULATION_STATUS.tasks.clear()
            R0_CALCULATION_STATUS.tasks.append("Connecting to server...")
            session["calculation_error"] = None

            # Make the model call
            session.calculation_in_progress = True
            task_wrapper(
                "R0 Calculation",
                "r0/calculate",
                schema,
                calculation_cancel_flag,
                status_params,
            )

            # Generate popup to let the user know it's pending
            st.toast(
                "Sending a request to calculate $R_0$. Please wait...",
                icon=":material/calculate:",
            )
            st.rerun()


@st.dialog("Cancel $R_0$ Calculation", width="large", icon=":material/stop_circle:")
def stop_calculation_button():
    """
    Callback function for the Calculate R0 button, opening a dialog window
    before cancelling the currently pending analysis.
    """
    # Disable button if it's taking a while to run
    cancel_pending = bool(session.get("confirm_calculation_cancel_button"))

    st.warning(
        "Are you sure you want to stop calculating $R_0$?",
        icon=":material/warning:",
    )
    st.button(
        "Confirm",
        key="confirm_calculation_cancel_button",
        icon="spinner" if cancel_pending else None,
        disabled=cancel_pending,
    )
    if cancel_pending:
        # Exit immediately if there's nothing to stop
        if not session.calculation_in_progress:
            st.toast(
                "$R_0$ is not currently being calculated; there's nothing to cancel.",
                icon=":material/stop:",
            )
            st.rerun()

        # Display as error on the progress bar
        session["calculation_error"] = (
            "Calculation cancelled",
            "The calculation was manually cancelled by the user.",
            "stop_circle",
            None,
        )
        R0_CALCULATION_STATUS.progress.append(-1.0)

        # Stop the run_model thread
        calculation_cancel_flag.set()
        session.calculation_in_progress = False
        session.show_calculation_progress = True

        # Generate popup to let the user know it's cancelled
        st.toast(
            "The calculation has been cancelled.",
            icon=":material/stop_circle:",
        )
        st.rerun()


# Page Content

st.title("$R_0$ Calibration")

st.markdown("""
This page is used to configure the experiment's parameters to match a desired
basic reproduction number ($R_0$).
""")

# Global parameters
# Advanced parameters toggle
# TODO: Move advanced parameters to either the sidebar or a separate settings page
load_key("show_advanced", default=False, no_zero_default=True)
show_advanced = st.toggle(
    "Show Advanced Parameters",
    False,
    key="_show_advanced",
    on_change=save_key,
    args=["show_advanced"],
    help="""
Toggle whether to include parameters that control more fine-grain aspects of
the simulation environment (such as waning vaccine-derived immunity) when
calibrating or calculating R0.
    """,
)

# Community Selection
st.markdown("""
- The community selection determines the population, demographic distribution
and other elements of the community that is simulated in the calculation,
chosen from one of two Australian cities.
""")
load_key("community", default="newcastle")
community = st.selectbox(
    "Simulated Community",
    COMMUNITY_NAMES,
    key="_community",
    format_func=lambda x: x.capitalize(),
    on_change=community_change,
    help="""
The Australian city whose community data will be used as the basis for the
population and demographic distribution in the calculation. Note that the data
used for these communities comes from 2011.

### Options:
- Newcastle: A metropolitan area in New South Wales, Australia. It has a
population of 272,407 (as of 2011 when this data was collected) and has a
demographic distribution that more closely matches that of Australia as a whole
compared to the other communities.
- Cairns: A major city in Queensland, Australia. It has a population of 140,402
and has a higher Indigenous population compared to the other communities.
- Albany: A major city in Western Australia. It has a population of 55,109 and
has a higher proportion of older adults and seniors compared to the other
communities.
    """,
)

# Warn if patch parameters are set
scenario_count = session.get("scenario_count", 0) + 1
scenario_names = session.scenario_names
scenarios_with_patches = []
for i in range(scenario_count):
    current_patches = session.get(
        f"seeding_patch_form{i}", pd.DataFrame(columns=["Location"])
    )
    if current_patches["Location"].notna().any():
        scenarios_with_patches.append(scenario_names[i])
if show_advanced and scenarios_with_patches:
    reset_scenario_list = ", ".join(scenarios_with_patches)
    st.warning(
        f"""
Warning: Location-specific seeding weights defined in some scenarios
({reset_scenario_list}) rely on locations that only exist in the currently
selected community. Changing this community will reset the location-specific
seeding weights for these scenarios.
        """,
        icon=":material/wrong_location:",
    )

# Calibration

st.header("Calibrate $R_0$")

st.markdown("""
Select a scenario to calculate the transmission parameter value necessary to
achieve a specific basic reproduction number.
""")

left_calibration_column, center_calibration_column, right_calibration_column = (
    st.columns(3, vertical_alignment="center")
)


load_key("target_reproduction_number", default=1.5)
left_calibration_column.number_input(
    label="Target $R_0$",
    min_value=0.0,
    value=1.5,
    step=0.1,
    format="%0.8g",
    key="_target_reproduction_number",
    on_change=save_key,
    args=["target_reproduction_number"],
    help="""
The desired basic reproduction number, i.e. the average number of new
infections a single infected individual will cause over the course of the
infection's lifespan. Calibrating $R_0$ will identify the experiment parameters
needed to simulate a disease with this basic reproduction number.
    """,
)

load_key("r_calibrate_scenario", default=0)
center_calibration_column.selectbox(
    "Scenario to Calibrate",
    range(len(scenario_names)),
    index=0,
    format_func=lambda x: scenario_names[x],
    key="_r_calibrate_scenario",
    on_change=save_key,
    args=["r_calibrate_scenario"],
    help="""
The scenario that the transmission parameters will be calculated for.
"Baseline Scenario" uses the parameters defined at the
:grey-badge[:material/variable_insert: Baseline Parameters] page. Scenarios
defined at the :grey-badge[:material/variable_add: Scenario Parameters] page
are listed by the names assigned to them.
    """,
)

if show_advanced:
    load_key("calibration_use_interventions", default=False)
    right_calibration_column.toggle(
        "Include Vaccinations and NPIs",
        False,
        key="_calibration_use_interventions",
        on_change=save_key,
        args=["calibration_use_interventions"],
        help="""
The basic reproduction number is calculated without the influence of medical
interventions such as vaccination, so they will be excluded from the simulation
when calculating the parameters necessary to achieve a specific $R_0$. Set this
toggle to `True` if you wish to include these interventions in the calibration
process, thereby comparing the effective reproduction number $R_t$ instead.
        """,
    )

# Button to begin calculation
st.button(
    label=("Calibrating $R_0$..." if calculation_in_progress else "Calibrate $R_0$"),
    on_click=calibrate_r0_button,
    key="_r_calibration_button",
    disabled=calibration_in_progress,
    type="primary",
    icon="spinner" if calibration_in_progress else ":material/partner_exchange:",
    help=(
        """
Send a request to the *Flusim* model server to run multiple simulations with
the specified parameters, then use the results of these simulations to
determine what transmission parameters achieve the desired $R_0$.
        """
        if not calibration_in_progress
        else """
$R_0$ is currently being calibrated; please wait for the process to complete.
        """
    ),
)


# Stop Simulation Button
if calibration_in_progress:
    st.button(
        label="Cancel $R_0$ Calibration",
        on_click=stop_calibration_button,
        key="_stop_calibration",
        type="primary",
        icon=":material/stop_circle:",
        help="Stop calibrating $R_0$.",
    )

calibration_results_container = st.empty()

# TODO: Since buttons can't be made in fragments, find a more robust way
# to ensure this appearance is synchronised with the fragment
calibration_results = session.get("r0_calibration")
id_to_update = session.get("calib_saved_id")
if calibration_results is not None and id_to_update is not None:
    scenario_name = session["calib_scenario_name"]
    beta = session["r_calibration_beta"]

    def update_beta():
        """
        Simple callback to update beta to match the calibrated value
        """
        session[f"beta{id_to_update}"] = beta
        st.toast(
            f"""
{"The baseline scenario" if id_to_update == 0 else scenario_name} now has a
basic transmission parameter of {beta}.
            """,
            icon=":material/sync:",
        )

    st.button(
        f"Update Parameters in {scenario_name}",
        icon=":material/sync:",
        on_click=update_beta,
        help=f"""
Update the value of the basic transmission parameter in
{"the baseline scenario" if id_to_update == 0 else scenario_name} to match the
calibrated value above.
        """,
    )

# Calculation

st.header("Calculate $R_0$")

st.markdown("""
    Select a scenario to calculate the basic reproduction number obtained
    with its parameter settings.
""")

left_calculation_column, right_calculation_column = st.columns(
    2, vertical_alignment="center"
)

load_key("r_calculate_scenario", default=0)
left_calculation_column.selectbox(
    "Scenario to Calculate",
    range(len(scenario_names)),
    index=0,
    format_func=lambda x: scenario_names[x],
    key="_r_calculate_scenario",
    on_change=save_key,
    args=["r_calculate_scenario"],
    help="""
The scenario that the basic reproduction number will be calculated for.
"Baseline Scenario" uses the parameters defined at the
:grey-badge[:material/variable_insert: Baseline Parameters] page. Scenarios
defined at the :grey-badge[:material/variable_add: Scenario Parameters] page
are listed by the names assigned to them.
    """,
)

if show_advanced:
    load_key("r_calculate_interventions", default=False)
    right_calculation_column.toggle(
        "Include Vaccinations and NPIs",
        False,
        key="_r_calculate_interventions",
        on_change=save_key,
        args=["r_calculate_interventions"],
        help="""
The basic reproduction number is calculated without the influence of medical
interventions such as vaccination, so they will be excluded from the simulation
when calculating the value of $R_0$. Set this toggle to `True` if you wish to
include these interventions in the calculation process, thereby calculating the
effective reproduction number $R_t$ instead.
        """,
    )


# Button to begin calculation
st.button(
    label=("Calculating $R_0$..." if calculation_in_progress else "Calculate $R_0$"),
    on_click=calculate_r0_button,
    key="_r_calculation_button",
    disabled=calculation_in_progress,
    type="primary",
    icon="spinner" if calculation_in_progress else ":material/calculate:",
    help=(
        """
Send a request to the *Flusim* model server to run multiple simulations with
the specified parameters, then use the results of these simulations to estimate
a value for $R_0$.
        """
        if not calculation_in_progress
        else """
$R_0$ is currently being calculated; please wait for the process to complete.
        """
    ),
)

# TODO: Show Calib Results and dashboardApp additions

calculation_results_container = st.empty()


@st.fragment(run_every=1)
def show_r0_results():
    """
    Fragment to display any errors that occur when calculating R0
    """
    if session.show_calibration_progress:
        try:
            progress = R0_CALIBRATION_STATUS.progress[0]
        except IndexError:
            progress = 0.0
            # TODO: Use status to list the estimates that have occurred
            # already in lieu of a progress bar/estimated time
        if progress < 0.0:
            calibration_contents = calibration_results_container.container()
            # Display errors that have occurred alongside progress
            error_title, error_body, error_icon, error_object = session.get(
                "calibration_error",
                (
                    "Error occurred when calibrating $R_0$",
                    "An unspecified error has occurred while calibrating $R_0$.",
                    "error",
                    None,
                ),
            )
            calibration_contents.progress(1.0, f":red[:material/error:] {error_title}")
            sim_status = calibration_contents.status(
                label="Calibration stopped due to error (click for more info)",
                state="error",
            )
            sim_status.error(f"Error: {error_body}", icon=f":material/{error_icon}:")
            if error_object is not None:
                sim_status.exception(error_object)
        elif session.get("r0_calibration") is not None:
            # TODO: Save scenario ID and make descriptions sound natural
            calibration_contents = calibration_results_container.container()
            scenario_name = session["calib_scenario_name"]
            r0 = session["r0_calibration"]
            beta = session["r_calibration_beta"]
            calibration_contents.metric(
                f"Transmission Parameter Required for $R_0$ of {r0} in {scenario_name}",
                beta,
                border=True,
                help=f"""
The probability that the disease spreads to a new person when they interact
with an infected individual is $1 - \\exp{{(-\\beta}}$ (before accounting for
other factors such as age and location). If $\\beta$ is set to {beta} in the
scenario named {scenario_name}, the disease will have a basic reproduction
number equal to {r0}.
                """,
            )

    if session.show_calculation_progress:
        try:
            progress = R0_CALCULATION_STATUS.progress[0]
        except IndexError:
            progress = 0.0
        if progress < 0.0:
            calculation_contents = calculation_results_container.container()
            # Display errors that have occurred alongside progress
            error_title, error_body, error_icon, error_object = session.get(
                "calculation_error",
                (
                    "Error occurred when calculating $R_0$",
                    "An unspecified error has occurred while calculating $R_0$.",
                    "error",
                    None,
                ),
            )
            calculation_contents.progress(1.0, f":red[:material/error:] {error_title}")
            sim_status = calculation_contents.status(
                label="Calculation stopped due to error (click for more info)",
                state="error",
            )
            sim_status.error(f"Error: {error_body}", icon=f":material/{error_icon}:")
            if error_object is not None:
                sim_status.exception(error_object)
        elif session.get("r0_calculation") is not None:
            # TODO: Save scenario ID and make descriptions sound natural
            calculation_contents = calculation_results_container.container()
            scenario_name = session["calculation_scenario_name"]
            r0 = session["r0_calculation"]
            interval_lower_bound, interval_upper_bound = session[
                "r0_calculation_interval"
            ]
            calculation_contents.metric(
                f"Basic Reproduction Number ($R_0$) for {scenario_name}",
                r0,
                border=True,
                delta_description=f"95% Confidence Interval: [{interval_lower_bound}, {interval_upper_bound}]",
                help=f"""
The basic reproduction number ($R_0$) is the average number of new infections
that will be caused by a single infected individual over the lifespan of their
infection. The scenario named {scenario_name} has an $R_0$ of {r0}.
                """,
            )


# Stop Simulation Button
if calculation_in_progress:
    st.button(
        label="Cancel $R_0$ Calculation",
        on_click=stop_calculation_button,
        key="_stop_calculation",
        type="primary",
        icon=":material/stop_circle:",
        help="Stop calculating $R_0$.",
    )


show_r0_results()
