# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server for running the simulation

# Imports
import asyncio, logging, threading, json
from io import BytesIO
from datetime import datetime
from zipfile import ZipFile
from aiohttp import ClientSession, ClientConnectorError, ClientResponseError
import streamlit as st
import streamlit_notify as stn
from ParameterTabs.basicParams import basicSchema
from ParameterTabs.diseaseParams import diseaseSchema
from ParameterTabs.communityParams import communitySchema
from ParameterTabs.vaccinationNPIParams import vaccineSchema
from ParameterTabs.dynamicParams import dynamicSchema
from ClientResources.ModelSchema import (
    Parameters, modelGuideFile, overrideParams, simulationSet, simulation
)
from ClientResources.InterfaceFunctions import idGet, checkErrors
from ClientResources.VisualisationFunctions import formatData
from ClientResources.SharedResources import (
    AnalysisFile, usePresetParams, tableOutcomes, outcomeRateVariables, 
    outcomeRateDefaults, serverUrl, resultQueue, ageCategories
)

# Logging
functionLog = logging.getLogger(__name__)

# Error class for getting full responses
class invalidSchemaError(Exception):
    def __init__(self, message, response):
        self.message = message
        self.response = response
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Full Response: {self.response})"








"""
Function to generate a JSON config file using the selected parameters
"""
def createConfig(scenarioCount):
    # Set up schema objects
    scenarioParams = [Parameters() for _ in range(scenarioCount)]

    # Populate parameters with session_state values
    for id, scenario in enumerate(scenarioParams):
        basicSchema(scenario, id)
        diseaseSchema(scenario, id)
        communitySchema(scenario, id)
        vaccineSchema(scenario, id)
        dynamicSchema(scenario, id)

    # Create config object
    return modelGuideFile(
        name = 'Flusim Dashboard Simulation',
        description = str(st.session_state.sessionID),
        output_folder = './results/',
        middle_joint = '-usingEpidemic',
        community_used = [st.session_state.get('community', 'newcastle')], 
        shared_overrides = overrideParams(parameters = scenarioParams[0]),
        simulation_sets = [simulationSet(
            name = 'Dashboard Simulation Set', 
            version = st.session_state.sessionID,
            simulations = [simulation(name = 'Baseline')] + [
                simulation(
                    name = st.session_state[f'scenarioName{i}'], 
                    override_setting = overrideParams(
                        parameters = scenarioParams[i]
                    )
                ) for i in range(1, scenarioCount)
            ]
        )]
    )





