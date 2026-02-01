# src/exiftool_handler.py
"""Handler for ExifTool operations including GPS coordinate writing."""

import subprocess
import shutil
import os
import sys
import logging
import tempfile
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# ExifTool version and download URLs
EXIFTOOL_VERSION = "13.45"
EXIFTOOL_WINDOWS_URL = f"https://netix.dl.sourceforge.net/project/exiftool/exiftool-{EXIFTOOL_VERSION}_64.zip?viasf=1"
EXIFTOOL_MAC_URL = f"https://netix.dl.sourceforge.net/project/exiftool/ExifTool-{EXIFTOOL_VERSION}.pkg"
EXIFTOOL_WEBSITE = "https://exiftool.org/index.html"


class ExifToolHandler:
    """Handles ExifTool detection, installation, and GPS coordinate operations."""

    def __init__(self):
        self._exiftool_path: Optional[str] = None
        self._check_exiftool()

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

    def is_available(self) -> bool:
        """Check if ExifTool is available.

        Returns:
            True if ExifTool is available, False otherwise
        """
        return self._exiftool_path is not None

    def get_version(self) -> Optional[str]:
        """Get ExifTool version string.

        Returns:
            Version string or None if ExifTool is not available
        """
        if not self.is_available():
            return None

        try:
            result = subprocess.run(
                [self._exiftool_path, "-ver"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get ExifTool version: {e}")
            return None

    def refresh_availability(self) -> bool:
        """Re-check ExifTool availability.

        Returns:
            True if ExifTool is now available
        """
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
            app_dir = Path(__file__).parent.parent
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

            # Build ExifTool command
            cmd = [
                self._exiftool_path,
                "-overwrite_original",
                f"-GPSLatitude={lat_abs}",
                f"-GPSLatitudeRef={lat_ref}",
                f"-GPSLongitude={lon_abs}",
                f"-GPSLongitudeRef={lon_ref}",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.debug(f"GPS written to {file_path}: {latitude}, {longitude}")
                return True, "GPS coordinates written successfully"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"ExifTool error: {error_msg}")
                return False, f"ExifTool error: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "ExifTool operation timed out"
        except Exception as e:
            logger.error(f"Failed to write GPS: {e}")
            return False, f"Failed to write GPS: {e}"

    def read_gps_coordinates(self, file_path: str) -> Tuple[Optional[float], Optional[float]]:
        """Read GPS coordinates from an image file's EXIF data.

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
            cmd = [
                self._exiftool_path,
                "-GPSLatitude",
                "-GPSLongitude",
                "-n",  # Output in decimal format
                "-s3",  # Short output, values only
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
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
