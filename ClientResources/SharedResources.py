# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other stored variables used by the client application

# Imports
import logging
import re
from collections import deque
from queue import Queue
from typing import List, Literal

import streamlit as st

# Logging
sharedLog = logging.getLogger(__name__)

# Debug Settings

# Toggle to use preset JSON config with runSimulation instead of using
# the parameters set by the user, for testing
usePresetParams = False

# Toggle to use built-in data instead of model output
# TODO: Include different types of preset data
# (e.g. vaccinated vs unvaccinated) for better testing
usePresetData = False

# Toggle to save the JSON form of parameters as a file
saveJSON = False

# Other Constants

# Maximum number of additional scenarios
maxScenarios = 30

# URLs where client/server is located (change to hosted URLs)
clientUrl = "http://localhost:8501/"
serverUrl = "http://127.0.0.1:8000/"

# Queues used to store data from server requests
resultQueue = Queue[list | tuple]()
currentProgress = deque[int](maxlen=1)
statusQueue = list[str]()

# Dictionary holding ordinal strings for variable-length forms
ordinals = {
    1: "First",
    2: "Second",
    3: "Third",
    4: "Fourth",
    5: "Fifth",
    6: "Sixth",
    7: "Seventh",
    8: "Eighth",
    9: "Ninth",
    10: "Tenth",
}

# Dictionary getting the population of each community the simulator uses
communityPopulation = {"newcastle": 272407, "cairns": 140402}

# List of age categories with times included, for tabling
ageWithTime = [
    "Young Infant (0-6 Months)",
    "Infant (7-24 Months)",
    "Young Child (3-5 Years)",
    "Child (6-12 Years)",
    "Adolescent (13-17 Years)",
    "Young Adult (18-24 Years)",
    "Adult (25-44 Years)",
    "Older Adult (45-64 Years)",
    "Senior (65-79 Years)",
    "Older Senior (80+ Years)",
]
# Dictionary to allow converting ages with time into schema-compatible names
ageTimeDict = {
    "young_infant": "Young Infant (0-6 Months)",
    "infant": "Infant (7-24 Months)",
    "young_child": "Young Child (3-5 Years)",
    "child": "Child (6-12 Years)",
    "adolescent": "Adolescent (13-17 Years)",
    "young_adult": "Young Adult (18-24 Years)",
    "adult": "Adult (25-44 Years)",
    "older_adult": "Older Adult (45-64 Years)",
    "senior": "Senior (65-79 Years)",
    "older_senior": "Older Senior (80+ Years)",
}
# Nested dictionary holding number of individuals in each age bracket
communityAgePops = {
    "newcastle": {
        "Young Infant (0-6 Months)": 2742,
        "Infant (7-24 Months)": 6641,
        "Young Child (3-5 Years)": 10242,
        "Child (6-12 Years)": 20603,
        "Adolescent (13-17 Years)": 18513,
        "Young Adult (18-24 Years)": 27015,
        "Adult (25-44 Years)": 71299,
        "Older Adult (45-64 Years)": 69949,
        "Senior (65-79 Years)": 31384,
        "Older Senior (80+ Years)": 14019,
        "Total": 272407,
    },
    "cairns": {
        "Young Infant (0-6 Months)": 1837,
        "Infant (7-24 Months)": 4277,
        "Young Child (3-5 Years)": 6381,
        "Child (6-12 Years)": 12650,
        "Adolescent (13-17 Years)": 10432,
        "Young Adult (18-24 Years)": 12074,
        "Adult (25-44 Years)": 42394,
        "Older Adult (45-64 Years)": 36541,
        "Senior (65-79 Years)": 10675,
        "Older Senior (80+ Years)": 3141,
        "Total": 140402,
    },
}


def ageRangeString(lower: int | float, upper: int | float) -> str:
    """
    Simple function to format 2 numbers as an age range, accounting for
    unbound ends and rendering decimal values as months.

    Parameters:
        lower (int or float): The lower bound of the range.

        lower (int or float): The upper bound of the range.

    Returns:
        str: The string representation of the specified range.
    """
    if upper > 250:
        # Use a + for ranges large enough to be uncapped
        return f"{lower}+"
    elif (isinstance(lower, float) or isinstance(upper, float)) and upper < 9:
        # Use months if it's more readable that way
        return "{low}-{high} Months".format(
            low=round(lower * 12), high=round((upper if upper < 1 else upper - 1) * 12)
        )
    else:
        return f"{lower}-{upper - 1}"


