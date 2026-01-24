import os
import sys
import subprocess
from typing import List, Tuple, Optional, Callable
from pydub import AudioSegment
from pydub.utils import mediainfo
from trimtofit.utils.system_utils import apply_windows_ffmpeg_patch
from trimtofit.utils.file_utils import get_unique_filepath

# Apply the patch immediately upon import if on Windows
apply_windows_ffmpeg_patch()


class AudioProcessor:
    """
    Handles audio processing logic using pydub and ffmpeg.
    """

    def invert_ranges(
        self, remove_ranges: List[Tuple[int, int]], total_duration_ms: int
    ) -> List[Tuple[int, int]]:
        """
        Calculates the 'keep' ranges based on the 'remove' ranges and total duration.

        Args:
            remove_ranges: List of (start_ms, end_ms) tuples to remove.
            total_duration_ms: Total duration of the audio in milliseconds.

        Returns:
            List of (start_ms, end_ms) tuples to keep.
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
        keep_selected_ranges: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Loads audio, removes specified ranges, and exports the result.

        Args:
            input_path: Path to source audio file.
            output_path: Proposed path to destination audio file.
            remove_ranges_ms: List of tuples [(start_ms, end_ms), ...].
            keep_selected_ranges: If True, keeps ONLY the selected ranges. If False, removes them.
            progress_callback: Optional function that accepts a float (0.0 to 1.0) for progress reporting.

        Returns:
            str: The actual output path used (handled for uniqueness).

        Raises:
            FileNotFoundError: If input file does not exist.
            RuntimeError: If audio loading or processing fails.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback(0.1)

        try:
            audio = AudioSegment.from_file(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load audio: {e}")

        if progress_callback:
            progress_callback(0.3)

        total_duration = len(audio)

        # Ranges are already in milliseconds
        if keep_selected_ranges:
            # If keeping selected, use them directly (sorted)
            remove_ranges_ms.sort(key=lambda x: x[0])
            keep_ranges = remove_ranges_ms
        else:
            # If removing selected, calculate the inverse
            keep_ranges = self.invert_ranges(remove_ranges_ms, total_duration)

        final_audio = AudioSegment.empty()

        if keep_ranges:
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
        except Exception:
            pass

        # Ensure directory exists for output
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Get unique file path
        actual_output_path = get_unique_filepath(output_path)

        try:
            final_audio.export(
                actual_output_path,
                format=actual_output_path.split(".")[-1],
                bitrate=bitrate,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to export audio: {e}")

        if progress_callback:
            progress_callback(1.0)

        return actual_output_path

    def change_speed(
        self,
        input_path: str,
        output_path: str,
        speed_factor: float,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Changes the speed of the audio using FFmpeg's atempo filter to preserve pitch.

        Args:
            input_path: Path to source audio file.
            output_path: Proposed path to destination audio file.
            speed_factor: Float between 0.5 and 2.0.
            progress_callback: Optional progress reporter.

        Returns:
            str: The actual output path used.

        Raises:
            ValueError: If speed_factor is out of range.
            FileNotFoundError: If input file does not exist.
            RuntimeError: If FFmpeg fails.
        """
        if not (0.5 <= speed_factor <= 2.0):
            raise ValueError("Speed factor must be between 0.5 and 2.0")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback(0.1)

        # Get unique file path
        actual_output_path = get_unique_filepath(output_path)

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
            actual_output_path,
        ]

        if progress_callback:
            progress_callback(0.3)

        try:
            # We use startupinfo hidden via the patch applied at module level implicitly for Popen
            # but for subprocess.run we might need to be explicit if the patch doesn't cover run's internals heavily enough on some python versions
            # However, since we monkeypatched Popen, run() calls Popen, so it should be fine.
            # To be safe and explicit for win32:
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                subprocess.run(
                    cmd, check=True, startupinfo=startupinfo, creationflags=0x08000000
                )
            else:
                subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed with error: {e}")

        if progress_callback:
            progress_callback(1.0)

        return actual_output_path

    def convert_format(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Converts audio file format using pydub.

        Args:
            input_path: Path to source audio file.
            output_path: Proposed path to destination audio file.
            target_format: Target format string (e.g., 'mp3', 'wav').
            progress_callback: Optional progress reporter.

        Returns:
            str: The actual output path used.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback(0.1)

        # Get unique file path
        actual_output_path = get_unique_filepath(output_path)

        try:
            audio = AudioSegment.from_file(input_path)
            if progress_callback:
                progress_callback(0.5)

            output_dir = os.path.dirname(actual_output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            audio.export(actual_output_path, format=target_format)

            if progress_callback:
                progress_callback(1.0)

            return actual_output_path

        except Exception as e:
            raise RuntimeError(f"Failed to convert format: {e}")

    def merge_audio_files(
        self,
        input_paths: List[str],
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Merges multiple audio files into a single MP3 file.
        Resamples all files to match the frame rate of the first file.

        Args:
            input_paths: List of paths to source audio files.
            output_path: Proposed path to destination MP3 file.
            progress_callback: Optional progress reporter.

        Returns:
            str: The actual output path used.
        """
        if not input_paths:
            raise ValueError("No input files provided")

        if progress_callback:
            progress_callback(0.0)

        merged_audio = AudioSegment.empty()
        base_frame_rate = None

        count = len(input_paths)
        for i, path in enumerate(input_paths):
            if not os.path.exists(path):
                continue

            try:
                segment = AudioSegment.from_file(path)

                # Normalize frame rate to the first file's rate
                if base_frame_rate is None:
                    base_frame_rate = segment.frame_rate
                elif segment.frame_rate != base_frame_rate:
                    segment = segment.set_frame_rate(base_frame_rate)

                merged_audio += segment

                if progress_callback:
                    # Progress from 0.0 to 0.7 during loading
                    progress_callback(0.7 * (i + 1) / count)

            except Exception as e:
                print(f"Skipping file {path} due to error: {e}")

        if progress_callback:
            progress_callback(0.75)

        # Get unique file path
        actual_output_path = get_unique_filepath(output_path)

        # Ensure directory exists for output
        output_dir = os.path.dirname(actual_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            # Export as MP3 192k
            merged_audio.export(actual_output_path, format="mp3", bitrate="192k")
        except Exception as e:
            raise RuntimeError(f"Failed to export merged audio: {e}")

        if progress_callback:
            progress_callback(1.0)

        return actual_output_path
