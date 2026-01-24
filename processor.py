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
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = startupinfo
        # Also ensure creationflags are set just in case (CREATE_NO_WINDOW = 0x08000000)
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000
        return _original_popen(*args, **kwargs)

    subprocess.Popen = _silent_popen
# -------------------------------------------------------------

from pydub import AudioSegment
from pydub.utils import mediainfo


class AudioProcessor:
    """
    Handles audio processing logic using pydub.
    """

    def invert_ranges(
        self, remove_ranges: List[Tuple[int, int]], total_duration_ms: int
    ) -> List[Tuple[int, int]]:
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

    def process_audio(
        self,
        input_path: str,
        output_path: str,
        remove_ranges_ms: List[Tuple[int, int]],
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
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

        if progress_callback:
            progress_callback(0.1)

        try:
            audio = AudioSegment.from_file(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load audio. {e}")

        if progress_callback:
            progress_callback(0.3)

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

        if progress_callback:
            progress_callback(0.8)

        # Detect original bitrate to prevent file size bloating
        bitrate = "192k"  # Default fallback
        try:
            info = mediainfo(input_path)
            if "bit_rate" in info:
                bitrate = info["bit_rate"]
        except:
            pass

        final_audio.export(
            output_path, format=output_path.split(".")[-1], bitrate=bitrate
        )

        if progress_callback:
            progress_callback(1.0)

    def change_speed(
        self,
        input_path: str,
        output_path: str,
        speed_factor: float,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Changes the speed of the audio using FFmpeg's atempo filter to preserve pitch.

        Args:
            input_path: Path to source.
            output_path: Path to dest.
            speed_factor: Float between 0.5 and 2.0.
            progress_callback: Progress reporter (simple start/end updates).
        """
        if not (0.5 <= speed_factor <= 2.0):
            raise ValueError("Speed factor must be between 0.5 and 2.0")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback(0.1)

        # Construct FFmpeg command
        # ffmpeg -i input.mp3 -filter:a "atempo=1.5" -vn output.mp3
        # -vn disables video if present (audio only)
        # -y overwrites output

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-filter:a",
            f"atempo={speed_factor}",
            "-vn",
            output_path,
        ]

        if progress_callback:
            progress_callback(0.3)

        try:
            # We use the silent startup info from the class level patch if on windows,
            # or just run it via subprocess.run
            if sys.platform == "win32":
                subprocess.run(
                    cmd, check=True, startupinfo=startupinfo, creationflags=0x08000000
                )
            else:
                subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed with error: {e}")

        if progress_callback:
            progress_callback(1.0)

    def convert_format(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Converts audio format.
        Args:
            input_path: Source file.
            output_path: Destination file.
            target_format: Target extension (e.g., 'wav').
            progress_callback: Progress reporter.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback(0.1)

        try:
            audio = AudioSegment.from_file(input_path)
            if progress_callback:
                progress_callback(0.5)

            # Map extensions to correct FFmpeg muxer/codec
            ffmpeg_format = target_format
            codec = None

            if target_format == "m4a":
                ffmpeg_format = "mp4"
                codec = "aac"
            elif target_format == "aac":
                ffmpeg_format = "adts"
                codec = "aac"

            # Use original bitrate if possible, or let pydub handle valid defaults
            audio.export(output_path, format=ffmpeg_format, codec=codec)

        except Exception as e:
            raise RuntimeError(f"Conversion failed: {e}")

        if progress_callback:
            progress_callback(1.0)
