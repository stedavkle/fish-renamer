# constants.py
"""Application-wide constants and configuration."""

import re

# ==============================================================================
# EXIF Tags
# ==============================================================================
EXIF_TAG_DATETIME_ORIGINAL = 36867  # DateTimeOriginal - when photo was taken
EXIF_TAG_DATETIME = 306  # DateTime - when file was modified

# ==============================================================================
# Default Values for Taxonomy and Attributes
# ==============================================================================
DEFAULT_FAMILY = '0-Fam'
DEFAULT_GENUS = 'genus'
DEFAULT_SPECIES = 'spec'
DEFAULT_CONFIDENCE = 'uncertain'
DEFAULT_PHASE = 'adult'
DEFAULT_COLOUR = 'typical colour'
DEFAULT_BEHAVIOUR = 'not specified'

# ==============================================================================
# Tree Column Names
# ==============================================================================
TREE_COLUMNS = ['Family', 'Genus', 'Species', 'Species English']

# ==============================================================================
# Filename Regex Patterns (compiled for performance)
# ==============================================================================

# Filenames are parsed by field position (fields are separated by '_'), not by
# checking field contents. Only date and time are validated. See
# filename_assembler.parse_filename().
#
# Basic:    Author_Site_Date_Time_Activity_Camera_Original_N_[free text]
#           ABCDE_IDN-Bangka-HRS_2024-01-15_14-30-45_dive_S-A7IV_IMG001_N_
# Identity: Family_Genus_Species_B_Conf_Phase_Colour_Behaviour_ + Basic
#           Labridae-Sc_Scarus_species3_B_ok_ad_ty_zz_ABCDE_IDN-Bangka-HRS_..._IMG001_G_
# _N_ = no GPS in EXIF yet, _G_ = GPS written. Anything after the marker is
# free user text and is never checked or changed. Legacy names end in a bare
# _N/_G (or have no marker) and are still accepted.
PATTERN_DATE_FIELD = re.compile(r'^\d{4}-\d{2}-\d{2}$')
PATTERN_TIME_FIELD = re.compile(r'^\d{2}-\d{2}-\d{2}$')

# Field positions (0-based) of the date in each format
BASIC_DATE_INDEX = 2
IDENTITY_DATE_INDEX = 10

# Splits the part after the camera field into original name, GPS marker and
# free text: 'IMG001_N_', 'IMG001_G_two fish', legacy 'IMG001_N' / 'IMG001_N copy'
PATTERN_GPS_MARKER = re.compile(r'^(?P<original>.+?)_(?P<gps>[NG])(?:_(?P<tail>.*)|(?P<legacy_tail> .*))?$')

# Pattern to extract datetime from filename
PATTERN_DATETIME_IN_FILENAME = re.compile(
    r'0?\-?[A-Za-z]*_[A-Za-z]+_[a-z]+_[A-Z]_[a-z]{2}_[A-Za-z]+_[A-Za-z\-]+_[A-Za-z\-]+_'
    r'[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_'
    r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_'  # Date-time (group 1)
    r'[A-Za-z]+_'
    r'([A-Za-z0-9]+)'                          # Original name (group 2)
)

# ==============================================================================
# UI Constants
# ==============================================================================
DEFAULT_PHOTOGRAPHER_TEXT = 'Select Photographer'
DEFAULT_SITE_TEXT = 'Select site'
DEFAULT_ACTIVITY_TEXT = 'Select activity'
DEFAULT_LOCATION_TEXT = 'Select location'

# Window titles
MAIN_WINDOW_TITLE = "Dave's Fish Renamer"
PREFERENCES_WINDOW_TITLE = "Preferences & Updates"

# Search placeholder
SEARCH_PLACEHOLDER = "Search by family, genus, species, or common name..."

# Status messages
STATUS_READY = "Ready"
STATUS_IDLE = "Status: Idle"

# ==============================================================================
# File Extensions
# ==============================================================================
DATA_FILE_EXTENSIONS = {'.csv', '.json'}
IMAGE_FILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.raw', '.hif'}

# ==============================================================================
# Configuration
# ==============================================================================
CONFIG_FILENAME = 'config.ini'
LOG_FILENAME = 'fish_renamer.log'

# Configuration sections
CONFIG_SECTION_USER_PREFS = 'USER_PREFS'
CONFIG_SECTION_PATHS = 'PATHS'
CONFIG_SECTION_MISC = 'MISC'

# ==============================================================================
# Data File Names (defaults)
# ==============================================================================
DEFAULT_SPECIES_FILE = "Species_Indopacific 2026-02-22.csv"
DEFAULT_PHOTOGRAPHERS_FILE = "Photographers_all 2026-01-26.csv"
DEFAULT_DIVESITES_FILE = "Divesites_Indopacific 2026-02-22.csv"
DEFAULT_ACTIVITIES_FILE = "Activities.csv"
DEFAULT_LABELS_FILE = "Labels 2026-02-22.json"
