# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other stored variables used by the client application

# Imports
import logging
from collections import deque
from queue import Queue
from typing import List, Literal, Optional

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

# Toggle to round the values displayed in infection curves/burden tables
roundResults = True

# Other Constants

# Maximum number of additional scenarios
maxScenarios = 30

# Change this constant to affect the scenario/analysis progress bar split
splitPoint = 0.65

# URLs where client/server is located (change to hosted URLs)
clientUrl = "http://localhost:8501/"
serverUrl = "http://127.0.0.1:8000/"

# Dictionary holding templates and their details
templateDict = {
    "Influenza": (
        "microbiology",
        "ClientResources/Templates/default.json",
        """
Parameters simulating an influenza outbreak with an existing vaccinated population.
        """,
    ),
    "COVID-19": (
        "coronavirus",
        "ClientResources/Templates/covid.json",
        """
Parameters simulating a SARS-CoV-2 Delta outbreak with moderate NPIs enabled.
        """,
        # R0 is 6; should that be mentioned?
        # TODO: Replace increased withdrawal in COVID template
        # with workplace nonattendance when it's added again
    ),
}


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

# Tuple holding the names of the different possible NPIs
npis = (
    # "Vaccination",
    "School Closure",
    "Withdrawal Increase",
    "Reduced Group Size",
    "Background Contact Count Reduction",
)

# Tuple holding the camelCase names of NPIs for anchor tags and the like
npiCamel = ("schoolClosure", "withdrawalIncrease", "reducedGroup", "bcc")
# "vaccination",

# Tuple holding the possible trigger conditions for NPIs
triggerConditions = {
    "None": "none",
    "Always": "timed",
    "Timed": "timed",
    "Community Case Rate": "community_rate",
    "Community Case Total": "community_cases",
    "Cases per School": "per_school_cases",
    # "Cases per K-12 School": "per_primary_high_school_cases",
}

# Colour codes for Paul Tol's "muted" colourblind-safe palette
mutedCodes = [
    "#BBBBBB",
    "#CC6677",
    "#332288",
    "#DDCC77",
    "#117733",
    "#88CCEE",
    "#882255",
    "#44AA99",
    "#999933",
    "#AA4499",
]

# Extend palette list if absolutely necessary
while len(mutedCodes) < maxScenarios:
    mutedCodes = mutedCodes + mutedCodes[1:]

# Queues used to store data from server requests
resultQueue = Queue[list]()
errorQueue = Queue[tuple[str, str, str, Optional[Exception]]]()
currentProgress = deque[float](maxlen=1)
statusQueue = list[str]()


class AnalysisFile:
    """
    Class for descriptions of analysis files and what data they hold
    """

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
            self.dataTag = f"Epidemic{"Cumulative" if self.useCumulative else "Daily"}"
        if tool == "asir":
            self.useProportion = kwargs.get("useProportion", False)
            self.differenceType = kwargs.get("differenceType", "")
            self.vaccinatedOnly = kwargs.get("vaccinated", False)
            self.dataTag = f"Asir{"Vaccinated" if self.vaccinatedOnly else "Full"}"
