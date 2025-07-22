'''
Here the TreeView widget is configured as a multi-column listbox
with adjustable column width and column-header-click sorting.
'''
import configparser
import tkinter as tk
from tkinter import filedialog
import tkinter.font as tkFont
import tkinter.ttk as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
from PIL import Image, ImageTk
import re
import numpy as np
import requests
import time

# TODO using exifread instead of pyexiv2 because pyexiv2 does not work with pyinstaller
import exifread
#from pyexiv2 import Image as ImgMeta
import sys, os

from pathlib import Path
import shutil

def get_app_path():
    """Get the appropriate path based on whether we're running in a bundle or not"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def get_data_path():
    """Get the writable data directory (different per OS)"""
    if sys.platform == 'win32':
        return Path(os.getenv('APPDATA')) / 'DavesFishRenamer'
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'DaveFishRenamer'
    else:  # Linux/other
        return Path.home() / '.DavesFishRenamer'
    
def initialize_data_files():
    """Copy bundled files to writable location on first run"""
    data_dir = get_data_path()
    data_dir.mkdir(parents=True, exist_ok=True)

    for file in os.listdir(get_app_path() / 'config'):
        if not (data_dir / file).exists():
            shutil.copy(get_app_path() / 'config' / file, data_dir / file)

access_token = '2vf3nQ3LO9MyHEFuHFdF'
pid = 'b1443699372.553636'
list_dir_url = f'https://my.hidrive.com/api/dir?pid={pid}&access_token={access_token}'
def get_filelist():
    response = requests.get(list_dir_url)
    if response.status_code == 200:
        return response.json().get('members', [])
    else:
        print(f"Error fetching file list: {response.status_code}")
        return []
def get_download_url(filename):
    return f'https://my.hidrive.com/api/file?pid={pid}&path={filename}&access_token={access_token}'


class FishRenamer(TkinterDnD.Tk):
    """use a ttk.TreeView as a multicolumn ListBox"""

    tree_columns = ['Family', 'Genus', 'Species', 'Species English']
    family_default = '0-Fam'
    genus_default = 'genus'
    species_default = 'spec'
    confidence = ["ok", "cf"]
    phase = ["ad", "IP", "F", "M", "TP", "juv", "pair", "subad", "trans"]
    colour_dict = {"typical colour": "ty", "aged": "aged", "banded": "band", "barred": "bar", "blotched": "blot", "brown": "brown", "dark": "dark", "dead": "dead", "diseased, deformed": "ill", "inds. w. different colours": "diverg", "white, pale, grey": "light", "lined": "line", "colour mutant": "mutant", "typical spot absent": "no-spot", "typical stripe absent": "no-stripe", "nocturnal": "noct", "nuptial colour": "nupt", "patterned": "pattern", "red": "red", "relaxed colour": "relax", "scarred, deformed": "scar", "speckled": "speck", "spotted": "spot", "striped": "strip", "tailspot": "tailspot", "bicolor": "two-tone", "variation": "vari", "yellow": "yell"} 
    behaviour_dict = {"not specified": "zz", "agitated": "agit", "burried": "bur", "captured": "caught", "being cleaned": "cleaned", "cleaning client": "cleans", "colony": "col", "colour change (pic series)": "col-ch", "compeYng": "comp", "courYng": "court", "D. Act. Photoloc. suggesYve": "DAP", "exposed (e.g. out of sand)": "exp", "feeding": "feed", "fighYng": "fight", "hiding": "hide", "mouth-brooding": "mouth-b", "parenYng, family": "parent", "resYng": "rest", "schooling": "school", "spawning, oviposiYon": "spawn", "interspecific team": "team", "warning": "warn", "yawning": "yawn"}

    def __init__(self):
        super().__init__()
        self.data_dir = get_data_path()
        self.tree = None
        self._setup_widgets()
        self._build_tree()
        initialize_data_files()

        self.fish_csv_path = tk.StringVar()
        self.users_csv_path = tk.StringVar()
        self.divesites_csv_path = tk.StringVar()
        self.activities_csv_path = tk.StringVar()

        self._load_personal_config()
        #self._load_preferences()

        self._load_data()
        
        # Set defaults if no preferences loaded
        

    def _setup_widgets(self):
        self.title("Dave's Fish Renamer")
        self._setup_icon()
        self._setup_dnd()
        main_container = self
        self._configure_main_container_grid(main_container)
        self._create_frames(main_container)
        self._setup_menu()
        self._setup_search_field()
        self._setup_treeview_and_scrollbars()
        self._setup_taxonomy_comboboxes()
        self._setup_edit_frame()
        self._setup_attribute_comboboxes()
        self._setup_info_comboboxes()
        self._setup_google_maps_link()
        self._setup_status_text()

    def _setup_menu(self):
        # Create main menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Create Preferences menu
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=config_menu)
        config_menu.add_command(label="Preferences", command=self._show_preferences)

    def _show_preferences(self):
        # Create preferences window
        self.prefs_window = tk.Toplevel(self)
        self.prefs_window.attributes('-topmost', 'true')
        self.prefs_window.drop_target_register(DND_FILES)
        self.prefs_window.dnd_bind('<<Drop>>', self._update_csv_files_dnd)

        self.prefs_window.title("Preferences")
        self.prefs_window.geometry("500x300")
        
        # Create frame for path settings
        path_frame = ttk.LabelFrame(self.prefs_window, text="Drag&Drop updated CSV files here")
        path_frame.grid(row=0, column=0, padx=10, pady=10, sticky='ew')

        files = [
            ("Species CSV", 'update_species'),
            ("Photographers CSV", 'update_users'),
            ("Divesites CSV", 'update_divesites'),
            ("Activities CSV", 'update_activities')
        ]
        for row, (label_text, var) in enumerate(files):
            ttk.Label(path_frame, text=label_text).grid(row=row, column=0, padx=5, pady=5, sticky='e')
            entry = ttk.Label(path_frame, width=20)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
            #ttk.Button(path_frame, text="Browse...", 
            #       command=lambda var=path_var: self._browse_csv(var)).grid(row=row, column=2, padx=5)
            setattr(self, var, entry)

        # create a button to try update over the web
        update_button = tk.Button(self.prefs_window, text="Fetch update", command=self._update_from_web).grid(row=1, column=0, padx=10, pady=10, sticky='ew')
        # add a label to show the status of the update
        self.update_status = ttk.Label(self.prefs_window, text="Status: Not updated")
        self.update_status.grid(row=1, column=1, padx=30, pady=10, sticky='ew')
        

    def _update_from_web(self):
        # create a dropdown menu for location
        try:
            response = requests.get(list_dir_url)
            if response.status_code == 200:
                filelist = [member.get('name') for member in response.json().get('members', [])]
                self.update_status.config(text="Files fetched successfully")
            else:
                self.update_status.config(text=f"Error {response.status_code}")
                return
        except requests.RequestException as e:
            self.update_status.config(text=f"Error: {str(e)}")
            return

        # Divesites_Bangka%202025-07-22.csv
        locations = set()
        for file in filelist:
            # get the date
            #match = re.search(r'(?:\b(?:Divesites|Species))_([A-Za-z]*)%20(\d{4}-\d{2}-\d{2})', file.get('name', ''))
            filename = file
            if file.startswith('Divesites_') or file.startswith('Species_'):
                match = re.search(r'[A-Za-z\s]+_([A-Za-z\s]+)%20[0-9-]+', file)
                if match:
                    location = match.group(1)
                    locations.add(location)
        
        # create a dropdown menu for location
        self.location_var = tk.StringVar()
        self.location_var.set("Select location")
        location_menu = ttk.OptionMenu(self.prefs_window, self.location_var, "Select location", *sorted(locations))
        location_menu.grid(row=2, column=0, padx=10, pady=10, sticky='ew')

        download_button = tk.Button(self.prefs_window, text="Update files", command=lambda: self._update_csv_files_web(filelist))
        download_button.grid(row=2, column=1, padx=10, pady=10, sticky='ew')

    def _download_file(self, url, filepath):
        """Downloads a file from a URL and saves it to a filepath."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}. Error: {e}")
            return None

    # --- Refactored main function ---
    def _update_csv_files_web(self, filelist):
        """
        Checks for and downloads updated CSV files from the web, using flags
        to control location-specific and date-checking logic.
        """
        print(f"Updating CSV files from web...\nFiles to check: {filelist}")
        data_path = get_data_path()
        current_location = self.location_var.get()

        # Configuration now drives all logic paths
        file_configs = {
            'Activities': {
                'path_var': self.activities_csv_path,
                'ui_element': self.update_activities,
                'is_location_specific': False,
                'requires_date_check': False, # Always update this file
            },
            'Divesites': {
                'path_var': self.divesites_csv_path,
                'ui_element': self.update_divesites,
                'is_location_specific': True,
                'requires_date_check': True,
            },
            'Species': {
                'path_var': self.fish_csv_path,
                'ui_element': self.update_species,
                'is_location_specific': True,
                'requires_date_check': True,
            },
            'Photographers': {
                'path_var': self.users_csv_path,
                'ui_element': self.update_users,
                'is_location_specific': False,
                'requires_date_check': True, # Now correctly checks the date
            }
        }

        for file in filelist:
            cleaned_file_name = file.replace('%20', ' ')
            
            for prefix, config in file_configs.items():
                if not cleaned_file_name.startswith(prefix):
                    continue

                # 1. Determine the local file to compare against (old_filepath)
                old_filepath = None
                if config['is_location_specific']:
                    if current_location not in cleaned_file_name:
                        continue # Not for the selected location
                    # Find local file for the specific location, e.g., "Divesites_Egypt*.csv"
                    local_files = list(data_path.glob(f"{prefix}_{current_location}*.csv"))
                    if local_files:
                        old_filepath = local_files[0]
                else: # Not location-specific
                    if config['path_var'].get():
                        old_filepath = Path(config['path_var'].get())

                # 2. Decide if an update is needed
                should_update = False
                if not config['requires_date_check']:
                    should_update = True # e.g., Activities file
                else:
                    new_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cleaned_file_name)
                    if not new_date_match:
                        continue # Malformed remote filename
                    new_date_str = new_date_match.group(1)

                    if not old_filepath or not old_filepath.exists():
                        # No local file exists, so update
                        should_update = True
                        print(f"No local file for {prefix} found. Downloading.")
                    else:
                        local_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', old_filepath.name)
                        if not local_date_match:
                            should_update = True # Local file malformed, update it
                        elif new_date_str > local_date_match.group(1):
                            should_update = True # Remote file is newer
                        else:
                            config['ui_element'].config(text="up-to-date")
                
                # 3. Perform update if needed
                if should_update:
                    print(f"Updating: {cleaned_file_name}")
                    new_filepath = data_path / cleaned_file_name
                    response = self._download_file(get_download_url(file), new_filepath)

                    if response:
                        # Remove old file only if it existed and we're replacing it
                        if old_filepath and old_filepath.exists() and old_filepath != new_filepath:
                            os.remove(old_filepath)
                        config['path_var'].set(str(new_filepath))
                        config['ui_element'].config(text="updated")
                    else:
                        config['ui_element'].config(text="Error")

                break # Move to next file from web

        self._load_data()
        self._save_personal_config()

    def _update_csv_files_dnd(self, event):
        files = self.splitlist(event.data)
        for file in files:
            if 'Species' in file:
                shutil.copy(file, get_data_path() / file)
                self.update_species.config(text="Species CSV updated")
            elif 'Photographers' in file:
                shutil.copy(file, get_data_path() / file)
                self.update_users.config(text="Photographers CSV updated")
            elif 'Divesites' in file:
                shutil.copy(file, get_data_path() / file)
                self.update_divesites.config(text="Divesites CSV updated")
            elif 'Activities' in file:
                shutil.copy(file, get_data_path() / file)
                self.update_activities.config(text="Activities CSV updated")
        self._load_data()

    def _browse_csv(self, path_var):
        # Add actual file browsing logic here
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filepath:
            path_var.set(filepath)

    def _setup_icon(self):
        ico = Image.open(Path(get_app_path(), 'config', 'icon.png'))
        photo = ImageTk.PhotoImage(ico)
        self.wm_iconphoto(False, photo)

    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._dnd_files)

    def _configure_main_container_grid(self, container):
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=0)
        container.grid_rowconfigure(0, weight=1)

    def _create_frames(self, main_container):
        frames = [
            ('upper_frame', {'row': 0, 'column': 0, 'sticky': 'nsew'}),
            ('upper_right_frame', {'row': 0, 'column': 1, 'sticky': 'nsew'}),
            ('middle_frame', {'row': 1, 'column': 0, 'sticky': 'nsew', 'columnspan': 2}),
            ('bottom_frame', {'row': 2, 'column': 0, 'sticky': 'nsew', 'padx': 10, 'pady': 10, 'columnspan': 2}),
        ]
        for name, grid_args in frames:
            frame = ttk.Frame(main_container)
            frame.grid(**grid_args)
            setattr(self, name, frame)
        # Configure bottom frame columns
        for col in range(3):
            self.bottom_frame.grid_columnconfigure(col, weight=1)

    def _setup_search_field(self):
        self.search_field = ttk.Entry(self.middle_frame)
        self.search_field.pack(fill='x', padx=10, pady=10)
        self.search_field.bind("<Return>", self.search)

    def _setup_treeview_and_scrollbars(self):
        self.tree = ttk.Treeview(self.upper_frame, columns=self.tree_columns, show="headings")
        vsb = ttk.Scrollbar(self.upper_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.upper_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        self.upper_frame.grid_columnconfigure(0, weight=1)
        self.upper_frame.grid_rowconfigure(0, weight=1)
        self.tree.bind("<ButtonRelease-1>", self._row_selected)

    def _setup_taxonomy_comboboxes(self):
        taxonomy_combos = [
            {
                'label': 'Family', 'var': 'cb_family',
                'values': [self.family_default] ,#+ sorted(self.fish_df['Family'].unique()),
                'row': 0, 'col': 0, 'cmd': self.set_family
            },
            {
                'label': 'Genus', 'var': 'cb_genus',
                'values': [self.genus_default],# + sorted(self.fish_df['Genus'].unique()),
                'row': 0, 'col': 1, 'cmd': self.set_genus
            },
            {
                'label': 'Species', 'var': 'cb_species',
                'values': [self.species_default],# + sorted(self.fish_df['Species'].unique()),
                'row': 0, 'col': 2, 'cmd': self.set_species
            }
        ]
        for combo in taxonomy_combos:
            ttk.Label(self.bottom_frame, text=combo['label']).grid(row=combo['row'], column=combo['col'], padx=5, pady=2, sticky='ew')
            cb = ttk.Combobox(self.bottom_frame, values=combo['values'], state='readonly')
            cb.grid(row=combo['row']+1, column=combo['col'], padx=5, pady=2, sticky='ew')
            cb.current(0)
            cb.state(['disabled'])
            cb.bind("<<ComboboxSelected>>", combo['cmd'])
            setattr(self, combo['var'], cb)

    def _setup_edit_frame(self):
        self.edit_frame = ttk.Frame(self.bottom_frame)
        self.edit_frame.grid(row=1, column=3, sticky="nsew")
        
        self.mode = tk.StringVar()
        self.om_mode = tk.OptionMenu(self.edit_frame, self.mode, "Basic", "Identify", "Edit")
        self.om_mode.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        self.mode.set("Basic")
        self.mode.trace_add('write', self._toggle_extended_info)
        
        self.bt_rename = tk.Button(self.edit_frame, text="Rename")
        self.bt_rename.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
        self.bt_rename.grid_remove()
        self.bt_rename.bind("<Button-1>", self._edit_info)

    def _setup_attribute_comboboxes(self):
        attributes = [
            {'label': 'Confidence', 'var': 'cb_confidence', 'values': ["ok", "cf"], 'row': 2, 'col': 0},
            {'label': 'Phase', 'var': 'cb_phase', 'values': ["ad", "IP", "F", "M", "TP", "juv", "pair", "subad", "trans"], 'row': 2, 'col': 1},
            {'label': 'Colour', 'var': 'cb_colour', 'values': list(self.colour_dict.keys()), 'row': 2, 'col': 2},
            {'label': 'Behaviour', 'var': 'cb_behaviour', 'values': list(self.behaviour_dict.keys()), 'row': 2, 'col': 3}
        ]
        for attr in attributes:
            tk.Label(self.bottom_frame, text=attr['label']).grid(row=attr['row'], column=attr['col'], padx=5, pady=2, sticky='ew')
            cb = ttk.Combobox(self.bottom_frame, values=attr['values'], state='readonly')
            cb.grid(row=attr['row']+1, column=attr['col'], padx=5, pady=2, sticky='ew')
            cb.current(0)
            cb.state(['disabled'])
            setattr(self, attr['var'], cb)

    def _setup_info_comboboxes(self):
        info_combos = [
            {
                'label': 'Photographer', 'var': 'cb_author',
                #'values': self.users_df['Full name'].tolist(), 'row': 4, 'col': 0
                'values': ['Anonymous'], 'row': 4, 'col': 0
            },
            {
                'label': 'Site', 'var': 'cb_site',
                #'values': self.divesites_df[['Area', 'Site']].apply(lambda x: ', '.join(x), axis=1).tolist(),
                'values': ['Nowhere'],
                'row': 4, 'col': 1
            },
            {
                'label': 'Activity', 'var': 'cb_activity',
                #'values': self.activities_df['activity'].tolist(), 'row': 4, 'col': 2
                'values': ['Nothing'], 'row': 4, 'col': 2
            }
        ]
        for combo in info_combos:
            ttk.Label(self.bottom_frame, text=combo['label']).grid(row=combo['row'], column=combo['col'], padx=5, pady=2, sticky='ew')
            cb = ttk.Combobox(self.bottom_frame, values=combo['values'], state='readonly')
            cb.grid(row=combo['row']+1, column=combo['col'], padx=5, pady=2, sticky='ew')
            cb.bind("<<ComboboxSelected>>", self._save_personal_config)
            setattr(self, combo['var'], cb)

    def _setup_google_maps_link(self):
        self.link = tk.Label(self.bottom_frame, text="Google Maps", fg="blue", cursor="hand2")
        self.link.grid(row=6, column=1, padx=5, pady=2, sticky='ew')
        self.link.bind("<Button-1>", self._open_googlemaps)

    def _open_googlemaps(self, event):
        location, site = self.cb_site.get().split(", ")
        coordinates = self.divesites_df[
            (self.divesites_df['Area'] == location) & 
            (self.divesites_df['Site'] == site)
        ][['latitude', 'longitude']].values[0]
        os.system(f"start https://maps.google.com/?q={coordinates[0]},{coordinates[1]}")

    def _setup_status_text(self):
        self.status = tk.Text(self.bottom_frame, height=3, width=1, font=("Arial", 8))
        self.status.grid(row=4, column=3, padx=5, pady=2, sticky='ew', rowspan=3)
        self.status.insert(tk.END, "Ready")

    def _reset_info(self):
        self.cb_family.set(self.family_default)
        self.cb_genus.set(self.genus_default)
        self.cb_species.set(self.species_default)
        self.cb_confidence.set("ok")
        self.cb_phase.set("ad")
        self.cb_colour.set("typical colour")
        self.cb_behaviour.set("not specified")

    def _save_personal_config(self, event=None):
        """Save user preferences to INI file"""
        config = configparser.ConfigParser()
        config_path = get_data_path() / "config.ini"
        
        # Preserve existing config if it exists
        if config_path.exists():
            config.read(config_path)
        
        if not config.has_section('USER_PREFS'):
            config.add_section('USER_PREFS')
            
        config.set('USER_PREFS', 'author', self.cb_author.get())
        config.set('USER_PREFS', 'site', self.cb_site.get())
        config.set('USER_PREFS', 'activity', self.cb_activity.get())

        if not config.has_section('PATHS'):
            config.add_section('PATHS')
        config['PATHS'] = {
            'Species': self.fish_csv_path.get(),
            'Photographers': self.users_csv_path.get(),
            'Divesites': self.divesites_csv_path.get(),
            'Activities': self.activities_csv_path.get()
        }
        
        try:
            with open(config_path, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            self.status.insert(tk.END, f"\nError saving preferences: {str(e)}")

    def _load_personal_config(self):
        """Load user preferences from INI file"""
        config_path = get_data_path() / "config.ini"
        
        if not config_path.exists():
            # Set default empty values
            self.cb_author.set('')
            self.cb_site.set('')
            self.cb_activity.set('')
            self.fish_csv_path.set(str(self.data_dir / "Species_Bangka 2025-04-15.csv"))
            self.users_csv_path.set(str(self.data_dir / "Photographers_all 2025-04-15.csv"))
            self.divesites_csv_path.set(str(self.data_dir / "Divesites_Bangka 2025-04-15.csv"))
            self.activities_csv_path.set(str(self.data_dir / "Activities.csv"))
            return

        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Get values with fallback to empty string
        self.cb_author.set(config.get('USER_PREFS', 'author', fallback=''))
        self.cb_site.set(config.get('USER_PREFS', 'site', fallback=''))
        self.cb_activity.set(config.get('USER_PREFS', 'activity', fallback=''))
        self.fish_csv_path.set(config.get('PATHS', 'Species', fallback=str(self.data_dir / "Species_Bangka 2025-04-15.csv")))
        self.users_csv_path.set(config.get('PATHS', 'Photographers', fallback=str(self.data_dir / "Photographers_all 2025-04-15.csv")))
        self.divesites_csv_path.set(config.get('PATHS', 'Divesites', fallback=str(self.data_dir / "Divesites_Bangka 2025-04-15.csv")))
        self.activities_csv_path.set(config.get('PATHS', 'Activities', fallback=str(self.data_dir / "Activities.csv")))


    # def _save_preferences(self):
    #     """Save paths to config file in appropriate directory"""
    #     config = configparser.ConfigParser()
    #     config_path = get_data_path() / "config.ini"
        
    #     # Preserve existing config if it exists
    #     if config_path.exists():
    #         config.read(config_path)
        
    #     if not config.has_section('PATHS'):
    #         config.add_section('PATHS')

    #     config['PATHS'] = {
    #         'Species': self.fish_csv_path.get(),
    #         'Photographers': self.users_csv_path.get(),
    #         'Divesites': self.divesites_csv_path.get(),
    #         'Activities': self.activities_csv_path.get()
    #     }

    #     config_dir = get_data_path()
    #     config_path = config_dir / "config.ini"
        
    #     try:
    #         config_dir.mkdir(parents=True, exist_ok=True)

    #         with open(config_path, 'w') as configfile:
    #             config.write(configfile)
    #         self.status.insert(tk.END, f"\nPreferences saved successfully to {config_path}")
    #     except Exception as e:
    #         self.status.insert(tk.END, f"\nError saving preferences: {str(e)}")

    # def _load_preferences(self):
    #     """Load paths from config file if exists"""
    #     config_path = get_data_path() / "config.ini"
        
    #     if not config_path.exists():
    #         return

    #     config = configparser.ConfigParser()
    #     try:
    #         config.read(config_path)
    #         self.fish_csv_path.set(config['PATHS'].get('Species', ''))
    #         self.users_csv_path.set(config['PATHS'].get('Photographers', ''))
    #         self.divesites_csv_path.set(config['PATHS'].get('Divesites', ''))
    #         self.activities_csv_path.set(config['PATHS'].get('Activities', ''))
    #     except Exception as e:
    #         self.status.insert(tk.END, f"\nError loading preferences: {str(e)}")


    def open_popup(self, content):
        top = tk.Toplevel(self)

        top.geometry("250x100")
        top.title("Alert")
        tk.Label(top, text=content).pack()
        # location should be in the middle of the top level window
        x = (top.winfo_screenwidth() - top.winfo_reqwidth()) / 2
        y = (top.winfo_screenheight() - top.winfo_reqheight()) / 2
        top.geometry("+%d+%d" % (x, y))
        top.after(5000, top.destroy)

    def _check_if_essential_info_set(self):
        if self.cb_author.get() == "":
            self.cb_author.focus()
            return False
        elif self.cb_site.get() == "":
            self.cb_site.focus()
            return False
        return True
            
    def _get_filedate_str(self, path):
        try:
            image = Image.open(path)
            exif = image._getexif()
            return exif[36867].replace(' ', '_').replace(':', '-')
        except:
            f = open(path, 'rb')
            tags = exifread.process_file(f)
            return tags['Image DateTime'].printable.replace(' ', '_').replace(':', '-')
        
    def _decdeg2dms(self, dd):
        mult = -1 if dd < 0 else 1
        mnt,sec = divmod(abs(dd)*3600, 60)
        deg,mnt = divmod(mnt, 60)

        d = mult*deg.as_integer_ratio()
        m = mult*mnt.as_integer_ratio()
        s = round(mult*sec).as_integer_ratio()
        return f"{d[0]}/{d[1]} {m[0]}/{m[1]} {s[0]}/{s[1]}"

    def _process_exif(self, path):
        # TODO excluding gps because pyexiv2 does not work with pyinstaller
        return self._get_filedate_str(path), False

        # img = ImgMeta(path)
        # exif = img.read_exif()
        # date = exif['Exif.Photo.DateTimeOriginal']
        # gps_set = False

        # extension = os.path.splitext(path)[1]
        # if extension.lower() != '.arw':
        #     location, site = self.cb_site.get().split(", ")
        #     lat, lon = self.divesites_df[(self.divesites_df['Area'] == location) & (self.divesites_df['Site'] == site)][['latitude', 'longitude']].values[0]
        #     lat_dms = self._decdeg2dms(lat)
        #     lon_dms = self._decdeg2dms(lon)
        #     exif["Exif.GPSInfo.GPSLatitude"] = lat_dms
        #     exif["Exif.GPSInfo.GPSLatitudeRef"] = "N"
        #     exif["Exif.GPSInfo.GPSLongitude"] = lon_dms
        #     exif["Exif.GPSInfo.GPSLongitudeRef"] = "E"
        #     exif["Exif.Image.GPSTag"] = 654
        #     exif["Exif.GPSInfo.GPSVersionID"] = '2 3 0 0'
        #     img.modify_exif(exif)
        #     gps_set = True
        # return date.replace(' ', '_').replace(':', '-'), gps_set
    def regex_match_basic_info(self, filename):
        return re.match(r'[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+', filename)

    def regex_match_info(self, filename):
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name
        return re.match(r'(0?\-?[A-Za-z]*)_([A-Za-z]+)_([a-z]+)_[A-Z]_([a-z]{2})_([A-Za-z]+)_([A-Za-z\-]+)_([A-Za-z\-]+)_([A-Za-z]{5})_([A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3})_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_([A-Za-z]+)_([A-Za-z0-9]+)', filename)

    def regex_match_datetime_filename(self, filename):
        return re.match(r'0?\-?[A-Za-z]*_[A-Za-z]+_[a-z]+_[A-Z]_[a-z]{2}_[A-Za-z]+_[A-Za-z\-]+_[A-Za-z\-]+_[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_[A-Za-z]+_([A-Za-z0-9]+)', filename)

    def _assemble_filename_name_site_datetime_activity(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath)
        
        if self.regex_match_basic_info(filename) or self.regex_match_info(filename):
            return None

        filename = filename.replace('_', '')
        filedate, gps_set = self._process_exif(path)

        author = self.cb_author.get()
        author_code = self.users_df[self.users_df['Full name'] == author]['Namecode'].values[0]
        site = self.cb_site.get()
        location, site = site.split(", ")
        site_string = self.divesites_df[(self.divesites_df['Area'] == location) & (self.divesites_df['Site'] == site)]['Site string'].values[0]
        activity = self.cb_activity.get()
        if gps_set:
            return f"{author_code}_{site_string}_{filedate}_{activity}_G_{filename}{extension}"
        return f"{author_code}_{site_string}_{filedate}_{activity}_{filename}{extension}"
    
    def _assemble_filename_family_genus_species_details(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath)

        if self.regex_match_info(filename) or not self.regex_match_basic_info(filename):
            return None

        family = self.cb_family.get()
        genus = self.cb_genus.get()
        species = self.cb_species.get()
        confidence = self.cb_confidence.get()
        phase = self.cb_phase.get()
        colour = self.colour_dict[self.cb_colour.get()]
        behaviour = self.behaviour_dict[self.cb_behaviour.get()]

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{filename}{extension}"
    
    def _assemble_edited_filename(self, path):
        filepath, extension = os.path.splitext(path)
        info = self.regex_match_info(os.path.basename(filepath)).groups()
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name

        family = self.cb_family.get() if self.editing_fields[0] else info[0]
        genus = self.cb_genus.get() if self.editing_fields[1] else info[1]
        species = self.cb_species.get() if self.editing_fields[2] else info[2]
        confidence = self.cb_confidence.get() if self.editing_fields[3] else info[3]
        phase = self.cb_phase.get() if self.editing_fields[4] else info[4]
        colour = self.colour_dict[self.cb_colour.get()] if self.editing_fields[5] else info[5]
        behaviour = self.behaviour_dict[self.cb_behaviour.get()] if self.editing_fields[6] else info[6]
        author = self.cb_author.get()
        author_code = self.users_df[self.users_df['Full name'] == author]['Namecode'].values[0] if self.editing_fields[7] else info[7]
        site = self.cb_site.get()
        location, site = site.split(", ")
        site_string = self.divesites_df[(self.divesites_df['Area'] == location) & (self.divesites_df['Site'] == site)]['Site string'].values[0] if self.editing_fields[8] else info[8]
        date = info[9]
        time = info[10]
        activity = self.cb_activity.get() if self.editing_fields[11] else info[11]
        filename = info[12]
        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{author_code}_{site_string}_{date}_{time}_{activity}_{filename}{extension}"

    def _edit_info(self, event):
        if len(self.editing_files) == 0:
            self._warn("No files selected")
            return
        
        renamed = 0
        for path in self.editing_files:
            new_filename = self._assemble_edited_filename(path)
            new_filepath = os.path.join(os.path.dirname(path), new_filename)
            if os.path.exists(new_filepath):
                continue
            os.rename(path, new_filepath)
            renamed += 1
        self._notice(f"{renamed}/{len(self.editing_files)} files were renamed successfully.")
        self._reset_info()
        self.editing_files = []

    def _check_if_same_info(self, files):
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name
        info = np.array([self.regex_match_info(os.path.basename(os.path.splitext(file)[0])).groups() for file in files])
        is_same = (info[:, :] == info[0, :]).all(axis=0)
        values = np.array([info[0][i] if is_same[i] else None for i in range(info.shape[1])])
        return is_same, values

    def _warn(self, text):
        # set background of self.status to red and display the text
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)
        self.status.config(foreground="red")
    def _notice(self, text):
        # set background of self.status to green and display the text
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)
        self.status.config(foreground="black")

    def _toggle_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity):
        self.cb_family.state(['!disabled'] if family else ['disabled'])
        self.cb_genus.state(['!disabled'] if genus else ['disabled'])
        self.cb_species.state(['!disabled'] if species else ['disabled'])
        self.cb_confidence.state(['!disabled'] if confidence else ['disabled'])
        self.cb_phase.state(['!disabled'] if phase else ['disabled'])
        self.cb_colour.state(['!disabled'] if colour else ['disabled'])
        self.cb_behaviour.state(['!disabled'] if behaviour else ['disabled'])
        self.cb_author.state(['!disabled'] if author else ['disabled'])
        self.cb_site.state(['!disabled'] if site else ['disabled'])
        self.cb_activity.state(['!disabled'] if activity else ['disabled'])

    def _set_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity):
        if family: self.cb_family.set(family)
        if genus: self.cb_genus.set(genus)
        if species: self.cb_species.set(species)
        if confidence: self.cb_confidence.set(confidence)
        if phase: self.cb_phase.set(phase)
        # reverse lookup
        if colour: self.cb_colour.set(next((k for k, v in self.colour_dict.items() if v == colour), None))
        if behaviour: self.cb_behaviour.set(next((k for k, v in self.behaviour_dict.items() if v == behaviour), None))
        if author: self.cb_author.set(self.users_df[self.users_df['Namecode'] == author]['Full name'].values[0])
        if site: self.cb_site.set(self.divesites_df[self.divesites_df['Site string'] == site]['Area'].values[0] + ", " + self.divesites_df[self.divesites_df['Site string'] == site]['Site'].values[0])
        if activity: self.cb_activity.set(activity)

    def _dnd_files(self, event):
        files = self.splitlist(event.data)
        if not self._check_if_essential_info_set(): return

        not_renamed = 0
        if self.mode.get() == "Edit":
            is_same, values = self._check_if_same_info(files)
            if not any(is_same): self._warn("No Info can be edited on these files.")
            self._toggle_checkboxes(*is_same[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]])
            self._set_checkboxes(*values[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]])
            self.editing_files = files
            self.editing_fields = is_same
            self._notice(f'Loaded {len(files)} files.')
        
        else:
            for file in files:
                if self.mode.get() == "Basic":
                    filename = self._assemble_filename_name_site_datetime_activity(file)
                elif self.mode.get() == "Identify":
                    filename = self._assemble_filename_family_genus_species_details(file)
                if filename is None:
                    not_renamed += 1
                    continue

                new_filepath = os.path.join(os.path.dirname(file), filename)
                if os.path.exists(new_filepath):
                    not_renamed += 1
                    continue
                else:
                    os.rename(file, new_filepath)
            
            if not_renamed > 0:
                self._warn(f"{not_renamed}/{len(files)} files were not renamed.\nThey might have been renamed already.")
            else:
                self._notice(f"All files were renamed successfully.")
                #self.open_popup(f"{not_renamed} files were not renamed.\nThey might have been renamed already.")

    def _row_selected(self, event):
        if self.tree.selection():
            item = self.tree.selection()[0]
            family, genus, species, common_name = self.tree.item(item, 'values')
            self.cb_family.set(family)
            self.cb_genus.set(genus)
            self.cb_species.set(species)
        # self._set_preview()

    def _toggle_extended_info(self, a, b, c):
        if self.mode.get() == 'Basic':
            self._toggle_checkboxes(False, False, False, False, False, False, False, True, True, True)
            self.bt_rename.grid_remove()
        elif self.mode.get() == 'Identify':
            self._toggle_checkboxes(True, True, True, True, True, True, True, False, False, False)
            self.bt_rename.grid_remove()
        elif self.mode.get() == 'Edit':
            self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False)
            self.bt_rename.grid()
        self._notice(f"Switched to \"{self.mode.get()}\" mode")

    def _set_preview(self):
        item = self.tree.selection()[0]
        family, genus, species = self.cb_family.get(), self.cb_genus.get(), self.cb_species.get()
        filename = f"config/preview/{family}_{genus}_{species}.jpg"
        if not os.path.exists(filename):
            filename = f"config/preview/dummy.jpg"
        img = Image.open(filename)
        img = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=img)
        self.preview_label.image = img

    def set_family(self, event):
        family = self.cb_family.get()
        filtered = self.fish_df[self.fish_df['Family'] == family]
        self.cb_family.set(family)
        self.cb_genus['values'] = [self.genus_default] + sorted(filtered['Genus'].unique())
        self.cb_genus.current(0)
        self.cb_species['values'] = [self.species_default] + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_genus(self, event):
        genus = self.cb_genus.get()
        if genus == self.genus_default:
            filtered = self.fish_df[self.fish_df['Family'] == self.cb_family.get()]
        else:
            filtered = self.fish_df[self.fish_df['Genus'] == genus]
        family = filtered['Family'].iloc[0]
        self.cb_family.set(family)
        self.cb_genus.set(genus)
        self.cb_species['values'] = [self.species_default] + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_species(self, event):
        species = self.cb_species.get()
        if species == self.species_default:
            filtered = self.fish_df[self.fish_df['Genus'] == self.cb_genus.get()]
        else:
            filtered = self.fish_df[self.fish_df['Species'] == species]
        genus = filtered['Genus'].iloc[0]
        family = filtered['Family'].iloc[0]
        self.cb_genus.set(genus)
        self.cb_family.set(family)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())
        # self._set_preview()

    def sort_fish_df(self, df):
        return df.sort_values(by=['Family', 'Genus', 'Species'])

    def _load_data(self):
        """Load data files using paths from configuration"""
        try:
            # Load fish data
            self.fish_df = pd.read_csv(get_data_path() / self.fish_csv_path.get(), sep=';').fillna('')
            #self.status.insert(tk.END, "\nLoaded species data from: " + self.fish_csv_path.get())
            # Load photographers
            self.users_df = pd.read_csv(get_data_path() / self.users_csv_path.get(), sep=';')
            #self.status.insert(tk.END, "\nLoaded photographers from: " + self.users_csv_path.get())
            # Load divesites
            self.divesites_df = pd.read_csv(get_data_path() / self.divesites_csv_path.get(), sep=';')
            #self.status.insert(tk.END, "\nLoaded divesites from: " + self.divesites_csv_path.get())
            # Load activities
            self.activities_df = pd.read_csv(get_data_path() / self.activities_csv_path.get(), sep=';')
            #self.status.insert(tk.END, "\nLoaded activities from: " + self.activities_csv_path.get())
    
        except FileNotFoundError as e:
            self.status.insert(tk.END, f"\nError: Missing data file - {str(e)}")
        except pd.errors.EmptyDataError:
            self.status.insert(tk.END, "\nError: One or more data files are empty/corrupt")
        except Exception as e:
            self.status.insert(tk.END, f"\nUnexpected error loading data: {str(e)}")
        finally:
            # Ensure fish_df has NaN replaced even if other files fail
            if hasattr(self, 'fish_df'):
                self.fish_df = self.fish_df.fillna('')
                self.cb_family['values'] =  [self.family_default] + sorted(self.fish_df['Family'].unique())
                self.cb_genus['values'] = [self.genus_default] + sorted(self.fish_df['Genus'].unique())
                self.cb_species['values'] = [self.species_default] + sorted(self.fish_df['Species'].unique())
                self.clear_tree()
                self.fill_tree(self.sort_fish_df(self.fish_df).values.tolist())
            else:
                self.status.insert(tk.END, "\nCritical error: Failed to load species data!")

            if hasattr(self, 'users_df'):
                self.cb_author['values'] = self.users_df['Full name'].tolist()
                self.cb_author.current(0)
            if hasattr(self, 'divesites_df'):
                self.cb_site['values'] = self.divesites_df[['Area', 'Site']].sort_values(by=['Area', 'Site'], inplace=False).apply(lambda x: ', '.join(x), axis=1).tolist()
                self.cb_site.current(0)
            if hasattr(self, 'activities_df'):
                self.cb_activity['values'] = self.activities_df['activity'].tolist()
                self.cb_activity.current(0)

    def _build_tree(self):
        for col in list(self.tree_columns):
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.tree, c, 0))
            # adjust the column's width to the header string
            self.tree.column(col,
                width=tkFont.Font().measure(col.title()))
        #self.fill_tree(self.sort_fish_df(self.fish_df).values.tolist())

    def fill_tree(self, items):
        for item in items:
            self.tree.insert('', 'end', values=item)
            # adjust column's width if necessary to fit each value
            for ix, val in enumerate(item):
                col_w = tkFont.Font().measure(val)
                if self.tree.column(list(self.fish_df.columns)[ix], width=None)<col_w:
                    self.tree.column(list(self.fish_df.columns)[ix], width=col_w)

    def clear_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def search(self, event):
        self.clear_tree()
        # get the search string
        search_string = self.search_field.get()
        search_substrings = search_string.split()
        # get the data from the dataframe
        fish_filtered = self.fish_df[self.fish_df.apply(lambda row: all([any([substring.lower() in value.lower() for value in row.values]) for substring in search_substrings]), axis=1)]
        # insert the data into the tree
        self.fill_tree(self.sort_fish_df(fish_filtered).values.tolist())

    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        data = [(tree.set(child, col), child) \
            for child in tree.get_children('')]
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, \
            int(not descending)))

if __name__ == '__main__':
    main = FishRenamer()
    main.mainloop()