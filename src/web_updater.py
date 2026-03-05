# web_updater.py
import requests
import re
import os
from pathlib import Path
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WebUpdater:
    """Handles fetching file lists and downloading updates from a remote server."""

    SHARE_ID = '5l-bcdzb6v'
    PID = 'b1443699372.553636'
    TOKEN_URL = 'https://api.hidrive.strato.com/2.1/share/token'

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.access_token = ''

    def connect(self, callback=None):
        """Connects to the HiDrive service and retrieves the access token."""
        if callback:
            callback("Connecting...")
        try:
            resp = requests.post(
                self.TOKEN_URL,
                data={'id': self.SHARE_ID},
                timeout=15,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self.access_token = token_data['access_token']
        except Exception as e:
            raise ValueError(f"Failed to retrieve access token from HiDrive: {e}")

        self.list_dir_url = (
            f'https://my.hidrive.com/api/dir?pid={self.PID}'
            f'&access_token={self.access_token}'
        )
        if callback:
            callback("Connected")

    def get_download_url(self, filename: str) -> str:
        return (
            f'https://my.hidrive.com/api/file?pid={self.PID}'
            f'&path={quote(filename)}&access_token={self.access_token}'
        )

    def fetch_file_list(self):
        """Fetches the list of available files from the server."""
        try:
            response = requests.get(self.list_dir_url, timeout=15)
            response.raise_for_status()
            return [
                member.get('name')
                for member in response.json().get('members', [])
            ], "Files fetched successfully"
        except requests.RequestException as e:
            return [], f"Error fetching file list: {e}"

    def get_available_locations(self, file_list):
        """Parses a file list to find unique location names."""
        locations = set()
        for file in file_list:
            if file.startswith('Divesites_') or file.startswith('Species_'):
                match = re.search(r'_(.+?)%20\d{4}-\d{2}-\d{2}', file)
                if match:
                    locations.add(match.group(1))
        return sorted(list(locations))

    def run_update(self, file_list, configs):
        """The main update logic, refactored from the original class."""
        logger.debug(f"Running update with {len(file_list)} files")
        logger.debug(f"Configs: {list(configs.keys())}")

        update_statuses = {}
        newest_files = {}
        for prefix, config in configs.items():
            logger.info(f"Processing {prefix}...")
            logger.debug(f"Config for {prefix}: {config}")
            prefix_files = [f.replace('%20', ' ') for f in file_list if f.startswith(prefix)]
            logger.debug(f"Found {len(prefix_files)} files for prefix {prefix}")
            newest_file = self._get_newest_file(prefix_files)
            logger.info(f"Newest file for {prefix}: {newest_file}")
            if newest_file:
                path_str = config['path_var']
                old_filepath = Path(path_str) if path_str else None
                should_update, reason = self._check_if_update_needed(config, newest_file, old_filepath)
                logger.info(f"Update check for {prefix}: {should_update} ({reason})")
                if should_update:
                    status = self._perform_download(newest_file, newest_file, old_filepath)
                    update_statuses[prefix] = status
                else:
                    update_statuses[prefix] = reason
                newest_files[prefix] = newest_file
        return update_statuses, newest_files

    def _get_newest_file(self, files):
        """Returns the file with the most recent date in its name."""
        newest_file = None
        newest_date = None
        date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')

        for file in files:
            match = date_pattern.search(file)
            if match:
                file_date = match.group(1)
                if not newest_date or file_date > newest_date:
                    newest_date = file_date
                    newest_file = file
            else:
                return file

        return newest_file

    def _check_if_update_needed(self, config, cleaned_file_name, old_filepath):
        """Check if a file needs to be updated."""
        logger.debug(f"Checking if update is needed for {old_filepath}")

        if not config['requires_date_check']:
            logger.debug(f"Skipping date check for {cleaned_file_name}")
            return True, "Update required"

        new_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cleaned_file_name)
        if not new_date_match:
            logger.warning(f"Malformed remote filename: {cleaned_file_name}")
            return False, "Malformed remote filename"
        new_date_str = new_date_match.group(1)

        if not old_filepath or not old_filepath.exists():
            logger.info(f"No local file found for {cleaned_file_name}")
            return True, "No local file"

        local_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', old_filepath.name)
        if not local_date_match:
            logger.warning(f"Malformed local file: {old_filepath.name}")
            return True, "Malformed local file"

        logger.debug(f"Comparing dates: {new_date_str} vs {local_date_match.group(1)}")
        if new_date_str > local_date_match.group(1):
            logger.info("Remote file is newer.")
            return True, "Remote is newer"

        return False, "up-to-date"

    def _perform_download(self, remote_file, cleaned_filename, old_filepath):
        new_filepath = self.data_path / cleaned_filename
        url = self.get_download_url(remote_file)
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(new_filepath, 'wb') as f:
                f.write(response.content)

            if old_filepath and old_filepath.exists() and old_filepath != new_filepath:
                os.remove(old_filepath)
            return "updated"
        except requests.exceptions.RequestException:
            return "Error"
