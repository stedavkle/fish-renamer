# filename_assembler.py
import os
import logging
from typing import NamedTuple, Optional, List, Tuple
from .constants import (
    PATTERN_DATE_FIELD,
    PATTERN_TIME_FIELD,
    PATTERN_GPS_MARKER,
    BASIC_DATE_INDEX,
    IDENTITY_DATE_INDEX
)

logger = logging.getLogger(__name__)

FIELD_NAMES = ['family', 'genus', 'species', 'confidence', 'phase', 'colour', 'behaviour',
               'author', 'site', 'date', 'time', 'activity', 'camera', 'original name']


class ParsedName(NamedTuple):
    """A Basic or Identity filename (without extension) split into its parts."""
    format: str    # 'basic' or 'identity'
    fields: tuple  # 14 slots, see FIELD_NAMES; slots 0-6 are None for basic names
    gps: str       # 'N', 'G' or '' (legacy name without marker)
    tail: str      # free user text after the marker, kept verbatim
    body: str      # the name up to and including the original name (no marker)

    @property
    def gps_suffix(self) -> str:
        """Marker plus free text in the current format, e.g. '_N_' or '_G_two fish'."""
        return f"_{self.gps}_{self.tail}" if self.gps else ''


def parse_filename(stem: str) -> Tuple[Optional[ParsedName], str]:
    """Split a filename (without extension) into fields by position.

    Field contents are not checked against the data lists, so old sites, former
    photographers, 'Labridae-Sc' or 'species3' all pass. Only the date and time
    fields must be well-formed, because they anchor the positions.

    Returns:
        (ParsedName, '') on success, (None, reason) otherwise
    """
    parts = stem.split('_')

    def has_datetime_at(i):
        return (len(parts) > i + 1 and PATTERN_DATE_FIELD.match(parts[i])
                and PATTERN_TIME_FIELD.match(parts[i + 1]))

    # Basic first: an Identity name never has a date at the Basic position,
    # but a Basic name's free text could contain one at the Identity position
    if has_datetime_at(BASIC_DATE_INDEX):
        fmt, date_index = 'basic', BASIC_DATE_INDEX
    elif has_datetime_at(IDENTITY_DATE_INDEX):
        fmt, date_index = 'identity', IDENTITY_DATE_INDEX
    else:
        found = next((i for i in range(len(parts)) if has_datetime_at(i)), None)
        if found is None:
            return None, 'No date_time (YYYY-MM-DD_HH-MM-SS) in name'
        return None, (f"Date is field {found + 1}, expected field {BASIC_DATE_INDEX + 1} (Basic) "
                      f"or {IDENTITY_DATE_INDEX + 1} (Identity) - missing or extra '_'?")

    # Fields before the date, then date, time, activity, camera, rest
    rest_index = date_index + 4
    rest = '_'.join(parts[rest_index:])
    if not rest:
        return None, 'Missing activity, camera or original name after date_time'

    marker = PATTERN_GPS_MARKER.match(rest)
    if marker:
        original = marker.group('original')
        gps = marker.group('gps')
        tail = marker.group('tail') if marker.group('tail') is not None else (marker.group('legacy_tail') or '')
    else:
        original, gps, tail = rest, '', ''

    if fmt == 'identity':
        fields = tuple(parts[:3] + parts[4:rest_index]) + (original,)
    else:
        fields = (None,) * 7 + tuple(parts[:rest_index]) + (original,)
    body = '_'.join(parts[:rest_index] + [original])
    return ParsedName(fmt, fields, gps, tail, body), ''


