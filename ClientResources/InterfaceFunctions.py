# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used by the rest of the client application

# Imports
import logging
from functools import partial
from typing import Callable, Literal, Optional, Union

import pandas as pd
import streamlit as st

# Logging
functionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state

# Tools for error messages
# Error Colours: Text #BD4043, Background #FFE9E9
errorFormat = partial(st.error, icon=":material/error:")
# Warning Colours: Text #926C05, Background #FFFFEC
warnFormat = partial(st.warning, icon=":material/warning:")
# Use sRGB in the colour picker for the best display/code match


def paramError(
    label: str,
    scenarioID: int,
    condition: Callable[[], bool],
    message: str,
    isSevere=False,
):
    """
    Function to throw an error if a condition is met

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        condition (callable, returns bool): The criteria that must be fulfilled
            to throw the error, formatted as a function that returns True when
            the criteria is met.

        message (str): The text to display for the error message.

        isSevere (bool): Set to True for red errors that prevent running the simulation.
    """
    if condition():
        if isSevere:
            errorFormat(message)
            session["activeErrors"][scenarioID][label] = (message, True)
        else:
            warnFormat(message)
            session["activeErrors"][scenarioID][label] = (message, False)
    else:
        session["activeErrors"][scenarioID].pop(label, None)


def dualError(
    label: str,
    scenarioID: int,
    errorCon: Callable[[], bool],
    warnCon: Callable[[], bool],
    errorMessage: str,
    warnMessage: str,
):
    """
    Function to throw either an error or a warning depending on certain conditions

    Parameters:
        label (str): A string to identify this specific error.

        scenarioID (int): The integer representing the scenario this error applies to.

        errorCon (callable, returns bool): The criteria for a red, run-blocking
            error, formatted as a function that returns True when the criteria is met.

        warnCon (callable, returns bool): The criteria for a yellow, minor error,
            formatted as a function that returns True when the criteria is met.

        errorMessage (str): The text to display for the red error message.

        warnMessage (str): The text to display for the yellow error message.
    """
    if errorCon():
        errorFormat(errorMessage)
        session["activeErrors"][scenarioID][label] = (errorMessage, True)
    elif warnCon():
        warnFormat(warnMessage)
        session["activeErrors"][scenarioID][label] = (warnMessage, False)
    else:
        session["activeErrors"][scenarioID].pop(label, None)


@st.fragment(run_every=1)
def errorChecker(scenarioID: int, name: str = "Errors in Current Scenario"):
    """
    Fragment to display errors from a specific scenario in a dropdown

    Parameters:
        scenarioID (int): The integer representing the scenario to pull errors from.

        name (str): The label of the dropdown.

    Returns:
        bool: Returns True if at least one error was run-blocking and False otherwise.


    """
    if session["activeErrors"].get(scenarioID, False):
        with st.status(label=name, state="error"):
            severeErrorsFound = False
            for message, isSevere in session["activeErrors"][scenarioID].values():
                if isSevere:
                    errorFormat(message)
                    severeErrorsFound = True
                else:
                    warnFormat(message)
        return severeErrorsFound


# Widget Functions
def saveKey(
    key: str,
    scenarioID: Union[int, Literal[""]] = "",
    extra: Optional[str] = "",
    notScenario=False,
    dataframe=False,
):
    """
    Function to save widget values into permanent `st.session_state` variables

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int or ""): The integer representing the scenario the widget
            is part of. Defaults to "", allowing for parameters that are not
            associated with scenarios to be saved.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        notScenario (bool): Set to True if the widget isn't a parameter for scenarios.

        dataframe (bool): Set to True if the widget is a dataframe that requires
            manual application of changes.
    """
    keyString = f"{key}{scenarioID}{extra}" if extra else f"{key}{scenarioID}"
    if dataframe:
        # Load both data and changes
        currentData = session[keyString]
        modifiedData = session[f"_{keyString}"]

        # Row changes
        for row, edit in modifiedData["edited_rows"].items():
            for column, newValue in edit.items():
                currentData.loc[row, column] = newValue

        # Row additions
        for newRow in modifiedData["added_rows"]:
            currentData.loc[currentData.shape[0]] = newRow

        # Row removals
        currentData = currentData.drop(modifiedData["deleted_rows"])

        # Save the widget and note scenario differences
        session[keyString] = currentData.reset_index(drop=True)
    else:
        session[keyString] = session.get(f"_{keyString}")

    # Add to scenario param lists if it's a scenario param (ID != 0 or "")
    if not notScenario and scenarioID:
        if extra:
            session["scenarioSetParamsExtra"][scenarioID].append((key, extra))
        else:
            session["scenarioSetParams"][scenarioID].append(key)


