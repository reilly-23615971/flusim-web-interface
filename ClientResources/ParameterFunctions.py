# Flusim Web Interface Application
# Developed by Reilly Evans
# Functions used for parameters and their relevant widgets

# Imports
import logging
from typing import Any, Callable, Literal, Optional

import pandas as pd
import streamlit as st

# Logging
paramFunctionLog = logging.getLogger(__name__)

# Store st.session_state as variable for efficiency
session = st.session_state


# Widget Functions
def containerSave(
    key: str,
    scenarioID: int | Literal[""] = "",
    containers: set[str] = set(),
):
    """
    Wrapper for `saveKey` that keeps specific containers open, used for
    advanced parameters and scenario names.

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int or ""): The integer representing the scenario the widget
            is part of. Defaults to `""`, allowing for parameters that are not
            associated with scenarios to be saved.

        containers (list of str): String used to identify each container to open.
    """
    saveKey(key, scenarioID)
    for container in containers:
        session[container] = session.get(container)


def saveKey(
    key: str,
    scenarioID: int | Literal[""] = "",
    extra: Optional[str] = "",
    notScenario=False,
    dataframe=False,
):
    """
    Function to save widget values into permanent `st.session_state` variables.

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int or ""): The integer representing the scenario the widget
            is part of. Defaults to `""`, allowing for parameters that are not
            associated with scenarios to be saved.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        notScenario (bool): Set to `True` if the widget isn't a parameter for scenarios.

        dataframe (bool): Set to `True` if the widget is a dataframe that requires
            manual application of changes.
    """
    # TODO: See if dataframes can not reload after every change
    # TODO: See if scenario dataframes can adapt to baseline changes
    # (e.g. by having None/NA cells with the placeholder "Same as baseline")

    # Prevent invalid calls after deleting scenarios
    if not isinstance(scenarioID, str) and scenarioID > session["scenarioCount"]:
        return
    keyString = f"{key}{scenarioID}{extra}" if extra else f"{key}{scenarioID}"
    if dataframe:
        # Load both data and changes
        currentData = session[keyString].copy()
        modifiedData = session[f"_{keyString}"]

        # Row changes
        for row, edit in modifiedData["edited_rows"].items():
            for column, newValue in edit.items():
                currentData.loc[row, column] = newValue

        # Row additions
        for newRow in modifiedData["added_rows"]:
            currentData.loc[currentData.shape[0]] = newRow

        # Row removals
        currentData = currentData.drop(modifiedData["deleted_rows"]).reset_index(
            drop=True
        )

        # Save the edited data
        session[keyString] = currentData
    else:
        session[keyString] = session.get(f"_{keyString}")

    # Add to scenario param lists if it's a scenario param (ID != 0 or "")
    if not notScenario and scenarioID:
        if extra:
            session["scenarioSetParamsExtra"][scenarioID].add((key, extra))
        else:
            session["scenarioSetParams"][scenarioID].add(key)


def loadKey(
    key: str,
    scenarioID: int | Literal[""] = "",
    default=None,
    extra: Optional[str] = "",
    noZeroDefault=False,
    dataframe=False,
):
    """
    Function to update widgets with permanent session state variables.

    Parameters:
        key (str): The string used to identify the widget.

        scenarioID (int or ""): The integer representing the scenario the
            widget is part of. Defaults to `""`, allowing for parameters that
            are not associated with scenarios to be saved.

        default: The value to use if the widget is not present.

        extra (str, optional): An additional part of the key used to distinguish
            variable-length forms.

        noZeroDefault (bool): Set to `True` if the widget shouldn't fall back
            on baseline values.

        dataframe (bool): Set to `True` for dataframe widgets that load
            their data differently.
    """
    keyString = f"{key}{scenarioID}{extra}"
    hiddenPrefix = "_" if not dataframe else ""
    if noZeroDefault or isinstance(scenarioID, str):
        session[f"{hiddenPrefix}{keyString}"] = session.get(f"{keyString}", default)
    else:
        session[f"{hiddenPrefix}{keyString}"] = (
            idGet(key, scenarioID, default, extra).copy()
            if dataframe
            else idGet(key, scenarioID, default, extra)
        )
    # Ensure dataframes are properly cleaned up even if never edited
    if dataframe and scenarioID:
        if extra:
            session["scenarioSetParamsExtra"][scenarioID].add((key, extra))
        else:
            session["scenarioSetParams"][scenarioID].add(key)


