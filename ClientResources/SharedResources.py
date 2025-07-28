# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other stored variables used by the client application

# Imports
from queue import Queue
import logging

# Logging
sharedLog = logging.getLogger(__name__)

# Constants

# URL where server is located (change to proxy URL)
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
# Tuple holding the possible age categories used by the simulator
ageCategories = (
    'Young Infant',  # 0-6 months
    'Infant',        # 7-24 months (0.5-2 years)
    'Young Child',   # 3-5 years
    'Child',         # 6-12 years
    'Adolescent',    # 13-17 years
    'Young Adult',   # 18-24 years
    'Adult',         # 25-44 years
    'Older Adult',   # 45-64 years
    'Senior',        # 65-79 years
    'Older Senior'   # 80+ years
)
# Set containing health outcomes selectable for tables
tableOutcomes = {
    'Infections', 'Cases', 'Hospitalisations', 
    'Deaths', 'ICU Visits', 'GP Visits'
}
# Dictionary getting adjective forms of health outcomes
outcomeAdjectives = {
    'Infections': 'Infected', 'Cases': 'Diagnosed', 
    'Hospitalisations': 'Hospitalised', 'Deaths': 'Dead', 
    'ICU Visits': 'Severely Ill', 'GP Visits': 'Visiting'
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
triggerConditions = (
    'Always', 'Timed', 'Community Case Rate', 'Community Case Total', 
    'Cases per School', 'Cases per K-12 School'  
)
# Tuple holding the different location types for kappa selection
kappaLocations = (
    'Households', 'K-12 Education', 'Tertiary Education', 
    'Workplaces', 'Childcare', 'Hospitals', 'Background'
)