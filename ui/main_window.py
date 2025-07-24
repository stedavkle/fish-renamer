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

class MainWindow(TkinterDnD.Tk):
    """The main application window, focused on UI management."""

    def __init__(self):
        super().__init__()
        self.title("Dave's Fish Renamer")
        
        # --- Composition Root: Create and wire up all components ---
        self.config_manager = ConfigManager()
        self.data = DataManager(self.config_manager)
        self.assembler = FilenameAssembler(self.data)
        self.exif = ExifHandler()
        self.web_updater = WebUpdater(app_utils.get_data_path())

        # --- UI Setup ---
        self.tree_columns = ['Family', 'Genus', 'Species', 'Species English']
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
        try:
            icon_path = app_utils.get_app_path().parent / 'config' / 'icon.png'
            ico = Image.open(icon_path)
            photo = ImageTk.PhotoImage(ico)
            self.wm_iconphoto(False, photo)
        except Exception as e:
            print(f"Could not load icon: {e}")

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
            {'label': 'Confidence', 'var': 'cb_confidence', 'values': ["ok", "cf"], 'row': 2, 'col': 0},
            {'label': 'Phase', 'var': 'cb_phase', 'values': ["ad", "IP", "F", "M", "TP", "juv", "pair", "subad", "trans"], 'row': 2, 'col': 1},
            {'label': 'Colour', 'var': 'cb_colour', 'values': list(self.assembler.COLOUR_DICT.keys()), 'row': 2, 'col': 2},
            {'label': 'Behaviour', 'var': 'cb_behaviour', 'values': list(self.assembler.BEHAVIOUR_DICT.keys()), 'row': 2, 'col': 3}
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
        self._notice("Ready")

    def on_data_updated(self):
        """Called to reload all data and refresh UI elements that depend on it."""
        status = self.data.load_all_data()
        self._notice(status)
        self.update_all_comboboxes()
        self.config_manager.save() # CHANGED

    def update_all_comboboxes(self):
        self.cb_family['values'] = ['0-Fam'] + self.data.get_unique_values('Family')
        self.cb_family.set(self.data.family_default)
        self.cb_genus['values'] = ['genus'] + self.data.get_unique_values('Genus')
        self.cb_genus.set(self.data.genus_default)
        self.cb_species['values'] = ['spec'] + self.data.get_unique_values('Species')
        self.cb_species.set(self.data.species_default)
        
        self.cb_author['values'] = self.data.get_unique_values('Full name', 'users_df')
        self.cb_author.set(0)  # Default to empty string
        
        # CHANGED: Replace the old line with this one
        self.cb_site['values'] = self.data.get_formatted_site_list()
        self.cb_site.set("Select site")  # Default to empty string
        
        self.cb_activity['values'] = self.data.get_unique_values('activity', 'activities_df')
        
        # Restore selections from config
        self.cb_author.set(self.config_manager.get_user_pref('author', 'Select Photographer'))
        self.cb_activity.set(self.config_manager.get_user_pref('activity', 'Select activity'))
        
        # Fill tree with all fish initially
        self.fill_tree(self.data.get_all_fish().values.tolist())

    def _show_preferences(self):
        """Opens the preferences and updates dialog window."""
        self.prefs_win = PreferencesWindow(self, self.config_manager, self.web_updater) # CHANGED
        self.wait_window(self.prefs_win)

    def _dnd_files(self, event):
        """Handles drag-and-drop events for renaming files."""
        files = self.splitlist(event.data)
        mode = self.mode.get()
        renamed_count = 0

        if mode == "Edit":
            self.files_to_edit = files # Store full paths for later
            basenames = [os.path.splitext(os.path.basename(f))[0] for f in files]
            
            is_same, values = self.assembler.analyze_files_for_editing(basenames)
            self.fields_to_edit = is_same # Store the flags for the rename operation
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
            return

        for file_path in files:
            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))
            new_filename_body = None

            if mode == "Basic":
                file_date = self.exif.get_creation_date_str(file_path)
                author = self.cb_author.get()
                site_tuple = self.cb_site.get().split(", ")
                activity = self.cb_activity.get()
                new_filename_body = self.assembler.assemble_basic_filename(
                    original_name, file_date, author, site_tuple, activity
                )
            
            elif mode == "Identify":
                family = self.cb_family.get()
                genus = self.cb_genus.get()
                species = self.cb_species.get()
                confidence = self.cb_confidence.get()
                phase = self.cb_phase.get()
                colour = self.cb_colour.get()
                behaviour = self.cb_behaviour.get()
                new_filename_body = self.assembler.assemble_identity_filename(
                    original_name, family, genus, species, confidence, phase, colour, behaviour
                )
            
            if new_filename_body:
                new_path = os.path.join(dir_name, new_filename_body + ext)
                if not os.path.exists(new_path):
                    os.rename(file_path, new_path)
                    renamed_count += 1
        
        # Update status bar
        self._notice(f"{renamed_count}/{len(files)} files renamed.")

    def _notice(self, text):
        self.status.config(foreground="black")
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)

    def _warn(self, text):
        self.status.config(foreground="red")
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)

    def _save_user_prefs(self, event=None):
        self.config_manager.set_user_pref('author', self.cb_author.get()) # CHANGED
        self.config_manager.set_user_pref('site', self.cb_site.get()) # CHANGED
        self.config_manager.set_user_pref('activity', self.cb_activity.get()) # CHANGED
        self.config_manager.save() # CHANGED

    def _toggle_extended_info(self, event=None):
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
        self._notice(f"Switched to '{mode}' mode.")
    
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
        if colour: self.cb_colour.set(self.assembler.COLOUR_DICT_REVERSE.get(colour, "typical colour"))
        if behaviour: self.cb_behaviour.set(self.assembler.BEHAVIOUR_DICT_REVERSE.get(behaviour, "not specified"))
        if author: self.cb_author.set(self.data.get_user_name(author))
        if site: self.cb_site.set(self.data.get_divesite_area_site(site))
        if activity: self.cb_activity.set(activity)

    def _row_selected(self, event):
        if not self.tree.selection(): return
        item = self.tree.selection()[0]
        fam, gen, spec, _ = self.tree.item(item, 'values')
        self.cb_family.set(fam)
        self.cb_genus.set(gen)
        self.cb_species.set(spec)

    def fill_tree(self, items):
        self.clear_tree()
        for item in items:
            self.tree.insert('', 'end', values=item)

    def clear_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def search(self, event):
        search_string = self.search_field.get().lower()
        search_substrings = search_string.split()
        if not search_string:
            self.fill_tree(self.data.get_all_fish().values.tolist())
            return
            
        df = self.data.fish_df
        mask = df.apply(lambda row: all([any([substring.lower() in value.lower() for value in row.values]) for substring in search_substrings]), axis=1)
        self.fill_tree(df[mask].values.tolist())

    def set_family(self, event):
        family = self.cb_family.get()
        filtered_df = self.data.filter_fish('Family', family)
        self.cb_genus['values'] = ['genus'] + sorted(filtered_df['Genus'].unique())
        self.cb_genus.set('genus')
        self.cb_species['values'] = ['spec'] + sorted(filtered_df['Species'].unique())
        self.cb_species.set('spec')
        self.fill_tree(filtered_df.values.tolist())

    def set_genus(self, event):
        genus = self.cb_genus.get()
        filtered_df = self.data.filter_fish('Genus', genus)
        self.cb_species['values'] = ['spec'] + sorted(filtered_df['Species'].unique())
        self.cb_species.set('spec')
        self.fill_tree(filtered_df.values.tolist())

    def set_species(self, event):
        species = self.cb_species.get()
        self.fill_tree(self.data.filter_fish('Species', species).values.tolist())
        
    def sortby(self, tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        tree.heading(col, command=lambda c=col: self.sortby(tree, c, not descending))
    
    def _reset_info(self):
        self.cb_family.set(self.data.family_default)
        self.cb_genus.set(self.data.genus_default)
        self.cb_species.set(self.data.species_default)
        self.cb_confidence.set("ok")
        self.cb_phase.set("ad")
        self.cb_colour.set("typical colour")
        self.cb_behaviour.set("not specified")

    def _edit_info(self, event=None):
        # Placeholder for the edit logic
        if len(self.editing_files) == 0:
            self._warn("No files selected")
            return

        renamed = 0
        for path in self.editing_files:
            filepath, extension = os.path.splitext(path)
            info = self.assembler.regex_match_identity(os.path.basename(filepath)).groups()
            # 0 family, 1 genus, 2 species, 3 confidence, 4 phase, 5 colour, 6 behaviour, 7 author, 8 site, 9 date, 10 time, 11 activity, 12 original name
            family = self.cb_family.get() if self.fields_to_edit[0] else info[0]
            genus = self.cb_genus.get() if self.fields_to_edit[1] else info[1]
            species = self.cb_species.get() if self.fields_to_edit[2] else info[2]
            confidence = self.cb_confidence.get() if self.fields_to_edit[3] else info[3]
            phase = self.cb_phase.get() if self.fields_to_edit[4] else info[4]
            colour = self.assembler.COLOUR_DICT[self.cb_colour.get()] if self.fields_to_edit[5] else info[5]
            behaviour = self.assembler.BEHAVIOUR_DICT[self.cb_behaviour.get()] if self.fields_to_edit[6] else info[6]
            author = self.cb_author.get()
            author_code = self.data.get_user_code(author) if self.fields_to_edit[7] else info[7]
            site = self.cb_site.get()
            site_string = self.data.get_divesite_string(*site.split(", ")) if self.fields_to_edit[8] else info[8]
            date = info[9]
            time = info[10]
            activity = self.cb_activity.get() if self.fields_to_edit[11] else info[11]
            filename = info[12]


            new_filename = self.assembler.assemble_edited_filename(
                family, genus, species, confidence, phase, colour, behaviour, author_code,
                site_string, date, time, activity, filename, extension
            )
            
            new_filepath = os.path.join(os.path.dirname(path), new_filename)
            if os.path.exists(new_filepath):
                continue
            os.rename(path, new_filepath)
            renamed += 1
        self._notice(f"{renamed}/{len(self.editing_files)} files were renamed successfully.")
        self._reset_info()
        self.editing_files = []