# data_manager.py
import json
import pandas as pd
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
        self.fish_df_raw = pd.DataFrame()
        self.divesites_df_raw = pd.DataFrame()

        self.fish_df = pd.DataFrame()
        self.users_df = pd.DataFrame()
        self.divesites_df = pd.DataFrame()
        self.activities_df = pd.DataFrame()
        self.labels = {}
        self.colour_reverse = {}
        self.behaviour_reverse = {}

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
        """Loads all CSVs into pandas DataFrames based on paths from config.

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
                        data = pd.read_csv(path, sep=';').fillna('')
                    setattr(self, attr, data)

                    messages.append(f"{msg} from {path.name}")
                else:
                    messages.append(f"Warning: {key} file not found at {path}")
            except Exception as e:
                messages.append(f"Error loading {key} data: {e}")
        self.filter_by_location()
        return "\n".join(messages)

    def filter_by_location(self, location: str = '') -> None:
        """Filter species and divesites data by location.

        Args:
            location: Location name to filter by (e.g., 'Bangka', 'Red Sea')
        """
        if location != '':
            self.location = location

        filter_map = {
            'species': ('fish_df_raw', 'fish_df', ["Family", "Genus", "Species", "Species English"]),
            'divesites': ('divesites_df_raw', 'divesites_df', ["Area", "Site", "Site string", "latitude", "longitude"]),
        }
        for key, (df_attr_raw, df_attr_loc, columns) in filter_map.items():
            df_raw = getattr(self, df_attr_raw)
            if self.location != '' and self.location in df_raw.columns:
                df = df_raw[df_raw[self.location] == 1]
                setattr(self, df_attr_loc, df[columns])
            else:
                setattr(self, df_attr_loc, df_raw[columns])
            
    def get_all_fish(self) -> pd.DataFrame:
        """Get all fish data sorted by taxonomy.

        Returns:
            DataFrame sorted by Family, Genus, Species
        """
        if self.fish_df.empty:
            return self.fish_df
        return self.fish_df.sort_values(by=['Family', 'Genus', 'Species'])

    def get_unique_values(self, column: str, df_attr: str = 'fish_df') -> List[str]:
        """Get unique values from a DataFrame column.

        Args:
            column: Column name to extract values from
            df_attr: DataFrame attribute name (default: 'fish_df')

        Returns:
            Sorted list of unique values
        """
        df = getattr(self, df_attr)
        if not df.empty and column in df.columns:
            return sorted(df[column].unique())
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

    def filter_fish(self, by_col: str, value: str) -> pd.DataFrame:
        """Filter fish DataFrame by column value.

        Args:
            by_col: Column name to filter by
            value: Value to match

        Returns:
            Filtered DataFrame
        """
        return self.fish_df[self.fish_df[by_col] == value]

    def search_fish(self, search_string: str) -> pd.DataFrame:
        """Search fish data by multiple keywords.

        Searches across all columns and returns rows where ALL search terms
        are found (in any column).

        Args:
            search_string: Space-separated search terms

        Returns:
            Filtered DataFrame with matching rows
        """
        if not search_string:
            return self.get_all_fish()

        search_substrings = search_string.lower().split()

        if self.fish_df.empty:
            return self.fish_df

        # For each row, check if all search terms appear somewhere in that row
        mask = self.fish_df.apply(
            lambda row: all([
                any([substring in str(value).lower() for value in row.values])
                for substring in search_substrings
            ]),
            axis=1
        )

        return self.fish_df[mask]
    
    def get_divesite_area_site(self, site_string: str) -> Optional[str]:
        """Get formatted 'Area, Site' from site string.

        Args:
            site_string: Site identifier code

        Returns:
            Formatted 'Area, Site' string, or None if not found
        """
        if self.divesites_df.empty or not site_string:
            return None

        try:
            result = self.divesites_df[self.divesites_df['Site string'] == site_string]
            if not result.empty:
                area = result['Area'].values[0]
                site = result['Site'].values[0]
                return f"{area}, {site}"
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
        if self.divesites_df.empty or not area or not site:
            return ""

        try:
            result = self.divesites_df[
                (self.divesites_df['Area'] == area) &
                (self.divesites_df['Site'] == site)
            ]
            if not result.empty:
                return str(result['Site string'].values[0])
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
        if self.users_df.empty or not full_name:
            return ""

        try:
            result = self.users_df[self.users_df['Full name'] == full_name]
            if not result.empty:
                return str(result['Namecode'].values[0])
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
        if self.users_df.empty or not code:
            return ""

        try:
            result = self.users_df[self.users_df['Namecode'] == code]
            if not result.empty:
                return str(result['Full name'].values[0])
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving user name for code '{code}': {e}")

        return ""
    
    def get_formatted_site_list(self) -> List[str]:
        """Returns a sorted list of sites formatted as 'Area, Site'.

        Returns:
            List of formatted site strings
        """
        if self.divesites_df.empty:
            return []

        # Sort the DataFrame by Area and then by Site
        sorted_df = self.divesites_df.sort_values(by=['Area', 'Site'])

        # The .apply() call creates a pandas Series.
        # The .tolist() method on that Series converts it to a Python list.
        site_series = sorted_df.apply(
            lambda row: f"{row['Area']}, {row['Site']}", axis=1
        )
        return site_series.tolist()
    
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

            if self.divesites_df.empty:
                return (None, None)

            result = self.divesites_df[
                (self.divesites_df['Area'] == location) &
                (self.divesites_df['Site'] == site)
            ]

            if result.empty:
                logger.warning(f"No coordinates found for site: '{site_string}'")
                return (None, None)

            coords = result[['latitude', 'longitude']].values[0]
            if len(coords) == 2:
                return (float(coords[0]), float(coords[1]))
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Error extracting coordinates for '{site_string}': {e}")

        return (None, None)