# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import logging
import streamlit as st

# from ParameterTabs.basicParams import buildBasicTab, rerunTime
from ParameterTabs.diseaseParams import buildDiseaseTab
from ParameterTabs.communityParams import buildCommunityTab
from ParameterTabs.vaccinationNPIParams import buildVaccinationNPITab
from ParameterTabs.dynamicParams import buildDynamicTab
from ClientResources.InterfaceFunctions import (
    saveKey,
    loadKey,
    checkErrors,
    errorChecker,
)

# Logging
scenarioLog = logging.getLogger(__name__)

session = st.session_state


# Function for displaying status of error messages here
# TODO: Update for new errors
@st.fragment(run_every=1)
def scenarioErrorChecker(id):
    scenarioErrors = max(checkErrors(id))
    if scenarioErrors == 2:
        st.error(
            """
        Error: The parameters defined for this scenario contain
        unresolvable errors. These errors must be corrected before the
        model can be ran. Check the individual tabs for detailed error
        messages.
    """,
            icon=":material/error:",
        )
    elif scenarioErrors == 1:
        st.warning(
            """
        Warning: The parameters defined for this scenario contain
        logical issues. The simulation may still be ran, but the results
        may differ from what was intended. Check the individual tabs for
        detailed error messages.
    """,
            icon=":material/warning:",
        )
    else:
        st.markdown(
            """
        Currently, all parameters have been set to valid values; the
        simulation should run as intended. If any errors are detected with
        the parameters selected for this scenario, they will be
        described here.
    """
        )


# Load necessary parameter values
scenarioCount = session.get("scenarioCount", 0)
errors = [checkErrors(id) for id in range(scenarioCount + 1)]

# Parameter lists for transferring scenarios upon deletion
parameterSet = {
    "scenarioName",
    # "runCount",
    # "cycleCount",
    # "startDay",
    "deathRowCount",
    "deathRemainingAgeGroups",
    "caseRatio",
    "gpRatio",
    "hospitalRatio",
    "icuRatio",
    "deathRatio",
    "withdrawalWork",
    "withdrawalSchool",
    "diagnosisDelay",
    "bccRate",
    "childSupervision",
    "maxClassCount",
    "maxClassSize",
    "maxAdultClassSize",
    "maxWorkGroupSize",
    "maxNeighborGroupSize",
    "maxChurchGroupSize",
    "transRowCount",
    "kappaRowCount",
    "seedPeriodError",
    "transRemainingAgeGroups",
    "kappaRemainingLocations",
    "seedRate",
    "seedPeriod",
    "beta",
    "betaAsymptomatic",
    "betaPostSymptomatic",
    "householdKappa",
    "asymptomaticChild",
    "asymptomaticAdult",
    "latencyPeriod",
    "preSymptomPeriod",
    "symptomPeriod",
    "postSymptomPeriod",
    "naturalImmunityDuration",
    "naturalWanedEfficacy",
    "naturalWaningRate",
    "seedRowCount",
    "closeRowCount",
    "bccRowCount",
    "seedDynamicError",
    "closeDynamicError",
    "bccDynamicError",
    "vacAgeRowCount",
    "primaryDoseCount",
    "primWanedRowCount",
    "boostAgeRowCount",
    "socialRowCount",
    "baseVacPropError",
    "ageVacPropError",
    "basePrimEfficacyError",
    "agePrimEfficacyError",
    "baseBoostEfficacyError",
    "ageBoostEfficacyError",
    "schoolTypeError",
    "adultWithdrawalError",
    "childWithdrawalError",
    "reducedGroupError",
    "bccError",
    "triggerRateError",
    "triggerTotalError",
    "vaccinePeriodError",
    "schoolClosurePeriodError",
    "withdrawalIncreasePeriodError",
    "reducedGroupPeriodError",
    "bccPeriodError",
    "classDismissal",
    "vaccineRemainingAgeGroups",
    "primaryRemainingWanedGroups",
    "boosterRemainingAgeGroups",
    "socialRemainingAgeGroups",
    "vaccineToggle",
    "vaccineTrigger",
    "vaccinePeriod",
    "limitDosesToggle",
    "initialDoseReserve",
    "firstDoseRate",
    "initialVaccinated",
    "targetVaccinated",
    "primaryDoseCount",
    "primaryDelay",
    "primaryDuration",
    "primaryWanedEfficacy",
    "primaryWaningRate",
    "boosterToggle",
    "boosterDoseCount",
    "boosterDelay",
    "boosterDuration",
    "boosterBaseEfficacy",
    "boosterWanedEfficacy",
    "boosterWaningRate",
    "socialDistancingToggle",
    "socialDistancingCompliance",
    "caseIsolation",
    "classDismissal",
    "schoolClosureToggle",
    "schoolClosureTrigger",
    "schoolClosurePeriod",
    "schoolClosureTypes",
    "schoolClosureCompliance",
    "withdrawalIncreaseToggle",
    "withdrawalIncreaseTrigger",
    "withdrawalIncreasePeriod",
    "withdrawalIncreaseAdult",
    "withdrawalIncreaseChild",
    "reducedGroupToggle",
    "reducedGroupTrigger",
    "reducedGroupPeriod",
    "reducedGroupSize",
    "bccToggle",
    "bccTrigger",
    "bccPeriod",
    "bccReducedRate",
    "rateStartThreshold",
    "rateRelaxThreshold",
    "caseTotalThreshold",
}

