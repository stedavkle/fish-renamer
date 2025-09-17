# web_updater.py
import requests
import re
import os
from pathlib import Path
import time
import json
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class network_request_is_made(object):
    """
    A custom WebDriverWait condition that checks the browser's performance logs
    to see if a network request containing a specific substring has been made.
    """
    def __init__(self, url_substring):
        self.url_substring = url_substring
        self.found_url = None

    def __call__(self, driver):
        try:
            logs = driver.get_log("performance")
            for entry in logs:
                log = json.loads(entry["message"])["message"]
                if (
                    "Network.requestWillBeSent" in log["method"]
                    and "request" in log["params"]
                    and self.url_substring in log["params"]["request"]["url"]
                ):
                    self.found_url = log["params"]["request"]["url"]
                    return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False

class WebUpdater:
    """Handles fetching file lists and downloading updates from a remote server."""
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.ACCESS_TOKEN = ''
        self.PID = 'b1443699372.553636'
        self.HI_DRIVE_URL = "https://my.hidrive.com/share/5l-bcdzb6v"
        self.list_dir_url = f'https://my.hidrive.com/api/dir?pid={self.PID}&access_token={self.ACCESS_TOKEN}'
    
    def get_hidrive_access_token(self, share_url, callback=None):
        """
        Navigates to a HiDrive share URL, clicks the 'Download all' button,
        and captures the resulting network request to extract the access_token.
        This version is hyper-optimized for speed and compatible with Selenium 4+.

        Args:
            share_url (str): The public URL to the HiDrive shared folder.

        Returns:
            str: The extracted access token, or None if not found.
        """
        access_token = None
        
        # --- HYPER-OPTIMIZATIONS ---
        options = webdriver.ChromeOptions()
        # Essential for speed
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.page_load_strategy = 'none'
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-features=Translate")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-dns-prefetch")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        driver = None 
        try:
            callback("Initializing...")
            driver = webdriver.Chrome(options=options)
            
            callback(f"Navigating...")
            driver.get(share_url)
            wait = WebDriverWait(driver, 15)
            
            callback("Waiting...")
            download_button_selector = "button[data-qa='menubar_download_all']"
            download_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, download_button_selector))
            )
            wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, download_button_selector))
            )
            callback("Clicking it...")
            download_button.click()
            callback("Waiting...")
            target_substring = "api/file/archive/download"
            request_wait = WebDriverWait(driver, 10, poll_frequency=0.05)
            request_condition = network_request_is_made(target_substring)
            request_wait.until(request_condition)
            download_url = request_condition.found_url
            callback(f"Found URL...")
            parsed_url = urlparse(download_url)
            query_params = parse_qs(parsed_url.query)
            if 'access_token' in query_params:
                callback("Access token extracted.")
                access_token = query_params['access_token'][0]

        except Exception as e:
            callback(f"Error: {e}")
            if driver:
                driver.save_screenshot("hidrive_error.png")
                print("Saved a screenshot to 'hidrive_error.png' for debugging.")
        finally:
            if driver:
                driver.quit()
                print("Browser closed.")
        return access_token
    
    def connect(self, callback=None):
        """Connects to the HiDrive service and retrieves the access token."""
        self.access_token = self.get_hidrive_access_token(self.HI_DRIVE_URL, callback)
        if not self.access_token:
            raise ValueError("Failed to retrieve access token from HiDrive.")
        self.list_dir_url = f'https://my.hidrive.com/api/dir?pid={self.PID}&access_token={self.access_token}'
        if callback:
            callback("Connected")

    def get_download_url(self, filename: str) -> str:
        return f'https://my.hidrive.com/api/file?pid={self.PID}&path={filename}&access_token={self.access_token}'

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

    def run_update(self, file_list, configs):
        print("file_list:", file_list)
        print("configs:", configs)
        """The main update logic, refactored from the original class."""
        update_statuses = {}
        newest_files = {}
        for prefix, config in configs.items():
            print(f"Processing {prefix}...")
            print("config:", config)
            prefix_files = [f.replace('%20', ' ') for f in file_list if f.startswith(prefix)]
            print(f"Found {len(prefix_files)} files for prefix {prefix}: {prefix_files}")
            newest_file = self._get_newest_file(prefix_files)
            print(f"Newest file for {prefix}: {newest_file}")
            if newest_file:
                path_str = config['path_var']
                old_filepath = Path(path_str) if path_str else None
                should_update, reason = self._check_if_update_needed(config, newest_file, old_filepath)
                print(f"Should update: {should_update}, Reason: {reason}")
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
        print(f"Checking if update is needed for {old_filepath}")
        if not config['requires_date_check']:
            print(f"Skipping date check for {cleaned_file_name}")
            return True, "Update required"
        new_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cleaned_file_name)
        if not new_date_match:
            print(f"Malformed remote filename: {cleaned_file_name}")
            return False, "Malformed remote filename"
        new_date_str = new_date_match.group(1)

        if not old_filepath or not old_filepath.exists():
            print(f"No local file found for {cleaned_file_name}")
            return True, "No local file"
        
        local_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', old_filepath.name)
        if not local_date_match:
            print(f"Malformed local file: {old_filepath.name}")
            return True, "Malformed local file"
        
        print(f"Comparing dates: {new_date_str} vs {local_date_match.group(1)}")
        if new_date_str > local_date_match.group(1):
            print("Remote file is newer.")
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