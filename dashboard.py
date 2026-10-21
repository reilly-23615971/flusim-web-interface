# Flusim Web Interface Application
# Developed by Reilly Evans
# Main program of dashboard, defining pages & setting universal parameters


# Imports
import logging
import os
from datetime import datetime

import streamlit as st

from resources.interface import time_string
from resources.types import (
    R0_CALCULATION_STATUS,
    R0_CALIBRATION_STATUS,
    SIM_STATUS,
    SimParams,
)
from resources.visualisation import format_data

# Set this early to minimise the time spent with a different page title
st.set_page_config(
    page_title="Flusim Web Dashboard",
    page_icon=":material/microbiology:",
    layout="wide",
    menu_items={"About": """
## Flusim Web Dashboard
This dashboard is designed to work with the *Flusim* model designed by the UWA
Infectious Disease Modelling Research Group.
### Additional Credits
Colour palette for scenarios created by Paul Tol
https://sronpersonalpages.nl/~pault/
    """},
)

# Logging config
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    filename="logs/interface_app_logs.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

app_log = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Initialise session variables used globally by the dashboard
session_parameters = {
    "simulation_in_progress": False,
    "calibration_in_progress": False,
    "calculation_in_progress": False,
    "show_sim_progress": False,
    "show_calibration_progress": False,
    "show_calculation_progress": False,
    "scenario_count": 0,
    "scenario_names": ["Baseline Scenario"],
    "scenario_extra_params": {},
    "scenario_set_params": {},
    "active_errors": {0: {}},
}
for parameter, default in session_parameters.items():
    session[parameter] = session.get(parameter, default)

# TODO: Load defaults from influenza template instead of hardcoding

# TODO: See if an extra cookie package like streamlit-cookie-controller
# can preserve parameters between refreshed pages

st.logo(image=":material/microbiology:")


# Define application pages
# TODO: Limit nested containers since apparently they might cause page blanking
landing_page = st.Page(
    "pages/landing_page.py",
    title="Main Page",
    icon=":material/home:",
)
model_description = st.Page(
    "pages/model_description.py",
    title="Model Description",
    icon=":material/description:",
)
baseline_parameters = st.Page(
    "pages/baseline_parameters.py",
    title="Baseline Parameters",
    icon=":material/variable_insert:",
)
scenario_parameters = st.Page(
    "pages/scenario_parameters.py",
    title="Scenario Parameters",
    icon=":material/variable_add:",
)
r0_calibration = st.Page(
    "pages/r0_calibration.py",
    title="$R_0$ Calibration",
    icon=":material/partner_exchange:",
)
run_simulations = st.Page(
    "pages/run_simulations.py",
    title="Run Simulations",
    icon=":material/motion_play:",
)
infection_curves = st.Page(
    "pages/infection_curves.py",
    title="Infection Curves",
    icon=":material/chart_data:",
)
health_burden_tables = st.Page(
    "pages/health_burden_tables.py",
    title="Health Burden Tables",
    icon=":material/table_chart_view:",
)

# TODO: Shorten section names, reduce font sizes or increase sidebar width
pages = {
    "Flusim Web Dashboard": [landing_page],
    "Parameter Configuration": [
        model_description,
        baseline_parameters,
        scenario_parameters,
    ],
    "Conducting Experiments": [r0_calibration, run_simulations],
    "Results Visualisation": [infection_curves, health_burden_tables],
}

# Initialise and run the application pages
flusim_pages = st.navigation(pages)
flusim_pages.run()

st.sidebar.link_button(
    "User Manual", "/app/static/UserManual.pdf", icon=":material/quick_reference:"
)


