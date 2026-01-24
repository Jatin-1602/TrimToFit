import customtkinter as ctk
import os
import threading
import tempfile
from tkinter import filedialog, messagebox
from typing import List, Dict, Any, Optional

from trimtofit.gui.widgets import TimeInputFrame
from trimtofit.core.audio_processor import AudioProcessor


def open_utils_safe(path: str):
    import sys
    import subprocess

    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        print(f"Error opening file: {e}")


class BaseView(ctk.CTkFrame):
    """
    Base class for application views to share common functionality.
    """

    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, **kwargs)
        self.processor = processor
        self.selected_file_path: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)

    def select_file_dialog(self):
        filetypes = (
            ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("All files", "*.*"),
        )
        return filedialog.askopenfilename(initialdir="/", filetypes=filetypes)

    def processing_finished(
        self, success: bool, message_or_path: str, is_preview: bool = False
    ):
        pass  # To be overridden


class TrimView(BaseView):
    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, processor, **kwargs)
        self.range_rows: List[Dict[str, Any]] = []

        # We need row 2 to expand (range list)
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

        # --- Processing Mode ---
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.mode_var = ctk.StringVar(value="remove")

        self.remove_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Remove Selected Ranges",
            variable=self.mode_var,
            value="remove",
        )
        self.remove_radio.pack(side="left", padx=20)

        self.keep_radio = ctk.CTkRadioButton(
            self.mode_frame,
            text="Keep Only Selected Ranges",
            variable=self.mode_var,
            value="keep",
        )
        self.keep_radio.pack(side="left", padx=20)

        # --- Actions & Progress ---
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
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
        self.progress_bar.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=6, column=0, padx=20, pady=(0, 5))

    def select_file(self):
        filename = self.select_file_dialog()
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

        keep_selected = self.mode_var.get() == "keep"

        thread = threading.Thread(
            target=self.run_processing, args=(ranges, is_preview, keep_selected)
        )
        thread.start()

    def set_ui_state(self, state):
        self.preview_btn.configure(state=state)
        self.save_btn.configure(state=state)
        self.select_btn.configure(state=state)
        self.add_btn.configure(state=state)

    def run_processing(self, ranges, is_preview, keep_selected):
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

            final_path = self.processor.process_audio(
                self.selected_file_path,
                output_path,
                ranges,
                keep_selected_ranges=keep_selected,
                progress_callback=self.update_progress,
            )
            self.after(
                0, lambda: self.processing_finished(True, final_path, is_preview)
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
                open_utils_safe(message_or_path)
            else:
                self.status_label.configure(
                    text=f"Saved: {message_or_path}", text_color="green"
                )
                messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            self.progress_bar.set(0)
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class SpeedView(BaseView):
    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, processor, **kwargs)
        self.speed_var = ctk.DoubleVar(value=1.0)
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
        filename = self.select_file_dialog()
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

            final_path = self.processor.change_speed(
                self.selected_file_path, output_path, float(self.speed_var.get())
            )

            self.after(0, lambda: self.processing_finished(True, final_path))
        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e)))

    def processing_finished(self, success, message_or_path, is_preview=False):
        self.process_btn.configure(state="normal")
        if success:
            self.status_label.configure(
                text=f"Saved: {message_or_path}", text_color="green"
            )
            messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class FormatView(BaseView):
    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, processor, **kwargs)
        self.available_formats = ["mp3", "wav", "flac", "ogg", "m4a", "aac"]
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
        filename = self.select_file_dialog()
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

            final_path = self.processor.convert_format(
                self.selected_file_path, output_path, target_fmt
            )

            self.after(0, lambda: self.processing_finished(True, final_path))
        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e)))

    def processing_finished(self, success, message_or_path, is_preview=False):
        self.process_btn.configure(state="normal")
        if success:
            self.status_label.configure(
                text=f"Saved: {message_or_path}", text_color="green"
            )
            messagebox.showinfo("Success", f"Audio saved:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class MergerView(BaseView):
    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, processor, **kwargs)
        self.selected_files: List[str] = []

        self.grid_rowconfigure(2, weight=1)  # Listbox expands
        self.grid_columnconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        self.header_label = ctk.CTkLabel(
            self, text="Audio Merger", font=("Roboto", 24, "bold")
        )
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # --- Controls ---
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.controls_frame.grid_columnconfigure(1, weight=1)

        self.add_btn = ctk.CTkButton(
            self.controls_frame, text="Add Files", command=self.add_files
        )
        self.add_btn.grid(row=0, column=0, padx=10, pady=10)

        self.clear_btn = ctk.CTkButton(
            self.controls_frame,
            text="Clear List",
            command=self.clear_files,
            fg_color="firebrick",
        )
        self.clear_btn.grid(row=0, column=2, padx=10, pady=10)

        # --- File List ---
        self.file_list_frame = ctk.CTkScrollableFrame(self, label_text="Selected Files")
        self.file_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # --- Action ---
        self.merge_btn = ctk.CTkButton(
            self,
            text="Merge & Save",
            command=self.on_process,
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.merge_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=5)

    def add_files(self):
        filetypes = (
            ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("All files", "*.*"),
        )
        filenames = filedialog.askopenfilenames(initialdir="/", filetypes=filetypes)
        if filenames:
            self.selected_files.extend(filenames)
            self.update_file_list_display()
            self.status_label.configure(text=f"Added {len(filenames)} files.")

    def clear_files(self):
        self.selected_files.clear()
        self.update_file_list_display()
        self.status_label.configure(text="List cleared.")

    def remove_file(self, index):
        if 0 <= index < len(self.selected_files):
            removed = self.selected_files.pop(index)
            self.update_file_list_display()
            self.status_label.configure(text=f"Removed: {os.path.basename(removed)}")

    def update_file_list_display(self):
        # Clear existing widgets
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        for idx, file_path in enumerate(self.selected_files):
            # Row container
            row_frame = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            # Label
            lbl = ctk.CTkLabel(
                row_frame,
                text=f"{idx + 1}. {os.path.basename(file_path)}",
                anchor="w",
            )
            lbl.pack(side="left", padx=5, expand=True, fill="x")

            # Delete Button
            del_btn = ctk.CTkButton(
                row_frame,
                text="❌",
                width=30,
                height=30,
                fg_color="transparent",
                text_color="red",
                hover_color=("gray90", "gray20"),
                command=lambda i=idx: self.remove_file(i),
            )
            del_btn.pack(side="right", padx=5)

    def on_process(self):
        if len(self.selected_files) < 2:
            messagebox.showwarning(
                "Warning", "Please select at least 2 audio files to merge."
            )
            return

        self.merge_btn.configure(state="disabled")
        self.status_label.configure(text="Merging...", text_color="#3B8ED0")

        thread = threading.Thread(target=self.run_processing)
        thread.start()

    def run_processing(self):
        try:
            # Determine output filename based on the first file
            first_file = self.selected_files[0]
            base_dir = os.path.dirname(first_file)
            output_name = "merged_output.mp3"
            output_path = os.path.join(base_dir, output_name)

            final_path = self.processor.merge_audio_files(
                self.selected_files, output_path
            )

            self.after(0, lambda: self.processing_finished(True, final_path))
        except Exception as e:
            self.after(0, lambda: self.processing_finished(False, str(e)))

    def processing_finished(self, success, message_or_path, is_preview=False):
        self.merge_btn.configure(state="normal")
        if success:
            self.status_label.configure(
                text=f"Saved: {message_or_path}", text_color="green"
            )
            messagebox.showinfo(
                "Success", f"Audio merged and saved:\n{message_or_path}"
            )
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")


