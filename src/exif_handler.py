# exif_handler.py
from PIL import Image
import exifread
import logging
from .constants import EXIF_TAG_DATETIME_ORIGINAL, EXIF_TAG_DATETIME

logger = logging.getLogger(__name__)

class ExifHandler:
    """Handles reading EXIF metadata, specifically the creation date, from images."""

    def get_creation_date_str(self, path: str) -> str:
        """
        Extracts the 'DateTimeOriginal' from an image's EXIF data.
        Returns a string formatted as 'YYYY-MM-DD_hh-mm-ss'.

        Args:
            path: Path to the image file

        Returns:
            Formatted date string, or empty string if extraction fails
        """
        # Try with Pillow first (faster and more reliable with modern API)
        date_str = self._get_date_from_pillow(path)
        if date_str:
            return date_str

        # Fallback to exifread library
        date_str = self._get_date_from_exifread(path)
        if date_str:
            return date_str

        logger.warning(f"Could not extract EXIF date from {path}")
        return ""

    def _get_date_from_pillow(self, path: str) -> str:
        """Extract date using Pillow library."""
        try:
            with Image.open(path) as img:
                # Use public API instead of deprecated _getexif()
                exif_data = img.getexif()
                if exif_data:
                    # Try DateTimeOriginal first (preferred)
                    datetime_str = exif_data.get(EXIF_TAG_DATETIME_ORIGINAL)
                    if datetime_str:
                        return self._format_datetime(datetime_str)

                    # Fallback to DateTime tag
                    datetime_str = exif_data.get(EXIF_TAG_DATETIME)
                    if datetime_str:
                        return self._format_datetime(datetime_str)
        except (IOError, OSError, AttributeError, KeyError) as e:
            logger.debug(f"Pillow EXIF extraction failed for {path}: {e}")

        return ""

    def _get_date_from_exifread(self, path: str) -> str:
        """Extract date using exifread library as fallback."""
        try:
            with open(path, 'rb') as f:
                tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')

                # Try DateTimeOriginal first
                if 'EXIF DateTimeOriginal' in tags:
                    return self._format_datetime(str(tags['EXIF DateTimeOriginal']))

                # Fallback to Image DateTime
                if 'Image DateTime' in tags:
                    return self._format_datetime(str(tags['Image DateTime']))
        except (IOError, OSError) as e:
            logger.debug(f"exifread extraction failed for {path}: {e}")

        return ""

    def _format_datetime(self, datetime_str: str) -> str:
        """
        Format datetime string from EXIF format to application format.

        Args:
            datetime_str: Date in format 'YYYY:MM:DD HH:MM:SS'

        Returns:
            Formatted as 'YYYY-MM-DD_HH-MM-SS'
        """
        try:
            # Replace first two colons with dashes (date part)
            # Then replace space with underscore
            # Then replace remaining colons with dashes (time part)
            return datetime_str.replace(':', '-', 2).replace(' ', '_').replace(':', '-')
        except (AttributeError, ValueError) as e:
            logger.warning(f"Failed to format datetime string '{datetime_str}': {e}")
            return ""