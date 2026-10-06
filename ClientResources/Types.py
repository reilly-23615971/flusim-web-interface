# Flusim Web Interface Application
# Developed by Reilly Evans
# Types, classes and associated constants used by the client application

# Imports
from collections import deque
from dataclasses import dataclass, field
from queue import Queue
from typing import Literal, Optional, Sequence, get_args

# Literal string classes

# Age groups used by the simulator and displayed on the dashboard
# Names used on the dashboard itself
type AgeGroup = Literal[
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
AGE_GROUPS = get_args(AgeGroup.__value__)
# Names plus total, for results tables
type AgeWithTotal = AgeGroup | Literal["Total"]
AGE_WITH_TOTAL = AGE_GROUPS + ("Total",)
# Keys (snake case used in JSON schema)
type AgeGroupKey = Literal[
    "young_infant",  # 0-6 months
    "infant",  # 7-24 months (0.5-2 years)
    "young_child",  # 3-5 years
    "child",  # 6-12 years
    "adolescent",  # 13-17 years
    "young_adult",  # 18-24 years
    "adult",  # 25-44 years
    "older_adult",  # 45-64 years
    "senior",  # 65-79 years
    "older_senior",  # 80+ years
]
AGE_GROUP_KEYS = get_args(AgeGroupKey.__value__)
# Convert between keys and names
AGE_KEY_CONVERTER: dict[AgeGroupKey, AgeGroup] = {
    key: name for key, name in zip(AGE_GROUP_KEYS, AGE_GROUPS)
}


# Types of vaccine dose administered in the simulation
type BoosterType = Literal["primary", "booster"]

# Communities that can be modelled
type CommunityName = Literal["albany", "cairns", "newcastle"]
COMMUNITY_NAMES = get_args(CommunityName.__value__)

# Health burden outcomes that can be calculated by the dashboard
type HealthOutcome = Literal[
    "Symptomatic Infections",
    "Diagnosed Cases",
    "GP Visits",
    "Hospitalisations",
    "ICU Visits",
    "Deaths",
]
HEALTH_OUTCOMES = get_args(HealthOutcome.__value__)

# Locations in the simulation
type AlbanyPatch = Literal[
    "Albany",
    "Kojonup",
    "Plantagenet",
    "Stirling Range National Park",
    "Denmark",
    "McKail - Willyung",
    "Gnowangerup",
    "Albany Region",
    "Little Grove - Elleker",
    "Bayonet Head - Lower King",
    "Katanning",
]
type CairnsPatch = Literal[
    "Westcourt - Bungalow",
    "Cairns City",
    "Redlynch",
    "White Rock",
    "Trinity Beach - Smithfield",
    "Earlville - Bayview Heights",
    "Clifton Beach - Kewarra Beach",
    "Freshwater - Stratford",
    "Woree",
    "Mount Sheridan",
    "Bentley Park",
    "Gordonvale - Trinity",
    "Whitfield - Edge Hill",
    "Brinsmead",
    "Lamb Range",
    "Kanimbla - Mooroobool",
    "Manunda",
    "Edmonton",
    "Manoora",
    "Yorkeys Knob - Machans Beach",
]
type NewcastlePatch = Literal[
    "Glendale - Cardiff - Hillsborough",
    "Maryland - Fletcher - Minmi",
    "Newcastle - Cooks Hill",
    "Newcastle Port - Kooragang",
    "Belmont - Bennetts Green",
    "Belmont South - Blacksmiths",
    "Shortland - Jesmond",
    "Redhead",
    "Wickham - Carrington - Tighes Hill",
    "Valentine - Eleebana",
    "Beresfield - Hexham",
    "Swansea - Caves Beach",
    "Hamilton - Broadmeadow",
    "Charlestown - Dudley",
    "Warners Bay - Boolaroo",
    "Merewether - The Junction",
    "Adamstown - Kotara",
    "Wallsend - Elermore Vale",
    "Stockton - Fullerton Cove",
    "Lambton - New Lambton",
    "Mayfield - Warabrook",
    "Mount Hutton - Windale",
    "Waratah - North Lambton",
]
ALBANY_PATCHES = get_args(AlbanyPatch.__value__)
CAIRNS_PATCHES = get_args(CairnsPatch.__value__)
NEWCASTLE_PATCHES = get_args(NewcastlePatch.__value__)
type CommunityPatch = AlbanyPatch | CairnsPatch | NewcastlePatch

# Conditions that control the enabling and disabling of interventions
type TriggerCondition = Literal[
    "none",
    "timed",
    "per_school_cases",
    "community_cases",
    "community_rate",
    "per_primary_high_school_cases",
]
# Dictionary to convert the names of conditions to keys
TRIGGER_KEY_CONVERTER: dict[str, TriggerCondition] = {
    "None": "none",
    "Always": "timed",
    "Timed": "timed",
    "Community Case Rate": "community_rate",
    "Community Case Total": "community_cases",
    "Cases per School": "per_school_cases",
    # "Cases per K-12 School": "per_primary_high_school_cases",
}


# Used by VisualisationFunctions to describe table columns
type VaccineStatus = Literal["All", "Vaccinated", "Unvaccinated"]
type ColumnDetails = tuple[
    HealthOutcome,  # health burden outcome
    Sequence[AgeWithTotal],  # age groups included in the column
    VaccineStatus,  # whether vaccinated individuals only should be included
    bool,  # display as percentages
    bool,  # display as difference from baseline
]


# Dataclasses
@dataclass
class AnalysisFile:
    """
    Class for descriptions of analysis files and what data they hold
    """

    def __init__(
        self,
        tool: Literal["epidemic", "asir"],
        names: list[str],
        summaryValue: Literal["mean", "median"] = "median",
        outcome: HealthOutcome = "Symptomatic Infections",
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


@dataclass
class CommunityData:
    """
    Class for storing a given community's relevant data
    """

    name: str
    population: int
    age_pops: dict[AgeWithTotal, int]
    patches: Sequence[CommunityPatch]


# Data for communities that can be modelled by the simulation
ALBANY = CommunityData(
    name="Albany",
    population=55109,
    age_pops={
        "Young Infant (0-6 Months)": 669,
        "Infant (7-24 Months)": 1430,
        "Young Child (3-5 Years)": 2312,
        "Child (6-12 Years)": 4782,
        "Adolescent (13-17 Years)": 4126,
        "Young Adult (18-24 Years)": 4061,
        "Adult (25-44 Years)": 12841,
        "Older Adult (45-64 Years)": 15668,
        "Senior (65-79 Years)": 6806,
        "Older Senior (80+ Years)": 2414,
        "Total": 55109,
    },
    patches=ALBANY_PATCHES,
)
CAIRNS = CommunityData(
    name="Cairns",
    population=140402,
    age_pops={
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
    patches=CAIRNS_PATCHES,
)
NEWCASTLE = CommunityData(
    name="Newcastle",
    population=272407,
    age_pops={
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
    patches=NEWCASTLE_PATCHES,
)
COMMUNITIES: dict[CommunityName, CommunityData] = {
    "albany": ALBANY,
    "cairns": CAIRNS,
    "newcastle": NEWCASTLE,
}


@dataclass
class SimParams:
    """
    Class for storing parameter details relevant for simulation run handling
    """

    scenario_names: list[str]
    analysis_formats: list[AnalysisFile]
    community: CommunityName
    symptomatic_rates: list[list[float]] = field(default_factory=list)
    health_outcome_rates: dict[str, dict] = field(default_factory=dict)
    age_health_outcome_rates: dict[str, dict] = field(default_factory=dict)
    scaling_factor: float = 1.0
    waning: bool = False


# Information on errors encountered while making requests to the server
# Tuple elements:

type RequestErrorData = tuple[
    str,  # brief description of the error
    str,  # long explanation of the error
    str,  # name of Material Symbols icon to display error with
    Optional[Exception],  # specific exception raised by server
]


@dataclass
class RequestStatus:
    """
    Class for storing queues monitoring server request results
    """

    results = Queue[list | dict]()  # Data returned by the request
    errors = Queue[RequestErrorData]()  # Error messages
    tasks = list[str]()  # Tasks completed as part of the request
    progress = deque[float](maxlen=1)  # Percent of request done


# Define a queue for each task type
SIM_STATUS = RequestStatus()
R0_CALIBRATION_STATUS = RequestStatus()
R0_CALCULATION_STATUS = RequestStatus()
