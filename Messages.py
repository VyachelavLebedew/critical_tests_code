import tkinter.messagebox as msgbox
from typing import Any, cast

MESSAGES: dict[str, dict[str, str | dict[str, str]]] = {
    # main.py
    "FILE_LOADED": {
        "title": "File Selection",
        "text": "File loaded successfully using encoding: {enc}"
    },

    "FILE_ERROR": {
        "title": "File Error",
        "text": "Failed to open file:\n{error}"
    },

    "NO_FILE": {
        "title": "File Selection",
        "text": "No file selected."
    },

    "BETA_ERROR": {
        "title": "Beta Error",
        "text": (
            "Failed to get Beta:\n{error}."
            "Beta should be positive integer or float value"
        )
    },

    "VALUE_POSTIVE": {
        "title": "{value} Error",
        "text": (
            "Failed to get {value}."
            "{value} should be {sign} integer or float value"
        )
    },

    # ITC_module.py
    "MISSING_PARAMS": {
        "title": "Missing Parameters",
        "text": {
            "single": (
                "This required parameter is missing: "
                "{param}\n\nPlease enter this parameter"
                "before starting {test} processing."
            ),
            "multiple": (
                "The following required parameters are missing:"
                "\n\n{params}\n\nPlease provide these parameters"
                "before starting {test} processing."
            )
        }
    },

    "PARAM_NOT_SELECTED": {
        "title": "Parameter Selection",
        "text": "Please select a parameter from the combobox list."
    },

    "NO_COLUMNS": {
        "title": "Columns Selection",
        "text": (
            "Please select columns from the NFME file"
            "via buttons on the left side."
        )
    },

    "COLUMNS_COUNT": {
        "title": "Warning",
        "text": (
            "For '{param}' parameter, {expected} column(s) expected.\n"
            "However, {selected} columns have been selected."
            "\n\nWould you like to proceed?"
        )
    },

    "EXPONENTIAL_FORMAT": {
        "title": "Warning",
        "text": (
            "Column '{col}' comprises values in exponential format.\n\n"
            "Example value: {example}\n\nWould you like to proceed?"
        )
    },

    "DATA_FORMAT": {
        "title": "Data format error",
        "text": (
            "Column '{col}' comprises invalid value:\n\n"
            "{value}\nPlease adjust the data in compliance"
            "with the expected format."
        )
    },

    "BASE_OUT_OF_RANGE": {
        "title": "Base out of range",
        "text": (
            "The entered {value} is {position} the expected range "
            "[{low}, {high}] s.\n"
            "This may lead to an incorrect result.\n"
            "Would you like to proceed?"
        )
    },

    "PCR_NO_BASE": {
        "title": "Base not selected",
        "text": (
            "Click on the steady section before the reactivity is added "
            "to define the base heating rate, then press 'Get DTDt RCPS'."
        )
    },

    "PCR_MISSING_VALUES": {
        "title": "Missing values",
        "text": (
            "One of the entered values (ITC, PrCR, MC, σ(DRDY)) is not set. "
            "Return with BACK and enter it before computing."
        )
    },

    "PCR_NO_POINTS": {
        "title": "Points not selected",
        "text": (
            "Two points after the reactivity is added are required: "
            "the start (t0) and the end (t1) of the power rise."
        )
    },

    "PCR_RATE_LOW": {
        "title": "Low heating rate",
        "text": (
            "At t1 the net heating rate is only {rate} degC/h, below the "
            "10 degC/h expected by the methodology.\n"
            "This may lead to an incorrect result.\n"
            "Would you like to proceed?"
        )
    },

    "PCR_ZERO_POWER": {
        "title": "Zero power",
        "text": (
            "The computed power N(t1) is zero, so the coefficient cannot "
            "be determined. Check the base and the t1 point."
        )
    },

    "PCR_SAME_POSITION": {
        "title": "Same group position",
        "text": (
            "The group is at the same position for the RCPS base as for the "
            "points after the reactivity was added.\n"
            "The positions are expected to differ. This may lead to an "
            "incorrect result.\n\n"
            "Yes - keep the current clicks and proceed.\n"
            "No - discard all clicks and start this procedure over."
        )
    },

    "PCR_HEADER_NOT_FOUND": {
        "title": "Column not found",
        "text": (
            "The new file does not contain the following column(s) used "
            "for the current parameters:\n\n{headers}\n\n"
            "The file was not loaded. Check that it has the same headers."
        )
    },

    "PCR_FILE_ERROR": {
        "title": "File error",
        "text": "The selected file could not be read."
    },

    "SYM_NO_FILE": {
        "title": "No file",
        "text": "Please load an experiment file first."
    },

    "SYM_FILE_ERROR": {
        "title": "File error",
        "text": "The selected file could not be read."
    },

    "SYM_BAD_COLUMNS": {
        "title": "Bad column spec",
        "text": (
            "The column numbers could not be parsed. Use a list like "
            "'10-12, 17, 20, 100-210'."
        )
    },

    "SYM_ONE_CURRENT": {
        "title": "One current channel",
        "text": (
            "Two current channels are expected, but only one was given.\n"
            "Continue anyway?"
        )
    },

    "SYM_NO_COLUMNS": {
        "title": "No columns",
        "text": (
            "The columns for this plot were not selected. Please use "
            "File -> Select columns first."
        )
    },

    "SYM_NO_FRAGMENT": {
        "title": "No fragment",
        "text": (
            "Please click the plot to place the left and right bounds of "
            "the fragment first, then save it."
        )
    },

    "SYM_NO_PLOT": {
        "title": "No plot",
        "text": "Draw a plot first, then save it."
    },

    "SYM_FRAGMENT_HINT": {
        "title": "Select a fragment",
        "text": (
            "Click the left and then the right bound of the fragment on "
            "the plot. The fragment is saved with rescaled axes."
        )
    },

    "CRIT_NO_PLOT": {
        "title": "No plot",
        "text": "There is no plot on this tab to save."
    },

    "PCR_REACT_UNIT": {
        "title": "Reactivity unit",
        "text": "Reactivity is now displayed in {unit}."
    },

    "CRIT_GROUPS_MODE": {
        "title": "Groups mode",
        "text": "Switched to {n}-group mode."
    },

    "SET_BETA_FIRST": {
        "title": "Beta required",
        "text": (
            "Please set the beta value first; it is used in the calculation."
        )
    },

    "CRIT_NOT_A_NUMBER": {
        "title": "Not a number",
        "text": "The entered value '{value}' is not a valid number."
    },

    "SYM_BAD_SIZES": {
        "title": "Invalid sizes",
        "text": (
            "The number of CRs per group, the reference period and the "
            "number of groups must all be positive integers."
        )
    },

    "SYM_NOT_A_NUMBER": {
        "title": "Not a number",
        "text": "The entered value '{value}' is not a valid number."
    },

    "OUT_OF_RANGE": {
        "title": "Warning",
        "text": (
            "Column '{col}' comprises values outside expected range.\n"
            "Example of unexpected value: {example}\n"
            "Would you like to proceed?"
        )
    },

    "VALUE_ERROR": {
        "title": "{value_name} Error",
        "text": (
            "Failed to get {value_name}:\n"
            "{error}. {value_name} should be integer or float value"
        )
    },

    # ITC_processing.py
    "SELECT_FIRST": {
        "title": "Warning",
        "text": (
            "Please select the first point (left click) before"
            "selecting the second point (right click)."
        )
    },

    "SECOND_EARLIER": {
        "title": "Warning",
        "text": "The second time point should be later than the first one."
    },

    "GROUP_MOVEMENT": {
        "title": "Warning",
        "text": (
            "Group movement occurred within the selected interval."
            "Please select another interval."
        )
    },

    "NARROW_INTERVAL": {
        "title": "Warning",
        "text": (
            "The selected interval is less than 300 seconds.\n"
            "A narrow time interval may lead to reduced computation accuracy."
            "\n\nWould you like to proceed?"
        )
    },

    "DECIMAL_SET": {
        "title": "Success",
        "text": "{type} decimal set to {value}"
    },

    "INVALID_DECIMAL": {
        "title": "Error",
        "text": "Please enter a valid integer"
    },

    # DRDH_processing.py
    "NO_GROUP_MOVEMENT": {
        "title": "Error",
        "text": (
            "No control groups moved."
        )
    },

    "GROUPS_MOVED": {
        "title": "Error",
        "text": (
            "The following control groups moved:\n\n"
            "{movements}\n\n"
            "Please select another interval."
        )
    },

    "SATISFACTORY_RESULT": {
        "title": "Confirm result",
        "text": "Are you satisfied with the result?"
    },

    "RIGHT_CLICK_BEFORE_LEFT": {
        "title": "Click error",
        "text": "Right click before the relevant left click"
    },

    "INITIAL_POSITION_MISMATCH": {
        "title": "Initial position mismatch",
        "text": (
            "The determination does not start at the beginning of the "
            "record.\n\n"
            "The first row of the table holds the group positions of the "
            "very first sample, so they do not correspond to the start of "
            "the first measured interval:\n\n"
            "{positions}\n\n"
            "Rewrite the first row with the positions at the start of the "
            "measurement?"
        )
    },

    "NO_DRDH_RESULTS": {
        "title": "Warning",
        "text": (
            "There are no DRDH results yet.\n"
            "Please measure at least one interval before completing."
        )
    },

    "NOT_READY_TO_PROCEED": {
        "title": "Warning",
        "text": (
            "Both lines have to be fixed before computing the DRDH.\n"
            "Please press  Fix 1  and  Fix 2  first."
        )
    },

    "LINE_NOT_DEFINED": {
        "title": "Warning",
        "text": (
            "The line is not defined yet.\n"
            "Please select both points (left click and right click)."
        )
    },

    # DRDH_module.py
    "GROUP_ORDER_ERROR": {
        "title": "Group order error",
        "text": "The order of selected groups is incorrect: {groups}"
    }

}


class Messages:
    """Message box.

    Comprises message templates and represents messages
    with info needed, with formatted text.
    """

    @classmethod
    def show(cls, kind: str, key: str, **kwargs: Any) -> str | bool:
        """
        Represent four message types with formatted text.

        kind: info | warning | error | question
        key: key from MESSAGES
        kwargs: data to format()

        Returns the dialog with a user result via messagebox. For questions
        returns bool, otherwise tkinter response string ("ok").
        """
        entry = MESSAGES[key]
        # "cast" for typing only,
        # "title: str = entry["title"]" is acceptable as well
        title = cast(str, entry["title"])
        text = entry["text"]

        # special case: MISSING_PARAMS
        if isinstance(text, dict):
            if "params" in kwargs:
                text = text["multiple"].format(**kwargs)
            else:
                text = text["single"].format(**kwargs)

        title = title.format(**kwargs)
        text = text.format(**kwargs)

        if kind == "info":
            return msgbox.showinfo(title, text)
        elif kind == "warning":
            return msgbox.showwarning(title, text)
        elif kind == "error":
            return msgbox.showerror(title, text)
        elif kind == "question":
            return msgbox.askyesno(title, text)
        # "return" for typing only
        return ""