def ageRangeCombiner(ages: list[str]) -> str:
    """
    Function to convert a list of age brackets into a single string
    concisely listing them all.

    Parameters:
        ages (list of str): The age groups to combine.

    Returns:
        str: The string representation of the specified age groups.
    """
    # Immediate end conditions
    if len(ages) == 1:
        return (
            "All Ages" if ages[0] == "Total" else re.findall(r"\((.*?)\)", ages[0])[0]
        )
    if set(ages) == set(ageWithTime):
        return "All Ages"

    # Dictionaries to get the starts/ends of each age bracket
    ageStarts = {
        "Young Infant (0-6 Months)": 0,
        "Infant (7-24 Months)": 0.5,
        "Young Child (3-5 Years)": 3,
        "Child (6-12 Years)": 6,
        "Adolescent (13-17 Years)": 13,
        "Young Adult (18-24 Years)": 18,
        "Adult (25-44 Years)": 25,
        "Older Adult (45-64 Years)": 45,
        "Senior (65-79 Years)": 65,
        "Older Senior (80+ Years)": 80,
    }
    ageEnds = {
        "Young Infant (0-6 Months)": 0.5,
        "Infant (7-24 Months)": 3,
        "Young Child (3-5 Years)": 6,
        "Child (6-12 Years)": 13,
        "Adolescent (13-17 Years)": 18,
        "Young Adult (18-24 Years)": 25,
        "Adult (25-44 Years)": 45,
        "Older Adult (45-64 Years)": 65,
        "Senior (65-79 Years)": 80,
        "Older Senior (80+ Years)": 999,
    }

    # Sort the ages
    ageList = ages.copy()
    ageList.sort(key=lambda x: ageStarts[x])

    # Iteratively identify continuous age blocks and display as string
    currentStart, currentEnd = ageStarts[ageList[0]], ageEnds[ageList[0]]
    currentString = ""
    for age in ageList[1:]:
        if ageStarts[age] == currentEnd:
            currentEnd = ageEnds[age]
        else:
            currentString += f", {ageRangeString(currentStart, currentEnd)}"
            currentStart, currentEnd = ageStarts[age], ageEnds[age]
    currentString += f", {ageRangeString(currentStart, currentEnd)}"
    currentString += " Years" if currentString[-6:] != "Months" else ""
    return currentString[2:]


# Set containing health outcomes selectable for tables
tableOutcomes = (
    "Symptomatic Infections",
    "Diagnosed Cases",
    "GP Visits",
    "Hospitalisations",
    "ICU Visits",
    "Deaths",
)

# Dictionary getting adjective forms of health outcomes
outcomeAdjectives = {
    "Symptomatic Infections": "Symptomatic",
    "Diagnosed Cases": "Diagnosed",
    "GP Visits": "GP Visiting",
    "Hospitalisations": "Hospitalised",
    "ICU Visits": "ICU Visiting",
    "Deaths": "Dead",
}

# Dictionary getting session_state variables for outcome rates
outcomeRateVariables = {
    "Diagnosed Cases": "caseRatio",
    "GP Visits": "gpRatio",
    "Hospitalisations": "hospitalRatio",
    "ICU Visits": "icuRatio",
    "Deaths": "deathRatio",
}

# Default values for rates
outcomeRateDefaults = {
    "Diagnosed Cases": 0.5,
    "GP Visits": 0.17,
    "Hospitalisations": 0.00316133,
    "ICU Visits": 0.00063227,
    "Deaths": 0.000115077,
}


# Tuple holding the names of the different possible NPIs
npis = (
    "Vaccination",
    "School Closure",
    "Withdrawal Increase",
    "Reduced Group Size",
    "Background Contact Count Reduction",
)

# Tuple holding the camelCase names of NPIs for anchor tags and the like
npiCamel = ("vaccination", "schoolClosure", "withdrawalIncrease", "reducedGroup", "bcc")

# Tuple holding the possible trigger conditions for NPIs
triggerConditions = {
    "Always": "timed",
    "Timed": "timed",
    "Community Case Rate": "community_rate",
    "Community Case Total": "community_cases",
    "Cases per School": "per_school_cases",
    # "Cases per K-12 School": "per_primary_high_school_cases",
}


# Simple function to get theme colours
# Change these values if background colour changes
def backgroundColour() -> str:
    """
    Simple function to get the background colour of the current theme.

    Returns:
        str: The hex code representing the background colour as a string.
    """
    return "#0F1116" if st.context.theme.type == "dark" else "#FFFFFF"


# Colour codes for Paul Tol's "bright" colourblind-safe palette
# (and other pallettes if enough scenarios are created)
brightCodes = (
    "#BBBBBB",
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#EE7733",
    "#CC3311",
    "#009988",
    "#332288",
    "#882255",
)

# Extend pallette list if absolutely necessary
while len(brightCodes) < maxScenarios:
    brightCodes = brightCodes + brightCodes  # type: ignore


class AnalysisFile:
    """
    Class for analysis file parameters
    """

    # TODO: Flesh out docstrings
    def __init__(
        self,
        tool: Literal["epidemic", "asir"],
        names: List[str],
        summaryValue: Literal["mean", "median"] = "median",
        outcome: Literal[
            "Symptomatic Infections",
            "Diagnosed Cases",
            "Hospitalisations",
            "Deaths",
            "ICU Visits",
            "GP Visits",
        ] = "Symptomatic Infections",
        **kwargs,
    ):
        self.tool = tool
        self.names = names
        self.summaryValue = summaryValue
        self.outcome = outcome
        # Check required values for different tools
        if tool == "epidemic":
            self.useCumulative = kwargs.get("useCumulative", False)
            self.splitByAge = kwargs.get("splitByAge", False)
        if tool == "asir":
            self.useProportion = kwargs.get("useProportion", False)
            self.differenceType = kwargs.get("differenceType", "")
            self.vaccinatedOnly = kwargs.get("vaccinated", False)
