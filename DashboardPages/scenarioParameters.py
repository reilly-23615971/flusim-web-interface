# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging

import streamlit as st

from ClientResources.InterfaceFunctions import (
    errorChecker,
    loadKey,
    rerunTime,
    saveKey,
    idGet,
)
from ClientResources.SharedResources import maxScenarios
from ParameterTabs.communityParams import buildCommunityTab

# from ParameterTabs.basicParams import buildBasicTab, rerunTime
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.dynamicParams import buildDynamicTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab

# Logging
scenarioLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Load scenario count early for efficiency
scenarioCount = session.get("scenarioCount", 0)


def addScenario():
    """
    Simple function to initialise an empty scenario
    """
    newCount = session["scenarioCount"] + 1
    session["scenarioCount"] = newCount
    session[f"scenarioName{newCount}"] = f"Scenario #{newCount}"
    session["scenarioSetParams"][newCount] = set()
    session["scenarioSetParamsExtra"][newCount] = set()
    session["activeErrors"][newCount] = {}


# Function to delete a scenario from the page
@st.dialog("Delete Scenario", width="large", icon=":material/delete:")
def deleteScenario(scenarioID: int):
    """
    Dialog function that removes a scenario if confirmed

    Parameters:
        scenarioID (int): The ID representing the scenario to be deleted.
    """
    st.markdown(
        f"""
        Deleting the "{session[f'scenarioName{scenarioID}']}"
        scenario will erase any unique parameter values set for it. Are
        you sure you want to delete this scenario?
    """
    )
    if st.button("Confirm"):
        # Get set of saved params
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
                # session[f"_{param}{s}"] = idGet(f"_{param}", s + 1, None)
            extraParamsToConsider = savedExtraParams[s] | savedExtraParams[s + 1]
            for param, extra in extraParamsToConsider:
                newValue = idGet(param, s + 1, None, extra=extra)
                if newValue is None:
                    del session[f"{param}{s}{extra}"]
                else:
                    session[f"{param}{s}{extra}"] = newValue
                # session[f"_{param}{s}{extra}"] =
                # idGet(f"_{param}", s+1, None, extra=extra)
            session["scenarioSetParams"][s] = savedParams[s + 1]
            session["scenarioSetParamsExtra"][s] = savedExtraParams[s + 1]
            session["activeErrors"][s] = session["activeErrors"][s + 1]

        # Delete duplicated end scenario params
        # TODO: Confirm if underscore params need to be deleted
        for param in savedParams[scenarioCount]:
            del session[f"{param}{scenarioCount}"]
            # del session[f"_{param}{scenarioCount}"]
        for param, extra in savedExtraParams[scenarioCount]:
            del session[f"{param}{scenarioCount}{extra}"]
            # del session[f"_{param}{scenarioCount}{extra}"]
        del session["scenarioSetParams"][scenarioCount]
        del session["scenarioSetParamsExtra"][scenarioCount]
        del session["activeErrors"][scenarioCount]

        # Update scenario count
        session["scenarioCount"] -= 1
        st.rerun()


# Page Content
st.title("Scenario Parameters")

st.markdown(
    (
        f"""
    This page allows for configuring the parameters that will be used
    in different scenarios by the simulation. To allow for direct
    comparison of different parameter sets, you may define a series of
    scenarios in which different parameter values are used. Up to {maxScenarios}
    additional scenarios plus the baseline can be run in a single
    simulation.

    Select a tab to view or modify the parameters under that category.
    Hover your mouse over the :material/help: help icon next to a
    parameter's input field to show an explanation of what that
    parameter represents. Hover your mouse over any buttons to show an
    explanation of what that button does. After moving a slider, use
    the left and right arrow keys to fine-tune the parameter's value.
"""
    )
)

rerunTime()

# List current scenarios
st.header("Current Scenarios")

if scenarioCount == 0:
    st.markdown(
        """
    No additional scenarios have been defined. If you run the
    simulation now without adding any additional scenarios, only the
    baseline scenario will be included in the model, using the
    parameters defined at the
    :grey-badge[:material/variable_insert: Baseline Parameters] page.
"""
    )
elif scenarioCount == 1:
    st.markdown(
        f"""
    There is currently 1 additional scenario defined for the simulation
    (excluding the baseline scenario),
    named {session[f'scenarioName{1}']}.
"""
    )
else:
    st.markdown(
        f'''
There are currently {scenarioCount} additional scenarios defined for
the simulation (excluding the baseline scenario), with the following
names:

{'\n'.join(f'- {session[f'scenarioName{id}']}' for id in range(1, scenarioCount + 1))}
'''
    )

# TODO: Loadable parameter templates (part of template tab?)

# Scenario addition field
st.header("Scenario Parameter Configuration")
for id in range(1, scenarioCount + 1):
    with st.container(border=True):
        st.header(f"Scenario #{id}")
        # Scenario name
        loadKey("scenarioName", id, f"Scenario #{id}")
        scenarioName = st.text_input(
            "Name of Scenario",
            f"Scenario #{id}",
            max_chars=50,
            key=f"_scenarioName{id}",
            autocomplete="off",
            on_change=saveKey,
            args=["scenarioName", id],  # type: ignore
            placeholder="Enter a name for this scenario",
            help="""
                The name to give to this scenario, which will display
                in tables and graphs generated by the dashboard.
            """,
        )
        # Remove button
        st.button(
            label="Remove Scenario",
            icon=":material/delete:",
            key=f"scenarioRemove{id}",
            on_click=deleteScenario,
            args=[id],
            help="""
                Remove this scenario from the simulation set, thus
                ensuring that it is not ran when you run the
                simulation.
            """,
        )
        # Parameters for this scenario
        st.subheader("Parameters")

        # Place to put warnings and errors in the current parameter selection
        errorChecker(id, f"Errors in {scenarioName}")

        # Create tabs for each category of parameters
        (diseaseTab, communityTab, interventionTab, dynamicTab) = st.tabs(
            [
                ":material/coronavirus: Disease",
                ":material/groups: Community",
                ":material/vaccines: Vaccination and NPIs",
                ":material/manage_history: Dynamic",
            ]
        )
        # :material/pattern: for the template tab
        # Basic parameters
        # with basicTab: buildBasicTab(id)

        # Disease parameters
        with diseaseTab:
            buildDiseaseTab(id)

        # Environment parameters
        with communityTab:
            buildCommunityTab(id)

        # Vaccination and NPIs
        with interventionTab:
            buildVaccinationNPITab(id)

        # Dynamic parameters
        with dynamicTab:
            buildDynamicTab(id)

# Button to add another scenario
st.button(
    label="Add Scenario",
    icon=":material/add:",
    on_click=addScenario,
    key=f"scenarioAdd{id}",
    disabled=not scenarioCount < maxScenarios,
    help=(
        """
        Add another scenario to the simulation, where you can configure
        different parameter values to use instead of the baseline
        values.
    """
        if scenarioCount < maxScenarios
        else f"""
        To keep the number of scenarios manageable, no more than {maxScenarios}
        scenarios plus the baseline may be added to the simulation set
        at once.
    """
    ),
)
