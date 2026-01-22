# app_utils.py
import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def validate_safe_path(base_dir: Path, file_path: Path) -> bool:
    """Ensure file_path is within base_dir to prevent path traversal attacks.

    Args:
        base_dir: The directory that should contain the file
        file_path: The file path to validate (can be relative or absolute)

    Returns:
        bool: True if the path is safe (within base_dir), False otherwise

    Example:
        >>> validate_safe_path(Path("/data"), Path("file.csv"))  # Safe
        True
        >>> validate_safe_path(Path("/data"), Path("../../../etc/passwd"))  # Unsafe
        False
    """
    try:
        # Resolve both paths to absolute paths
        base_dir_resolved = base_dir.resolve()

        # If file_path is relative, resolve it relative to base_dir
        if not file_path.is_absolute():
            file_path_resolved = (base_dir / file_path).resolve()
        else:
            file_path_resolved = file_path.resolve()

        # Check if the resolved file path is within the base directory
        # In Python 3.9+, use is_relative_to()
        # For compatibility with older Python, use this approach:
        try:
            file_path_resolved.relative_to(base_dir_resolved)
            return True
        except ValueError:
            # Path is not relative to base_dir
            return False
    except (ValueError, OSError, RuntimeError) as e:
        logger.warning(f"Path validation failed for {file_path}: {e}")
        return False

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
        # Validate path to prevent path traversal attacks
        if not validate_safe_path(config_source_dir, Path(file_name)):
            logger.warning(f"Skipping potentially unsafe path: {file_name}")
            continue

        source_path = config_source_dir / file_name
        dest_path = data_dir / file_name

        # Also validate destination path
        if not validate_safe_path(data_dir, Path(file_name)):
            logger.warning(f"Skipping unsafe destination path: {file_name}")
            continue

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

def get_filename_diff(original: str, new: str) -> tuple[str, str, str]:
    """Calculate common prefix, changed part, and common suffix between two filenames.

    Args:
        original: Original filename
        new: New filename

    Returns:
        Tuple of (prefix, changed_middle, suffix)
        Example: ('IMG', '001' -> 'ABC_Site_001') returns ('', 'ABC_Site_', '001')
    """
    # Find common prefix
    prefix_len = 0
    min_len = min(len(original), len(new))
    for i in range(min_len):
        if original[i] == new[i]:
            prefix_len += 1
        else:
            break

    # Find common suffix (search from end)
    suffix_len = 0
    for i in range(1, min_len - prefix_len + 1):
        if original[-i] == new[-i]:
            suffix_len += 1
        else:
            break

    prefix = new[:prefix_len]
    suffix = new[-suffix_len:] if suffix_len > 0 else ''
    changed_middle = new[prefix_len:len(new) - suffix_len] if suffix_len > 0 else new[prefix_len:]

    return (prefix, changed_middle, suffix)