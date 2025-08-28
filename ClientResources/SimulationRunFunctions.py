# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used to make requests to the server for running the simulation

# Imports
import time, asyncio, logging, threading
from io import BytesIO
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
from ClientResources.InterfaceFunctions import checkErrors
from ClientResources.VisualisationFunctions import formatData
from ClientResources.SharedResources import (
    AnalysisFile, tableOutcomes, serverUrl, resultQueue
)

# Logging
functionLog = logging.getLogger(__name__)



"""
Function to generate a JSON config file using the selected parameters
"""
def createConfig():
    # Check number of extra scenarios
    scenarioCount = st.session_state['scenarioCount'] + 1

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
        # TODO: Use middle joint to telegraph what toolbox data to get
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
} ({errors[id].count(2)} errors)
''' 
for id in range(scenarioCount + 1) if max(errors[id]) >= 2)
}                            
        
Please correct these errors by modifying the corresponding parameters 
to valid values before running the simulation.
'''
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
- {st.session_state[f'scenarioName{id}']} ({errors[id].count(1)} issues)
''' 
for id in range(1, scenarioCount + 1) if max(errors[id]) >= 1)}                            
        
Please make sure that these issues do not interfere with your intended 
simulation design before running the simulation.
'''
        )
        st.markdown('''
            Are you sure you want to run the simulation with the 
            selected parameters?
        ''')
        if st.button('Run Simulation'):
            # Set params indicating model is simulating
            st.session_state.simulationInProgress = True
            st.session_state.simulationStartTime = time.time()

            # Get scenario names
            scenarioNames = ['Baseline'] + [
                st.session_state[f'scenarioName{i}'] 
                for i in range(1, st.session_state['scenarioCount'] + 1)
            ]

            # Make the model call
            runModelWrapper(scenarioNames)
            # TODO: Inform user if server doesn't respond

            # Reset page to close popup
            stn.toast(
                'Sending a request to run the simulation...', 
                icon = ":material/experiment:"
            )
            st.rerun()

"""
Function to send JSON model parameters to the server, awaiting a 
response containing the results of the simulation
"""
async def runModel(scenarioNames):
    try:
        # TODO: Better error handling

        # For testing use this default simulation JSON instead of parameters
        parameterJSON = {
            "name": "Simple Test",
            "description": "2184",
            "output_folder": "./results/",
            "middle_joint": "-usingEpidemic-Emean",
            "community_used": ["newcastle"],
            "shared_overrides": {
                "parameters": {
                    "Command_Argument": {"n_runs": 12,"n_cycles": 180},
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

        # Use this version in final dashboard
        """parameterJSON = createConfig().model_dump_json(
            indent = 4, exclude_unset = True#, exclude_defaults = True
        )"""

        # TODO: Decide on what data must be gathered
        # TODO: Make alphabetical by prospective filename
        dataForms = [AnalysisFile(tool = 'epidemic', names = scenarioNames)]
        
        # Send POST request to server with parameters
        functionLog.info(
            f'[runModel] Initialising session with base url {serverUrl}...'
        )
        async with ClientSession(
            raise_for_status = True, base_url = serverUrl
        ) as session:
            functionLog.info(f'[runModel] Sending post request...')
            async with session.post('runModel', json = parameterJSON) as response:
                responseData = await response.read()
            functionLog.info(f'[runModel] Response received! Returning data...')
        
        # Convert CSV statistics into DataFrame(s)
        # TODO: Use JSON parameters to determine how to format CSV data
        # TODO: Store different data based on the request parameters
        # TODO: Determine if doing all analysis tasks with each model 
        # call is necessary/useful for the user
        functionLog.info(
            f'[runModel] Preparing to process {len(dataForms)} analyses...'
        )
        # Process without unzipping if there's only one analysis
        if len(dataForms) == 1: return [formatData(responseData, dataForms[0])]
        # Unzip data and format each analysis file
        with ZipFile(BytesIO(responseData)) as analyses:
            fileNames = analyses.namelist()
            # TODO: Make sure file order matches analyses
            processedData = [
                formatData(analyses.read(file), dataForms[index]) 
                for index, file in enumerate(fileNames)
            ]
        return processedData
    except ClientConnectorError as e:
        functionLog.error(f'[runner] Couldn\'t connect to server: {e}')
        return ['ClientConnectorError']
    except ClientResponseError as e:
        functionLog.error(f'[runner] Server returned status {e.status}: {e}')
        # TODO: Figure out why this toast isn't displaying
        if e.status in {500, '500'}:
            stn.toast(f'''
                Error: Simulation server had an internal error. 
                Please try again later.
            ''', icon = ':material/error:')
            return ['ClientResponseError500']
        else:
            stn.toast(f'''
                Error: Simulation server responded poorly. 
                Please try again later.
            ''', icon = ':material/error:')
            return ['ClientResponseError']
    except Exception as e:
        functionLog.error(f'[runModel] Encountered {type(e).__name__}: {e}')
        return ['UncaughtError']

"""
Async wrapper function for runModel, allowing HTTP requests to be made 
asynchronously without blocking Streamlit operations
"""
def runModelWrapper(scenarioNames):
    # Inner function to asynchronously call the server and await results
    # Needed to avoid interrupting Streamlit UI functionality
    def runner():
        try:
            formattedData = asyncio.run(runModel(scenarioNames))
            if formattedData: resultQueue.put(formattedData)
        except Exception as e:
            # TODO: Inform the user of server errors (make toasts?)
            functionLog.error(f'[runner] Encountered {type(e).__name__}: {e}')
            raise e
    st.session_state.simulationInProgress = True
    runModelThread = threading.Thread(target = runner)
    runModelThread.start()