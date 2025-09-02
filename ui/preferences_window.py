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

        location_frame = ttk.LabelFrame(main_frame, text="Location Filter")
        location_frame.pack(fill='x', expand=True, pady=5)
        self.location_var = tk.StringVar()
        def on_location_change(event):
            self.config_manager.set_misc('location', self.location_var.get())
            self.master.data.filter_by_location(event)
            self.master.update_all_comboboxes()
        self.location_menu = ttk.OptionMenu(location_frame, self.location_var, "Select location", "Bangka", "Red Sea", command=on_location_change)
        self.location_menu.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        self.location_var.set(self.config_manager.get_misc('location', ''))


        # Web Update Section
        update_frame = ttk.LabelFrame(main_frame, text="Update from Web")
        update_frame.pack(fill='x', expand=True, pady=5)

        fetch_button = ttk.Button(update_frame, text="Update", command=self._fetch_remote_files)
        fetch_button.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        
        self.update_status_label = ttk.Label(update_frame, text="Status: Idle")
        self.update_status_label.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
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

        self._run_web_update()

    def _run_web_update(self):
        # This configuration is passed to the web_updater.
        # It's decoupled from the main app's tk.StringVars.
        update_configs = {
            'Activities': {'requires_date_check': False},
            'Divesites': {'requires_date_check': True},
            'Species': {'requires_date_check': True},
            'Photographers': {'requires_date_check': True},
        }

        # The updater works with plain paths, not tk variables.
        for prefix, config in update_configs.items():
             config['path_var'] = self.config_manager.get_path(prefix.lower())

        statuses, newest_files = self.web_updater.run_update(self.remote_filelist, update_configs)

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