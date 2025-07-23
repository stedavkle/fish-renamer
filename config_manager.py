# config_manager.py
import configparser
from pathlib import Path
import app_utils

class ConfigManager:
    """Manages reading and writing application settings to config.ini."""
    def __init__(self):
        self.data_dir = app_utils.get_data_path()
        self.config_path = self.data_dir / "config.ini"
        self.config = configparser.ConfigParser()
        self.user_prefs = {}
        self.paths = {}
        self.load()

    def load(self):
        """Loads configuration from the INI file or sets defaults."""
        if not self.config_path.exists():
            self._set_defaults()
            return

        self.config.read(self.config_path)
        self.user_prefs = dict(self.config.items('USER_PREFS'))
        self.paths = dict(self.config.items('PATHS'))
        
        # Ensure essential paths have defaults if missing
        if not self.paths:
            self._set_default_paths()


    def save(self):
        """Saves the current configuration to the INI file."""
        self.config['USER_PREFS'] = self.user_prefs
        self.config['PATHS'] = self.paths
        try:
            with self.config_path.open('w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Error saving preferences: {e}")
            
    def get_path(self, key):
        return self.data_dir / self.paths.get(key, "")

    def set_path(self, key, value: Path):
        self.paths[key] = value.name # Store only the filename

    def get_user_pref(self, key, fallback=''):
        return self.user_prefs.get(key, fallback)
    
    def set_user_pref(self, key, value):
        self.user_prefs[key] = value

    def _set_defaults(self):
        """Sets default values for a fresh configuration."""
        self.user_prefs = {'author': '', 'site': '', 'activity': ''}
        self._set_default_paths()
        self.save()
        
    def _set_default_paths(self):
        self.paths = {
            'species': "Species_Bangka 2025-04-15.csv",
            'photographers': "Photographers_all 2025-04-15.csv",
            'divesites': "Divesites_Bangka 2025-04-15.csv",
            'activities': "Activities.csv"
        }