def loadKey(
    key: str,
    scenarioID: Union[int, Literal[""]] = "",
    default=None,
    extra: Optional[str] = "",
    noZeroDefault=False,
    dataframe=False,
):
    """
    Function to update widgets with permanent session state vars

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int or ""): The integer representing the scenario the
            widget is part of. Defaults to "", allowing for parameters that
            are not associated with scenarios to be saved.

        default: the value to use if the widget is not present

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        noZeroDefault (bool): Set to True if the widget shouldn't fall back
            on baseline values.

        dataframe (bool): Set to True for dataframe widgets that load
            their data differently.
    """
    keyString = f"{key}{scenarioID}{extra}"
    hiddenPrefix = "_" if not dataframe else ""
    if noZeroDefault or isinstance(scenarioID, str):
        session[f"{hiddenPrefix}{keyString}"] = session.get(f"{keyString}", default)
    else:
        session[f"{hiddenPrefix}{keyString}"] = idGet(key, scenarioID, default, extra)


# List of parameters that will be affected by changing cycleCount
# TODO: Add additional parameters or devise a way to automate their addition
timeParamList = [
    "seedPeriod",
    "schoolClosurePeriod",
    "withdrawalIncreasePeriod",
    "reducedGroupPeriod",
    "bccPeriod",
]

dynamicParamList = {"seedPeriod": "seedTimeForm"}


# TODO: Notify users if parameters are changed when cycle count is adjusted
def timeScaleChange():
    """
    Function to update the ranges of time-based parameters
    """
    saveKey("cycleCount")
    newLength = session["cycleCount"]
    for id in range(session["scenarioCount"] + 1):
        for key in timeParamList:
            fullKey = f"{key}{id}"
            if session.get(fullKey, None):
                session[fullKey] = (
                    min(session[fullKey][0], newLength),
                    min(session[fullKey][1], newLength),
                )
    for param, form in dynamicParamList.items():
        dynamicScaleChange(param, form, 0, noSave=True)
    # session["rerunTime"] = True


def dynamicScaleChange(
    key: str,
    formKey: str,
    scenarioID: int,
    condition: Optional[Callable[[], bool]] = None,
    noSave=False,
):
    """
    Function to update the ranges of dynamic parameters

    Parameters:
        key (str): The identifier used to distinguish the dynamic parameter
            being modified.

        formKey (str): The identifier used to distinguish the form
        whose ranges must be updated.

        scenarioID (int): The integer representing the scenario the widget
            is part of.

        condition (callable, returns bool, optional): A criteria that skips
            the range update if fulfilled, formatted as a function that
            returns True when the criteria is met.

        noSave (bool): Set to True if running this function from a different
            page where saving the widget value would instead set it to None.
    """
    if not noSave:
        saveKey(key, scenarioID)
    if condition is None or condition():
        newMin, newMax = idGet(key, scenarioID, None)
        if scenarioID == 0:
            # Check all scenarios if the baseline was modified
            for id in range(session["scenarioCount"] + 1):
                fullKey = f"{formKey}{id}"
                scenarioMin, scenarioMax = idGet(key, id, (newMin, newMax))
                if session.get(fullKey, None) is not None:
                    form = session[fullKey]
                    form["Day to Update Parameter"] = form[
                        "Day to Update Parameter"
                    ].clip(lower=scenarioMin, upper=scenarioMax)
                    session[fullKey] = form
        else:
            # Only update the relevant scenario
            fullKey = f"{formKey}{scenarioID}"
            if session.get(fullKey, None):
                form = session[fullKey]
                form["Day to Update Parameter"] = form["Day to Update Parameter"].clip(
                    lower=newMin, upper=newMax
                )
                session[fullKey] = form
        session["rerunTime"] = True


@st.fragment(run_every=1)
def rerunTime():
    """
    Fragment for rerunning the app when simulation length changes
    """
    if session.get("rerunTime", None):
        session["rerunTime"] = False
        st.rerun(scope="app")


def idGet(key: str, scenarioID: int, defaultValue, extra: Optional[str] = None):
    """
    Simple function to get a specific session state value with a specific
    ID, checking ID 0 if the specified one doesn't exist before falling
    back on a default

    Parameters:
        key (str): The string component of the session state variable to get.

        scenarioID (int): The integer representing the scenario the value is part of.

        defaultValue: The value to return if neither the specified key nor the
            baseline have values in `st.session_state`.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.
    """
    if not extra:
        return session.get(f"{key}{scenarioID}", session.get(f"{key}0", defaultValue))
    else:
        return session.get(
            f"{key}{scenarioID}{extra}",
            session.get(f"{key}0{extra}", defaultValue),
        )


def dayCount(count: int):
    """
    Simple function to convert an integer into a string describing a number of days

    Parameters:
        count (int): The number of days to return.
    """
    return "1 Day" if count == 1 else f"{count} Days"


# Variable-Length Form Functions
def hasDuplicates(df: pd.DataFrame, column: str = "Age Group"):
    """
    Simple function to check if there are duplicates in a given DataFrame row

    Parameters:
        df (DataFrame): The dataframe to check.

        column (str): The column to check.
    """
    return len(set(df[column])) != len(df[column])