class FilenameAssembler:
    """Contains all logic for validating and assembling new filenames."""

    def __init__(self, data_manager):
        self.data = data_manager

    def is_already_processed(self, filename: str) -> bool:
        """Checks if a filename is already in Basic or Identity format."""
        return parse_filename(filename)[0] is not None

    def analyze_files_for_editing(self, filenames: List[str]) -> Tuple[str, list, list]:
        """
        Parses a list of filenames to find which metadata fields are identical across all files.

        Args:
            filenames: List of filenames without extension (all Basic or all Identity)

        Returns:
            Tuple of (format, is_same_flags, common_values); the lists have 14
            elements (see FIELD_NAMES), taxonomy slots are never 'same' for Basic

        Raises:
            ValueError: If a filename can't be parsed or formats are mixed
        """
        if not filenames:
            raise ValueError("No filenames provided for analysis")

        parsed_info = []
        for filename in filenames:
            parsed, error = parse_filename(filename)
            if not parsed:
                raise ValueError(f"'{filename}': {error}")
            parsed_info.append(parsed)

        fmt = parsed_info[0].format
        if any(p.format != fmt for p in parsed_info):
            raise ValueError("Mixed Basic and Identity files - edit them separately")

        first = parsed_info[0].fields
        is_same = [first[i] is not None and all(p.fields[i] == first[i] for p in parsed_info)
                   for i in range(len(first))]
        values = [first[i] if is_same[i] else None for i in range(len(first))]
        return fmt, is_same, values

    def assemble_basic_filename(self, original_filename: str, file_date: str, author_name: str,
                                site_tuple: Tuple[str, str], activity: str, camera: str) -> Optional[str]:
        """Assembles the initial filename with metadata like author, site, and date.

        Args:
            original_filename: Original file name without extension
            file_date: Creation date in format 'YYYY-MM-DD_HH-MM-SS'
            author_name: Full name of photographer
            site_tuple: Tuple of (area, site)
            activity: Activity type
            camera: Camera abbreviation (e.g., 'S-A7IV')

        Returns:
            Assembled filename, or None if already processed or missing required data
        """
        # Check if already processed
        if self.is_already_processed(original_filename):
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
        if not all([author_code, site_string, file_date, activity, camera]):
            missing = []
            if not author_code: missing.append('author_code')
            if not site_string: missing.append('site_string')
            if not file_date: missing.append('file_date')
            if not activity: missing.append('activity')
            if not camera: missing.append('camera')
            logger.warning(f"Missing essential info for basic rename: {', '.join(missing)}")
            return None

        # Sanitize original name by removing underscores
        sanitized_original = original_filename.replace('_', '')

        # Append _N_ to indicate no GPS data (will be replaced with _G_ when GPS is added)
        return f"{author_code}_{site_string}_{file_date}_{activity}_{camera}_{sanitized_original}_N_"

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
        parsed, error = parse_filename(existing_filename)
        if not parsed:
            logger.warning(f"File is not in basic format: '{existing_filename}': {error}")
            return None

        if parsed.format == 'identity':
            logger.info(f"File already has identity: '{existing_filename}'")
            return None

        # Basic fields without GPS marker; marker and free text are re-appended
        base_name = '_'.join(parsed.fields[7:])
        gps_suffix = f"_{parsed.gps or 'N'}_{parsed.tail}"
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

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour_code}_{behaviour_code}_{base_name}{gps_suffix}"
    
    def assemble_edited_filename(self, family: str, genus: str, species: str, confidence: str, phase: str, colour: str, behaviour: str, author_code: str, site_string: str, date: str, time: str, activity: str, camera: str, filename: str, extension: str) -> str:
        """
        Constructs a new filename by replacing edited fields and keeping original ones.
        """

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{author_code}_{site_string}_{date}_{time}_{activity}_{camera}_{filename}{extension}"

    def assemble_edited_basic_filename(self, author_code: str, site_string: str, date: str, time: str, activity: str, camera: str, filename: str, extension: str) -> str:
        """
        Constructs a new Basic format filename by replacing edited fields and keeping original ones.

        Args:
            author_code: Author code (5 letters)
            site_string: Site string (e.g., IDN-Bangka-PA1)
            date: Date string (YYYY-MM-DD)
            time: Time string (HH-MM-SS)
            activity: Activity type
            camera: Camera abbreviation (e.g., 'S-A7IV')
            filename: Original filename part
            extension: File extension

        Returns:
            Complete filename with extension
        """
        return f"{author_code}_{site_string}_{date}_{time}_{activity}_{camera}_{filename}{extension}"
