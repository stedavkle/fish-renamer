# data_manager.py
import csv
import json
import logging
from typing import Optional, List, Tuple
from .constants import (
    DEFAULT_FAMILY, DEFAULT_GENUS, DEFAULT_SPECIES,
    DEFAULT_CONFIDENCE, DEFAULT_PHASE, DEFAULT_COLOUR, DEFAULT_BEHAVIOUR
)

logger = logging.getLogger(__name__)

class DataManager:
    """Loads and manages all application data from CSV files."""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.fish_df_raw = []
        self.divesites_df_raw = []

        self.fish_df = []
        self.users_df = []
        self.divesites_df = []
        self.activities_df = []
        self.labels = {}
        self.colour_reverse = {}
        self.behaviour_reverse = {}

        self._fish_columns = ['Family', 'Genus', 'Species', 'Species English']

        # Use constants for default values
        self.family_default = DEFAULT_FAMILY
        self.genus_default = DEFAULT_GENUS
        self.species_default = DEFAULT_SPECIES
        self.confidence_default = DEFAULT_CONFIDENCE
        self.phase_default = DEFAULT_PHASE
        self.colour_default = DEFAULT_COLOUR
        self.behaviour_default = DEFAULT_BEHAVIOUR
        self.location = self.config_manager.get_misc('location', '')

    def load_all_data(self) -> str:
        """Loads all CSVs into list-of-dicts based on paths from config.

        Returns:
            Status message string describing what was loaded
        """
        load_map = {
            'species': ('fish_df_raw', 'Loaded species data'),
            'photographers': ('users_df', 'Loaded photographers'),
            'divesites': ('divesites_df_raw', 'Loaded divesites'),
            'activities': ('activities_df', 'Loaded activities'),
            'labels': ('labels', 'Loaded labels'),
        }
        messages = []
        for key, (attr, msg) in load_map.items():
            try:
                path = self.config_manager.get_path(key)
                if path.exists():
                    if key == 'labels':
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        with open(path, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f, delimiter=';')
                            data = [{k: (v or '') for k, v in row.items()} for row in reader]
                    setattr(self, attr, data)

                    messages.append(f"{msg} from {path.name}")
                else:
                    messages.append(f"Warning: {key} file not found at {path}")
            except Exception as e:
                messages.append(f"Error loading {key} data: {e}")
        self.filter_by_location()
        return "\n".join(messages)

    def get_available_locations(self) -> List[str]:
        """Get list of available location columns from species data.

        Returns:
            List of location names from CSV columns (e.g., ['Bangka', 'Red Sea', 'All'])
        """
        standard_columns = {'Family', 'Genus', 'Species', 'Species English'}

        if not self.fish_df_raw:
            return []

        locations = [col for col in self.fish_df_raw[0].keys() if col not in standard_columns]
        return locations

    def filter_by_location(self, location: str = '') -> None:
        """Filter species and divesites data by location.

        Args:
            location: Location name to filter by (e.g., 'Bangka', 'Red Sea')
        """
        self.location = location

        filter_map = {
            'species': ('fish_df_raw', 'fish_df', ["Family", "Genus", "Species", "Species English"]),
            'divesites': ('divesites_df_raw', 'divesites_df', ["Area", "Site", "Site string", "latitude", "longitude"]),
        }
        for key, (df_attr_raw, df_attr_loc, columns) in filter_map.items():
            raw_rows = getattr(self, df_attr_raw)
            if self.location != '' and raw_rows and self.location in raw_rows[0]:
                rows = [row for row in raw_rows if row.get(self.location) == '1']
                filtered = [{col: row[col] for col in columns} for row in rows]
            else:
                filtered = [{col: row[col] for col in columns} for row in raw_rows]
            setattr(self, df_attr_loc, filtered)

    def get_all_fish(self) -> List[list]:
        """Get all fish data sorted by taxonomy.

        Returns:
            List of lists sorted by Family, Genus, Species
        """
        if not self.fish_df:
            return []
        sorted_rows = sorted(self.fish_df, key=lambda r: (r['Family'], r['Genus'], r['Species']))
        return [[row[c] for c in self._fish_columns] for row in sorted_rows]

    def get_unique_values(self, column: str, df_attr: str = 'fish_df') -> List[str]:
        """Get unique values from a data column.

        Args:
            column: Column name to extract values from
            df_attr: Data attribute name (default: 'fish_df')

        Returns:
            Sorted list of unique values
        """
        data = getattr(self, df_attr)
        if data and column in data[0]:
            return sorted(set(row[column] for row in data))
        return []

    def get_abbreviation_reverse(self, category: str, label: str) -> str:
        """Get the abbreviation for a label in a category.

        Args:
            category: Category name (e.g., 'Colour', 'Behaviour')
            label: Full label name

        Returns:
            Abbreviated label, or empty string if not found
        """
        category_dict = self.labels.get(category, {})
        reverse_dict = {v: k for k, v in category_dict.items()}
        return reverse_dict.get(label, '')

    def get_active_label_abbrevs(self, category: str) -> List[str]:
        """Get list of active label keys for a category.

        Args:
            category: Category name (e.g., 'Confidence', 'Phase')

        Returns:
            List of label abbreviations
        """
        return list(self.labels.get(category, {}).keys())

    def get_active_labels(self, category: str) -> List[str]:
        """Get list of active label keys for a category.

        Args:
            category: Category name (e.g., 'Confidence', 'Phase')

        Returns:
            List of label abbreviations
        """
        return list(self.labels.get(category, {}).values())

    def filter_fish(self, filters: dict[str, str] = None) -> list[dict]:
        """Filter fish data by multiple column values.

        Args:
            filters: Dictionary of {column_name: value} pairs to filter by

        Returns:
            Filtered list of dicts matching all filter conditions
        """
        if not filters:
            return self.fish_df

        return [row for row in self.fish_df if all(row.get(col) == val for col, val in filters.items())]

    def search_fish(self, search_string: str) -> List[list]:
        """Search fish data by multiple keywords.

        Searches across all columns and returns rows where ALL search terms
        are found (in any column).

        Args:
            search_string: Space-separated search terms

        Returns:
            List of lists with matching rows
        """
        if not search_string:
            return self.get_all_fish()

        search_substrings = search_string.lower().split()

        if not self.fish_df:
            return []

        matched = [row for row in self.fish_df if all(
            any(sub in str(v).lower() for v in row.values())
            for sub in search_substrings
        )]

        sorted_rows = sorted(matched, key=lambda r: (r['Family'], r['Genus'], r['Species']))
        return [[row[c] for c in self._fish_columns] for row in sorted_rows]

    @staticmethod
    def to_values(rows):
        """Convert list-of-dicts to list-of-lists for fill_tree()."""
        if not rows:
            return []
        columns = ['Family', 'Genus', 'Species', 'Species English']
        return [[row[c] for c in columns] for row in rows]

    @staticmethod
    def unique_column(rows, column):
        """Get sorted unique values from a column in list-of-dicts."""
        return sorted(set(row[column] for row in rows))

    def get_divesite_area_site(self, site_string: str) -> Optional[str]:
        """Get formatted 'Area, Site' from site string.

        Args:
            site_string: Site identifier code

        Returns:
            Formatted 'Area, Site' string, or None if not found
        """
        if not self.divesites_df or not site_string:
            return None

        try:
            result = next((row for row in self.divesites_df if row['Site string'] == site_string), None)
            if result:
                return f"{result['Area']}, {result['Site']}"
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving site for '{site_string}': {e}")

        return None

    def get_divesite_string(self, area: str, site: str) -> str:
        """Get site string identifier from area and site names.

        Args:
            area: Geographic area name
            site: Specific dive site name

        Returns:
            Site string identifier, or empty string if not found
        """
        if not self.divesites_df or not area or not site:
            return ""

        try:
            result = next((row for row in self.divesites_df if row['Area'] == area and row['Site'] == site), None)
            if result:
                return str(result['Site string'])
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving site string for '{area}, {site}': {e}")

        return ""

    def get_user_code(self, full_name: str) -> str:
        """Get user code from full name.

        Args:
            full_name: Photographer's full name

        Returns:
            User code, or empty string if not found
        """
        if not self.users_df or not full_name:
            return ""

        try:
            result = next((row for row in self.users_df if row['Full name'] == full_name), None)
            if result:
                return str(result['Namecode'])
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving user code for '{full_name}': {e}")

        return ""

    def get_user_name(self, code: str) -> str:
        """Get full name from user code.

        Args:
            code: User/photographer code

        Returns:
            Full name, or empty string if not found
        """
        if not self.users_df or not code:
            return ""

        try:
            result = next((row for row in self.users_df if row['Namecode'] == code), None)
            if result:
                return str(result['Full name'])
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving user name for code '{code}': {e}")

        return ""

    def get_formatted_site_list(self) -> List[str]:
        """Returns a sorted list of sites formatted as 'Area, Site'.

        Returns:
            List of formatted site strings
        """
        if not self.divesites_df:
            return []

        sorted_rows = sorted(self.divesites_df, key=lambda r: (r['Area'], r['Site']))
        return [f"{r['Area']}, {r['Site']}" for r in sorted_rows]

    def get_lat_long_from_site(self, site_string: str) -> Tuple[Optional[float], Optional[float]]:
        """Returns the latitude and longitude for a given site string.

        Args:
            site_string: Site formatted as 'Area, Site'

        Returns:
            Tuple of (latitude, longitude) or (None, None) if not found
        """
        if not site_string or ', ' not in site_string:
            logger.warning(f"Invalid site string format: '{site_string}'")
            return (None, None)

        try:
            location, site = site_string.split(", ", 1)

            if not self.divesites_df:
                return (None, None)

            result = next((row for row in self.divesites_df if row['Area'] == location and row['Site'] == site), None)

            if not result:
                logger.warning(f"No coordinates found for site: '{site_string}'")
                return (None, None)

            return (float(result['latitude']), float(result['longitude']))
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Error extracting coordinates for '{site_string}': {e}")

        return (None, None)

    def get_camera_models(self) -> List[str]:
        """Get list of camera full names from labels.

        Returns:
            List of camera full names (e.g., ['Sony A7IV', 'Canon EOS R5'])
        """
        if 'Camera' not in self.labels:
            return []
        return [self.labels['Camera'][abbrev] for abbrev in self.labels['Camera']]

    def get_camera_abbreviations(self) -> List[str]:
        """Get list of camera abbreviations.

        Returns:
            List of camera abbreviations (e.g., ['S-A7IV', 'C-R5'])
        """
        if 'Camera' not in self.labels:
            return []
        return list(self.labels['Camera'].keys())

    def get_camera_abbreviation(self, full_name: str) -> str:
        """Get abbreviation from full camera name.

        Args:
            full_name: Full camera name (e.g., 'Sony A7IV')

        Returns:
            Camera abbreviation (e.g., 'S-A7IV'), or empty string if not found
        """
        if 'Camera' not in self.labels:
            return ''
        for abbrev, name in self.labels['Camera'].items():
            if name == full_name:
                return abbrev
        return ''

    def get_camera_full_name(self, abbrev: str) -> str:
        """Get full name from camera abbreviation.

        Args:
            abbrev: Camera abbreviation (e.g., 'S-A7IV')

        Returns:
            Full camera name (e.g., 'Sony A7IV'), or empty string if not found
        """
        return self.labels.get('Camera', {}).get(abbrev, '')
