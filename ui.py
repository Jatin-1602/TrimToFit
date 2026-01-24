import customtkinter as ctk
import threading
import os
import tempfile
import sys
import subprocess
from tkinter import filedialog, messagebox
from processor import AudioProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def open_file_safe(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        print(f"Error opening file: {e}")


class Spinbox(ctk.CTkFrame):
    """
    A custom Spinbox widget (Entry + Up/Down buttons) to handle time input.
    """

    def __init__(
        self, *args, width=100, height=32, min_val=0, max_val=100, step_size=1, **kwargs
    ):
        super().__init__(*args, width=width, height=height, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.step_size = step_size

        self.configure(fg_color=("gray78", "gray28"))

        self.grid_columnconfigure(0, weight=1)  # Entry
        self.grid_columnconfigure(1, weight=0)  # Button column

        self.grid_rowconfigure(0, weight=1)

        # Entry
        self.entry = ctk.CTkEntry(
            self, width=width - 30, height=height - 6, border_width=0, justify="center"
        )
        self.entry.grid(row=0, column=0, padx=(3, 3), pady=3, sticky="ew")
        self.entry.insert(0, f"{min_val:02d}")
        self.entry.bind("<FocusOut>", self.validate)

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
                val = self.min_val  # Loop around
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def subtract(self):
        try:
            val = int(self.entry.get()) - self.step_size
            if val < self.min_val:
                val = self.max_val  # Loop around
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def set_val(self, val):
        self.entry.delete(0, "end")
        self.entry.insert(0, f"{val:02d}")

    def validate(self, event=None):
        try:
            val = int(self.entry.get())
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

        # Hours (0-24)
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


class TrimView(ctk.CTkFrame):
    def __init__(self, master, processor, **kwargs):
        super().__init__(master, **kwargs)
        self.processor = processor
        self.selected_file_path = None
        self.range_rows = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        self.header_label = ctk.CTkLabel(
            self, text="Trim Audio", font=("Roboto", 24, "bold")
        )
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # --- File Selection ---
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(1, weight=1)

        self.select_btn = ctk.CTkButton(
            self.file_frame, text="Select Audio File", command=self.select_file
        )
        self.select_btn.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = ctk.CTkLabel(
            self.file_frame, text="No file selected", text_color="gray"
        )
        self.file_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # --- Dynamic Range List ---
        self.ranges_container = ctk.CTkFrame(self, fg_color="transparent")
        self.ranges_container.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        self.ranges_container.grid_rowconfigure(1, weight=1)
        self.ranges_container.grid_columnconfigure(0, weight=1)

        # Header
        self.ranges_header = ctk.CTkFrame(
            self.ranges_container, height=30, fg_color="transparent"
        )
        self.ranges_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(
            self.ranges_header, text="Ranges to Remove:", font=("Roboto", 14, "bold")
        ).pack(side="left")

        self.add_btn = ctk.CTkButton(
            self.ranges_header,
            text="Add Range",
            width=120,
            command=self.add_range_row,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.add_btn.pack(side="right")

        # Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.ranges_container, label_text="Time Ranges (Start -> End)"
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        # Add initial row
        self.add_range_row()

        # --- Actions & Progress ---
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(
            self.action_frame,
            text="Preview / Check",
            command=self.on_preview,
            height=40,
            font=("Roboto", 14),
        )
        self.preview_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.save_btn = ctk.CTkButton(
            self.action_frame,
            text="Save Final Audio",
            command=self.on_save,
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.save_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 5))

    def select_file(self):
        filetypes = (
            ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("All files", "*.*"),
        )
        filename = filedialog.askopenfilename(initialdir="/", filetypes=filetypes)
        if filename:
            self.selected_file_path = filename
            self.file_label.configure(
                text=os.path.basename(filename), text_color=("black", "white")
            )
            self.status_label.configure(text=f"Selected: {os.path.basename(filename)}")

    def add_range_row(self):
        row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)
        row_frame.grid_columnconfigure((0, 2), weight=1)
        row_frame.grid_columnconfigure(1, weight=0)
        row_frame.grid_columnconfigure(3, weight=0)

        start_input = TimeInputFrame(row_frame)
        start_input.grid(row=0, column=0, padx=5)

        ctk.CTkLabel(row_frame, text="to").grid(row=0, column=1, padx=5)

        end_input = TimeInputFrame(row_frame)
        end_input.grid(row=0, column=2, padx=5)

        remove_btn = ctk.CTkButton(
            row_frame,
            text="Remove",
            width=80,
            fg_color="darkred",
            hover_color="#800000",
            command=lambda f=row_frame: self.remove_range_row(f),
        )
        remove_btn.grid(row=0, column=3, padx=(10, 5))

        self.range_rows.append(
            {"frame": row_frame, "start": start_input, "end": end_input}
        )

    def remove_range_row(self, frame_to_remove):
        self.range_rows = [r for r in self.range_rows if r["frame"] != frame_to_remove]
        frame_to_remove.destroy()

    def get_ranges_in_ms(self):
        ranges = []
        for row in self.range_rows:
            start_ms = row["start"].get_milliseconds()
            end_ms = row["end"].get_milliseconds()
            if end_ms > 0 and start_ms < end_ms:
                ranges.append((start_ms, end_ms))
        return ranges

    def on_preview(self):
        self.start_processing_thread(is_preview=True)

    def on_save(self):
        self.start_processing_thread(is_preview=False)

    def start_processing_thread(self, is_preview=False):
        if not self.selected_file_path:
            messagebox.showwarning("Warning", "Please select an audio file first.")
            return

        ranges = self.get_ranges_in_ms()
        if not ranges:
            messagebox.showwarning(
                "Warning", "Please ensure valid time ranges are set (Start < End)."
            )
            return

        self.set_ui_state("disabled")
        self.progress_bar.set(0)
        self.status_label.configure(
            text="Generating Preview..." if is_preview else "Processing & Saving...",
            text_color="#3B8ED0",
        )

        thread = threading.Thread(target=self.run_processing, args=(ranges, is_preview))
        thread.start()

    def set_ui_state(self, state):
        self.preview_btn.configure(state=state)
        self.save_btn.configure(state=state)
        self.select_btn.configure(state=state)
        self.add_btn.configure(state=state)

    def run_processing(self, ranges, is_preview):
        try:
            if is_preview:
                base, ext = os.path.splitext(self.selected_file_path)
                if not ext:
                    ext = ".mp3"
                temp_filename = f"preview_temp{ext}"
                output_path = os.path.join(tempfile.gettempdir(), temp_filename)
            else:
                base, ext = os.path.splitext(self.selected_file_path)
                output_path = f"{base}_trimmed{ext}"

            self.processor.process_audio(
                self.selected_file_path,
                output_path,
                ranges,
                progress_callback=self.update_progress,
            )
            self.after(
                0, lambda: self.processing_finished(True, output_path, is_preview)
            )

        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e), is_preview))

    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))

    def processing_finished(self, success, message_or_path, is_preview):
        self.set_ui_state("normal")
        if success:
            self.progress_bar.set(1)
            if is_preview:
                self.status_label.configure(text="Preview Opened", text_color="green")
                open_file_safe(message_or_path)
            else:
                self.status_label.configure(
                    text="Saved Successfully!", text_color="green"
                )
                messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            self.progress_bar.set(0)
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class SpeedView(ctk.CTkFrame):
    def __init__(self, master, processor, **kwargs):
        super().__init__(master, **kwargs)
        self.processor = processor
        self.selected_file_path = None
        self.speed_var = ctk.DoubleVar(value=1.0)

        self.grid_columnconfigure(0, weight=1)
        self.setup_ui()

    def setup_ui(self):
        # Header
        ctk.CTkLabel(self, text="Speed Control", font=("Roboto", 24, "bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10)
        )

        # File Select
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(1, weight=1)

        self.select_btn = ctk.CTkButton(
            self.file_frame, text="Select Audio File", command=self.select_file
        )
        self.select_btn.grid(row=0, column=0, padx=10, pady=10)
        self.file_label = ctk.CTkLabel(
            self.file_frame, text="No file selected", text_color="gray"
        )
        self.file_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Slider
        self.slider_frame = ctk.CTkFrame(self)
        self.slider_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.slider_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.slider_frame, text="Speed Factor").pack(pady=(10, 0))
        self.slider = ctk.CTkSlider(
            self.slider_frame,
            from_=0.5,
            to=2.0,
            number_of_steps=30,
            variable=self.speed_var,
            command=self.update_label,
        )
        self.slider.pack(pady=10, padx=20, fill="x")

        self.speed_label = ctk.CTkLabel(self.slider_frame, text="Current Speed: 1.00x")
        self.speed_label.pack(pady=(0, 10))

        # Action
        self.process_btn = ctk.CTkButton(
            self,
            text="Process & Save Speed",
            command=self.on_process,
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.process_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=5)

    def select_file(self):
        filetypes = (
            ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("All files", "*.*"),
        )
        filename = filedialog.askopenfilename(initialdir="/", filetypes=filetypes)
        if filename:
            self.selected_file_path = filename
            self.file_label.configure(
                text=os.path.basename(filename), text_color=("black", "white")
            )
            self.status_label.configure(text=f"Selected: {os.path.basename(filename)}")

    def update_label(self, value):
        self.speed_label.configure(text=f"Current Speed: {float(value):.2f}x")

    def on_process(self):
        if not self.selected_file_path:
            messagebox.showwarning("Warning", "Please select an audio file first.")
            return

        self.process_btn.configure(state="disabled")
        self.status_label.configure(text="Processing...", text_color="#3B8ED0")

        thread = threading.Thread(target=self.run_processing)
        thread.start()

    def run_processing(self):
        try:
            base, ext = os.path.splitext(self.selected_file_path)
            output_path = f"{base}_speed_{self.speed_var.get():.2f}x{ext}"

            self.processor.change_speed(
                self.selected_file_path, output_path, float(self.speed_var.get())
            )

            self.after(0, lambda: self.processing_finished(True, output_path))
        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e)))

    def processing_finished(self, success, message_or_path):
        self.process_btn.configure(state="normal")
        if success:
            self.status_label.configure(text="Saved Successfully!", text_color="green")
            messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class FormatView(ctk.CTkFrame):
    def __init__(self, master, processor, **kwargs):
        super().__init__(master, **kwargs)
        self.processor = processor
        self.selected_file_path = None
        self.available_formats = ["mp3", "wav", "flac", "ogg", "m4a", "aac"]

        self.grid_columnconfigure(0, weight=1)
        self.setup_ui()

    def setup_ui(self):
        # Header
        ctk.CTkLabel(self, text="Format Converter", font=("Roboto", 24, "bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10)
        )

        # File Select
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(1, weight=1)

        self.select_btn = ctk.CTkButton(
            self.file_frame, text="Select Audio File", command=self.select_file
        )
        self.select_btn.grid(row=0, column=0, padx=10, pady=10)
        self.file_label = ctk.CTkLabel(
            self.file_frame, text="No file selected", text_color="gray"
        )
        self.file_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Format Options
        self.format_frame = ctk.CTkFrame(self)
        self.format_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.format_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.format_frame, text="Target Format").pack(pady=(10, 0))
        self.format_combo = ctk.CTkComboBox(
            self.format_frame, values=self.available_formats
        )
        self.format_combo.set("mp3")
        self.format_combo.pack(pady=10)

        # Action
        self.process_btn = ctk.CTkButton(
            self,
            text="Convert Format",
            command=self.on_process,
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.process_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=5)

    def select_file(self):
        filetypes = (
            ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("All files", "*.*"),
        )
        filename = filedialog.askopenfilename(initialdir="/", filetypes=filetypes)
        if filename:
            self.selected_file_path = filename
            self.file_label.configure(
                text=os.path.basename(filename), text_color=("black", "white")
            )
            self.status_label.configure(text=f"Selected: {os.path.basename(filename)}")

    def on_process(self):
        if not self.selected_file_path:
            messagebox.showwarning("Warning", "Please select an audio file first.")
            return

        self.process_btn.configure(state="disabled")
        self.status_label.configure(text="Converting...", text_color="#3B8ED0")

        thread = threading.Thread(target=self.run_processing)
        thread.start()

    def run_processing(self):
        try:
            target_fmt = self.format_combo.get()
            base, _ = os.path.splitext(self.selected_file_path)
            output_path = f"{base}_converted.{target_fmt}"

            self.processor.convert_format(
                self.selected_file_path, output_path, target_fmt
            )

            self.after(0, lambda: self.processing_finished(True, output_path))
        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e)))

    def processing_finished(self, success, message_or_path):
        self.process_btn.configure(state="normal")
        if success:
            self.status_label.configure(text="Saved Successfully!", text_color="green")
            messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class AudioTrimmerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TrimToFit - Audio Suite")
        self.geometry("1000x700")

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
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

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

    def select_trim_view(self):
        self.set_button_active(self.trim_btn)
        self.speed_view.grid_forget()
        self.format_view.grid_forget()
        self.trim_view.grid(row=0, column=0, sticky="nsew")

    def select_speed_view(self):
        self.set_button_active(self.speed_btn)
        self.trim_view.grid_forget()
        self.format_view.grid_forget()
        self.speed_view.grid(row=0, column=0, sticky="nsew")

    def select_format_view(self):
        self.set_button_active(self.format_btn)
        self.trim_view.grid_forget()
        self.speed_view.grid_forget()
        self.format_view.grid(row=0, column=0, sticky="nsew")

    def set_button_active(self, btn):
        # Reset all
        self.trim_btn.configure(fg_color="transparent")
        self.speed_btn.configure(fg_color="transparent")
        self.format_btn.configure(fg_color="transparent")
        # Set active
        btn.configure(fg_color=("gray75", "gray25"))