doubleParameterSet = {
    "deathAgeGroup",
    "deathRatio",
    "transAgeGroup",
    "kappaLocation",
    "transInfect",
    "transSuscept",
    "kappaValue",
    "seedCycle",
    "seedNewRate",
    "closeCycle",
    "closeNewRate",
    "bccCycle",
    "bccNewRate",
    "vacAgeGroup",
    "primWanedGroup",
    "boostAgeGroup",
    "socialAgeGroup",
    "primAgeRowCount",
    "primaryRemainingAgeGroups",
    "vacAgeInitial",
    "vacAgeTarget",
    "primAgeWanedEfficacy",
    "primaryBaseEfficacy",
    "boostAgeEfficacy",
    "boostAgeWanedEfficacy",
    "socialCompliance",
}

tripleParameterSet = {"primAgeGroup", "primAgeEfficacy"}


# Simple function to add an additional scenario
def addScenario():
    session["scenarioCount"] += 1
    newCount = session["scenarioCount"]
    session[f"scenarioName{newCount}"] = f"Scenario #{newCount}"
    session["scenarioSetParams"][newCount] = []
    session["scenarioSetParamsExtra"][newCount] = []
    session["activeErrors"][newCount] = {}


# Function to delete a scenario from the page
@st.dialog("Delete Scenario")
def deleteScenario(scenarioID):
    st.markdown(
        f"""
        Deleting the "{session[f'scenarioName{scenarioID}']}"
        scenario will erase any unique parameter values set for it. Are
        you sure you want to delete this scenario?
    """
    )
    if st.button("Delete Scenario"):
        # Get set of saved params
        savedParams = session["scenarioSetParams"]
        savedExtraParams = session["scenarioSetParamsExtra"]

        # Shift existing values down
        for s in range(scenarioID, scenarioCount):
            for param in savedParams[s]:
                session[f"{param}{s}"] = session[f"{param}{s + 1}"]
                session[f"_{param}{s}"] = session[f"_{param}{s + 1}"]
            for param, extra in savedExtraParams[s]:
                session[f"{param}{s}{extra}"] = session[f"{param}{s + 1}{extra}"]
                session[f"_{param}{s}{extra}"] = session[f"_{param}{s + 1}{extra}"]
            session["scenarioSetParams"][s] = savedParams[s + 1]
            session["scenarioSetParamsExtra"][s] = savedExtraParams[s + 1]
            session["activeErrors"][s] = session["activeErrors"][s + 1]

        # Delete end scenario params
        for param in savedParams[scenarioCount]:
            del session[f"{param}{scenarioCount}"]
            del session[f"_{param}{scenarioCount}"]
        for param, extra in savedExtraParams[scenarioCount]:
            del session[f"{param}{scenarioCount}{extra}"]
            del session[f"_{param}{scenarioCount}{extra}"]
        session["scenarioSetParams"][scenarioCount] = []
        session["scenarioSetParamsExtra"][scenarioCount] = []
        del session["activeErrors"][scenarioCount]

        # Update scenario count
        session["scenarioCount"] -= 1
        st.rerun()


# Page Content
st.title("Scenario Parameters")

st.markdown(
    (
        """
    This page allows for configuring the parameters that will be used
    in different scenarios by the simulation. To allow for direct
    comparison of different parameter sets, you may define a series of
    scenarios in which different parameter values are used. Up to 4
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
            args=[id],  # type: ignore
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
        oldTabs = """
        (basicTab, diseaseTab, communityTab, interventionTab, dynamicTab) = st.tabs(
            [
                ":material/start: Initialisation",
                ":material/coronavirus: Disease",
                ":material/groups: Community",
                ":material/vaccines: Vaccination and NPIs",
                ":material/manage_history: Dynamic",
            ]
        )"""
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
    disabled=not scenarioCount < 4,
    help=(
        """
        Add another scenario to the simulation, where you can configure
        different parameter values to use instead of the baseline
        values.
    """
        if scenarioCount <= 3
        else """
        To keep the number of scenarios manageable, no more than 4
        scenarios plus the baseline may be added to the simulation set
        at once.
    """
    ),
)

# TODO: Debug
# st.header('DEBUG ZONE')
# st.write(session)
