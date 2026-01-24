import customtkinter as ctk
from typing import Callable, Union


class Spinbox(ctk.CTkFrame):
    """
    A custom Spinbox widget (Entry + Up/Down buttons) to handle integer input.
    """

    def __init__(
        self,
        *args,
        width: int = 100,
        height: int = 32,
        min_val: int = 0,
        max_val: int = 100,
        step_size: int = 1,
        command: Callable[[int], None] = None,
        **kwargs,
    ):
        super().__init__(*args, width=width, height=height, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.step_size = step_size
        self.command = command

        self.configure(fg_color=("gray78", "gray28"))

        self.grid_columnconfigure(0, weight=1)  # Entry
        self.grid_columnconfigure(1, weight=0)  # Button column
        self.grid_rowconfigure(0, weight=1)

        # Entry
        self.entry = ctk.CTkEntry(
            self,
            width=width - 30,
            height=height - 6,
            border_width=0,
            justify="center",
        )
        self.entry.grid(row=0, column=0, padx=(3, 3), pady=3, sticky="ew")
        self.entry.insert(0, f"{min_val:02d}")
        self.entry.bind("<FocusOut>", self.validate)
        self.entry.bind("<Return>", self.validate)

        # Buttons Column
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent", width=25)
        self.btn_frame.grid(row=0, column=1, padx=(0, 3), pady=3, sticky="ns")

        btn_height = (height - 8) // 2

        self.add_button = ctk.CTkButton(
            self.btn_frame,
            text="^",
            width=25,
            height=btn_height,
            command=self.add,
            fg_color="gray40",
            hover_color="gray30",
        )
        self.add_button.pack(side="top", pady=(0, 1))

        self.subtract_button = ctk.CTkButton(
            self.btn_frame,
            text="v",
            width=25,
            height=btn_height,
            command=self.subtract,
            fg_color="gray40",
            hover_color="gray30",
        )
        self.subtract_button.pack(side="bottom", pady=(1, 0))

    def add(self):
        try:
            val = int(self.entry.get()) + self.step_size
            if val > self.max_val:
                val = (
                    self.min_val
                )  # Loop is okay for time (seconds/minutes), but optional.
                # However, industry standard suggests clamping or looping depending on context.
                # For seconds/minutes, looping 59 -> 0 is expected.
                # I will keep the loop behavior as it was in original but make it explicit.
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def subtract(self):
        try:
            val = int(self.entry.get()) - self.step_size
            if val < self.min_val:
                val = self.max_val
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def set_val(self, val: int):
        self.entry.delete(0, "end")
        self.entry.insert(0, f"{val:02d}")
        if self.command:
            self.command(val)

    def validate(self, event=None):
        try:
            val = int(self.entry.get())
            # Clamp on direct entry
            val = max(self.min_val, min(val, self.max_val))
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def get(self) -> int:
        try:
            return int(self.entry.get())
        except ValueError:
            return self.min_val


class TimeInputFrame(ctk.CTkFrame):
    """
    A helper class that provides a HH:MM:SS input group using Spinboxes.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(fg_color="transparent")

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 2, 4), weight=0)  # Spinboxes
        self.grid_columnconfigure((1, 3), weight=0)  # Separators

        # Hours (0-24) - Clamped usually, or loop 23->0
        self.hh_spin = Spinbox(self, width=80, min_val=0, max_val=24)
        self.hh_spin.grid(row=0, column=0, padx=2)

        # Sep
        ctk.CTkLabel(self, text=":", font=("Roboto", 16, "bold")).grid(row=0, column=1)

        # Minutes (0-59)
        self.mm_spin = Spinbox(self, width=80, min_val=0, max_val=59)
        self.mm_spin.grid(row=0, column=2, padx=2)

        # Sep
        ctk.CTkLabel(self, text=":", font=("Roboto", 16, "bold")).grid(row=0, column=3)

        # Seconds (0-59)
        self.ss_spin = Spinbox(self, width=80, min_val=0, max_val=59)
        self.ss_spin.grid(row=0, column=4, padx=2)

    def get_milliseconds(self) -> int:
        h = self.hh_spin.get()
        m = self.mm_spin.get()
        s = self.ss_spin.get()
        return ((h * 3600) + (m * 60) + s) * 1000