class DownloaderView(BaseView):
    def __init__(self, master, processor: AudioProcessor, **kwargs):
        super().__init__(master, processor, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(
            self, text="YouTube to MP3", font=("Roboto", 24, "bold")
        )
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # URL Input
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.input_frame, text="YouTube URL:").grid(
            row=0, column=0, padx=10, pady=20
        )

        self.url_entry = ctk.CTkEntry(
            self.input_frame, placeholder_text="Paste your link here..."
        )
        self.url_entry.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

        # Action
        self.download_btn = ctk.CTkButton(
            self,
            text="Download & Convert to MP3",
            command=self.on_download,
            height=40,
            font=("Roboto", 14, "bold"),
        )
        self.download_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Status
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=3, column=0, padx=20, pady=5)

    def on_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL.")
            return

        # Let user choose output folder
        output_folder = filedialog.askdirectory(title="Select Download Folder")
        if not output_folder:
            return

        self.download_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.status_label.configure(text="Initializing...", text_color="#3B8ED0")

        thread = threading.Thread(target=self.run_download, args=(url, output_folder))
        thread.start()

    def run_download(self, url, output_folder):
        try:

            def update_progress(msg):
                self.after(0, lambda: self.status_label.configure(text=msg))

            final_path = self.processor.download_audio_from_youtube(
                url, output_folder, progress_callback=update_progress
            )
            self.after(0, lambda: self.download_finished(True, final_path))

        except Exception as e:
            # Fix: Must pass parameters to self.after to avoid capturing 'e' which is deleted
            # or convert to string immediately.
            msg = str(e)
            self.after(0, self.download_finished, False, msg)

    def download_finished(self, success, message_or_path):
        self.download_btn.configure(state="normal")
        self.url_entry.configure(state="normal")

        if success:
            self.status_label.configure(text="Download Complete!", text_color="green")
            messagebox.showinfo("Success", f"MP3 saved to:\n{message_or_path}")
        else:
            self.status_label.configure(text="Error", text_color="red")
            messagebox.showerror("Error", f"Download failed:\n{message_or_path}")
