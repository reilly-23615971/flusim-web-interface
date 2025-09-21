# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other stored variables used by the client application

# Imports
import logging
from queue import Queue
from typing import List, Literal
import streamlit as st

# Logging
sharedLog = logging.getLogger(__name__)

# Constants

# Toggle to use preset JSON config with runSimulation instead of using 
# the parameters set by the user, for testing
usePresetParams = True

# Toggle to use built-in data instead of model output
usePresetData = True

# URLs where client/server is located (change to proxy URL)
clientUrl = 'http://localhost:8501/'
serverUrl = 'http://127.0.0.1:8000/'
# Queue used to store CSV data from completed server requests
resultQueue = Queue()

# Dictionary holding ordinal strings for variable-length forms
ordinals = {
    1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth', 5: 'Fifth', 
    6: 'Sixth', 7: 'Seventh', 8: 'Eighth', 9: 'Ninth', 10: 'Tenth'
}



# Dictionary getting the population of each community the simulator uses
communityPopulation = {'newcastle': 272407, 'cairns': 140402}

# Dictionary holding the possible age categories used by the simulator
ageCategories = {
    'Young Infant': 'young_infant',  # 0-6 months
    'Infant': 'infant',              # 7-24 months (0.5-2 years)
    'Young Child': 'young_child',    # 3-5 years
    'Child': 'child',                # 6-12 years
    'Adolescent': 'adolescent',      # 13-17 years
    'Young Adult': 'young_adult',    # 18-24 years
    'Adult': 'adult',                # 25-44 years
    'Older Adult': 'older_adult',    # 45-64 years
    'Senior': 'senior',              # 65-79 years
    'Older Senior': 'older_senior'   # 80+ years
}
# List of age categories with times included, for tabling
ageWithTime = [
    'Young Infant (0-6 Months)', 'Infant (7-24 Months)', 
    'Young Child (3-5 Years)', 'Child (6-12 Years)', 
    'Adolescent (13-17 Years)', 'Young Adult (18-24 Years)', 
    'Adult (25-44 Years)', 'Older Adult (45-64 Years)', 
    'Senior (65-79 Years)', 'Older Senior (80+ Years)'
]
# Nested dictionary holding number of individuals in each age bracket
communityAgePops = {
    'newcastle': {
        'Young Infant (0-6 Months)': 2742, 'Infant (7-24 Months)': 6641, 
        'Young Child (3-5 Years)': 10242, 'Child (6-12 Years)': 20603, 
        'Adolescent (13-17 Years)': 18513, 'Young Adult (18-24 Years)': 27015, 
        'Adult (25-44 Years)': 71299, 'Older Adult (45-64 Years)': 69949, 
        'Senior (65-79 Years)': 31384, 'Older Senior (80+ Years)': 14019, 
        'Total': 272407
    }, 
    'cairns': {
        'Young Infant (0-6 Months)': 1837, 'Infant (7-24 Months)': 4277, 
        'Young Child (3-5 Years)': 6381, 'Child (6-12 Years)': 12650, 
        'Adolescent (13-17 Years)': 10432, 'Young Adult (18-24 Years)': 12074, 
        'Adult (25-44 Years)': 42394, 'Older Adult (45-64 Years)': 36541, 
        'Senior (65-79 Years)': 10675, 'Older Senior (80+ Years)': 3141, 
        'Total': 140402
    }
}



# Set containing health outcomes selectable for tables
tableOutcomes = {
    'Infections', 'Cases', 'Hospitalisations', 
    'Deaths', 'ICU Visits', 'GP Visits'
}

"""
# Set containing possible forms the health outcomes can take
tableTypes = {
    'Frequency', 'Percentage of Population'
}
"""

# Dictionary getting adjective forms of health outcomes
outcomeAdjectives = {
    'Infections': 'Infected', 'Cases': 'Diagnosed', 
    'Hospitalisations': 'Hospitalised', 'Deaths': 'Dead', 
    'ICU Visits': 'Severely Ill', 'GP Visits': 'Visiting'
}

# Dictionary getting session_state variables for outcome rates
outcomeRateVariables = {
    'Cases': 'caseRatio', 'Hospitalisations': 'hospitalRatio', 
    'Deaths': 'deathRatio', 'ICU Visits': 'icuRatio', 'GP Visits': 'gpRatio'
}

# Default values for rates
outcomeRateDefaults = {
    'Cases': 0.5, 'Hospitalisations': 0.25, 
    'Deaths': 0.05, 'ICU Visits': 0.1, 'GP Visits': 0.333
}



# Tuple holding the names of the different possible NPIs
npis = (
    'Vaccination', 'School Closure', 'Withdrawal Increase', 
    'Reduced Group Size', 'Background Contact Count Reduction'
)

# Tuple holding the camelCase names of NPIs for anchor tags and the like
npiCamel = (
    'vaccination', 'schoolClosure', 'withdrawalIncrease', 'reducedGroup', 'bcc'
)

# Tuple holding the possible trigger conditions for NPIs
triggerConditions = {
    'Always': 'timed', 'Timed': 'timed', 
    'Community Case Rate': 'community_rate', 
    'Community Case Total': 'community_cases', 
    'Cases per School': 'per_school_cases', 
    'Cases per K-12 School': 'per_primary_high_school_cases'  
}

# Tuple holding the different location types for kappa selection
kappaLocations = {
    'Households': 'household', 'K-12 Education': 'child_education', 
    'Tertiary Education': 'adult_education', 'Workplaces': 'workplace', 
    'Childcare': 'child_care', 'Hospitals': 'hospital', 
    'Background Interactions': 'background'
}



# Simple function to get theme colours
# Change these values if background colour changes
def backgroundColour(): return (
    '#0F1116' if st.context.theme.type == 'dark' else '#FFFFFF'
)



"""
Class for analysis file parameters
"""
class AnalysisFile:
    def __init__(
        self, tool: Literal['epidemic', 'asir'], names: List[str], 
        summaryValue: Literal['mean', 'median'] = 'median', 
        outcome: Literal[
            'Infections', 'Cases', 'Hospitalisations', 
            'Deaths', 'ICU Visits', 'GP Visits'
        ] = 'Infections', **kwargs
    ):
        self.tool = tool
        self.names = names
        self.summaryValue = summaryValue
        self.outcome = outcome
        # Check required values for different tools
        if tool == 'epidemic':
            self.useCumulative = kwargs.get('useCumulative', False)
            self.splitByAge = kwargs.get('splitByAge', False)
        if tool == 'asir':
            self.useProportion = kwargs.get('useProportion', False)
            self.differenceType = kwargs.get('differenceType', '')