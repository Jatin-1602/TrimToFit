import os
import sys
import subprocess
from typing import List, Tuple, Optional, Callable

# --- Monkey Patch: Suppress FFmpeg Console Window (Windows) ---
# This prevents the black cmd window from popping up when running as a GUI/EXE.
if sys.platform == "win32":
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

    _original_popen = subprocess.Popen

    def _silent_popen(*args, **kwargs):
        if 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = startupinfo
        # Also ensure creationflags are set just in case (CREATE_NO_WINDOW = 0x08000000)
        if 'creationflags' not in kwargs: 
             kwargs['creationflags'] = 0x08000000
        return _original_popen(*args, **kwargs)

    subprocess.Popen = _silent_popen
# -------------------------------------------------------------

from pydub import AudioSegment
from pydub.utils import mediainfo

class AudioProcessor:
    """
    Handles audio processing logic using pydub.
    """

    def invert_ranges(self, remove_ranges: List[Tuple[int, int]], total_duration_ms: int) -> List[Tuple[int, int]]:
        """
        Calculates the 'keep' ranges based on the 'remove' ranges and total duration.
        """
        keep_ranges = []
        current_time = 0

        # Ensure sorted
        remove_ranges.sort(key=lambda x: x[0])

        for start, end in remove_ranges:
            if start > current_time:
                keep_ranges.append((current_time, start))
            current_time = max(current_time, end)
        
        if current_time < total_duration_ms:
            keep_ranges.append((current_time, total_duration_ms))
            
        return keep_ranges

    def process_audio(self, input_path: str, output_path: str, remove_ranges_ms: List[Tuple[int, int]], progress_callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Loads audio, removes specified ranges, and exports the result.
        
        Args:
            input_path: Path to source.
            output_path: Path to dest.
            remove_ranges_ms: List of tuples [(start_ms, end_ms), ...].
            progress_callback: Progress reporter.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback: progress_callback(0.1)
        
        try:
            audio = AudioSegment.from_file(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load audio. {e}")

        if progress_callback: progress_callback(0.3)

        total_duration = len(audio)
        
        # Ranges are already in milliseconds
        keep_ranges = self.invert_ranges(remove_ranges_ms, total_duration)

        final_audio = AudioSegment.empty()
        
        if not keep_ranges:
             # Result is empty if everything removed
             pass 
        else:
            count = len(keep_ranges)
            for i, (start, end) in enumerate(keep_ranges):
                segment = audio[start:end]
                final_audio += segment
                
                # Animate progress between 30% and 80%
                if progress_callback: 
                    step_size = 0.5 / count
                    current_progress = 0.3 + ((i + 1) * step_size)
                    progress_callback(current_progress)

        if progress_callback: progress_callback(0.8)

        # Detect original bitrate to prevent file size bloating
        target_bitrate = "128k" # Default fallback
        try:
            info = mediainfo(input_path)
            if info and 'bit_rate' in info:
                target_bitrate = info['bit_rate']
        except Exception:
            pass # Keep default

        # Export
        fmt = os.path.splitext(output_path)[1].lower().replace('.', '') or "mp3"
        final_audio.export(output_path, format=fmt, bitrate=target_bitrate)
        
        if progress_callback: progress_callback(1.0)
