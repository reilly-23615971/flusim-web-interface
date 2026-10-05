# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and debug settings used by the client application

# Imports
from ClientResources.Types import AgeWithTotal, Community

# Debug Settings

# Toggle to use preset JSON config with runSimulation instead of using
# the parameters set by the user, for testing
# Note that R0 calibration has its own file paths!
USE_PRESET_PARAMS = False
PRESET_JSON_PATH = "ClientResources/MultiStrainParams.json"

# Toggle to use built-in data instead of model output
USE_PRESET_DATA = False
PRESET_SCENARIO_NAMES = [
    "Baseline",
    "School Closure",
    "Case Isolation",
    "Community Contact Reduction",
]
PRESET_COMMUNITY: Community = "newcastle"
PRESET_DATA_PATHS = {
    "Cumulative": "./TestData/epidemicMedianCumulative.csv",
    "Daily Rate": "./TestData/epidemicMedianDaily.csv",
    "ASIR": "./TestData/asirMedianAbsolute.csv",
    "Vaccinated": "./TestData/asirMedianVaccinated.csv",
}

# Toggle to save the JSON form of parameters as a file
LOG_PARAM_JSON = False

# Toggle to round the values displayed in infection curves/burden tables
ROUND_RESULTS = True

# Toggle to add buttons downloading frequently-used tables to Health Burden Outcomes
SHOW_DEBUG_DOWNLOADS = False

# Other Constants

# Maximum number of additional scenarios
MAX_SCENARIOS = 30

# Change this constant to affect the scenario/analysis progress bar split
PROGRESS_SPLIT_POINT = 0.65

# URLs where client/server is located
CLIENT_URL = "http://localhost:8501/"
SERVER_URL = "http://127.0.0.1:8000/"

# Dictionary holding templates and their details
TEMPLATES = {
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
ORDINALS = {
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
POPULATION: dict[Community, int] = {"newcastle": 272407, "cairns": 140402}

# Nested dictionary holding number of individuals in each age bracket
AGE_POPULATION: dict[Community, dict[AgeWithTotal, int]] = {
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


# Colour codes for Paul Tol's "muted" colourblind-safe palette
MUTED_CODES = [
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
while len(MUTED_CODES) < MAX_SCENARIOS:
    MUTED_CODES = MUTED_CODES + MUTED_CODES[1:]