"""
Callback function for the Run Simulation button
"""
@st.dialog('Run Simulation')
def runSimulationButton():
    scenarioCount = st.session_state.get('scenarioCount', 0)
    errors = [checkErrors(id) for id in range(scenarioCount + 1)]
    if max((max(e) for e in errors)) >= 2: st.error(
f'''
There are errors with the parameters that have currently been selected 
for the following scenarios: {'\n'.join(
f'''
- {
    st.session_state[f'scenarioName{id}'] if id > 0 else 'Baseline'
}: {errors[id].count(2)} error(s)
''' 
for id in range(scenarioCount + 1) if max(errors[id]) >= 2)
}                            
        
Please correct these errors by modifying the corresponding parameters 
to valid values before running the simulation.
''', icon = ':material/error:'
    )
    else:
        # TODO: More detailed estimated time breakdown
        st.markdown(
f'''
With the current parameters, this simulation will use the 
"{st.session_state.get('community', 'newcastle').capitalize()}" 
community data, {'with only a single baseline scenario.' if not scenarioCount 
else f'''
with the following {scenarioCount + 1} scenarios:
                    
- Baseline
{'\n'.join(
    f'- {st.session_state[f'scenarioName{id}']}' 
    for id in range(1, scenarioCount + 1)
)}
'''}
'''
        )
        if max((max(e) for e in errors)) >= 1: st.warning(
f'''
There are minor issues with the parameters that have currently been 
selected for the following scenarios:

- Baseline                                 
{'\n'.join(
f'''
- {st.session_state[f'scenarioName{id}']}: {errors[id].count(1)} issue(s)
''' 
for id in range(1, scenarioCount + 1) if max(errors[id]) >= 1)}                            
        
Please make sure that these issues do not interfere with your intended 
simulation design before running the simulation.
''', icon = ':material/warning:'
        )
        # TODO: Make warning display for the chart one too
        if st.session_state.get('ChartGenerated'): st.warning('''
Running a new simulation will result in future tables and graphs using 
the new simulation's data. Please make sure to save any tables or graphs 
you wish to keep with the current simulation data before running a new 
simulation.
        ''', icon = ':material/bar_chart_off:')
        st.markdown('''
            Are you sure you want to run the simulation with the 
            selected parameters?
        ''')
        if st.button('Run Simulation'):
            # Set params indicating model is simulating
            st.session_state.simulationInProgress = True
            st.session_state.simulationStartTime = datetime.now()

            # Create the final model JSON
            # For testing use this JSON instead of parameters
            if usePresetParams: 
                parameterJSON = {
                    "name": "Simple Test",
                    "description": "2184",
                    "output_folder": "./results/",
                    "middle_joint": "-usingEpidemic_Emean",
                    "community_used": ["newcastle"],
                    "shared_overrides": {
                        "parameters": {
                            "Command_Argument": {"n_runs": 16,"n_cycles": 180},
                            "Scenario_Strain": [{"StrainId": 0,"Beta": 0.11}],
                            "Scenario_Parameter": {
                                "school_closure_trigger": "timed",
                                "school_closure_compliance": 0.5,
                                "school_closure_delay": 28,
                                "withdrawal_increase_trigger": "timed",
                                "withdrawal_increase_delay": 28,
                                "work_nonattendance_trigger": "timed",
                                "prob_work_nonattendance": 0.5,
                                "work_nonattendance_delay": 28
                            }
                        }
                    },
                    "override_templates": [{
                        "name": "test_1",
                        "parameters": {
                            "Scenario_Parameter": {
                                "seed_rate": 1.5
                            }
                        }
                    }],
                    "simulation_sets": [{
                        "name": "test_set_1",
                        "version": 2184,
                        "simulations": [
                            {"name": "test_sim_1"},
                            {"name": "test_sim_2", "apply_template": ["test_1"]}
                        ]
                    }]
                }
                scenarioNames = ['Base Rate', 'Boosted Rate']

            # Use this version in production
            else: 
                parameterJSON = createConfig(scenarioCount + 1).model_dump_json(
                    indent = 4, exclude_unset = True#, exclude_defaults = True
                )
                scenarioNames = ['Baseline'] + [
                    st.session_state[f'scenarioName{i}'] 
                    for i in range(1, scenarioCount + 1)
                ]

            # Save current parameter values that'll be used for 
            # visualisation when the user has potentially changed them
            st.session_state.PendingDataCommunity = st.session_state.get(
                'community', 'newcastle'
            )
            st.session_state.PendingDataScenarioNames = scenarioNames
            st.session_state.PendingDataScenarioCount = st.session_state[
                'scenarioCount'
            ]
            st.session_state.PendingDataHealthOutcomeRates = {
                outcome: {
                    scenario: idGet(
                        outcomeRateVariables[outcome], i, 
                        outcomeRateDefaults[outcome]
                    ) 
                    for i, scenario in enumerate(scenarioNames)
                }
                for outcome in outcomeRateDefaults.keys()
            }
            st.session_state.PendingDataMortalityRates = {
                scenarioNames[scenarioID]: {
                    idGet('deathAgeGroup', scenarioID, None, f'-{rowID}'): 
                    idGet(
                        'deathRatio', scenarioID, 
                        outcomeRateDefaults['Deaths'], f'-{rowID}'
                    ) 
                    for rowID in range(idGet('deathRowCount', scenarioID, 0))
                } 
                for scenarioID in range(
                    st.session_state.PendingDataScenarioCount + 1
                )
            }

            # Make the model call
            runModelWrapper(scenarioNames, parameterJSON)

            # Generate popup to let the user know it's pending
            stn.toast(
                'Sending a request to run the simulation. Please wait...', 
                icon = ":material/experiment:"
            )
            st.rerun()





