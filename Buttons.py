import tkinter as tk
from typing import Any, Callable

from Settings import COLORS, FONTS


class Buttons(tk.Button):
    """
    Base class for creating a customizable Tkinter Button.

    Args:
        master: Parent widget.
        text: Text to display on the button.
        command: Function to call when the button is clicked.
        fg: Text color.
        bg: Background color.
        **kwargs: Additional Tkinter Button options.
    """
    def __init__(
            self,
            master: tk.Widget,
            text: str,
            command: Callable[[], None],
            fg: str = COLORS['FOREGROUND_COLOR'],
            bg: Any = None,
            **kwargs: Any
    ) -> None:
        super().__init__(
            master=master,
            text=text,
            command=command,
            fg=fg,
            bg=bg,
            **kwargs
        )


class MainButtons(Buttons):
    """
    Button for main design options.

    Button parameters:
    Color: MAIN_BUTTON_COLOR
    Font: BUTTON_FONT
    Width: 15
    """
    def __init__(self, master: tk.Widget, **kwargs: Any) -> None:
        super().__init__(
            master,
            bg=COLORS['MAIN_BUTTON_COLOR'],
            font=FONTS['BUTTON_FONT'],
            width=15,
            **kwargs
        )


class TestButtons(Buttons):
    """
    Button for computation actions.

    Button parameters:
    Color: TEST_BUTTON_COLOR
    Font: BUTTON_FONT
    Width: 15
    """
    def __init__(self, master: tk.Widget, **kwargs: Any) -> None:
        super().__init__(
            master,
            bg=COLORS['TEST_BUTTON_COLOR'],
            font=FONTS['BUTTON_FONT'],
            width=15,
            **kwargs
        )


class SmallButtons(Buttons):
    """
    Button for minor actions.

    Button parameters:
    Color: TEST_BUTTON_COLOR
    Font: DATA_FONT
    Width: 17
    """
    def __init__(self, master: tk.Widget, **kwargs: Any) -> None:
        super().__init__(
            master,
            bg=COLORS['TEST_BUTTON_COLOR'],
            font=FONTS['DATA_FONT'],
            width=17,
            **kwargs
        )
