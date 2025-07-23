# exif_handler.py
from PIL import Image
import exifread

class ExifHandler:
    """Handles reading EXIF metadata, specifically the creation date, from images."""

    def get_creation_date_str(self, path: str) -> str:
        """
        Extracts the 'DateTimeOriginal' from an image's EXIF data.
        Returns a string formatted as 'YYYY-MM-DD_hh-mm-ss'.
        """
        # try:
        #     # First, try with Pillow, which is faster
        #     with Image.open(path) as img:
        #         exif = img._getexif()
        #         if exif and 36867 in exif:
        #             # 36867 is the tag for DateTimeOriginal
        #             return exif[36867].replace(':', '-', 2).replace(' ', '_')
        # except Exception:
        #     # If Pillow fails, fall back to the more robust exifread
        #     pass

        # try:
        #     with open(path, 'rb') as f:
        #         tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')
        #         if 'EXIF DateTimeOriginal' in tags:
        #             return str(tags['EXIF DateTimeOriginal']).replace(':', '-', 2).replace(' ', '_')
        # except Exception as e:
        #     print(f"Could not read EXIF data for {path}: {e}")
        try:
            image = Image.open(path)
            exif = image._getexif()
            return exif[36867].replace(' ', '_').replace(':', '-')
        except:
            f = open(path, 'rb')
            tags = exifread.process_file(f)
            return tags['Image DateTime'].printable.replace(' ', '_').replace(':', '-')
        
        return ""