"""
Function to send JSON model parameters to the server, awaiting a 
response containing the results of the simulation
"""
async def runModel(scenarioNames, parameterJSON):
    try:
        dataForms = [
            AnalysisFile(
                tool = 'epidemic', names = scenarioNames, useCumulative = True
            ), 
            AnalysisFile(
                tool = 'epidemic', names = scenarioNames, useCumulative = False
            ), 
            AnalysisFile(tool = 'asir', names = scenarioNames)
        ]
        
        # Send POST request to server with parameters
        functionLog.info(
            f'[runModel] Initialising session with base url {serverUrl}...'
        )
        async with ClientSession(
            raise_for_status = False, base_url = serverUrl
        ) as session:
            functionLog.info(f'[runModel] Sending post request...')
            async with session.post('runModel', json = json.loads(parameterJSON)) as response:
                responseData = await response.read()
                if response.status == 422:
                    responseText = await response.text()
                    raise invalidSchemaError('The parameter schema did not comply with the Pydantic model', responseText)
                response.raise_for_status()
            functionLog.info(f'[runModel] Response received! Returning data...')
        
        # Convert CSV statistics into DataFrame(s)
        functionLog.info(
            f'[runModel] Preparing to process {len(dataForms)} analyses...'
        )
        # Process without unzipping if there's only one analysis
        if len(dataForms) == 1: return [formatData(responseData, dataForms[0])]
        # Unzip data and format each analysis file
        with ZipFile(BytesIO(responseData)) as analyses:
            fileNames = analyses.namelist()
            for file in fileNames:
                functionLog.info(f'File Data: {analyses.read(file)}')
            if len(fileNames) == 0:
                functionLog.error(
                    f'[runModel] Server returned no readable files'
                )
                return 'EmptyZipFile'

            try: processedData = [
                formatData(analyses.read(file), dataForms[index]) 
                for index, file in enumerate(fileNames)
            ]
            except ValueError as e: 
                functionLog.error(
                    f'[runModel] Server returned malformed files: {e}'
                )
                return ('ValueError', e)
            except Exception as e:
                functionLog.error(
                    '[runModel] Server returned '
                    f'unspecified malformed files: {e}'
                )
                return ('UncaughtFormatError', e)
        return processedData
    # Catch errors and return specific values to indicate them
    except ClientConnectorError as e:
        functionLog.error(f'[runModel] Couldn\'t connect to server: {e}')
        return ('ClientConnectorError', e)
    except ClientResponseError as e:
        functionLog.error(f'[runModel] Server returned status {e.status}: {e}')
        if e.status in {500, '500'}: return ('ClientResponseError500', e)
        else: return ('ClientResponseError', e)
    except invalidSchemaError as e:
        functionLog.error(f'[runModel] Parameter schema was invalid: {e}')
        return ('InvalidSchemaError', e)
    except Exception as e:
        functionLog.error(f'[runModel] Encountered {type(e).__name__}: {e}')
        return ('UncaughtError', e)





"""
Async wrapper function for runModel, allowing HTTP requests to be made 
asynchronously without blocking Streamlit operations
"""
def runModelWrapper(scenarioNames, parameterJSON):
    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def threadRunner():
        try:
            #time.sleep(5) # Debug for testing dashboard while running
            formattedData = asyncio.run(runModel(scenarioNames, parameterJSON))
            if formattedData: resultQueue.put(formattedData)
        except Exception as e:
            functionLog.info(f'[runner] Encountered {type(e).__name__}: {e}')
            functionLog.error(f'[runner] Encountered {type(e).__name__}: {e}')
            raise e
    st.session_state.simulationInProgress = True
    runModelThread = threading.Thread(target = threadRunner)
    runModelThread.start()