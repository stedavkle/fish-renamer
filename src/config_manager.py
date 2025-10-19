# config_manager.py
import configparser
import logging
from pathlib import Path
from typing import Dict, Union
from src import app_utils
from src.constants import (
    CONFIG_FILENAME,
    CONFIG_SECTION_USER_PREFS,
    CONFIG_SECTION_PATHS,
    CONFIG_SECTION_MISC,
    DEFAULT_SPECIES_FILE,
    DEFAULT_PHOTOGRAPHERS_FILE,
    DEFAULT_DIVESITES_FILE,
    DEFAULT_ACTIVITIES_FILE,
    DEFAULT_LABELS_FILE
)

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages reading and writing application settings to config.ini."""

    def __init__(self):
        self.data_dir: Path = app_utils.get_data_path()
        self.config_path: Path = self.data_dir / CONFIG_FILENAME
        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.user_prefs: Dict[str, str] = {}
        self.paths: Dict[str, str] = {}
        self.misc: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """Loads configuration from the INI file or sets defaults."""
        if not self.config_path.exists():
            self._set_defaults()
            return

        self.config.read(self.config_path)
        self.user_prefs = dict(self.config.items(CONFIG_SECTION_USER_PREFS))
        self.paths = dict(self.config.items(CONFIG_SECTION_PATHS))
        self.misc = dict(self.config.items(CONFIG_SECTION_MISC))
        
        # Ensure essential paths have defaults if missing
        if not self.paths:
            self._set_default_paths()


    def save(self) -> None:
        """Saves the current configuration to the INI file."""
        self.config[CONFIG_SECTION_USER_PREFS] = self.user_prefs
        self.config[CONFIG_SECTION_PATHS] = self.paths
        self.config[CONFIG_SECTION_MISC] = self.misc
        try:
            with self.config_path.open('w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            
    def get_path(self, key: str) -> Path:
        """Get full path for a configuration key.

        Args:
            key: Configuration key name

        Returns:
            Full path to the file
        """
        return self.data_dir / self.paths.get(key, "")

    def set_path(self, key: str, value: Union[str, Path]) -> None:
        """Set a path in configuration.

        Args:
            key: Configuration key name
            value: Path or filename to store
        """
        logger.debug(f"Setting path for {key} to {value}")
        self.paths[key] = str(value) if isinstance(value, Path) else value
        self.save()

    def get_user_pref(self, key: str, fallback: str = '') -> str:
        """Get user preference value.

        Args:
            key: Preference key name
            fallback: Default value if not found

        Returns:
            Preference value or fallback
        """
        user = self.user_prefs.get(key, fallback)
        return user if user != '' else fallback

    def set_user_pref(self, key: str, value: str) -> None:
        """Set user preference value.

        Args:
            key: Preference key name
            value: Value to store
        """
        self.user_prefs[key] = value
        self.save()

    def get_misc(self, key: str, fallback: str = '') -> str:
        """Get miscellaneous configuration value.

        Args:
            key: Configuration key
            fallback: Default value if not found

        Returns:
            Configuration value or fallback
        """
        return self.misc.get(key, fallback)

    def set_misc(self, key: str, value: str) -> None:
        """Sets a miscellaneous configuration value.

        Args:
            key: Configuration key
            value: Value to store
        """
        self.misc[key] = value
        self.save()

    def _set_defaults(self) -> None:
        """Sets default values for a fresh configuration."""
        self.user_prefs = {'author': '', 'site': '', 'activity': ''}
        self._set_default_paths()
        self.save()

    def _set_default_paths(self) -> None:
        """Set default file paths using constants."""
        self.paths = {
            'species': DEFAULT_SPECIES_FILE,
            'photographers': DEFAULT_PHOTOGRAPHERS_FILE,
            'divesites': DEFAULT_DIVESITES_FILE,
            'activities': DEFAULT_ACTIVITIES_FILE,
            'labels': DEFAULT_LABELS_FILE
        }
        self.save()