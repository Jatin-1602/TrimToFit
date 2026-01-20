# TrimToFit Build Guide

This guide explains how to package the TrimToFit into a standalone `.exe` file that works on any Windows PC without needing Python installed.

## Prerequisites

1.  **Python Installed:** Ensure you have Python installed and the virtual environment is activated.
2.  **Dependencies:** Ensure all `requirements.txt` packages are installed.
3.  **FFmpeg:** You must have the FFmpeg binaries (`ffmpeg.exe` and `ffprobe.exe`) downloaded.

---

## Step 1: Install PyInstaller

Open your terminal in the project directory and run:

```powershell
pip install pyinstaller
```

## Step 2: Build the Executable

Run the following command to generate the `.exe`. This command does three things:
1.  `--noconsole`: Hides the black terminal window.
2.  `--onefile`: Bundles everything into a single file.
3.  `--collect-all customtkinter`: Ensures the UI theme files are included.

```powershell
pyinstaller --noconsole --onefile --collect-all customtkinter --name "TrimToFit" main.py
```

*Note: The build process may take a minute or two.*

## Step 3: Bundle FFmpeg (Crucial)

The `pydub` library requires FFmpeg to process audio files. PyInstaller **does not** bundle these external tools automatically. You must distribute them alongside your app.

1.  Navigate to the newly created **`dist`** folder (inside your project directory).
2.  You will see `TrimToFit.exe`.
3.  **Copy** `ffmpeg.exe` and `ffprobe.exe` from your local FFmpeg installation (usually `C:\Program Files\ffmpeg\bin\`).
4.  **Paste** them into the `dist` folder, right next to `TrimToFit.exe`.

The folder structure should look like this:
```text
dist/
├── TrimToFit.exe
├── ffmpeg.exe
└── ffprobe.exe
```

## Step 4: Distribution

To share the app with others:
1.  Select all three files in the `dist` folder (`TrimToFit.exe`, `ffmpeg.exe`, `ffprobe.exe`).
2.  Right-click -> **Compress to ZIP file**.
3.  Send the ZIP file to the user.

**Important:** The user must extract the ZIP before running. As long as the `.exe` and the `ffmpeg` files are in the same folder, the app will work efficiently.
