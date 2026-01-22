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

# Basic filename pattern: AuthorCode_SiteString_Date_Time_Activity_Camera_OriginalName
# Example: ABCDE_ABC-Location-123_2024-01-15_14-30-45_diving_S-A7IV_IMG001.JPG
PATTERN_BASIC_FILENAME = re.compile(
    r'^[A-Za-z]{5}_'                    # Author code (5 letters)
    r'[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_'  # Site string
    r'\d{4}-\d{2}-\d{2}_'               # Date (YYYY-MM-DD)
    r'\d{2}-\d{2}-\d{2}_'               # Time (HH-MM-SS)
    r'[A-Za-z]+_'                       # Activity
    r'[A-Z]-[A-Za-z0-9]+_'              # Camera (REQUIRED: uppercase-alphanumeric)
    r'[A-Za-z0-9]+'                     # Original filename
    r'(?:_G)?$'                         # Optional _G suffix
)

# Identity filename pattern: Full taxonomy + basic fields
# Example: Pomacentridae_Amphiprion_clarkii_B_ok_ad_ty_zz_ABCDE_ABC-Location-123_2024-01-15_14-30-45_diving_S-A7IV_IMG001
PATTERN_IDENTITY_FILENAME = re.compile(
    r'(0?\-?[A-Za-z]*)_'                       # Family (group 1)
    r'([A-Za-z]+)_'                            # Genus (group 2)
    r'([a-z]+)_'                               # Species (group 3)
    r'[A-Z]_'                                  # Separator 'B'
    r'([a-z]{2})_'                             # Confidence (group 4)
    r'([A-Za-z]+)_'                            # Phase (group 5)
    r'([A-Za-z\-]+)_'                          # Colour (group 6)
    r'([A-Za-z\-]+)_'                          # Behaviour (group 7)
    r'([A-Za-z]{5})_'                          # Author code (group 8)
    r'([A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3})_'       # Site string (group 9)
    r'(\d{4}-\d{2}-\d{2})_'                    # Date (group 10)
    r'(\d{2}-\d{2}-\d{2})_'                    # Time (group 11)
    r'([A-Za-z]+)_'                            # Activity (group 12)
    r'([A-Z]-[A-Za-z0-9]+)_'                   # Camera (group 13, REQUIRED)
    r'(.*?)'                                   # Original name (group 14)
    r'(?:_G)?$'                                # Optional _G suffix (non-capturing)
)

# Pattern to extract base name from identity filename
PATTERN_BASIC_BASENAME = re.compile(
    r'([A-Za-z]{5}_.*?_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_.*)'
)

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
DEFAULT_SPECIES_FILE = "Species_Indopacific 2025-04-15.csv"
DEFAULT_PHOTOGRAPHERS_FILE = "Photographers_all 2025-04-15.csv"
DEFAULT_DIVESITES_FILE = "Divesites_Indopacific 2025-04-15.csv"
DEFAULT_ACTIVITIES_FILE = "Activities.csv"
DEFAULT_LABELS_FILE = "Labels 2025-04-15.json"