# List of parameters that will be affected by changing cycleCount
# TODO: Add additional parameters or devise a way to automate their addition
timeParamList = [
    "seedPeriod",
    "schoolClosurePeriod",
    "withdrawalIncreasePeriod",
    "reducedGroupPeriod",
    "bccPeriod",
]

# List of parameters that modify dynamic parameter forms when changed
dynamicParamList = {
    "seedPeriod": "seedTimeForm",
    "schoolClosurePeriod": "closeTimeForm",
    "bccPeriod": "bccTimeForm",
}


# TODO: Notify users if parameters are changed when cycle count is adjusted
def timeScaleChange():
    """
    Function to update the ranges of time-based parameters.
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


def dynamicScaleChange(
    key: str,
    formKey: str,
    scenarioID: int,
    condition: Optional[Callable[[], bool]] = None,
    noSave=False,
):
    """
    Function to update the ranges of dynamic parameters.

    Parameters:
        key (str): The identifier used to distinguish the dynamic parameter
            being modified.

        formKey (str): The identifier used to distinguish the form
            whose ranges must be updated.

        scenarioID (int): The integer representing the scenario the widget
            is part of.

        condition (callable, returns bool, optional): A criteria that skips
            the range update if fulfilled, formatted as a function that
            returns `True` when the criteria is met.

        noSave (bool): Set to `True` if running this function from a different
            page where saving the widget value would instead set it to `None`.
    """
    if not noSave:
        saveKey(key, scenarioID)
    if condition is None or condition():
        newMin, newMax = idGet(key, scenarioID, (1, 720))
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
            form = session.get(fullKey, None)
            if form is not None and not form.empty:
                form["Day to Update Parameter"] = form["Day to Update Parameter"].clip(
                    lower=newMin, upper=newMax
                )
                session[fullKey] = form


def idGet(key: str, scenarioID: int, defaultValue, extra: Optional[str] = None):
    """
    Simple function to get a specific session state value with a specific
    ID, checking ID 0 if the specified one doesn't exist before falling
    back on a default.

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


# Variable-Length Form Functions
def hasDuplicates(df: pd.DataFrame, column: str = "Age Group"):
    """
    Simple function to check if there are duplicates in a given dataframe row.

    Parameters:
        df (DataFrame): The dataframe to check.

        column (str): The column to check.
    """
    return len(set(df[column])) != len(df[column])


def replaceTableNA(df: pd.DataFrame, columnDict: dict[str, Any]) -> pd.DataFrame:
    """
    Function to fill NA values in specific dataframe columns, accounting for
    values that don't work with pandas' built-in `fillna` function like the empty list.

    Parameters:
        df (DataFrame): The dataframe to modify.

        columnDict (dict with str keys): A dictionary containing column names
            and the value to replace NA values with.

    Returns:
        Dataframe: The dataframe with NA values replaced as needed.
    """
    newTable = df.copy()
    for column, value in columnDict.items():
        if column in newTable.columns:
            for row in newTable.loc[newTable[column].isnull(), column].index:
                newTable.at[row, column] = value
    return newTable


# All functions beyond this point are currently unused
def getRemainingGroups(groupSets, possibleValues):
    """
    Function to update what parameters are selectable for different
    parts of a form, to avoid duplicates.

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
    Function to add an additional row to a specific variable-length form.

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
    Function to remove a row from a specific variable-length form.

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
    # paramFunctionLog.info(f'Deleting row {deletedRowIndex} from the row
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


# Parameter Classes (unfinished)
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
        """Get the current value for this parameter."""
        return session.get(self.fullKey, self.defaultValue)

    def loadKey(self, noZeroDefault=False):
        """Update the value for this parameter's widget."""
        if noZeroDefault:
            session[self.internalKey] = session.get(self.fullKey, self.defaultValue)
        else:
            session[self.internalKey] = idGet(
                self.key, self.scenarioID, self.defaultValue
            )

    def saveKey(self):
        """Save the new value for this parameter set by its widget."""
        session[self.fullKey] = session.get(self.internalKey)
        if self.scenarioID != 0:
            session["scenarioSetParams"][self.scenarioID].add(self.key)

    def populateSchema(self, schema):
        """Populate a schema with this parameter's value."""
        setattr(schema, self.paramName, self.value)



"""
Subclass for parameters that use sliders
"""


class SliderParam(Parameter):

    def __init__(
        self,
        key: str,
        scenarioID: int,
        paramName: str,
        defaultValue: int | float,
        min: int | float,
        max: int | float,
        step: int | float,
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
