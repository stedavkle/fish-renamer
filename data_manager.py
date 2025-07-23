# data_manager.py
import pandas as pd

class DataManager:
    """Loads and manages all application data from CSV files."""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.fish_df = pd.DataFrame()
        self.users_df = pd.DataFrame()
        self.divesites_df = pd.DataFrame()
        self.activities_df = pd.DataFrame()
        self.family_default = '0-Fam'
        self.genus_default = 'genus'
        self.species_default = 'spec'

    def load_all_data(self):
        """Loads all CSVs into pandas DataFrames based on paths from config."""
        load_map = {
            'species': ('fish_df', 'Loaded species data'),
            'photographers': ('users_df', 'Loaded photographers'),
            'divesites': ('divesites_df', 'Loaded divesites'),
            'activities': ('activities_df', 'Loaded activities'),
        }
        messages = []
        for key, (df_attr, msg) in load_map.items():
            try:
                path = self.config_manager.get_path(key)
                if path.exists():
                    df = pd.read_csv(path, sep=';').fillna('')
                    setattr(self, df_attr, df)
                    messages.append(f"{msg} from {path.name}")
                else:
                    messages.append(f"Warning: {key} file not found at {path}")
            except Exception as e:
                messages.append(f"Error loading {key} data: {e}")
        return "\n".join(messages)

    def get_all_fish(self):
        if self.fish_df.empty:
            return self.fish_df
        return self.fish_df.sort_values(by=['Family', 'Genus', 'Species'])

    def get_unique_values(self, column, df_attr='fish_df'):
        df = getattr(self, df_attr)
        if not df.empty and column in df.columns:
            return sorted(df[column].unique())
        return []

    def filter_fish(self, by_col, value):
        return self.fish_df[self.fish_df[by_col] == value]
    
    def get_divesite_area_site(self, site_string):
        if self.divesites_df.empty: return None, None
        result = self.divesites_df[self.divesites_df['Site string'] == site_string]
        if not result.empty:
            return result['Area'].values[0] + ', ' + result['Site'].values[0]
        return None, None
        
    def get_divesite_string(self, area, site):
        if self.divesites_df.empty: return ""
        result = self.divesites_df[
            (self.divesites_df['Area'] == area) & 
            (self.divesites_df['Site'] == site)
        ]
        return result['Site string'].values[0] if not result.empty else ""

    def get_user_code(self, full_name):
        if self.users_df.empty: return ""
        result = self.users_df[self.users_df['Full name'] == full_name]
        return result['Namecode'].values[0] if not result.empty else ""
    
    def get_user_name(self, code):
        if self.users_df.empty: return ""
        result = self.users_df[self.users_df['Namecode'] == code]
        return result['Full name'].values[0] if not result.empty else ""
    
    def get_formatted_site_list(self):
        """Returns a sorted list of sites formatted as 'Area, Site'."""
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
    
    def get_lat_long_from_site(self, site_string):
        """Returns the latitude and longitude for a given site string."""
        location, site = site_string.split(", ")
        coordinates = self.divesites_df[
            (self.divesites_df['Area'] == location) & 
            (self.divesites_df['Site'] == site)
        ][['latitude', 'longitude']].values[0]
        return coordinates if len(coordinates) == 2 else (None, None)