import customtkinter as ctk
import threading
import os
import tempfile
from tkinter import filedialog, messagebox
from processor import AudioProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class Spinbox(ctk.CTkFrame):
    """
    A custom Spinbox widget (Entry + Up/Down buttons) to handle time input 
    using vertical buttons to save space and ensure entry visibility.
    """
    def __init__(self, *args, width=100, height=32, min_val=0, max_val=100, step_size=1, **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.step_size = step_size
        
        self.configure(fg_color=("gray78", "gray28")) 

        self.grid_columnconfigure(0, weight=1) # Entry
        self.grid_columnconfigure(1, weight=0) # Button column

        self.grid_rowconfigure(0, weight=1)

        # Entry
        # Using sticky="ew" to fill available space minus buttons
        self.entry = ctk.CTkEntry(self, width=width-30, height=height-6, border_width=0, justify="center")
        self.entry.grid(row=0, column=0, padx=(3, 3), pady=3, sticky="ew")
        self.entry.insert(0, f"{min_val:02d}")
        # Validate on focus out
        self.entry.bind("<FocusOut>", self.validate)

        # Buttons Column
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent", width=25)
        self.btn_frame.grid(row=0, column=1, padx=(0, 3), pady=3, sticky="ns")
        
        # Calculate button height to fit perfectly
        btn_height = (height - 8) // 2 
        
        self.add_button = ctk.CTkButton(self.btn_frame, text="^", width=25, height=btn_height, 
                                        command=self.add, fg_color="gray40", hover_color="gray30")
        self.add_button.pack(side="top", pady=(0, 1))

        self.subtract_button = ctk.CTkButton(self.btn_frame, text="v", width=25, height=btn_height, 
                                             command=self.subtract, fg_color="gray40", hover_color="gray30")
        self.subtract_button.pack(side="bottom", pady=(1, 0))

    def add(self):
        try:
            val = int(self.entry.get()) + self.step_size
            if val > self.max_val: val = self.min_val # Loop around
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def subtract(self):
        try:
            val = int(self.entry.get()) - self.step_size
            if val < self.min_val: val = self.max_val # Loop around
            self.set_val(val)
        except ValueError:
            self.set_val(self.min_val)

    def set_val(self, val):
        self.entry.delete(0, "end")
        self.entry.insert(0, f"{val:02d}")

    def validate(self, event=None):
        try:
            val = int(self.entry.get())
            # Clamp
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
        self.grid_columnconfigure((0, 2, 4), weight=0) # Spinboxes
        self.grid_columnconfigure((1, 3), weight=0) # Separators

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
        """
        Parses current selection to milliseconds.
        """
        h = self.hh_spin.get()
        m = self.mm_spin.get()
        s = self.ss_spin.get()
        
        total_seconds = (h * 3600) + (m * 60) + s
        return total_seconds * 1000


class AudioTrimmerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TrimToFit - Range-Based Audio Trimmer")
        self.geometry("900x700") # Slightly wider for spinboxes
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.processor = AudioProcessor()
        self.selected_file_path = None
        self.range_rows = [] 

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        self.header_label = ctk.CTkLabel(self, text="TrimToFit", font=("Roboto", 24, "bold"))
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # --- File Selection ---
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(1, weight=1)

        self.select_btn = ctk.CTkButton(self.file_frame, text="Select Audio File", command=self.select_file)
        self.select_btn.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = ctk.CTkLabel(self.file_frame, text="No file selected", text_color="gray")
        self.file_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # --- Dynamic Range List ---
        self.ranges_container = ctk.CTkFrame(self, fg_color="transparent")
        self.ranges_container.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        self.ranges_container.grid_rowconfigure(1, weight=1)
        self.ranges_container.grid_columnconfigure(0, weight=1)

        # Header
        self.ranges_header = ctk.CTkFrame(self.ranges_container, height=30, fg_color="transparent")
        self.ranges_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(self.ranges_header, text="Ranges to Remove:", font=("Roboto", 14, "bold")).pack(side="left")
        
        self.add_btn = ctk.CTkButton(self.ranges_header, text="Add Range", width=120, command=self.add_range_row, fg_color="green", hover_color="darkgreen")
        self.add_btn.pack(side="right")

        # Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self.ranges_container, label_text="Time Ranges (Start -> End)")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # --- Actions & Progress ---
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(self.action_frame, text="Preview / Check", command=self.on_preview, height=40, font=("Roboto", 14))
        self.preview_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.save_btn = ctk.CTkButton(self.action_frame, text="Save Final Audio", command=self.on_save, height=40, font=("Roboto", 14, "bold"))
        self.save_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 5))

        self.output_path_label = ctk.CTkLabel(self, text="", text_color="#3B8ED0", wraplength=550)
        self.output_path_label.grid(row=6, column=0, padx=20, pady=(0, 15))

        # Add initial row
        self.add_range_row()

    def select_file(self):
        filetypes = (('Audio files', '*.mp3 *.wav *.ogg *.flac *.m4a'), ('All files', '*.*'))
        filename = filedialog.askopenfilename(initialdir='/', filetypes=filetypes)
        if filename:
            self.selected_file_path = filename
            self.file_label.configure(text=os.path.basename(filename), text_color=("black", "white"))
            self.status_label.configure(text=f"Selected: {os.path.basename(filename)}")
            self.output_path_label.configure(text="")

    def add_range_row(self):
        # Create a container frame for the row
        row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)
        
        # Grid layout for alignment
        # We need enough space for Spinboxes (80*3 + gaps)
        row_frame.grid_columnconfigure((0, 2), weight=1) 
        row_frame.grid_columnconfigure(1, weight=0) 
        row_frame.grid_columnconfigure(3, weight=0)

        start_input = TimeInputFrame(row_frame)
        start_input.grid(row=0, column=0, padx=5)

        ctk.CTkLabel(row_frame, text="to").grid(row=0, column=1, padx=5)

        end_input = TimeInputFrame(row_frame)
        end_input.grid(row=0, column=2, padx=5)

        remove_btn = ctk.CTkButton(row_frame, text="Remove", width=80, fg_color="darkred", hover_color="#800000",
                                   command=lambda f=row_frame: self.remove_range_row(f))
        remove_btn.grid(row=0, column=3, padx=(10, 5))

        self.range_rows.append({
            "frame": row_frame,
            "start": start_input,
            "end": end_input
        })

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
            messagebox.showwarning("Warning", "Please ensure valid time ranges are set (Start < End).")
            return

        self.set_ui_state("disabled")
        self.progress_bar.set(0)
        
        if is_preview:
            self.status_label.configure(text="Generating Preview...", text_color="#3B8ED0")
        else:
            self.status_label.configure(text="Processing & Saving...", text_color="#3B8ED0")

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
                if not ext: ext = ".mp3"
                temp_filename = f"preview_temp{ext}"
                output_path = os.path.join(tempfile.gettempdir(), temp_filename)
            else:
                base, ext = os.path.splitext(self.selected_file_path)
                output_path = f"{base}_trimmed{ext}"

            self.processor.process_audio(
                self.selected_file_path,
                output_path,
                ranges,
                progress_callback=self.update_progress
            )
            
            self.after(0, lambda: self.processing_finished(True, output_path, is_preview))
            
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
                try:
                    os.startfile(message_or_path)
                except Exception as e:
                     messagebox.showerror("Error", f"Could not open preview:\n{e}")
            else:
                self.status_label.configure(text="Saved Successfully!", text_color="green")
                self.output_path_label.configure(text=f"Saved to: {message_or_path}")
                messagebox.showinfo("Success", "Audio saved successfully!")
                
        else:
            self.status_label.configure(text="Error", text_color="red")
            self.progress_bar.set(0)
            messagebox.showerror("Error", f"An error occurred:\n{message_or_path}")
