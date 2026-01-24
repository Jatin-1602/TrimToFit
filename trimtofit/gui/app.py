import customtkinter as ctk
from tkinter import messagebox

from trimtofit.core.audio_processor import AudioProcessor
from trimtofit.gui.views import TrimView, SpeedView, FormatView, MergerView
from trimtofit.utils.system_utils import check_ffmpeg_availability

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AudioTrimmerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TrimToFit - Audio Suite")
        self.geometry("1000x700")

        if not check_ffmpeg_availability():
            messagebox.showwarning(
                "FFmpeg Not Found",
                "FFmpeg was not found in your system PATH.\n\n"
                "Some features (Speed Control, Format Conversion) might not work correctly.\n"
                "Please install FFmpeg to ensure full functionality.",
            )

        self.processor = AudioProcessor()

        # Grid layout: 1 row, 2 cols (Sidebar, Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.create_sidebar()
        self.create_content_area()

        # Select first view by default
        self.select_trim_view()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="TrimToFit", font=("Roboto", 20, "bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.trim_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="✂️ Audio Trimmer",
            command=self.select_trim_view,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
        )
        self.trim_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.speed_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="⏩ Speed Control",
            command=self.select_speed_view,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
        )
        self.speed_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.format_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="🔄 Format Converter",
            command=self.select_format_view,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
        )
        self.format_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.merger_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="➕ Audio Merger",
            command=self.select_merger_view,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
        )
        self.merger_btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Instantiate views
        self.trim_view = TrimView(
            self.content_frame, self.processor, fg_color="transparent"
        )
        self.speed_view = SpeedView(
            self.content_frame, self.processor, fg_color="transparent"
        )
        self.format_view = FormatView(
            self.content_frame, self.processor, fg_color="transparent"
        )
        self.merger_view = MergerView(
            self.content_frame, self.processor, fg_color="transparent"
        )

    def select_trim_view(self):
        self.set_button_active(self.trim_btn)
        self.speed_view.grid_forget()
        self.format_view.grid_forget()
        self.merger_view.grid_forget()
        self.trim_view.grid(row=0, column=0, sticky="nsew")

    def select_speed_view(self):
        self.set_button_active(self.speed_btn)
        self.trim_view.grid_forget()
        self.format_view.grid_forget()
        self.merger_view.grid_forget()
        self.speed_view.grid(row=0, column=0, sticky="nsew")

    def select_format_view(self):
        self.set_button_active(self.format_btn)
        self.trim_view.grid_forget()
        self.speed_view.grid_forget()
        self.merger_view.grid_forget()
        self.format_view.grid(row=0, column=0, sticky="nsew")

    def select_merger_view(self):
        self.set_button_active(self.merger_btn)
        self.trim_view.grid_forget()
        self.speed_view.grid_forget()
        self.format_view.grid_forget()
        self.merger_view.grid(row=0, column=0, sticky="nsew")

    def set_button_active(self, btn):
        # Reset all
        self.trim_btn.configure(fg_color="transparent")
        self.speed_btn.configure(fg_color="transparent")
        self.format_btn.configure(fg_color="transparent")
        self.merger_btn.configure(fg_color="transparent")
        # Set active
        btn.configure(fg_color=("gray75", "gray25"))
