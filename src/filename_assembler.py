# filename_assembler.py
import re
import os
import numpy as np
import logging
from typing import Optional, List, Tuple
from .constants import (
    PATTERN_BASIC_FILENAME,
    PATTERN_IDENTITY_FILENAME,
    PATTERN_BASIC_BASENAME,
    PATTERN_DATETIME_IN_FILENAME
)

logger = logging.getLogger(__name__)

class FilenameAssembler:
    """Contains all logic for validating and assembling new filenames."""

    def __init__(self, data_manager):
        self.data = data_manager

    def is_already_processed(self, filename: str) -> bool:
        """Checks if a filename matches the basic or full processed format."""
        return PATTERN_BASIC_FILENAME.match(filename) is not None

    def analyze_files_for_editing(self, filenames: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parses a list of filenames to find which metadata fields are identical across all files.

        Args:
            filenames: List of filenames to analyze

        Returns:
            Tuple of (is_same_flags, common_values) as numpy arrays

        Raises:
            ValueError: If filenames don't match identity pattern
        """
        if not filenames:
            raise ValueError("No filenames provided for analysis")

        parsed_info = []
        for filename in filenames:
            basename = os.path.basename(os.path.splitext(filename)[0])
            match = self.regex_match_identity(basename)

            if not match:
                logger.error(f"Filename does not match identity pattern: '{basename}'")
                raise ValueError(f"Invalid filename format: '{basename}'")

            parsed_info.append(match.groups())

        try:
            info = np.array(parsed_info)
            is_same = (info[:, :] == info[0, :]).all(axis=0)
            values = np.array([info[0][i] if is_same[i] else None for i in range(info.shape[1])])
            return is_same, values
        except (IndexError, ValueError) as e:
            logger.error(f"Error analyzing files for editing: {e}")
            raise ValueError(f"Failed to analyze filenames: {e}")

    def regex_match_basic(self, filename):
        """Match basic filename pattern."""
        return PATTERN_BASIC_FILENAME.match(filename)

    def regex_match_identity(self, filename):
        """Match identity filename pattern.

        Returns match object with groups:
        0: Family, 1: Genus, 2: species, 3: confidence, 4: phase,
        5: colour, 6: behaviour, 7: author, 8: site, 9: date,
        10: time, 11: activity, 12: original name
        """
        return PATTERN_IDENTITY_FILENAME.match(filename)

    def regex_match_datetime_filename(self, filename):
        """Extract datetime from filename."""
        return PATTERN_DATETIME_IN_FILENAME.match(filename)

    def assemble_basic_filename(self, original_filename: str, file_date: str, author_name: str,
                                site_tuple: Tuple[str, str], activity: str) -> Optional[str]:
        """Assembles the initial filename with metadata like author, site, and date.

        Args:
            original_filename: Original file name without extension
            file_date: Creation date in format 'YYYY-MM-DD_HH-MM-SS'
            author_name: Full name of photographer
            site_tuple: Tuple of (area, site)
            activity: Activity type

        Returns:
            Assembled filename, or None if already processed or missing required data
        """
        # Check if already processed
        if self.regex_match_basic(original_filename) or self.regex_match_identity(original_filename):
            logger.info(f"File already processed: '{original_filename}'")
            return None

        # Validate inputs
        if not author_name or not site_tuple or len(site_tuple) != 2:
            logger.warning(f"Invalid inputs for basic rename: author='{author_name}', site='{site_tuple}'")
            return None

        area, site = site_tuple
        author_code = self.data.get_user_code(author_name)
        site_string = self.data.get_divesite_string(area, site)

        # Check all required fields are present
        if not all([author_code, site_string, file_date, activity]):
            missing = []
            if not author_code: missing.append('author_code')
            if not site_string: missing.append('site_string')
            if not file_date: missing.append('file_date')
            if not activity: missing.append('activity')
            logger.warning(f"Missing essential info for basic rename: {', '.join(missing)}")
            return None

        # Sanitize original name by removing underscores
        sanitized_original = original_filename.replace('_', '')

        return f"{author_code}_{site_string}_{file_date}_{activity}_{sanitized_original}"

    def assemble_identity_filename(self, existing_filename: str, family: str, genus: str,
                                   species: str, confidence: str, phase: str, colour: str,
                                   behaviour: str) -> Optional[str]:
        """Adds fish identification details to an already processed basic filename.

        Args:
            existing_filename: Already processed basic filename
            family: Taxonomic family
            genus: Taxonomic genus
            species: Species name
            confidence: Confidence level
            phase: Life phase
            colour: Colour variant
            behaviour: Observed behaviour

        Returns:
            Assembled identity filename, or None if invalid or already processed
        """
        # Check if already has identity or if not basic format
        if self.regex_match_identity(existing_filename):
            logger.info(f"File already has identity: '{existing_filename}'")
            return None

        if not self.regex_match_basic(existing_filename):
            logger.warning(f"File is not in basic format: '{existing_filename}'")
            return None

        # Extract base name from basic filename
        base_name_match = PATTERN_BASIC_BASENAME.search(existing_filename)
        if not base_name_match:
            logger.error(f"Failed to extract base name from: '{existing_filename}'")
            return None

        base_name = base_name_match.group(1)
        colour_code = colour
        behaviour_code = behaviour

        # Validate all required fields
        if not all([family, genus, species, confidence, phase, colour_code, behaviour_code, base_name]):
            missing = []
            if not family: missing.append('family')
            if not genus: missing.append('genus')
            if not species: missing.append('species')
            if not confidence: missing.append('confidence')
            if not phase: missing.append('phase')
            if not colour_code: missing.append('colour')
            if not behaviour_code: missing.append('behaviour')
            if not base_name: missing.append('base_name')
            logger.warning(f"Missing essential info for identity rename: {', '.join(missing)}")
            return None

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour_code}_{behaviour_code}_{base_name}"
    
    def assemble_edited_filename(self, family: str, genus: str, species: str, confidence: str, phase: str, colour: str, behaviour: str, author_code: str, site_string: str, date: str, time: str, activity: str, filename: str, extension: str) -> str:
        """
        Constructs a new filename by replacing edited fields and keeping original ones.
        """

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{author_code}_{site_string}_{date}_{time}_{activity}_{filename}{extension}"