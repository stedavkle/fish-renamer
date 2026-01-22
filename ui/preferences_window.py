# ui/preferences_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import re
import subprocess
import sys
from src.app_utils import clear_data_files, initialize_data_files, get_data_path


class PreferencesWindow(tk.Toplevel):
    """The 'Preferences' dialog for managing CSV paths and web updates."""
    def __init__(self, parent, config_manager, web_updater):
        super().__init__(parent)
        self.config_manager = config_manager
        self.web_updater = web_updater
        self.transient(parent)
        self.title("Preferences & Updates")
        self.geometry("520x400")
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
            if event == "All":
                self.master.data.filter_by_location()
            else:
                self.master.data.filter_by_location(event)
            self.master.update_all_comboboxes()

        # Get dynamic location list from data, ensure 'All' is first
        locations = self.master.data.get_available_locations()
        if 'All' in locations:
            locations.remove('All')
        locations = ['All'] + locations

        current_location = self.config_manager.get_misc('location', 'All')
        self.location_var.set(current_location)
        self.location_menu = ttk.OptionMenu(location_frame, self.location_var, current_location, *locations, command=on_location_change)
        self.location_menu.grid(row=0, column=0, padx=5, pady=5, sticky='ew')


        # Web Update Section
        update_frame = ttk.LabelFrame(main_frame, text="Update from Web")
        update_frame.pack(fill='x', expand=True, pady=5)

        self.fetch_button = ttk.Button(update_frame, text="Update", command=self._fetch_remote_files)
        self.fetch_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        self.update_status_label = ttk.Label(update_frame, text="Status: Idle")
        self.update_status_label.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        # Progress bar (hidden by default)
        self.progress_bar = ttk.Progressbar(update_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky='ew')
        self.progress_bar.grid_remove()  # Hidden initially

        update_frame.grid_columnconfigure(1, weight=1)

        # Status display for individual files
        status_frame = ttk.LabelFrame(main_frame, text="File Update Status")
        status_frame.pack(fill='x', expand=True, pady=5)

        # Header row
        ttk.Label(status_frame, text="File", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(status_frame, text="Current Version", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=1, sticky='w', padx=5)
        ttk.Label(status_frame, text="Status", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=2, sticky='w', padx=5)

        self.file_status_labels = {}
        self.file_date_labels = {}
        files_to_track = ['Species', 'Photographers', 'Divesites', 'Labels', 'Activities']
        for i, name in enumerate(files_to_track):
            ttk.Label(status_frame, text=f"{name}:").grid(row=i+1, column=0, sticky='w', padx=5)

            # Date label showing current file version
            current_date = self._get_file_date(name.lower())
            date_label = ttk.Label(status_frame, text=current_date, width=12, anchor='w')
            date_label.grid(row=i+1, column=1, sticky='w', padx=5)
            self.file_date_labels[name] = date_label

            # Status label
            status_label = ttk.Label(status_frame, text="-", width=15, anchor='w')
            status_label.grid(row=i+1, column=2, sticky='w', padx=5)
            self.file_status_labels[name] = status_label

        # Debug Section
        debug_frame = ttk.LabelFrame(main_frame, text="Debug")
        debug_frame.pack(fill='x', expand=True, pady=5)

        open_dir_button = ttk.Button(debug_frame, text="Open App Directory", command=self._open_app_directory)
        open_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        restore_button = ttk.Button(debug_frame, text="Restore Default Paths", command=self._restore_defaults)
        restore_button.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        reset_button = ttk.Button(debug_frame, text="Reset Directory", command=self._reset_directory)
        reset_button.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        debug_frame.grid_columnconfigure(0, weight=1)
        debug_frame.grid_columnconfigure(1, weight=1)
        debug_frame.grid_columnconfigure(2, weight=1)

    def _get_file_date(self, file_key):
        """Extract date from the current filename in config.

        Args:
            file_key: Config key for the file (e.g., 'species', 'divesites')

        Returns:
            Date string (YYYY-MM-DD) or '-' if not found
        """
        path = self.config_manager.get_path(file_key)
        if path and path.exists():
            match = re.search(r'(\d{4}-\d{2}-\d{2})', path.name)
            if match:
                return match.group(1)
        return '-'

    def _update_date_labels(self):
        """Refresh all date labels with current file versions."""
        for name, label in self.file_date_labels.items():
            current_date = self._get_file_date(name.lower())
            label.config(text=current_date)

    def _fetch_remote_files(self):
        """Start the update process in a background thread."""
        # Disable button and show progress bar
        self.fetch_button.config(state='disabled')
        self.progress_bar.grid()
        self.progress_bar.start(10)
        self.update_status_label.config(text="Status: Connecting...")

        # Run update in background thread
        thread = threading.Thread(target=self._run_update_thread, daemon=True)
        thread.start()

    def _run_update_thread(self):
        """Background thread for web update."""
        try:
            def callback(status):
                self.after(0, lambda: self.update_status_label.config(text="Status: " + status))

            self.web_updater.connect(callback)

            self.after(0, lambda: self.update_status_label.config(text="Status: Fetching file list..."))
            self.remote_filelist, status_msg = self.web_updater.fetch_file_list()
            self.after(0, lambda: self.update_status_label.config(text=f"Status: {status_msg}"))

            if self.remote_filelist:
                self.after(0, lambda: self.update_status_label.config(text="Status: Downloading updates..."))
                self._run_web_update()
        except Exception as e:
            self.after(0, lambda: self.update_status_label.config(text=f"Status: Error - {e}"))
        finally:
            # Re-enable button and hide progress bar
            self.after(0, self._finish_update)

    def _finish_update(self):
        """Clean up UI after update completes."""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.fetch_button.config(state='normal')

    def _restore_defaults(self):
        clear_data_files()
        initialize_data_files()
        self.config_manager._set_defaults()
        self.update_status_label.config(text="Status: Defaults restored.")
        self.master.on_data_updated()

    def _open_app_directory(self):
        """Open the application data directory in the file explorer."""
        data_path = get_data_path()
        if sys.platform == 'win32':
            os.startfile(data_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', data_path])
        else:
            subprocess.run(['xdg-open', data_path])

    def _reset_directory(self):
        """Delete all files in the application data directory after confirmation."""
        if not messagebox.askyesno(
            "Confirm Reset",
            "This will delete all data files in the application directory.\n\nAre you sure?"
        ):
            return

        data_path = get_data_path()
        try:
            for file in data_path.iterdir():
                if file.is_file():
                    file.unlink()
            self.update_status_label.config(text="Status: Directory reset.")
            self.master.on_data_updated()
        except Exception as e:
            self.update_status_label.config(text=f"Status: Error - {e}")

    def _run_web_update(self):
        """Execute the web update (called from background thread)."""
        # This configuration is passed to the web_updater.
        update_configs = {
            'Activities': {'requires_date_check': False},
            'Divesites': {'requires_date_check': True},
            'Species': {'requires_date_check': True},
            'Photographers': {'requires_date_check': True},
            'Labels': {'requires_date_check': True},
        }

        # The updater works with plain paths, not tk variables.
        for prefix, config in update_configs.items():
            config['path_var'] = self.config_manager.get_path(prefix.lower())

        statuses, newest_files = self.web_updater.run_update(self.remote_filelist, update_configs)

        # Update the config manager with new paths
        for prefix, path in newest_files.items():
            self.config_manager.set_path(prefix.lower(), path)
        self.config_manager.save()

        # Update UI on main thread
        def update_ui():
            for name, label in self.file_status_labels.items():
                if name in statuses:
                    label.config(text=statuses[name])
            self._update_date_labels()
            self.update_status_label.config(text="Status: Update complete.")
            self.master.on_data_updated()

        self.after(0, update_ui)