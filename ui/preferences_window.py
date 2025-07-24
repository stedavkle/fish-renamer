# ui/preferences_window.py
import tkinter as tk
from tkinter import ttk
import threading
import time

class PreferencesWindow(tk.Toplevel):
    """The 'Preferences' dialog for managing CSV paths and web updates."""
    def __init__(self, parent, config_manager, web_updater):
        super().__init__(parent)
        self.config_manager = config_manager
        self.web_updater = web_updater
        self.transient(parent)
        self.title("Preferences & Updates")
        self.geometry("500x300")
        self.grab_set()

        self.remote_filelist = []
        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Web Update Section
        update_frame = ttk.LabelFrame(main_frame, text="Update from Web")
        update_frame.pack(fill='x', expand=True, pady=5)

        fetch_button = ttk.Button(update_frame, text="1. Fetch Available Files", command=self._fetch_remote_files)
        fetch_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.update_status_label = ttk.Label(update_frame, text="Status: Idle")
        self.update_status_label.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.location_var = tk.StringVar(value="Select location")
        self.location_menu = ttk.OptionMenu(update_frame, self.location_var, "Select location")
        self.location_menu.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        self.location_menu['state'] = 'disabled'

        download_button = ttk.Button(update_frame, text="2. Update For Selected Location", command=self._run_web_update)
        download_button.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        # Status display for individual files
        status_frame = ttk.LabelFrame(main_frame, text="File Update Status")
        status_frame.pack(fill='x', expand=True, pady=5)
        
        self.file_status_labels = {}
        files_to_track = ['Species', 'Photographers', 'Divesites', 'Activities']
        for i, name in enumerate(files_to_track):
            ttk.Label(status_frame, text=f"{name} CSV:").grid(row=i, column=0, sticky='w', padx=5)
            status_label = ttk.Label(status_frame, text="-", width=20, anchor='w')
            status_label.grid(row=i, column=1, sticky='w', padx=5)
            self.file_status_labels[name] = status_label


    def _fetch_remote_files(self):
        self.update_status_label.config(text="Status: Fetching...")
        connected = False
        def callback(status):
            self.update_status_label.config(text="Status: " + status)
            self.update_idletasks()

        # Start the web updater in a separate thread to avoid blocking the UI
        self.web_updater.connect(callback)
        
        self.remote_filelist, status_msg = self.web_updater.fetch_file_list()
        self.update_status_label.config(text=f"Status: {status_msg}")

        if self.remote_filelist:
            locations = self.web_updater.get_available_locations(self.remote_filelist)
            menu = self.location_menu['menu']
            menu.delete(0, 'end')
            for loc in locations:
                menu.add_command(label=loc, command=lambda v=loc: self.location_var.set(v))
            self.location_menu['state'] = 'normal'

    def _run_web_update(self):
        if not self.remote_filelist or self.location_var.get() == "Select location":
            self.update_status_label.config(text="Status: First fetch files and select a location.")
            return

        # This configuration is passed to the web_updater.
        # It's decoupled from the main app's tk.StringVars.
        update_configs = {
            'Activities': {'is_location_specific': False, 'requires_date_check': False},
            'Divesites': {'is_location_specific': True, 'requires_date_check': True},
            'Species': {'is_location_specific': True, 'requires_date_check': True},
            'Photographers': {'is_location_specific': False, 'requires_date_check': True},
        }

        # The updater works with plain paths, not tk variables.
        for prefix, config in update_configs.items():
             config['path_var'] = self.config_manager.get_path(prefix.lower())

        statuses, newest_files = self.web_updater.run_update(self.remote_filelist, update_configs, self.location_var.get())

        print("Update statuses:", statuses)
        print("Newest files:", newest_files)
        # # Update the config manager with new paths
        for prefix, path in newest_files.items():
            self.config_manager.set_path(prefix.lower(), path)
        self.config_manager.save()
        
        # Update UI based on results from the logic class
        for name, label in self.file_status_labels.items():
            if name in statuses:
                label.config(text=statuses[name])
        
        self.update_status_label.config(text="Status: Update complete.")
        # Optionally, tell the parent window to reload data
        self.master.on_data_updated()