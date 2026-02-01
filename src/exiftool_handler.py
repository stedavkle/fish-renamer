# src/exiftool_handler.py
"""Handler for ExifTool operations including GPS coordinate writing.

Uses ExifTool's -stay_open mode for optimal performance. This keeps a single
ExifTool process running and communicates via stdin/stdout, avoiding the
~100ms startup overhead for each operation.
"""

import subprocess
import shutil
import os
import sys
import logging
import tempfile
import zipfile
import urllib.request
import json
import threading
import atexit
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from src import app_utils

logger = logging.getLogger(__name__)

# ExifTool version and download URLs
EXIFTOOL_VERSION = "13.48"
EXIFTOOL_WINDOWS_URL = f"https://netix.dl.sourceforge.net/project/exiftool/exiftool-{EXIFTOOL_VERSION}_64.zip?viasf=1"
EXIFTOOL_MAC_URL = f"https://netix.dl.sourceforge.net/project/exiftool/ExifTool-{EXIFTOOL_VERSION}.pkg"
EXIFTOOL_WEBSITE = "https://exiftool.org/index.html"

# Sentinel that ExifTool outputs when a command is complete
EXIFTOOL_READY_SENTINEL = "{ready}"


class ExifToolHandler:
    """Handles ExifTool detection, installation, and operations.

    Uses -stay_open mode to maintain a persistent ExifTool process for
    optimal performance across multiple operations.
    """

    def __init__(self):
        self._exiftool_path: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()  # Thread safety for process communication
        self._check_exiftool()

        # Register cleanup on application exit
        atexit.register(self.shutdown)

    def _check_exiftool(self) -> None:
        """Check if ExifTool is available in system PATH or local installation."""
        # Check system PATH first
        exiftool_cmd = "exiftool.exe" if sys.platform == "win32" else "exiftool"
        path = shutil.which(exiftool_cmd)
        
        if path:
            self._exiftool_path = path
            logger.info(f"Found ExifTool in PATH: {path}")
            return

        # Check local installation in app directory
        app_dir = Path(__file__).parent.parent
        local_paths = [
            app_dir / "exiftool" / "exiftool.exe",  # Windows
            app_dir / "exiftool" / "exiftool",  # Mac/Linux
            app_dir / "exiftool.exe",  # Windows in root
            app_utils.get_data_path() / "exiftool" / "exiftool.exe",  # In app data
        ]

        for local_path in local_paths:
            if local_path.exists():
                self._exiftool_path = str(local_path)
                logger.info(f"Found local ExifTool: {self._exiftool_path}")
                return

        # Check common macOS installation paths (Homebrew, manual installs)
        # These paths may not be in PATH when app is launched from Finder
        if sys.platform == "darwin":
            mac_paths = [
                Path("/usr/local/bin/exiftool"),           # Intel Homebrew / manual install
                Path("/opt/homebrew/bin/exiftool"),        # Apple Silicon Homebrew
                Path("/usr/bin/exiftool"),                 # System install
                Path.home() / "bin" / "exiftool",          # User bin
            ]
            for mac_path in mac_paths:
                if mac_path.exists():
                    self._exiftool_path = str(mac_path)
                    logger.info(f"Found macOS ExifTool: {self._exiftool_path}")
                    return

        logger.warning("ExifTool not found")

    def _start_process(self) -> bool:
        """Start the persistent ExifTool process.

        Returns:
            True if process started successfully, False otherwise
        """
        if self._process is not None and self._process.poll() is None:
            return True  # Already running

        if not self._exiftool_path:
            return False

        try:
            # Start ExifTool in stay_open mode
            # -@ - means read arguments from stdin
            # -stay_open True keeps the process running
            startupinfo = None
            if sys.platform == "win32":
                # Hide console window on Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            self._process = subprocess.Popen(
                [self._exiftool_path, "-stay_open", "True", "-@", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                startupinfo=startupinfo,
                bufsize=1,  # Line buffered
            )
            logger.info("Started persistent ExifTool process")
            return True

        except Exception as e:
            logger.error(f"Failed to start ExifTool process: {e}")
            self._process = None
            return False

    def _ensure_process(self) -> bool:
        """Ensure the persistent process is running.

        Returns:
            True if process is running, False otherwise
        """
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                return self._start_process()
            return True

    def _execute(self, *args: str, timeout: float = 30.0) -> str:
        """Execute an ExifTool command and return the output.

        Args:
            *args: Command arguments to pass to ExifTool
            timeout: Timeout in seconds for the operation

        Returns:
            Output from ExifTool, or empty string on error
        """
        if not self._ensure_process():
            return ""

        with self._lock:
            try:
                # Send command arguments, one per line
                for arg in args:
                    self._process.stdin.write(arg + "\n")

                # Send -execute to signal end of command
                # ExifTool will output {ready} when done
                self._process.stdin.write("-execute\n")
                self._process.stdin.flush()

                # Read output until we see the ready sentinel
                output_lines = []
                while True:
                    line = self._process.stdout.readline()
                    if not line:
                        # Process died
                        logger.warning("ExifTool process died unexpectedly")
                        self._process = None
                        break

                    line = line.rstrip('\r\n')
                    if line == EXIFTOOL_READY_SENTINEL:
                        break
                    output_lines.append(line)

                return "\n".join(output_lines)

            except Exception as e:
                logger.error(f"ExifTool execution error: {e}")
                # Try to restart on next call
                self._process = None
                return ""

    def shutdown(self) -> None:
        """Shutdown the persistent ExifTool process.

        Called automatically on application exit via atexit.
        """
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                try:
                    # Send shutdown command
                    self._process.stdin.write("-stay_open\n")
                    self._process.stdin.write("False\n")
                    self._process.stdin.flush()

                    # Wait for graceful shutdown
                    self._process.wait(timeout=5)
                    logger.info("ExifTool process shutdown gracefully")

                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't respond
                    self._process.kill()
                    logger.warning("ExifTool process killed after timeout")

                except Exception as e:
                    logger.error(f"Error shutting down ExifTool: {e}")
                    try:
                        self._process.kill()
                    except:
                        pass

                finally:
                    self._process = None

    def is_available(self) -> bool:
        """Check if ExifTool is available.

        Returns:
            True if ExifTool is available, False otherwise
        """
        return self._exiftool_path is not None

    def get_version(self) -> Optional[str]:
        """Get ExifTool version string.

        Uses the persistent process if available.

        Returns:
            Version string or None if ExifTool is not available
        """
        if not self.is_available():
            return None

        try:
            output = self._execute("-ver")
            return output.strip() if output else None
        except Exception as e:
            logger.error(f"Failed to get ExifTool version: {e}")
            return None

    def refresh_availability(self) -> bool:
        """Re-check ExifTool availability.

        Shuts down any existing process and re-checks for ExifTool.

        Returns:
            True if ExifTool is now available
        """
        self.shutdown()  # Stop existing process if running
        self._exiftool_path = None
        self._check_exiftool()
        return self.is_available()

    @staticmethod
    def get_download_url() -> str:
        """Get the appropriate download URL for the current platform.

        Returns:
            Download URL string
        """
        if sys.platform == "win32":
            return EXIFTOOL_WINDOWS_URL
        elif sys.platform == "darwin":
            return EXIFTOOL_MAC_URL
        else:
            return EXIFTOOL_WEBSITE

    @staticmethod
    def get_website_url() -> str:
        """Get the ExifTool website URL.

        Returns:
            Website URL string
        """
        return EXIFTOOL_WEBSITE

    def download_and_install(self, progress_callback=None) -> Tuple[bool, str]:
        """Download and install ExifTool for Windows.

        Args:
            progress_callback: Optional callback function(percent, message)

        Returns:
            Tuple of (success, message)
        """
        if sys.platform != "win32":
            return False, "Automatic installation is only supported on Windows. Please install manually."

        try:
            app_dir = app_utils.get_data_path()
            install_dir = app_dir / "exiftool"
            install_dir.mkdir(exist_ok=True)

            # Download
            if progress_callback:
                progress_callback(10, "Downloading ExifTool...")

            zip_path = install_dir / "exiftool.zip"

            try:
                urllib.request.urlretrieve(EXIFTOOL_WINDOWS_URL, zip_path)
            except Exception as e:
                return False, f"Download failed: {e}"

            if progress_callback:
                progress_callback(50, "Extracting...")

            # Extract
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
            except Exception as e:
                return False, f"Extraction failed: {e}"

            # Move all contents from extracted subfolder to install_dir
            # The zip extracts to a subfolder like "exiftool-13.45_64"
            if progress_callback:
                progress_callback(80, "Configuring...")

            extracted_folder = install_dir / f"exiftool-{EXIFTOOL_VERSION}_64"

            if extracted_folder.exists() and extracted_folder.is_dir():
                # Move all contents from extracted folder to install_dir
                for item in extracted_folder.iterdir():
                    target_path = install_dir / item.name
                    # Remove existing target if present
                    if target_path.exists():
                        if target_path.is_dir():
                            shutil.rmtree(str(target_path))
                        else:
                            target_path.unlink()
                    shutil.move(str(item), str(target_path))

                # Remove the now-empty extracted folder
                extracted_folder.rmdir()

            # Rename exiftool(-k).exe to exiftool.exe
            source_exe = install_dir / "exiftool(-k).exe"
            target_exe = install_dir / "exiftool.exe"

            if source_exe.exists():
                if target_exe.exists():
                    target_exe.unlink()
                source_exe.rename(target_exe)

            # Clean up zip
            if zip_path.exists():
                zip_path.unlink()

            if progress_callback:
                progress_callback(100, "Complete!")

            # Refresh availability
            self.refresh_availability()

            if self.is_available():
                return True, f"ExifTool installed successfully. Version: {self.get_version()}"
            else:
                return False, "Installation completed but ExifTool not detected. Please check manually."

        except Exception as e:
            logger.error(f"ExifTool installation failed: {e}")
            return False, f"Installation failed: {e}"

    def write_gps_coordinates(self, file_path: str, latitude: float, longitude: float) -> Tuple[bool, str]:
        """Write GPS coordinates to an image file's EXIF data.

        Uses the persistent ExifTool process for optimal performance.

        Args:
            file_path: Path to the image file
            latitude: GPS latitude (positive = North, negative = South)
            longitude: GPS longitude (positive = East, negative = West)

        Returns:
            Tuple of (success, message)
        """
        if not self.is_available():
            return False, "ExifTool is not available"

        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        try:
            # Determine latitude/longitude references
            lat_ref = "N" if latitude >= 0 else "S"
            lon_ref = "E" if longitude >= 0 else "W"

            # Use absolute values for coordinates
            lat_abs = abs(latitude)
            lon_abs = abs(longitude)

            # Execute via persistent process
            output = self._execute(
                "-overwrite_original",
                f"-GPSLatitude={lat_abs}",
                f"-GPSLatitudeRef={lat_ref}",
                f"-GPSLongitude={lon_abs}",
                f"-GPSLongitudeRef={lon_ref}",
                file_path
            )

            # Check for success indicators in output
            if "1 image files updated" in output or "1 image file updated" in output:
                logger.debug(f"GPS written to {file_path}: {latitude}, {longitude}")
                return True, "GPS coordinates written successfully"
            elif "error" in output.lower() or "warning" in output.lower():
                logger.error(f"ExifTool error: {output}")
                return False, f"ExifTool error: {output}"
            else:
                # Assume success if no error
                logger.debug(f"GPS written to {file_path}: {latitude}, {longitude}")
                return True, "GPS coordinates written successfully"

        except Exception as e:
            logger.error(f"Failed to write GPS: {e}")
            return False, f"Failed to write GPS: {e}"

    def read_gps_coordinates(self, file_path: str) -> Tuple[Optional[float], Optional[float]]:
        """Read GPS coordinates from an image file's EXIF data.

        Uses the persistent ExifTool process for optimal performance.

        Args:
            file_path: Path to the image file

        Returns:
            Tuple of (latitude, longitude) or (None, None) if not found
        """
        if not self.is_available():
            return None, None

        if not os.path.exists(file_path):
            return None, None

        try:
            # Execute via persistent process
            output = self._execute(
                "-GPSLatitude",
                "-GPSLongitude",
                "-n",   # Output in decimal format
                "-s3",  # Short output, values only
                file_path
            )

            lines = output.strip().split('\n')
            if len(lines) >= 2:
                try:
                    lat = float(lines[0])
                    lon = float(lines[1])
                    return lat, lon
                except ValueError:
                    pass

            return None, None

        except Exception as e:
            logger.error(f"Failed to read GPS: {e}")
            return None, None

    # Maximum files per ExifTool batch to avoid command line length issues
    BATCH_SIZE = 40

    def batch_read_creation_dates(self, file_paths: List[str],
                                    progress_callback=None) -> Dict[str, str]:
        """Read creation dates from multiple files using the persistent process.

        Uses -stay_open mode for optimal performance - no subprocess spawn
        overhead for each batch. Files are processed in batches to avoid
        command line length limits.

        Args:
            file_paths: List of file paths to read dates from
            progress_callback: Optional callback function(current, total) for progress updates

        Returns:
            Dict mapping file_path to formatted date string ('YYYY-MM-DD_HH-MM-SS')
            Files without valid dates are omitted from the result.
        """
        if not self.is_available() or not file_paths:
            return {}

        results = {}
        total = len(file_paths)

        # Process files in batches to avoid command line length issues
        for i in range(0, len(file_paths), self.BATCH_SIZE):
            batch = file_paths[i:i + self.BATCH_SIZE]
            batch_results = self._read_creation_dates_batch(batch)
            results.update(batch_results)

            # Report progress after each batch
            if progress_callback:
                processed = min(i + self.BATCH_SIZE, total)
                progress_callback(processed, total)

        return results

    def _read_creation_dates_batch(self, file_paths: List[str]) -> Dict[str, str]:
        """Read creation dates from a single batch of files.

        Args:
            file_paths: List of file paths (should be <= BATCH_SIZE)

        Returns:
            Dict mapping file_path to formatted date string
        """
        results = {}

        try:
            # Build command arguments for JSON output with date tags
            args = ["-json", "-DateTimeOriginal", "-CreateDate", "-ModifyDate"]
            args.extend(file_paths)

            # Execute via persistent process
            output = self._execute(*args)

            if output.strip():
                # ExifTool may output summary lines before JSON (e.g., "2 image files read")
                # Find the JSON array start
                json_start = output.find('[')
                if json_start != -1:
                    json_str = output[json_start:]
                else:
                    json_str = output

                try:
                    data = json.loads(json_str)
                    for entry in data:
                        file_path = entry.get("SourceFile", "")
                        if not file_path:
                            continue

                        # Try DateTimeOriginal first, then CreateDate, then ModifyDate
                        date_str = (
                            entry.get("DateTimeOriginal") or
                            entry.get("CreateDate") or
                            entry.get("ModifyDate")
                        )

                        if date_str and date_str != "0000:00:00 00:00:00":
                            formatted = self._format_exif_datetime(date_str)
                            if formatted:
                                results[file_path] = formatted

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse ExifTool JSON output: {e}")
                    logger.debug(f"JSON string was: {json_str[:200]}")

        except Exception as e:
            logger.error(f"Failed to batch read creation dates: {e}")

        return results

    def _format_exif_datetime(self, datetime_str: str) -> str:
        """Format EXIF datetime string to application format.

        Args:
            datetime_str: Date in format 'YYYY:MM:DD HH:MM:SS' (with possible timezone)

        Returns:
            Formatted as 'YYYY-MM-DD_HH-MM-SS', or empty string if invalid
        """
        try:
            # Remove timezone suffix if present (e.g., '+08:00')
            if '+' in datetime_str:
                datetime_str = datetime_str.split('+')[0].strip()
            elif datetime_str.count('-') > 2:
                # Handle format like '2024:01:15 14:30:45-08:00'
                parts = datetime_str.rsplit('-', 1)
                if ':' in parts[-1]:
                    datetime_str = parts[0].strip()

            # Replace first two colons with dashes (date part)
            # Then replace space with underscore
            # Then replace remaining colons with dashes (time part)
            return datetime_str.replace(':', '-', 2).replace(' ', '_').replace(':', '-')
        except (AttributeError, ValueError) as e:
            logger.warning(f"Failed to format datetime string '{datetime_str}': {e}")
            return ""

    def batch_write_gps(self, file_coords_list: List[Tuple[str, float, float]],
                        progress_callback=None) -> List[Tuple[str, bool, str]]:
        """Write GPS coordinates to multiple files.

        Args:
            file_coords_list: List of (file_path, latitude, longitude) tuples
            progress_callback: Optional callback function(current, total, file_path)

        Returns:
            List of (file_path, success, message) tuples
        """
        results = []
        total = len(file_coords_list)

        for i, (file_path, lat, lon) in enumerate(file_coords_list):
            if progress_callback:
                progress_callback(i + 1, total, file_path)

            success, message = self.write_gps_coordinates(file_path, lat, lon)
            results.append((file_path, success, message))

        return results
