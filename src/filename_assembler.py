# filename_assembler.py
import re
import os
import numpy as np

class FilenameAssembler:
    """Contains all logic for validating and assembling new filenames."""

    # These could be moved to a constants file
    COLOUR_DICT = {"typical colour": "ty", "aged": "aged", "banded": "band", "yellow": "yell"}
    COLOUR_DICT_REVERSE = {v: k for k, v in COLOUR_DICT.items()}  # Reverse lookup for UI
    BEHAVIOUR_DICT = {"not specified": "zz", "feeding": "feed", "hiding": "hide", "schooling": "school"}
    BEHAVIOUR_DICT_REVERSE = {v: k for k, v in BEHAVIOUR_DICT.items()}  # Reverse lookup for UI

    def __init__(self, data_manager):
        self.data = data_manager

    def is_already_processed(self, filename: str) -> bool:
        """Checks if a filename matches the basic or full processed format."""
        basic_pattern = r'[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'
        return re.match(basic_pattern, filename) is not None

    def analyze_files_for_editing(self, filenames: list):
        """
        Parses a list of filenames to find which metadata fields are identical across all files.
        Returns a tuple of (is_same_flags, common_values).
        """
        info = np.array([self.regex_match_identity(os.path.basename(os.path.splitext(filename)[0])).groups() for filename in filenames])
        is_same = (info[:, :] == info[0, :]).all(axis=0)
        values = np.array([info[0][i] if is_same[i] else None for i in range(info.shape[1])])
        return is_same, values

    def regex_match_basic(self, filename):
        return re.match(r'[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+', filename)

    def regex_match_identity(self, filename):
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name
        return re.match(r'(0?\-?[A-Za-z]*)_([A-Za-z]+)_([a-z]+)_[A-Z]_([a-z]{2})_([A-Za-z]+)_([A-Za-z\-]+)_([A-Za-z\-]+)_([A-Za-z]{5})_([A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3})_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_([A-Za-z]+)_(.*)', filename)

    def regex_match_datetime_filename(self, filename):
        return re.match(r'0?\-?[A-Za-z]*_[A-Za-z]+_[a-z]+_[A-Z]_[a-z]{2}_[A-Za-z]+_[A-Za-z\-]+_[A-Za-z\-]+_[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_[A-Za-z]+_([A-Za-z0-9]+)', filename)

    def assemble_basic_filename(self, original_filename: str, file_date: str, author_name: str, site_tuple: tuple, activity: str) -> str:
        """Assembles the initial filename with metadata like author, site, and date."""
        if self.regex_match_basic(original_filename) or self.regex_match_identity(original_filename):
            return None

        author_code = self.data.get_user_code(author_name)
        area, site = site_tuple
        site_string = self.data.get_divesite_string(area, site)

        if not all([author_code, site_string, file_date, activity]):
            print("Missing essential info for basic rename")
            return None
        
        # Sanitize original name by removing underscores
        sanitized_original = original_filename.replace('_', '')

        return f"{author_code}_{site_string}_{file_date}_{activity}_{sanitized_original}"

    def assemble_identity_filename(self, existing_filename: str, family: str, genus: str, species: str, confidence: str, phase: str, colour: str, behaviour: str) -> str:
        """Adds fish identification details to an already processed basic filename."""
        base_name_match = re.search(r'([A-Za-z]{5}_.*?_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_.*)', existing_filename)
        if self.regex_match_identity(existing_filename) or not self.regex_match_basic(existing_filename):
            return None

        #colour_code = self.COLOUR_DICT.get(colour, "ty")
        #behaviour_code = self.BEHAVIOUR_DICT.get(behaviour, "zz")
        colour_code = colour
        behaviour_code = behaviour
        
        base_name = base_name_match.group(1)

        if not all([family, genus, species, confidence, phase, colour_code, behaviour_code, base_name]):
            print("Missing essential info for identity rename")
            return None

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour_code}_{behaviour_code}_{base_name}"
    
    def assemble_edited_filename(self, family: str, genus: str, species: str, confidence: str, phase: str, colour: str, behaviour: str, author_code: str, site_string: str, date: str, time: str, activity: str, filename: str, extension: str) -> str:
        """
        Constructs a new filename by replacing edited fields and keeping original ones.
        """

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{author_code}_{site_string}_{date}_{time}_{activity}_{filename}{extension}"