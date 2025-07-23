# app_utils.py
import os
import sys
import shutil
from pathlib import Path

def get_app_path() -> Path:
    """Gets the application path (works for scripts and PyInstaller bundles)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent # Assumes this file is in a subdirectory

def get_data_path() -> Path:
    """Gets the OS-specific writable data directory."""
    app_name = "DavesFishRenamer"
    if sys.platform == 'win32':
        return Path(os.getenv('APPDATA')) / app_name
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / app_name
    else: # Linux/other
        return Path.home() / f".{app_name}"

def initialize_data_files():
    """Copies bundled default data files to the writable data directory if they don't exist."""
    data_dir = get_data_path()
    data_dir.mkdir(parents=True, exist_ok=True)

    config_source_dir = get_app_path() / 'config'
    if not config_source_dir.exists():
        print(f"Warning: Config source directory not found at {config_source_dir}")
        return

    for file_name in os.listdir(config_source_dir):
        source_path = config_source_dir / file_name
        dest_path = data_dir / file_name
        if not dest_path.exists():
            print(f"Initializing data file: {file_name}")
            shutil.copy(source_path, dest_path)