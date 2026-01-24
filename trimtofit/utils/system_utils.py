import sys
import subprocess
import shutil

def check_ffmpeg_availability():
    """Returns True if ffmpeg is found in PATH."""
    return shutil.which("ffmpeg") is not None

def apply_windows_ffmpeg_patch():
    """
    Monkey Patch: Suppress FFmpeg Console Window (Windows)
    This prevents the black cmd window from popping up when running as a GUI/EXE.
    """
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
