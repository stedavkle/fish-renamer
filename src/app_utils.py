# app_utils.py
import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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

    # Create data directory if it doesn't exist
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory at {data_dir}")

    # Check if data files already exist (look for CSV/JSON files, not just any files like logs)
    data_extensions = {'.csv', '.json'}
    existing_data_files = [f for f in data_dir.iterdir() if f.suffix.lower() in data_extensions]

    if existing_data_files:
        logger.info(f"Data directory already has {len(existing_data_files)} data files. Skipping initialization.")
        return

    config_source_dir = get_app_path().parent / 'config'
    if not config_source_dir.exists():
        logger.warning(f"Config source directory not found at {config_source_dir}")
        return

    for file_name in os.listdir(config_source_dir):
        source_path = config_source_dir / file_name
        dest_path = data_dir / file_name
        if not dest_path.exists():
            logger.info(f"Initializing data file: {file_name}")
            shutil.copy(source_path, dest_path)

def clear_data_files():
    """Deletes all files in the data directory (useful for testing)."""
    data_dir = get_data_path()
    if data_dir.exists() and data_dir.is_dir():
        for item in data_dir.iterdir():
            os.remove(item)
        logger.info(f"Cleared all data files in {data_dir}")
    else:
        logger.warning(f"Data directory {data_dir} does not exist or is not a directory.")