@st.fragment(run_every=1)
def update_data() -> None:
    """
    Fragment to regularly check if server results have been received yet.
    """
    results_obtained = False
    # Simulation Results
    simulation_has_results, simulation_has_errors = (
        not SIM_STATUS.results.empty(),
        not SIM_STATUS.errors.empty(),
    )
    if session.simulation_in_progress and (
        simulation_has_results or simulation_has_errors
    ):
        if simulation_has_results and not simulation_has_errors:
            # Reset pending simulation variables
            # TODO: Add a check to ensure visualisations can't use the new values
            # while this function is still processing the data
            current_params: SimParams = session["pending_sim_params"]
            session.sim_params = current_params

            # Process data and ensure there is no formatting errors
            returned_data = SIM_STATUS.results.get()
            app_log.info(
                f"[update_data] Processing the following data:\n{returned_data}"
            )

            # Remove any old session data that is no longer valid
            # TODO: Make more robust when number of returned values can vary more
            scenario_count = len(current_params.scenario_names)
            data_forms = current_params.analysis_formats
            if len(data_forms) < 4:
                session.pop("model_data_asir_vaccinated", None)

            # Format data
            formatted_data = [
                format_data(d, f) for d, f in zip(returned_data, data_forms)
            ]

            # Check for any errors in the data
            if any(len(data) == 0 for data in formatted_data):
                SIM_STATUS.errors.put(
                    (
                        "Simulation results were empty",
                        """
No data was present on one or more of the files received from the server.
Please make sure your parameters do not possess any errors and try again.
                    """,
                        "tab_unselected",
                        None,
                    )
                )
                simulation_has_errors = True
            elif any(
                form.tool == "epidemic"
                and len(data["Scenario"].value_counts()) != scenario_count
                for data, form in zip(formatted_data, data_forms)
            ):
                SIM_STATUS.errors.put(
                    (
                        "Some scenarios were not run properly",
                        """
One or more scenarios were not run correctly by the simulation server. Please
ensure all scenarios do not possess any errors and try again.
                    """,
                        "donut_small",
                        None,
                    )
                )
                simulation_has_errors = True
            else:
                # Save the data to st.session_state
                for data, form in zip(formatted_data, data_forms):
                    session[f"modelData{form.data_tag}"] = data

                # Tell the user what's happened
                session.simulation_end_time = datetime.now()
                total_time = session.simulation_end_time - session.simulation_start_time
                formatted_time = time_string(total_time.total_seconds())
                st.toast(
                    f"Simulation complete! Total duration: {formatted_time}",
                    icon=":material/check_circle:",
                    duration="infinite",
                )
                app_log.info("[update_data] Data processing is complete.")
                session.chart_generated = False
        if simulation_has_errors:
            # Notify user of errors, but leave displaying them to run_simulations
            session["simulation_error"] = SIM_STATUS.errors.get()
            SIM_STATUS.progress.append(-1.0)
            st.toast(
                """
Simulation encountered an error; see
:primary-badge[:material/motion_play: Run Simulations] for more.
                """,
                icon=":material/error:",
                duration="infinite",
            )

        # Re-enable running new simulations and using their data
        session.simulation_in_progress = False
        session.show_sim_progress = True

        results_obtained = True

    # R0 Calibration Results
    calibration_has_results, calibration_has_errors = (
        not R0_CALIBRATION_STATUS.results.empty(),
        not R0_CALIBRATION_STATUS.results.empty(),
    )
    if session.calibration_in_progress and (
        calibration_has_results or calibration_has_errors
    ):
        if calibration_has_results and not calibration_has_errors:
            # Get calculation results
            calibration_data = R0_CALIBRATION_STATUS.results.get()
            app_log.info(
                f"[update_data] Obtained the following calibration data:\n{calibration_data}"
            )
            if isinstance(calibration_data, dict):
                r0 = calibration_data["r0"]
                interval_lower_bound, interval_upper_bound = calibration_data[
                    "interval"
                ]
                beta = calibration_data["beta"]
                scenario_name = session.get("calib_scenario_name")
                session["r0_calibration"] = r0
                session["r_calibration_beta"] = beta

                st.toast(
                    f"""
$R_0$ of {r0} for {scenario_name} achieved with transmission value of {beta}
                    """,
                    icon=":material/partner_exchange:",
                    duration="infinite",
                )
                app_log.info("[update_data] R0 calibration is complete.")
            else:
                R0_CALIBRATION_STATUS.errors.put(
                    (
                        "Calibration results were incorrectly formatted",
                        """
The results of the $R_0$ calibration process were formatted incorrectly. This
is likely an error with the server; contact a developer to resolve the issue.
                    """,
                        "error",
                        None,
                    )
                )
                calibration_has_errors = True
        if calibration_has_errors:
            # Notify user of errors, but leave displaying them to run_simulations
            session["calibration_error"] = R0_CALIBRATION_STATUS.errors.get()
            R0_CALIBRATION_STATUS.progress.append(-1.0)
            st.toast(
                """
Error calibrating $R_0$; see
:primary-badge[:material/partner_exchange: $R_0$ Calibration] for more.
                """,
                icon=":material/error:",
                duration="infinite",
            )

        # Re-enable running new simulations and using their data
        session.calibration_in_progress = False
        session.show_calibration_progress = True

        results_obtained = True

    # R0 Calculation Results
    calculation_has_results, calculation_has_errors = (
        not R0_CALCULATION_STATUS.results.empty(),
        not R0_CALCULATION_STATUS.errors.empty(),
    )
    if session.calculation_in_progress and (
        calculation_has_results or calculation_has_errors
    ):
        if calculation_has_results and not calculation_has_errors:
            # Get calculation results
            calculation_data = R0_CALCULATION_STATUS.results.get()
            app_log.info(
                f"[update_data] Obtained the following calculation data:\n{calculation_data}"
            )
            if isinstance(calculation_data, dict):
                r0 = calculation_data["r0"]
                interval_lower_bound, interval_upper_bound = calculation_data[
                    "interval"
                ]
                scenario_name = session.get("calculation_scenario_name")
                session["r0_calculation"] = r0
                session["r0_calculation_interval"] = (
                    interval_lower_bound,
                    interval_upper_bound,
                )

                st.toast(
                    f"""
$R_0$ for {scenario_name} is {r0} with a 95% confidence interval of
[{interval_lower_bound}, {interval_upper_bound}]
                    """,
                    icon=":material/calculate:",
                )
                app_log.info("[update_data] R0 calculation is complete.")
            else:
                R0_CALCULATION_STATUS.errors.put(
                    (
                        "Calculation results were incorrectly formatted",
                        """
The results of the $R_0$ calculation process were formatted incorrectly. This
is likely an error with the server; contact a developer to resolve the issue.
                    """,
                        "error",
                        None,
                    )
                )
                calibration_has_errors = True
        if calculation_has_errors:
            # Notify user of errors, but leave displaying them to run_simulations
            session["calculation_error"] = R0_CALCULATION_STATUS.errors.get()
            R0_CALCULATION_STATUS.progress.append(-1.0)
            st.toast(
                """
Error calculating $R_0$; see
:primary-badge[:material/partner_exchange: $R_0$ Calibration] for more.
                """,
                icon=":material/error:",
            )

        # Re-enable running new simulations and using their data
        session.calculation_in_progress = False
        session.show_calculation_progress = True

        results_obtained = True

    # Rerun if results have been updated
    if results_obtained:
        st.rerun()


update_data()