def getRemainingGroups(groupSets, possibleValues):
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
    for set, (rowCount, prefix) in groupSets.items():
        # Calculate age groups that haven't been used yet
        remainingGroups = dict.fromkeys(possibleValues)
        takenGroups = [session.get(f"{prefix}{i}") for i in range(session[rowCount])]
        for group in takenGroups:
            if group:
                remainingGroups.pop(group, None)
        # Save the new age groups
        session[set] = list(remainingGroups.keys())


def addFormRow(rowCounter, forceSetParams=None):
    """
    Function to add an additional row to a specific variable-length form

    Parameters:
        rowCounter: A string representing the Streamlit session state
            variable storing the current number of rows in the form.

        forceSetParams: A dictionary of strings representing Streamlit
            state variables and values to assign to them. Used to preload
            widgets and keep drop-down selections up-to-date.
    """
    session[rowCounter] += 1
    if forceSetParams:
        for var, value in forceSetParams.items():
            if value is not None:
                session[var] = value


def deleteFormRow(deletedRowIndex, rowCounter, inputPrefixes, minRows=0):
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
    numberOfRows = session[rowCounter]
    # functionLog.info(f'Deleting row {deletedRowIndex} from the row
    # moderated by {rowCounter}; there\'s {numberOfRows} here, and
    # we\'re modifying the values ')
    # Make sure there's at least 1 row remaining
    if numberOfRows <= minRows:
        raise ValueError(
            (
                "Tried to delete a row from a form that "
                "already has the minimum number of rows."
            )
        )

    # Shift any rows below the deleted one up
    for row in range(deletedRowIndex, numberOfRows - 1):
        for input in inputPrefixes:
            session[f"{input}{row}"] = session[f"{input}{row+1}"]

    # Erase any lingering data
    for input in inputPrefixes:
        del session[f"{input}{numberOfRows - 1}"]
    session[rowCounter] -= 1


def checkErrors(id):
    """
    Deprecated function to check if any errors are present in the parameters
    """
    return [
        session.get(error, 0)
        for error in (
            f"seedPeriodError{id}",
            f"seedDynamicError{id}",
            f"closeDynamicError{id}",
            f"bccDynamicError{id}",
            f"baseVacPropError{id}",
            f"ageVacPropError{id}",
            f"basePrimEfficacyError{id}",
            f"agePrimEfficacyError{id}",
            f"baseBoostEfficacyError{id}",
            f"ageBoostEfficacyError{id}",
            f"schoolTypeError{id}",
            f"adultWithdrawalError{id}",
            f"childWithdrawalError{id}",
            f"reducedGroupError{id}",
            f"bccError{id}",
            f"triggerRateError{id}",
            f"triggerTotalError{id}",
            f"vaccinePeriodError{id}",
            f"schoolClosurePeriodError{id}",
            f"withdrawalIncreasePeriodError{id}",
            f"reducedGroupPeriodError{id}",
            f"bccPeriodError{id}",
        )
    ]


# Parameter Classes
'''
class Parameter:
    def __init__(self, key: str, scenarioID: int, paramName: str, defaultValue):
        self.key = key
        self.scenarioID = scenarioID
        self.fullKey = f"{key}_{scenarioID}"
        self.internalKey = f"_{key}_{scenarioID}"
        self.paramName = paramName
        self.defaultValue = defaultValue
        self._value = defaultValue

    @property
    def value(self):
        """Get the current value for this parameter"""
        return session.get(self.fullKey, self.defaultValue)

    def loadKey(self, noZeroDefault=False):
        """Update the value for this parameter's widget"""
        if noZeroDefault:
            session[self.internalKey] = session.get(self.fullKey, self.defaultValue)
        else:
            session[self.internalKey] = idGet(
                self.key, self.scenarioID, self.defaultValue
            )

    def saveKey(self):
        """Save the new value for this parameter set by its widget"""
        session[self.fullKey] = session.get(self.internalKey)
        if self.scenarioID != 0:
            session["scenarioSetParams"][self.scenarioID].append(self.key)

    def populateSchema(self, schema):
        """Populate a schema with this parameter's value"""
        setattr(schema, self.paramName, self.value)

    # TODO: Add error functionality


"""
Subclass for parameters that use sliders
"""


class SliderParam(Parameter):

    def __init__(
        self,
        key: str,
        scenarioID: int,
        paramName: str,
        defaultValue: Union[int, float],
        min: Union[int, float],
        max: Union[int, float],
        step: Union[int, float],
        title: str,
        format: Optional[str],
        help: Optional[str],
    ):
        super().__init__(key, scenarioID, paramName, defaultValue)
        self.loadKey
        self.widget = st.slider(
            title,
            min_value=min,
            max_value=max,
            value=defaultValue,
            step=step,
            format=format,
            key=self.internalKey,
            help=help,
            on_change=self.saveKey,
        )

'''
