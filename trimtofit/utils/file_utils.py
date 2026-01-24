import os


def get_unique_filepath(filepath: str) -> str:
    """
    Checks if a file exists at the given path.
    If it does, appends a counter to the filename (preserves extension)
    to generate a unique path.

    Example: 'file.mp3' -> 'file_1.mp3' -> 'file_2.mp3'
    """
    if not os.path.exists(filepath):
        return filepath

    base, ext = os.path.splitext(filepath)
    counter = 1

    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1

    return f"{base}_{counter}{ext}"
