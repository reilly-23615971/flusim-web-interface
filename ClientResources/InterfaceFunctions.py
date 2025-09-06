# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
import logging
import streamlit as st

# Logging
functionLog = logging.getLogger(__name__)



"""
Function to save widget values into permanent session state vars
"""
def saveKey(key, id, extra = None, notScenario = False): 
    keyString = f'{key}{id}{extra}' if extra else f'{key}{id}'
    st.session_state[keyString] = st.session_state[f'_{keyString}']
    if not notScenario and id != 0:
        if extra: st.session_state['scenarioSetParamsExtra'][id].append(
            (key, extra)
        )
        else: st.session_state['scenarioSetParams'][id].append(key)

"""
Function to update widgets with permanent session state vars
"""
def loadKey(key, id, default, extra = '', noZeroDefault = False): 
    if noZeroDefault: 
        st.session_state[f'_{key}{id}{extra}'] = st.session_state.get(
            f'{key}{id}{extra}', default
        )
    else: 
        st.session_state[f'_{key}{id}{extra}'] = idGet(key, id, default, extra)

"""
Simple function to get a specific session state value with a specific 
ID, checking ID 0 if the specified one doesn't exist before falling 
back on a default

Parameters:
    string: The string component of the session state variable to get.

    id: An integer that will be used to differentiate the parameters in 
    different scenarios by adding numbers to session state variables.

    defaultValue: What to return if neither the specified ID nor 0 give 
    a value in session state.

    extra: An additional part of the ID that isn't used for scenario chicanery
"""
def idGet(string, id, defaultValue, extra = None): 
    if not extra: return st.session_state.get(
        f'{string}{id}', st.session_state.get(f'{string}0', defaultValue)
    )
    else: return st.session_state.get(
        f'{string}{id}{extra}', 
        st.session_state.get(f'{string}0{extra}', defaultValue)
    )

"""
Simple function to convert an integer into a string describing a number of days
"""
def dayCount(count): return '1 Day' if count == 1 else f'{count} Days'

"""
Function to update what parameters are selectable for different 
parts of a form, to avoid duplicates

Parameters:
    groupSets: A dictionary with strings as keys and tuples containing 
    two strings as values, representing the form sections where age 
    groups need to be kept unique. The key strings are the Streamlit 
    session state variables holding the groups that haven't been 
    selected already. The first string of each value tuple is the 
    variable holding the number of rows in the corresponding age 
    selection form. The second string is the prefix used to identify 
    variables holding the groups that have already been used.

    possibleValues: A tuple containing strings representing the 
    possible values that can be selected in the form
"""
def getRemainingGroups(groupSets, possibleValues):
    for set, (rowCount, prefix) in groupSets.items():
        # Calculate age groups that haven't been used yet
        remainingGroups = dict.fromkeys(possibleValues)
        takenGroups = [
            st.session_state.get(f'{prefix}{i}') 
            for i in range(st.session_state[rowCount])
        ]
        for group in takenGroups: 
            if group: remainingGroups.pop(group, None)
        # Save the new age groups
        st.session_state[set] = list(remainingGroups.keys())

"""
Function to add an additional row to a specific variable-length form

Parameters:
    rowCounter: A string representing the Streamlit session state 
    variable storing the current number of rows in the form.

    forceSetParams: A dictionary of strings representing Streamlit 
    state variables and values to assign to them. Used to preload 
    widgets and keep drop-down selections up-to-date.
"""
def addFormRow(rowCounter, forceSetParams = None): 
    st.session_state[rowCounter] += 1
    if forceSetParams: 
        for var, value in forceSetParams.items(): 
            if value is not None: st.session_state[var] = value

"""
Function to remove a row from a specific variable-length form

Parameters:
    deletedRowIndex: An integer representing the index (first is 0) of 
    the row that is to be deleted from the form.

    rowCounter: A string representing the Streamlit session state 
    variable storing the current number of rows in the form.

    inputPrefixes: A set of strings representing the prefixes that 
    denote the input widgets within the rows of the form.

    minRows: An integer representing the minimum number of rows the 
    form can have.
"""
def deleteFormRow(deletedRowIndex, rowCounter, inputPrefixes, minRows = 0):
    numberOfRows = st.session_state[rowCounter]
    #functionLog.info(f'Deleting row {deletedRowIndex} from the row moderated by {rowCounter}; there\'s {numberOfRows} here, and we\'re modifying the values ')
    # Make sure there's at least 1 row remaining
    if numberOfRows <= minRows: raise ValueError((
        'Tried to delete a row from a form that '
        'already has the minimum number of rows.'
    ))

    # Shift any rows below the deleted one up
    for row in range(deletedRowIndex, numberOfRows - 1):
        for input in inputPrefixes:
            st.session_state[f'{input}{row}'] = st.session_state[
                f'{input}{row+1}'
            ]
    
    # Erase any lingering data
    for input in inputPrefixes: del st.session_state[
        f'{input}{numberOfRows - 1}'
    ]
    st.session_state[rowCounter] -= 1

"""
Function to check if any errors are present in the parameters
"""

def checkErrors(id): return [
    st.session_state.get(error, 0) for error in (
        f'seedPeriodError{id}', f'seedDynamicError{id}', 
        f'closeDynamicError{id}', f'bccDynamicError{id}', 
        f'baseVacPropError{id}', f'ageVacPropError{id}', 
        f'basePrimEfficacyError{id}', f'agePrimEfficacyError{id}', 
        f'baseBoostEfficacyError{id}', f'ageBoostEfficacyError{id}', 
        f'schoolTypeError{id}', f'adultWithdrawalError{id}', 
        f'childWithdrawalError{id}', f'reducedGroupError{id}', 
        f'bccError{id}', f'triggerRateError{id}', f'triggerTotalError{id}',
        f'vaccinePeriodError{id}', f'schoolClosurePeriodError{id}', 
        f'withdrawalIncreasePeriodError{id}', f'reducedGroupPeriodError{id}',
        f'bccPeriodError{id}'
    )
]