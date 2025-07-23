# web_updater.py
import requests
import re
import os
from pathlib import Path

class WebUpdater:
    """Handles fetching file lists and downloading updates from a remote server."""
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.access_token = 'II5JlY9vFxxpJZxEbG57' # Should be in a secure config
        self.pid = 'b1443699372.553636'
        self.list_dir_url = f'https://my.hidrive.com/api/dir?pid={self.pid}&access_token={self.access_token}'

    def get_download_url(self, filename: str) -> str:
        return f'https://my.hidrive.com/api/file?pid={self.pid}&path={filename}&access_token={self.access_token}'

    def fetch_file_list(self):
        """Fetches the list of available files from the server."""
        try:
            response = requests.get(self.list_dir_url)
            response.raise_for_status()
            return [member.get('name') for member in response.json().get('members', [])], "Files fetched successfully"
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

    def run_update(self, file_list, configs, current_location):
        """The main update logic, refactored from the original class."""
        update_statuses = {}
        for file in file_list:
            cleaned_file_name = file.replace('%20', ' ')
            
            for prefix, config in configs.items():
                if not cleaned_file_name.startswith(prefix):
                    continue

                old_filepath = None
                if config['is_location_specific']:
                    if current_location not in cleaned_file_name:
                        continue
                    local_files = list(self.data_path.glob(f"{prefix}_{current_location}*.csv"))
                    if local_files: old_filepath = local_files[0]
                else:
                    path_str = config['path_var'].get()
                    if path_str: old_filepath = Path(path_str)

                should_update, reason = self._check_if_update_needed(config, cleaned_file_name, old_filepath)
                
                if should_update:
                    status = self._perform_download(file, cleaned_file_name, old_filepath)
                    update_statuses[prefix] = status
                else:
                    update_statuses[prefix] = reason
                break
        return update_statuses

    def _check_if_update_needed(self, config, cleaned_file_name, old_filepath):
        if not config['requires_date_check']:
            return True, "Update required"
        
        new_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cleaned_file_name)
        if not new_date_match:
            return False, "Malformed remote filename"
        new_date_str = new_date_match.group(1)

        if not old_filepath or not old_filepath.exists():
            return True, "No local file"
        
        local_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', old_filepath.name)
        if not local_date_match:
            return True, "Malformed local file"
        
        if new_date_str > local_date_match.group(1):
            return True, "Remote is newer"
        
        return False, "up-to-date"

    def _perform_download(self, remote_file, cleaned_filename, old_filepath):
        new_filepath = self.data_path / cleaned_filename
        url = self.get_download_url(remote_file)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(new_filepath, 'wb') as f:
                f.write(response.content)
            
            if old_filepath and old_filepath.exists() and old_filepath != new_filepath:
                os.remove(old_filepath)
            return "updated"
        except requests.exceptions.RequestException:
            return "Error"