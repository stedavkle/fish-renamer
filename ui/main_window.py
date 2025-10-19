# ui/main_window.py
import tkinter as tk
from tkinter import ttk, font as tkFont
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from PIL import Image, ImageTk

# Import refactored components
from src.config_manager import ConfigManager
from src.data_manager import DataManager
from src.filename_assembler import FilenameAssembler
from src.exif_handler import ExifHandler
from src.web_updater import WebUpdater
from .preferences_window import PreferencesWindow
from src import app_utils
from src.constants import (
    MAIN_WINDOW_TITLE,
    TREE_COLUMNS,
    STATUS_READY,
    DEFAULT_PHOTOGRAPHER_TEXT,
    DEFAULT_SITE_TEXT,
    DEFAULT_ACTIVITY_TEXT
)

class MainWindow(TkinterDnD.Tk):
    """The main application window, focused on UI management."""

    def __init__(self):
        super().__init__()
        self.title(MAIN_WINDOW_TITLE)

        # --- Composition Root: Create and wire up all components ---
        self.config_manager = ConfigManager()
        self.data = DataManager(self.config_manager)
        self.assembler = FilenameAssembler(self.data)
        self.exif = ExifHandler()
        self.web_updater = WebUpdater(app_utils.get_data_path())

        # --- UI Setup ---
        self.tree_columns = TREE_COLUMNS
        self._setup_widgets()
        
        self.on_data_updated() # Initial data load and UI population

    def _setup_widgets(self):
        """Master method to build the entire UI by calling sub-methods."""
        self._setup_icon()
        self._setup_dnd()
        self._configure_main_container_grid(self)
        self._create_frames(self)
        self._setup_menu()
        self._setup_search_field()
        self._setup_treeview_and_scrollbars()
        self._setup_taxonomy_comboboxes()
        self._setup_edit_frame()
        self._setup_attribute_comboboxes()
        self._setup_info_comboboxes()
        self._setup_maps_link() # Assuming _open_googlemaps is also implemented
        self._setup_status_text()
        self._build_tree_headers()
        self._toggle_extended_info()  # Set initial mode to Basic

    def _setup_icon(self):
        """Set application icon."""
        try:
            icon_path = app_utils.get_app_path().parent / 'config' / 'icon.png'
            ico = Image.open(icon_path)
            photo = ImageTk.PhotoImage(ico)
            self.wm_iconphoto(False, photo)
        except Exception as e:
            # Icon loading is non-critical, just log and continue
            pass

    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._dnd_files)

    def _configure_main_container_grid(self, container):
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _create_frames(self, main_container):
        frames = [
            ('upper_frame', {'row': 0, 'column': 0, 'sticky': 'nsew'}),
            ('middle_frame', {'row': 1, 'column': 0, 'sticky': 'nsew'}),
            ('bottom_frame', {'row': 2, 'column': 0, 'sticky': 'nsew', 'padx': 10, 'pady': 10}),
        ]
        for name, grid_args in frames:
            frame = ttk.Frame(main_container)
            frame.grid(**grid_args)
            setattr(self, name, frame)
        for col in range(4):
            self.bottom_frame.grid_columnconfigure(col, weight=1)

    def _setup_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar) # This line is now correct because self.config is no longer shadowed
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=config_menu)
        config_menu.add_command(label="Preferences & Updates", command=self._show_preferences)

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

    def _build_tree_headers(self):
        for col in self.tree_columns:
            self.tree.heading(col, text=col.title(), command=lambda c=col: self.sortby(self.tree, c, False))
            self.tree.column(col, width=tkFont.Font().measure(col.title()), anchor='w')

    def _setup_combobox_group(self, frame, configs):
        for config in configs:
            ttk.Label(frame, text=config['label']).grid(row=config['row'], column=config['col'], padx=5, pady=2, sticky='ew')
            cb = ttk.Combobox(frame, values=config.get('values', []), state='readonly')
            cb.grid(row=config['row']+1, column=config['col'], padx=5, pady=2, sticky='ew')
            if cb['values']:
                cb.current(0)
            if 'cmd' in config: cb.bind("<<ComboboxSelected>>", config['cmd'])
            setattr(self, config['var'], cb)

    def _setup_taxonomy_comboboxes(self):
        configs = [
            {'label': 'Family', 'var': 'cb_family', 'values': [self.data.family_default], 'row': 0, 'col': 0, 'cmd': self.set_family},
            {'label': 'Genus', 'var': 'cb_genus', 'values': [self.data.genus_default], 'row': 0, 'col': 1, 'cmd': self.set_genus},
            {'label': 'Species', 'var': 'cb_species', 'values': [self.data.species_default],'row': 0, 'col': 2, 'cmd': self.set_species}
        ]
        self._setup_combobox_group(self.bottom_frame, configs)

    def _setup_attribute_comboboxes(self):
        configs = [
            {'label': 'Confidence', 'var': 'cb_confidence', 'values': self.data.confidence_default, 'row': 2, 'col': 0},
            {'label': 'Phase', 'var': 'cb_phase', 'values': self.data.phase_default, 'row': 2, 'col': 1},
            {'label': 'Colour', 'var': 'cb_colour', 'values': self.data.colour_default, 'row': 2, 'col': 2},
            {'label': 'Behaviour', 'var': 'cb_behaviour', 'values': self.data.behaviour_default, 'row': 2, 'col': 3}
        ]
        self._setup_combobox_group(self.bottom_frame, configs)

    def _setup_info_comboboxes(self):
        configs = [
            {'label': 'Photographer', 'var': 'cb_author', 'row': 4, 'col': 0, 'cmd': self._save_user_prefs},
            {'label': 'Site', 'var': 'cb_site', 'row': 4, 'col': 1, 'cmd': self._save_user_prefs},
            {'label': 'Activity', 'var': 'cb_activity', 'row': 4, 'col': 2, 'cmd': self._save_user_prefs}
        ]
        self._setup_combobox_group(self.bottom_frame, configs)

    def _open_googlemaps(self, event):
        coordinates = self.data.get_lat_long_from_site(self.cb_site.get())
        os.system(f"start https://maps.google.com/?q={coordinates[0]},{coordinates[1]}")

    def _setup_maps_link(self):
        self.link = tk.Label(self.bottom_frame, text="Google Maps", fg="blue", cursor="hand2")
        self.link.grid(row=6, column=1, padx=5, pady=2, sticky='ew')
        self.link.bind("<Button-1>", self._open_googlemaps)

    def _setup_edit_frame(self):
        self.edit_frame = ttk.Frame(self.bottom_frame)
        self.edit_frame.grid(row=1, column=3, sticky="nsew")
        self.mode = tk.StringVar(value="Basic")
        om_mode = tk.OptionMenu(self.edit_frame, self.mode, "Basic", "Identify", "Edit", command=self._toggle_extended_info)
        om_mode.grid(row=0, column=0, padx=5, pady=2, sticky='ew')
        self.mode.set("Basic")
        self.bt_rename = tk.Button(self.edit_frame, text="Rename", command=self._edit_info)
        self.bt_rename.grid(row=1, column=0, padx=5, pady=2, sticky='ew')
        self.bt_rename.grid_remove()

    def _setup_status_text(self):
        self.status = tk.Text(self.bottom_frame, height=3, width=1, font=("Arial", 8))
        self.status.grid(row=4, column=3, padx=5, pady=2, sticky='ew', rowspan=3)
        self._notice(STATUS_READY)

    def on_data_updated(self):
        """Reload all data files and refresh the UI.

        Called after updating data files from the web or when explicitly requested.
        Reloads CSV/JSON data files, updates all comboboxes, and saves config.
        """
        status = self.data.load_all_data()
        self._notice(status)
        self.update_all_comboboxes()
        self.config_manager.save()

    def update_all_comboboxes(self):
        """Refresh all combobox values from loaded data.

        Populates all comboboxes with current data from DataManager, restores
        user preferences from config, and fills the treeview with all fish species.
        """
        self.cb_family['values'] = ['0-Fam'] + self.data.get_unique_values('Family')
        self.cb_family.set(self.data.family_default)
        self.cb_genus['values'] = ['genus'] + self.data.get_unique_values('Genus')
        self.cb_genus.set(self.data.genus_default)
        self.cb_species['values'] = ['spec'] + self.data.get_unique_values('Species')
        self.cb_species.set(self.data.species_default)

        self.cb_author['values'] = self.data.get_unique_values('Full name', 'users_df')
        self.cb_author.set(0)  # Default to empty string

        self.cb_confidence['values'] = self.data.get_active_labels('Confidence')
        self.cb_phase['values'] = self.data.get_active_labels('Phase')
        self.cb_colour['values'] = self.data.get_active_labels('Colour')
        self.cb_behaviour['values'] = self.data.get_active_labels('Behaviour')

        self.cb_site['values'] = self.data.get_formatted_site_list()
        self.cb_site.set(DEFAULT_SITE_TEXT)  # Default to empty string

        self.cb_activity['values'] = self.data.get_unique_values('activity', 'activities_df')

        # Restore selections from config
        self.cb_author.set(self.config_manager.get_user_pref('author', DEFAULT_PHOTOGRAPHER_TEXT))
        self.cb_site.set(self.config_manager.get_user_pref('site', DEFAULT_SITE_TEXT))
        self.cb_activity.set(self.config_manager.get_user_pref('activity', DEFAULT_ACTIVITY_TEXT))

        # Fill tree with all fish initially
        self.fill_tree(self.data.get_all_fish().values.tolist())

    def _show_preferences(self):
        """Open the preferences and updates dialog window.

        Creates a modal preferences window where users can configure data file
        locations and update data from HiDrive.
        """
        self.prefs_win = PreferencesWindow(self, self.config_manager, self.web_updater)
        self.wait_window(self.prefs_win)

    def _dnd_files(self, event):
        """Handle drag-and-drop events for renaming files.

        Dispatches to the appropriate handler based on current mode (Basic,
        Identify, or Edit). Files are passed as a list of absolute paths.

        Args:
            event: Tkinter DND event containing dropped file paths
        """
        files = self.splitlist(event.data)
        mode = self.mode.get()

        mode_handlers = {
            "Edit": self._handle_edit_mode,
            "Basic": self._handle_basic_mode,
            "Identify": self._handle_identify_mode
        }

        handler = mode_handlers.get(mode)
        if handler:
            handler(files)
        else:
            self._warn(f"Unknown mode: {mode}")

    def _handle_edit_mode(self, files):
        """Prepare files for batch editing.

        Analyzes dropped files to find common fields that can be batch edited.
        Enables only those fields in the UI and populates them with common values.

        Args:
            files: List of absolute file paths to prepare for editing
        """
        self.files_to_edit = files  # Store full paths for later
        basenames = [os.path.splitext(os.path.basename(f))[0] for f in files]

        try:
            is_same, values = self.assembler.analyze_files_for_editing(basenames)
        except ValueError as e:
            self._warn(f"Error analyzing files: {e}")
            return

        self.fields_to_edit = is_same  # Store the flags for the rename operation
        self.editing_files = files

        if not any(is_same):
            self._warn("Files have no common editable information.")
            return

        # Map the 13-element array to the 10 UI controls
        ui_flags = is_same[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]]
        ui_values = values[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]]

        self._toggle_checkboxes(*ui_flags)
        self._set_checkboxes(*ui_values)
        self._notice(f"Loaded {len(files)} files for editing. Make changes and click 'Rename'.")

    def _handle_basic_mode(self, files):
        """Rename files with basic metadata (photographer, site, activity).

        Validates that photographer, site, and activity are selected, then
        renames each file with EXIF date and basic metadata.

        Args:
            files: List of absolute file paths to rename
        """
        author = self.cb_author.get()
        site_raw = self.cb_site.get()
        activity = self.cb_activity.get()

        # Validate selections
        if not author or author == DEFAULT_PHOTOGRAPHER_TEXT:
            self._warn("Please select a photographer.")
            return
        if not site_raw or site_raw == DEFAULT_SITE_TEXT or ', ' not in site_raw:
            self._warn("Please select a dive site.")
            return
        if not activity or activity == DEFAULT_ACTIVITY_TEXT:
            self._warn("Please select an activity.")
            return

        site_tuple = tuple(site_raw.split(", ", 1))
        renamed_count = 0

        for file_path in files:
            if self._rename_single_file_basic(file_path, author, site_tuple, activity):
                renamed_count += 1

        self._notice(f"{renamed_count}/{len(files)} files renamed.")

    def _handle_identify_mode(self, files):
        """Rename files with taxonomic identification and attributes.

        Adds fish identification (family, genus, species) and attributes
        (confidence, phase, colour, behaviour) to files that already have
        basic metadata in their filenames.

        Args:
            files: List of absolute file paths to rename
        """
        family = self.cb_family.get()
        genus = self.cb_genus.get()
        species = self.cb_species.get()
        confidence = self.cb_confidence.get()
        phase = self.cb_phase.get()
        colour = self.cb_colour.get()
        behaviour = self.cb_behaviour.get()

        renamed_count = 0

        for file_path in files:
            if self._rename_single_file_identity(
                file_path, family, genus, species, confidence, phase, colour, behaviour
            ):
                renamed_count += 1

        self._notice(f"{renamed_count}/{len(files)} files renamed.")

    def _rename_single_file_basic(self, file_path, author, site_tuple, activity):
        """Rename a single file with basic metadata.

        Returns:
            bool: True if file was renamed successfully, False otherwise
        """
        try:
            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            file_date = self.exif.get_creation_date_str(file_path)
            new_filename_body = self.assembler.assemble_basic_filename(
                original_name, file_date, author, site_tuple, activity
            )

            if not new_filename_body:
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)
            if os.path.exists(new_path):
                return False

            os.rename(file_path, new_path)
            return True
        except (OSError, IOError) as e:
            self._warn(f"Error renaming {os.path.basename(file_path)}: {e}")
            return False

    def _rename_single_file_identity(self, file_path, family, genus, species,
                                     confidence, phase, colour, behaviour):
        """Rename a single file with identity metadata.

        Returns:
            bool: True if file was renamed successfully, False otherwise
        """
        try:
            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            new_filename_body = self.assembler.assemble_identity_filename(
                original_name, family, genus, species, confidence, phase, colour, behaviour
            )

            if not new_filename_body:
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)
            if os.path.exists(new_path):
                return False

            os.rename(file_path, new_path)
            return True
        except (OSError, IOError) as e:
            self._warn(f"Error renaming {os.path.basename(file_path)}: {e}")
            return False

    def _notice(self, text):
        """Display an informational message in the status area.

        Args:
            text: The message to display (shown in black)
        """
        self.status.config(foreground="black")
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)

    def _warn(self, text):
        """Display a warning or error message in the status area.

        Args:
            text: The warning message to display (shown in red)
        """
        self.status.config(foreground="red")
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)

    def _save_user_prefs(self, event=None):
        """Save user preferences to config file.

        Called when photographer, site, or activity selections change. Persists
        the current selections so they can be restored on next application launch.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        self.config_manager.set_user_pref('author', self.cb_author.get())
        self.config_manager.set_user_pref('site', self.cb_site.get())
        self.config_manager.set_user_pref('activity', self.cb_activity.get())
        self.config_manager.save()

    def _toggle_extended_info(self, event=None):
        """Switch between Basic, Identify, and Edit modes.

        Adjusts which comboboxes are enabled/disabled and whether the Rename button
        is visible based on the selected mode:
        - Basic: Enable author, site, activity for metadata-only renaming
        - Identify: Enable taxonomy and attributes for adding identification
        - Edit: Disable all fields until files are loaded for batch editing

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        mode = self.mode.get()
        is_basic = mode == 'Basic'
        is_identify = mode == 'Identify'
        is_edit = mode == 'Edit'

        if is_basic:
            self._toggle_checkboxes(False, False, False, False, False, False, False, True, True, True)
            self.bt_rename.grid_remove()
        elif is_identify:
            self._toggle_checkboxes(True, True, True, True, True, True, True, False, False, False)
            self.bt_rename.grid_remove()
        elif is_edit:
            self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False)
            self.bt_rename.grid()

        if is_edit: self.bt_rename.grid()
        else: self.bt_rename.grid_remove()
        self._reset_info()
        self._notice(f"Switched to '{mode}' mode.")
    
    def _toggle_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity):
        """Enable or disable comboboxes based on boolean flags.

        Args:
            family: Enable/disable family combobox
            genus: Enable/disable genus combobox
            species: Enable/disable species combobox
            confidence: Enable/disable confidence combobox
            phase: Enable/disable phase combobox
            colour: Enable/disable colour combobox
            behaviour: Enable/disable behaviour combobox
            author: Enable/disable author combobox
            site: Enable/disable site combobox
            activity: Enable/disable activity combobox
        """
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
        """Set combobox values from parsed filename data.

        Used in Edit mode to populate comboboxes with values extracted from
        filenames. Triggers cascading updates for taxonomy fields.

        Args:
            family: Family name to set (triggers genus/species update)
            genus: Genus name to set (triggers species update)
            species: Species name to set
            confidence: Confidence level to set
            phase: Phase to set
            colour: Colour abbreviation/label to set
            behaviour: Behaviour abbreviation/label to set
            author: Author code to set (converted to full name)
            site: Site code to set (converted to formatted string)
            activity: Activity to set
        """
        if family:
            self.cb_family.set(family)
            self.set_family(None)  # Trigger to update genus/species comboboxes based on family
        if genus:
            self.cb_genus.set(genus)
            self.set_genus(None)  # Trigger to update species combobox based on genus
        if species: self.cb_species.set(species)
        if confidence: self.cb_confidence.set(confidence)
        if phase: self.cb_phase.set(phase)
        # reverse lookup
        if colour: self.cb_colour.set(colour)
        if behaviour: self.cb_behaviour.set(behaviour)
        if author: self.cb_author.set(self.data.get_user_name(author))
        if site: self.cb_site.set(self.data.get_divesite_area_site(site))
        if activity: self.cb_activity.set(activity)

    def _row_selected(self, event):
        """Handle treeview row selection.

        When user clicks on a fish in the treeview, populate the comboboxes
        with that fish's taxonomy for easy identification.

        Args:
            event: Tkinter event
        """
        if not self.tree.selection(): return
        item = self.tree.selection()[0]
        fam, gen, spec, _ = self.tree.item(item, 'values')
        self._reset_info()
        self.cb_family.set(fam)
        self.cb_genus.set(gen)
        self.cb_species.set(spec)


    def fill_tree(self, items):
        """Populate the treeview with fish data.

        Args:
            items: List of lists containing fish data rows [Family, Genus, Species, Common Name]
        """
        self.clear_tree()
        for item in items:
            self.tree.insert('', 'end', values=item)

    def clear_tree(self):
        """Remove all items from the treeview."""
        for i in self.tree.get_children():
            self.tree.delete(i)

    def search(self, event):
        """Search for fish species based on user input.

        Args:
            event: Tkinter event (can be None)
        """
        search_string = self.search_field.get()
        results = self.data.search_fish(search_string)
        self.fill_tree(results.values.tolist())

    def set_family(self, event):
        """Filter species by selected family and update genus/species dropdowns.

        Triggered when user selects a family from the dropdown. Updates the genus
        and species comboboxes with values that belong to the selected family.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        family = self.cb_family.get()
        filtered_df = self.data.filter_fish('Family', family)
        self.cb_genus['values'] = ['genus'] + sorted(filtered_df['Genus'].unique())
        self.cb_genus.set('genus')
        self.cb_species['values'] = ['spec'] + sorted(filtered_df['Species'].unique())
        self.cb_species.set('spec')
        self.fill_tree(filtered_df.values.tolist())

    def set_genus(self, event):
        """Filter species by selected genus and update species dropdown.

        Triggered when user selects a genus from the dropdown. Updates the species
        combobox with values that belong to the selected genus.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        genus = self.cb_genus.get()
        filtered_df = self.data.filter_fish('Genus', genus)
        self.cb_species['values'] = ['spec'] + sorted(filtered_df['Species'].unique())
        self.cb_species.set('spec')
        self.fill_tree(filtered_df.values.tolist())

    def set_species(self, event):
        """Filter and display only the selected species.

        Triggered when user selects a species from the dropdown. Updates the treeview
        to show only entries matching the selected species.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        species = self.cb_species.get()
        self.fill_tree(self.data.filter_fish('Species', species).values.tolist())
        
    def sortby(self, tree, col, descending):
        """Sort treeview items by column.

        Triggered when user clicks on a column header. Sorts the treeview by the
        selected column and toggles between ascending and descending order.

        Args:
            tree: The ttk.Treeview widget to sort
            col: The column name to sort by
            descending: If True, sort in descending order; if False, ascending
        """
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        tree.heading(col, command=lambda c=col: self.sortby(tree, c, not descending))
    
    def _reset_info(self):
        """Reset all comboboxes to their default values and refresh the tree."""
        self.cb_family.set(self.data.family_default)
        self.cb_genus.set(self.data.genus_default)
        self.cb_species.set(self.data.species_default)
        self.cb_confidence.set(self.data.confidence_default)
        self.cb_phase.set(self.data.phase_default)
        self.cb_colour.set(self.data.colour_default)
        self.cb_behaviour.set(self.data.behaviour_default)
        self.search(None)

    def _edit_info(self, event=None):
        """Performs batch editing of files based on user selections."""
        if not hasattr(self, 'editing_files') or len(self.editing_files) == 0:
            self._warn("No files selected for editing")
            return

        renamed_count = 0

        for file_path in self.editing_files:
            if self._edit_single_file(file_path):
                renamed_count += 1

        # Update UI
        self._notice(f"{renamed_count}/{len(self.editing_files)} files were renamed successfully.")
        self._cleanup_after_edit()

    def _edit_single_file(self, file_path):
        """Edit a single file based on current UI selections.

        Returns:
            bool: True if file was renamed successfully, False otherwise
        """
        try:
            filepath, extension = os.path.splitext(file_path)
            basename = os.path.basename(filepath)

            # Parse existing filename
            match = self.assembler.regex_match_identity(basename)
            if not match:
                return False

            info = match.groups()

            # Build new filename from edited/original fields
            edited_fields = self._collect_edited_fields(info)

            new_filename = self.assembler.assemble_edited_filename(
                edited_fields['family'],
                edited_fields['genus'],
                edited_fields['species'],
                edited_fields['confidence'],
                edited_fields['phase'],
                edited_fields['colour'],
                edited_fields['behaviour'],
                edited_fields['author_code'],
                edited_fields['site_string'],
                edited_fields['date'],
                edited_fields['time'],
                edited_fields['activity'],
                edited_fields['filename'],
                extension
            )

            new_filepath = os.path.join(os.path.dirname(file_path), new_filename)

            # Check if target exists
            if os.path.exists(new_filepath):
                return False

            os.rename(file_path, new_filepath)
            return True

        except (OSError, IOError, AttributeError, IndexError) as e:
            self._warn(f"Error editing {os.path.basename(file_path)}: {e}")
            return False

    def _collect_edited_fields(self, info):
        """Collect edited fields from UI or keep original values.

        Args:
            info: Tuple of parsed filename components

        Returns:
            dict: Dictionary of field names to values
        """
        # Field indices in parsed info tuple:
        # 0: family, 1: genus, 2: species, 3: confidence, 4: phase,
        # 5: colour, 6: behaviour, 7: author, 8: site, 9: date,
        # 10: time, 11: activity, 12: original name

        fields = {}

        # Taxonomy fields
        fields['family'] = self.cb_family.get() if self.fields_to_edit[0] else info[0]
        fields['genus'] = self.cb_genus.get() if self.fields_to_edit[1] else info[1]
        fields['species'] = self.cb_species.get() if self.fields_to_edit[2] else info[2]

        # Attribute fields
        fields['confidence'] = self.cb_confidence.get() if self.fields_to_edit[3] else info[3]
        fields['phase'] = self.cb_phase.get() if self.fields_to_edit[4] else info[4]

        # Colour and behaviour (may need reverse lookup for abbreviations)
        if self.fields_to_edit[5]:
            colour_value = self.cb_colour.get()
            # Check if it's already an abbreviation or if we need to convert it
            colour_abbrev = self.data.get_abbreviation_reverse('Colour', colour_value)
            fields['colour'] = colour_abbrev if colour_abbrev else colour_value
        else:
            fields['colour'] = info[5]

        if self.fields_to_edit[6]:
            behaviour_value = self.cb_behaviour.get()
            # Check if it's already an abbreviation or if we need to convert it
            behaviour_abbrev = self.data.get_abbreviation_reverse('Behaviour', behaviour_value)
            fields['behaviour'] = behaviour_abbrev if behaviour_abbrev else behaviour_value
        else:
            fields['behaviour'] = info[6]

        # Author field
        if self.fields_to_edit[7]:
            author = self.cb_author.get()
            fields['author_code'] = self.data.get_user_code(author)
        else:
            fields['author_code'] = info[7]

        # Site field
        if self.fields_to_edit[8]:
            site = self.cb_site.get()
            if ', ' in site:
                fields['site_string'] = self.data.get_divesite_string(*site.split(", ", 1))
            else:
                fields['site_string'] = info[8]
        else:
            fields['site_string'] = info[8]

        # Datetime fields (never edited)
        fields['date'] = info[9]
        fields['time'] = info[10]

        # Activity field
        fields['activity'] = self.cb_activity.get() if self.fields_to_edit[11] else info[11]

        # Original filename (never edited)
        fields['filename'] = info[12]

        return fields

    def _cleanup_after_edit(self):
        """Reset UI state after editing operation.

        Clears the list of files being edited, resets all comboboxes to defaults,
        and disables all fields until new files are dropped.
        """
        self._reset_info()
        self.editing_files = []
        self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False)