# ui/main_window.py
import tkinter as tk
from tkinter import ttk, font as tkFont
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import logging
from PIL import Image, ImageTk
from tktooltip import ToolTip

# Import refactored components
from src.config_manager import ConfigManager
from src.data_manager import DataManager
from src.filename_assembler import FilenameAssembler
from src.exif_handler import ExifHandler
from src.exiftool_handler import ExifToolHandler
from src.web_updater import WebUpdater
from .preferences_window import PreferencesWindow
from src import app_utils
from src.constants import (
    MAIN_WINDOW_TITLE,
    TREE_COLUMNS,
    STATUS_READY,
    DEFAULT_PHOTOGRAPHER_TEXT,
    DEFAULT_SITE_TEXT,
    DEFAULT_ACTIVITY_TEXT,
    SEARCH_PLACEHOLDER,
    IMAGE_FILE_EXTENSIONS
)

logger = logging.getLogger(__name__)

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
        self.exiftool = ExifToolHandler()
        self.web_updater = WebUpdater(app_utils.get_data_path())

        # Undo history for rename operations
        self.rename_history = []  # List of (old_path, new_path) tuples

        # Tab enable/disable flag (used instead of widget state for tk.Label tabs)
        self._tabs_enabled = True

        # Edit mode tracking
        self.editing_files = []
        self.editing_format = None  # 'basic' or 'identity'
        self.fields_to_edit = None

        # Processing state flag (prevents re-entrancy during batch operations)
        self._processing = False

        # --- UI Setup ---
        self.tree_columns = TREE_COLUMNS
        self._setup_widgets()

        # Set fixed width (height can still change with modes)
        self.update_idletasks()  # Ensure geometry is calculated
        self.geometry(f"800x{self.winfo_reqheight()}")
        self.minsize(800, 0)
        self.maxsize(800, 2000)

        self.on_data_updated() # Initial data load and UI population

    def _setup_widgets(self):
        """Master method to build the entire UI by calling sub-methods."""
        self._setup_icon()
        self._setup_dnd()
        self._configure_main_container_grid(self)
        self._setup_mode_tabs()  # Add tabs at the very top
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
        self._setup_tooltips()
        self._setup_exif_frame()  # EXIF mode UI
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
        self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        self._drop_highlight_color = '#e3f2fd'  # Light blue
        self._default_bg = 'SystemButtonFace'

    def _on_drag_enter(self, event):
        """Highlight window when files are dragged over it."""
        self.config(bg=self._drop_highlight_color)
        self._notice("Drop files here to rename...")

    def _on_drag_leave(self, event):
        """Reset window background when files are dragged away."""
        self.config(bg=self._default_bg)
        # Restore mode hint
        mode_hints = {
            'Basic': "Drop files to add photographer, site, and activity info",
            'Identify': "Search or select a species, then drop files to identify",
            'Edit': "Drop files to batch edit their metadata",
            'Meta': "Drop Basic/Identify format files to auto-extract GPS from filename"
        }
        self._notice(mode_hints[self.mode.get()])

    def _configure_main_container_grid(self, container):
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)  # Row 2 is upper_frame (treeview)

    def _setup_mode_tabs(self):
        """Create 4 large colored tabs at the top for mode switching."""
        self.mode = tk.StringVar(value="Basic")

        self.tabs_frame = tk.Frame(self)
        self.tabs_frame.grid(row=0, column=0, sticky='ew')

        # Configure columns to expand equally
        for col in range(4):
            self.tabs_frame.grid_columnconfigure(col, weight=1)

        # Define tab colors
        self.tab_colors = {
            'Basic': {'bg': '#4CAF50', 'active': '#66BB6A'},      # Green
            'Identify': {'bg': '#2196F3', 'active': '#42A5F5'},   # Blue
            'Edit': {'bg': '#FF9800', 'active': '#FFB74D'},       # Orange
            'Meta': {'bg': '#9C27B0', 'active': '#AB47BC'}        # Purple
        }

        self.tab_buttons = {}
        for col, mode_name in enumerate(['Basic', 'Identify', 'Edit', 'Meta']):
            # Add "(Beta)" suffix for EXIF tab display
            display_name = "Meta (Beta)" if mode_name == 'Meta' else mode_name
            lbl = tk.Label(
                self.tabs_frame,
                text=display_name,
                font=('Arial', 14, 'bold'),
                bg=self.tab_colors[mode_name]['bg'],
                fg='white',
                relief='flat',
                pady=12,
                cursor='hand2'
            )
            lbl.bind('<Button-1>', lambda e, m=mode_name: self._on_tab_click(m))
            lbl.grid(row=0, column=col, sticky='ew')
            self.tab_buttons[mode_name] = lbl

        # Set initial active state
        self._update_tab_appearance()

        # Status bar below tabs
        self.status_frame = tk.Frame(self, bg='#f0f0f0', pady=5)
        self.status_frame.grid(row=1, column=0, sticky='ew')
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            self.status_frame,
            text="",
            font=('Arial', 10),
            bg='#f0f0f0',
            fg='#333333',
            anchor='w',
            padx=10
        )
        self.status_label.grid(row=0, column=0, sticky='ew')

        # Progress bar (hidden by default)
        self.progress_frame = tk.Frame(self.status_frame, bg='#f0f0f0')
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#666666',
            anchor='w',
            padx=10
        )
        self.progress_label.pack(side='left')
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=200
        )
        self.progress_bar.pack(side='left', padx=(0, 10), fill='x', expand=True)

    def _on_tab_click(self, mode_name):
        """Gate tab clicks through the enabled flag."""
        if self._tabs_enabled:
            self._select_mode_tab(mode_name)

    def _select_mode_tab(self, mode_name):
        """Handle tab selection and update mode."""
        self.mode.set(mode_name)
        self._update_tab_appearance()
        self._toggle_extended_info()
        self._adjust_window_height()

    def _adjust_window_height(self):
        """Adjust window height to fit all visible content without compressing the tree."""
        # Force geometry recalculation by temporarily allowing window to shrink
        self.update_idletasks()

        # Determine if tree should be visible based on mode
        mode = self.mode.get()
        tree_visible = mode in ('Identify', 'Edit')
        exif_panel_visible = mode == 'Meta'

        # Calculate required height based on visible elements
        required_height = 0

        # Tabs and status bar (always visible)
        required_height += self.tabs_frame.winfo_reqheight()
        required_height += self.status_frame.winfo_reqheight()

        # Tree area (if visible in current mode)
        if tree_visible:
            required_height += self.upper_frame.winfo_reqheight()
            required_height += self.middle_frame.winfo_reqheight()

        # EXIF panel (if visible)
        if exif_panel_visible and hasattr(self, 'exif_frame'):
            required_height += self.exif_frame.winfo_reqheight()

        # Bottom controls - calculate based on visible rows per mode
        if not exif_panel_visible:
            # Each row is approximately 30px (label) + 30px (combobox) + padding
            row_height = 35
            if mode == 'Basic':
                # Basic mode: Author/Site/Activity/Camera (1 label row + 1 combo row) + Maps link
                required_height += row_height * 3
            elif mode == 'Identify':
                # Identify mode: Taxonomy (2 rows) + Attributes (2 rows)
                required_height += row_height * 4
            elif mode == 'Edit':
                # Edit mode: Similar to Identify when populated
                required_height += row_height * 4

        # Add padding
        required_height += 30

        # Get current width
        current_width = self.winfo_width()
        if current_width < 800:
            current_width = 800

        # Set geometry with appropriate minimum
        min_height = 200 if mode == 'Basic' else 300
        final_height = max(required_height, min_height)

        self.geometry(f"{current_width}x{final_height}")

    def _update_tab_appearance(self):
        """Update tab visual appearance based on current mode."""
        current_mode = self.mode.get()
        for mode_name, btn in self.tab_buttons.items():
            if mode_name == current_mode:
                btn.config(
                    bg=self.tab_colors[mode_name]['bg'],
                    fg='white',
                    relief='sunken'
                )
            else:
                btn.config(
                    bg='#90D5FF',  # Light grey for inactive tabs (better contrast)
                    fg='#424242',  # Dark text for visibility
                    relief='flat'
                )

    def _create_frames(self, main_container):
        frames = [
            ('upper_frame', {'row': 2, 'column': 0, 'sticky': 'nsew'}),
            ('middle_frame', {'row': 3, 'column': 0, 'sticky': 'nsew'}),
            ('bottom_frame', {'row': 4, 'column': 0, 'sticky': 'nsew', 'padx': 10, 'pady': 10}),
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

        # Edit menu with undo
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo Last Rename", command=self._undo_last_rename, accelerator="Ctrl+Z")
        self.bind('<Control-z>', lambda e: self._undo_last_rename())

        # Settings menu
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=config_menu)
        config_menu.add_command(label="Preferences & Updates", command=self._show_preferences)

    def _setup_search_field(self):
        self.search_field = ttk.Entry(self.middle_frame)
        self.search_field.pack(fill='x', padx=10, pady=10)
        self.search_field.insert(0, SEARCH_PLACEHOLDER)
        self.search_field.config(foreground='gray')
        self.search_field.bind("<FocusIn>", self._on_search_focus_in)
        self.search_field.bind("<FocusOut>", self._on_search_focus_out)
        self.search_field.bind("<Return>", self.search)
        self.search_field.bind("<KeyRelease>", self._on_search_key_release)
        self._search_after_id = None

    def _on_search_focus_in(self, event):
        """Clear placeholder text when search field gains focus."""
        if self.search_field.get() == SEARCH_PLACEHOLDER:
            self.search_field.delete(0, tk.END)
            self.search_field.config(foreground='black')

    def _on_search_focus_out(self, event):
        """Restore placeholder text when search field loses focus and is empty."""
        if not self.search_field.get():
            self.search_field.insert(0, SEARCH_PLACEHOLDER)
            self.search_field.config(foreground='gray')

    def _on_search_key_release(self, event):
        """Handle key release in search field with debounce for auto-filtering."""
        # Ignore modifier keys and navigation keys
        if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                           'Alt_L', 'Alt_R', 'Return', 'Tab', 'Escape',
                           'Up', 'Down', 'Left', 'Right', 'Home', 'End'):
            return

        # Cancel any pending search
        if self._search_after_id:
            self.after_cancel(self._search_after_id)

        # Schedule search after 300ms of no typing
        self._search_after_id = self.after(300, lambda: self.search(None))

    def _setup_treeview_and_scrollbars(self):
        # Set height=10 to ensure minimum visible rows
        self.tree = ttk.Treeview(self.upper_frame, columns=self.tree_columns, show="headings", height=10)
        self.vsb = ttk.Scrollbar(self.upper_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.upper_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.upper_frame.grid_columnconfigure(0, weight=1)
        self.upper_frame.grid_rowconfigure(0, weight=1)
        self.tree.bind("<ButtonRelease-1>", self._row_selected)

    def _build_tree_headers(self):
        for col in self.tree_columns:
            self.tree.heading(col, text=col.title(), command=lambda c=col: self.sortby(self.tree, c, False))
            self.tree.column(col, width=tkFont.Font().measure(col.title()), anchor='w')

    def _setup_tooltips(self):
        """Add tooltips to UI elements for better usability."""
        ToolTip(self.search_field, msg="Search by family, genus, species, or common name")
        ToolTip(self.cb_family, msg="Select a fish family to filter")
        ToolTip(self.cb_genus, msg="Select a genus within the family")
        ToolTip(self.cb_species, msg="Select the species")
        ToolTip(self.cb_confidence, msg="How certain is this identification?")
        ToolTip(self.cb_phase, msg="Life phase (juvenile, adult, etc.)")
        ToolTip(self.cb_colour, msg="Color variation")
        ToolTip(self.cb_behaviour, msg="Observed behaviour")
        ToolTip(self.cb_author, msg="Photographer who took the image")
        ToolTip(self.cb_site, msg="Dive site location")
        ToolTip(self.cb_activity, msg="Activity type (diving, snorkeling, etc.)")
        ToolTip(self.cb_camera, msg="Camera model used to take the photo")

    def _setup_combobox_group(self, frame, configs):
        for config in configs:
            lbl = ttk.Label(frame, text=config['label'])
            lbl.grid(row=config['row'], column=config['col'], padx=5, pady=2, sticky='ew')
            cb = ttk.Combobox(frame, values=config.get('values', []), state='readonly', height=15)
            cb.grid(row=config['row']+1, column=config['col'], padx=5, pady=2, sticky='ew')
            if cb['values']:
                cb.current(0)
            if 'cmd' in config: cb.bind("<<ComboboxSelected>>", config['cmd'])
            setattr(self, config['var'], cb)
            setattr(self, config['var'] + '_label', lbl)  # Store label reference for show/hide

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
            {'label': 'Activity', 'var': 'cb_activity', 'row': 4, 'col': 2, 'cmd': self._save_user_prefs},
            {'label': 'Camera', 'var': 'cb_camera', 'row': 4, 'col': 3, 'cmd': self._save_user_prefs}
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
        self.bt_rename = tk.Button(self.edit_frame, text="Rename", command=self._edit_info)
        self.bt_rename.grid(row=0, column=0, padx=5, pady=2, sticky='ew')
        self.bt_rename.grid_remove()

    def _setup_exif_frame(self):
        """Setup the EXIF mode UI panel."""
        self.exif_frame = ttk.Frame(self, padding=10)
        self.exif_frame.grid(row=4, column=0, sticky='nsew')
        self.exif_frame.grid_remove()  # Hidden by default

        # ExifTool status section
        status_frame = ttk.LabelFrame(self.exif_frame, text="ExifTool Status", padding=10)
        status_frame.pack(fill='x', padx=5, pady=5)

        self.exiftool_status_label = ttk.Label(status_frame, text="Checking...")
        self.exiftool_status_label.pack(anchor='w')

        self.exiftool_version_label = ttk.Label(status_frame, text="")
        self.exiftool_version_label.pack(anchor='w')

        # Install/download buttons frame
        self.exiftool_buttons_frame = ttk.Frame(status_frame)
        self.exiftool_buttons_frame.pack(fill='x', pady=(10, 0))

        self.btn_install_exiftool = ttk.Button(
            self.exiftool_buttons_frame,
            text="Install ExifTool (Windows)",
            command=self._install_exiftool
        )

        self.btn_open_website = ttk.Button(
            self.exiftool_buttons_frame,
            text="Open ExifTool Website",
            command=self._open_exiftool_website
        )

        self.btn_refresh_status = ttk.Button(
            self.exiftool_buttons_frame,
            text="Refresh",
            command=self._update_exiftool_status
        )
        self.btn_refresh_status.pack(side='left', padx=(0, 5))

        # Instructions
        instructions_frame = ttk.LabelFrame(self.exif_frame, text="Instructions", padding=10)
        instructions_frame.pack(fill='x', padx=5, pady=5)

        instructions_text = (
            "1. Ensure ExifTool is installed (see status above)\n"
            "2. Drop image files with Basic or Identify format filenames\n"
            "3. Review extracted locations in the preview\n"
            "4. Confirm to write GPS coordinates to images"
        )
        ttk.Label(instructions_frame, text=instructions_text, justify='left').pack(anchor='w')

    def _update_exiftool_status(self):
        """Update the ExifTool status display."""
        import sys

        if self.exiftool.is_available():
            version = self.exiftool.get_version()
            self.exiftool_status_label.config(
                text="Status: Installed",
                foreground='green'
            )
            self.exiftool_version_label.config(text=f"Version: {version}")
            self.btn_install_exiftool.pack_forget()
            self.btn_open_website.pack_forget()
        else:
            self.exiftool_status_label.config(
                text="Status: Not installed",
                foreground='red'
            )
            self.exiftool_version_label.config(text="ExifTool is required to write GPS coordinates")

            # Show install button on Windows, website button on other platforms
            if sys.platform == "win32":
                self.btn_install_exiftool.pack(side='left', padx=(0, 5))
            self.btn_open_website.pack(side='left', padx=(0, 5))

    def _install_exiftool(self):
        """Attempt to download and install ExifTool."""
        self.exiftool_status_label.config(text="Installing...", foreground='orange')
        self.update_idletasks()

        def progress_callback(percent, message):
            self.exiftool_version_label.config(text=f"{message} ({percent}%)")
            self.update_idletasks()

        success, message = self.exiftool.download_and_install(progress_callback)

        if success:
            self._notice(message)
        else:
            self._warn(message)

        self._update_exiftool_status()

    def _open_exiftool_website(self):
        """Open the ExifTool website in the default browser."""
        import webbrowser
        webbrowser.open(self.exiftool.get_website_url())

    def _setup_status_text(self):
        """Status is now handled by status_label in the status bar below tabs."""
        pass  # Status bar is created in _setup_mode_tabs

    def on_data_updated(self):
        """Reload all data files and refresh the UI.

        Called after updating data files from the web or when explicitly requested.
        Reloads CSV/JSON data files, updates all comboboxes, and saves config.
        """
        self.data.load_all_data()
        self.update_all_comboboxes()
        self.config_manager.save()
        # Show mode hint after data is loaded
        self._toggle_extended_info()

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

        # Filter out empty strings and prepend default text
        author_values = [v for v in self.data.get_unique_values('Full name', 'users_df') if v]
        self.cb_author['values'] = [DEFAULT_PHOTOGRAPHER_TEXT] + author_values
        self.cb_author.set(DEFAULT_PHOTOGRAPHER_TEXT)  # Default to placeholder text

        self.cb_confidence['values'] = self.data.get_active_labels('Confidence')
        self.cb_phase['values'] = self.data.get_active_labels('Phase')
        self.cb_colour['values'] = self.data.get_active_labels('Colour')
        self.cb_behaviour['values'] = self.data.get_active_labels('Behaviour')

        # Prepend default text to site list
        site_values = self.data.get_formatted_site_list()
        self.cb_site['values'] = [DEFAULT_SITE_TEXT] + site_values
        self.cb_site.set(DEFAULT_SITE_TEXT)  # Default to placeholder text

        # Filter out empty strings and prepend default text
        activity_values = [v for v in self.data.get_unique_values('activity', 'activities_df') if v]
        self.cb_activity['values'] = [DEFAULT_ACTIVITY_TEXT] + activity_values

        # Load camera values
        camera_values = self.data.get_camera_models()
        self.cb_camera['values'] = camera_values
        if camera_values:
            default_camera = camera_values[0]
        else:
            default_camera = ''

        # Restore selections from config
        self.cb_author.set(self.config_manager.get_user_pref('author', DEFAULT_PHOTOGRAPHER_TEXT))
        self.cb_site.set(self.config_manager.get_user_pref('site', DEFAULT_SITE_TEXT))
        self.cb_activity.set(self.config_manager.get_user_pref('activity', DEFAULT_ACTIVITY_TEXT))
        self.cb_camera.set(self.config_manager.get_user_pref('camera', default_camera))

        # Fill tree with all fish initially
        self.fill_tree(self.data.get_all_fish().values.tolist())

    def _show_preferences(self):
        """Open the preferences and updates dialog window.

        Creates a modal preferences window where users can configure data file
        locations and update data from HiDrive.
        """
        self.prefs_win = PreferencesWindow(self, self.config_manager, self.web_updater)
        self.wait_window(self.prefs_win)

    def _is_preview_enabled(self):
        """Check if renaming preview is enabled in preferences.

        Returns:
            bool: True if preview is enabled (default), False otherwise
        """
        setting = self.config_manager.get_misc('enable_renaming_preview', 'true')
        return setting.lower() == 'true'

    def _dnd_files(self, event):
        """Handle drag-and-drop events for renaming files.

        Dispatches to the appropriate handler based on current mode (Basic,
        Identify, or Edit). Files are passed as a list of absolute paths.

        Args:
            event: Tkinter DND event containing dropped file paths
        """
        # Ignore drops during processing
        if getattr(self, '_processing', False):
            return

        # Reset background color
        self.config(bg=self._default_bg)

        files = self.splitlist(event.data)
        mode = self.mode.get()

        mode_handlers = {
            "Edit": self._handle_edit_mode,
            "Basic": self._handle_basic_mode,
            "Identify": self._handle_identify_mode,
            "Meta": self._handle_exif_mode
        }

        handler = mode_handlers.get(mode)
        if handler:
            handler(files)
        else:
            self._warn(f"Unknown mode: {mode}")

    def _handle_edit_mode(self, files):
        """Prepare files for batch editing.

        Analyzes dropped files to find common fields that can be batch edited.
        Supports both Basic and Identity format files.
        Enables only those fields in the UI and populates them with common values.

        Args:
            files: List of absolute file paths to prepare for editing
        """
        self.files_to_edit = files  # Store full paths for later
        basenames = [os.path.splitext(os.path.basename(f))[0] for f in files]

        # Detect file format (Basic or Identity)
        first_basename = basenames[0]
        is_identity_format = self.assembler.regex_match_identity(first_basename) is not None
        is_basic_format = self.assembler.regex_match_basic(first_basename) is not None

        try:
            if is_identity_format:
                # Use Identity format analysis
                is_same, values = self.assembler.analyze_files_for_editing(basenames)
                self.editing_format = 'identity'
            elif is_basic_format:
                # Use Basic format analysis
                is_same, values = self.assembler.analyze_basic_files_for_editing(basenames)
                self.editing_format = 'basic'
            else:
                self._warn("Files are not in Basic or Identity format.")
                return
        except ValueError as e:
            self._warn(f"Error analyzing files: {e}")
            return

        self.fields_to_edit = is_same  # Store the flags for the rename operation
        self.editing_files = files

        if not any(is_same):
            self._warn("Files have no common editable information.")
            return

        # Map the 14-element list to the 11 UI controls
        # [0-6: taxonomy, 7: author, 8: site, 9-10: date/time (not editable), 11: activity, 12: camera, 13: original (not editable)]
        ui_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12]
        ui_flags = [is_same[i] for i in ui_indices]
        ui_values = [values[i] for i in ui_indices]

        # Convert attribute abbreviations to labels (only for Identity format)
        if self.editing_format == 'identity':
            for i, field in zip([3, 4, 5, 6], ['Confidence', 'Phase', 'Colour', 'Behaviour']):
                if ui_values[i] is not None:
                    ui_values[i] = self.data.labels[field][str(ui_values[i])]

        # Convert camera abbreviation to full name
        if ui_values[10] is not None:  # Camera is now at index 10
            camera_full_name = self.data.get_camera_full_name(ui_values[10])
            if camera_full_name:
                ui_values[10] = camera_full_name

        self._toggle_checkboxes(*ui_flags)
        self._set_checkboxes(*ui_values)

        format_name = "Identity" if self.editing_format == 'identity' else "Basic"
        self._notice(f"Loaded {len(files)} {format_name} format files for editing. Make changes and click 'Rename'.")
        # Adjust window to fit newly visible controls
        self._adjust_window_height()

    def _handle_basic_mode(self, files):
        """Rename files with basic metadata (photographer, site, activity, camera).

        Validates that photographer, site, activity, and camera are selected, then
        renames each file with EXIF date and basic metadata.

        Args:
            files: List of absolute file paths to rename
        """
        author = self.cb_author.get()
        site_raw = self.cb_site.get()
        activity = self.cb_activity.get()
        camera = self.cb_camera.get()

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
        if not camera:
            self._warn("Please select a camera model.")
            return

        # Get camera abbreviation for filename
        camera_abbrev = self.data.get_camera_abbreviation(camera)
        if not camera_abbrev:
            self._warn("Invalid camera model.")
            return

        site_tuple = tuple(site_raw.split(", ", 1))

        # Generate previews
        previews = self._generate_previews_basic(files, author, site_tuple, activity, camera_abbrev)

        # Show preview dialog if enabled, otherwise proceed with all valid files
        if self._is_preview_enabled():
            from .preview_dialog import BatchPreviewDialog
            dialog = BatchPreviewDialog(self, previews)
            self.wait_window(dialog)

            to_rename = dialog.get_files_to_rename()
            if not to_rename:
                self._notice("Rename cancelled")
                return
        else:
            # Skip errors automatically when preview is disabled
            to_rename = [p for p in previews if not p.get('error')]
            if not to_rename:
                self._notice("No valid files to rename")
                return

        # Clear history for new rename batch
        self.rename_history.clear()

        renamed_count = 0
        total = len(to_rename)
        self._show_progress(total, f"Renaming 0/{total}...")

        for i, mapping in enumerate(to_rename):
            if self._rename_single_file_basic(mapping['path'], author, site_tuple, activity, camera_abbrev):
                renamed_count += 1
            self._update_progress(i + 1, f"Renaming {i + 1}/{total}...")

        self._hide_progress()
        self._notice(f"{renamed_count}/{len(to_rename)} files renamed.")

    def _generate_previews_basic(self, files, author, site_tuple, activity, camera_abbrev):
        """Generate preview data for basic mode renames.

        Uses ExifTool batch reading when available for faster processing of
        multiple files. Falls back to PIL for single files or when ExifTool
        is not available.

        Args:
            files: List of file paths
            author: Photographer name
            site_tuple: (area, site) tuple
            activity: Activity type
            camera_abbrev: Camera abbreviation (e.g., 'S-A7IV')

        Returns:
            List of dicts with keys: path, original, new, error
        """
        total = len(files)

        # Use ExifTool batch reading for multiple files when available
        if total > 1 and self.exiftool.is_available():
            self._show_progress(total, f"Reading EXIF 0/{total}...")

            # Progress callback for batch reading
            def on_exif_progress(current, total_files):
                self._update_progress(current, f"Reading EXIF {current}/{total_files}...")

            # Batch read all dates at once
            date_map = self.exiftool.batch_read_creation_dates(files, progress_callback=on_exif_progress)
            self._hide_progress()

            previews = []
            for file_path in files:
                original = os.path.basename(file_path)
                name, ext = os.path.splitext(original)

                preview = {'path': file_path, 'original': original, 'new': None, 'error': None}

                file_date = date_map.get(file_path, "")
                if not file_date:
                    preview['error'] = 'No EXIF date'
                else:
                    new_name = self.assembler.assemble_basic_filename(name, file_date, author, site_tuple, activity, camera_abbrev)
                    if new_name:
                        preview['new'] = new_name + ext
                    else:
                        preview['error'] = 'Already processed'

                previews.append(preview)
            return previews

        # Fallback to PIL for single files or when ExifTool unavailable
        previews = []
        for i, file_path in enumerate(files):
            # Update status bar with progress and keep UI responsive
            self._notice(f"Processing {i + 1} of {total} files...")
            self.update_idletasks()

            original = os.path.basename(file_path)
            name, ext = os.path.splitext(original)

            preview = {'path': file_path, 'original': original, 'new': None, 'error': None}

            file_date = self.exif.get_creation_date_str(file_path)
            if not file_date:
                preview['error'] = 'No EXIF date'
            else:
                new_name = self.assembler.assemble_basic_filename(name, file_date, author, site_tuple, activity, camera_abbrev)
                if new_name:
                    preview['new'] = new_name + ext
                else:
                    preview['error'] = 'Already processed'

            previews.append(preview)
        return previews

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
        confidence = self.data.get_abbreviation_reverse("Confidence", self.cb_confidence.get())
        phase = self.data.get_abbreviation_reverse("Phase", self.cb_phase.get())
        colour = self.data.get_abbreviation_reverse("Colour", self.cb_colour.get())
        behaviour = self.data.get_abbreviation_reverse("Behaviour", self.cb_behaviour.get())

        # Validate that species is not set when genus is default
        if genus == self.data.genus_default and species != self.data.species_default:
            self._warn("Cannot set species when genus is on default. Please select a genus first.")
            return

        # Generate previews
        previews = self._generate_previews_identify(
            files, family, genus, species, confidence, phase, colour, behaviour
        )

        # Show preview dialog if enabled, otherwise proceed with all valid files
        if self._is_preview_enabled():
            from .preview_dialog import BatchPreviewDialog
            dialog = BatchPreviewDialog(self, previews)
            self.wait_window(dialog)

            to_rename = dialog.get_files_to_rename()
            if not to_rename:
                self._notice("Rename cancelled")
                return
        else:
            # Skip errors automatically when preview is disabled
            to_rename = [p for p in previews if not p.get('error')]
            if not to_rename:
                self._notice("No valid files to rename")
                return

        # Clear history for new rename batch
        self.rename_history.clear()

        renamed_count = 0
        total = len(to_rename)
        self._show_progress(total, f"Renaming 0/{total}...")

        for i, mapping in enumerate(to_rename):
            if self._rename_single_file_identity(
                mapping['path'], family, genus, species, confidence, phase, colour, behaviour
            ):
                renamed_count += 1
            self._update_progress(i + 1, f"Renaming {i + 1}/{total}...")

        self._hide_progress()
        self._notice(f"{renamed_count}/{len(to_rename)} files renamed.")
        self._reset_info()

    def _generate_previews_identify(self, files, family, genus, species,
                                     confidence, phase, colour, behaviour):
        """Generate preview data for identify mode renames.

        Args:
            files: List of file paths
            family: Fish family
            genus: Fish genus
            species: Fish species
            confidence: Confidence level abbreviation
            phase: Phase abbreviation
            colour: Colour abbreviation
            behaviour: Behaviour abbreviation

        Returns:
            List of dicts with keys: path, original, new, error
        """
        previews = []
        total = len(files)
        for i, file_path in enumerate(files):
            # Update status bar with progress and keep UI responsive
            self._notice(f"Processing {i + 1} of {total} files...")
            self.update_idletasks()

            original = os.path.basename(file_path)
            name, ext = os.path.splitext(original)

            preview = {'path': file_path, 'original': original, 'new': None, 'error': None}

            new_name = self.assembler.assemble_identity_filename(
                name, family, genus, species, confidence, phase, colour, behaviour
            )
            if new_name:
                preview['new'] = new_name + ext
            else:
                preview['error'] = 'Invalid format'

            previews.append(preview)
        return previews

    def _handle_exif_mode(self, files):
        """Write GPS coordinates to image EXIF data.

        Extracts site string from filenames, looks up coordinates from the
        divesites database, and writes GPS coordinates to image EXIF data.

        Args:
            files: List of absolute file paths to process
        """
        # Check ExifTool availability
        if not self.exiftool.is_available():
            self._warn("ExifTool is not installed. Please install it first.")
            return

        # Generate previews by extracting site from each filename
        previews = self._generate_previews_exif(files)

        # Show preview dialog if enabled, otherwise proceed with all valid files
        if self._is_preview_enabled():
            from .exif_preview_dialog import ExifPreviewDialog
            dialog = ExifPreviewDialog(self, previews)
            self.wait_window(dialog)

            to_process = dialog.get_files_to_process()
            if not to_process:
                self._notice("GPS writing cancelled")
                return
        else:
            # Skip errors automatically when preview is disabled
            to_process = [p for p in previews if not p.get('error')]
            if not to_process:
                self._notice("No valid files to process")
                return

        # Write GPS to files and rename them
        success_count = 0
        rename_count = 0
        total = len(to_process)
        self._show_progress(total, f"Writing GPS 0/{total}...")

        for i, mapping in enumerate(to_process):
            # Write GPS coordinates
            success, _ = self.exiftool.write_gps_coordinates(
                mapping['path'], mapping['lat'], mapping['lon']
            )
            if success:
                success_count += 1

                # Rename file to include GPS marker (if filename changed)
                new_filename = mapping.get('new_filename')
                current_filename = os.path.basename(mapping['path'])

                if new_filename and new_filename != current_filename:
                    dir_name = os.path.dirname(mapping['path'])
                    new_path = os.path.join(dir_name, new_filename)

                    # Check if target already exists
                    if not os.path.exists(new_path):
                        try:
                            os.rename(mapping['path'], new_path)
                            rename_count += 1
                            logger.debug(f"Renamed: {current_filename} -> {new_filename}")
                        except OSError as e:
                            logger.warning(f"Failed to rename {current_filename}: {e}")
                    else:
                        logger.warning(f"Cannot rename to {new_filename}: file already exists")
                elif new_filename == current_filename:
                    # Filename unchanged (GPS marker already present)
                    logger.debug(f"Skipped rename for {current_filename}: GPS marker already present")
                    rename_count += 1  # Count as successful since no rename needed

            self._update_progress(i + 1, f"Writing GPS {i + 1}/{total}...")

        self._hide_progress()
        if rename_count == success_count:
            self._notice(f"GPS written and {rename_count}/{len(to_process)} files renamed")
        else:
            self._notice(f"GPS written to {success_count}/{len(to_process)} files, {rename_count} renamed")

    def _construct_gps_filename(self, filename_without_ext):
        """Construct filename with GPS marker at the end.

        New format:
        - Identity: Family_Genus_Species_B_conf_phase_colour_behav_Author_Site_Date_Time_Activity_Camera_Filename_G
        - Basic: Author_Site_Date_Time_Activity_Camera_Filename_G

        If _G already exists at end, this is idempotent (no change).
        If _N exists at end, replace it with _G.

        Args:
            filename_without_ext: Filename without extension

        Returns:
            New filename with GPS marker at end, or None if format is invalid
        """
        # Check if _G already exists at the end
        if filename_without_ext.endswith('_G'):
            return filename_without_ext  # Already has GPS marker

        # Check if _N exists at the end - replace with _G
        if filename_without_ext.endswith('_N'):
            return filename_without_ext[:-2] + '_G'

        # Try Identity format first
        match = self.assembler.regex_match_identity(filename_without_ext)
        if match:
            # Append _G to end (for legacy files without _N)
            return f"{filename_without_ext}_G"

        # Try Basic format
        match = self.assembler.regex_match_basic(filename_without_ext)
        if match:
            # Append _G to end (for legacy files without _N)
            return f"{filename_without_ext}_G"

        # Invalid format
        return None

    def _generate_previews_exif(self, files):
        """Generate preview data for EXIF GPS writing.

        Extracts site string from each filename, looks up coordinates
        from the divesites database, and generates new filename with GPS marker.

        Args:
            files: List of file paths

        Returns:
            List of dicts with keys: path, filename, site_string, site_name, lat, lon, new_filename, error
        """
        previews = []
        for file_path in files:
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)

            preview = {
                'path': file_path,
                'filename': filename,
                'site_string': None,
                'site_name': None,
                'lat': None,
                'lon': None,
                'new_filename': None,
                'error': None
            }

            # Check if file exists and is an image
            if not os.path.exists(file_path):
                preview['error'] = 'File not found'
                previews.append(preview)
                continue

            if ext.lower() not in IMAGE_FILE_EXTENSIONS:
                preview['error'] = 'Not an image file'
                previews.append(preview)
                continue

            # Extract site string from filename
            site_string = self.assembler.extract_site_string(name)
            if not site_string:
                preview['error'] = 'Invalid filename format'
                previews.append(preview)
                continue

            preview['site_string'] = site_string

            # Look up site name
            site_name = self.data.get_divesite_area_site(site_string)
            if not site_name:
                preview['error'] = f'Site not found: {site_string}'
                previews.append(preview)
                continue

            preview['site_name'] = site_name

            # Get coordinates
            lat, lon = self.data.get_lat_long_from_site(site_name)
            if lat is None or lon is None:
                preview['error'] = 'No coordinates for site'
                previews.append(preview)
                continue

            preview['lat'] = lat
            preview['lon'] = lon

            # Generate new filename with GPS marker
            new_filename_body = self._construct_gps_filename(name)
            if new_filename_body:
                preview['new_filename'] = new_filename_body + ext
            else:
                preview['error'] = 'Failed to generate GPS filename'
                previews.append(preview)
                continue

            previews.append(preview)

        return previews

    def _rename_single_file_basic(self, file_path, author, site_tuple, activity, camera_abbrev):
        """Rename a single file with basic metadata.

        Returns:
            bool: True if file was renamed successfully, False otherwise
        """
        try:
            from pathlib import Path
            from src.app_utils import validate_safe_path
            import shutil

            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            file_date = self.exif.get_creation_date_str(file_path)
            new_filename_body = self.assembler.assemble_basic_filename(
                original_name, file_date, author, site_tuple, activity, camera_abbrev
            )

            if not new_filename_body:
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)

            # Validate that new path is in the same directory (prevent path traversal)
            if not validate_safe_path(Path(dir_name), Path(new_filename_body + ext)):
                logger.warning(f"Rejecting unsafe rename path: {new_filename_body + ext}")
                return False

            if os.path.exists(new_path):
                return False

            # Create backup before renaming
            backup_path = f"{file_path}.backup"
            try:
                # Copy file to backup
                shutil.copy2(file_path, backup_path)

                # Attempt rename
                os.rename(file_path, new_path)

                # Remove backup on success
                os.remove(backup_path)

                # Record for undo
                self.rename_history.append((file_path, new_path))

                logger.debug(f"Successfully renamed: {os.path.basename(file_path)} -> {os.path.basename(new_path)}")
                return True
            except Exception as e:
                # Restore from backup if rename failed
                if os.path.exists(backup_path):
                    if not os.path.exists(file_path):
                        shutil.move(backup_path, file_path)
                        logger.info(f"Restored from backup: {os.path.basename(file_path)}")
                    else:
                        os.remove(backup_path)
                logger.error(f"Rename failed, restored backup: {e}")
                raise
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
            from pathlib import Path
            from src.app_utils import validate_safe_path
            import shutil

            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            new_filename_body = self.assembler.assemble_identity_filename(
                original_name, family, genus, species, confidence, phase, colour, behaviour
            )

            if not new_filename_body:
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)

            # Validate that new path is in the same directory (prevent path traversal)
            if not validate_safe_path(Path(dir_name), Path(new_filename_body + ext)):
                logger.warning(f"Rejecting unsafe rename path: {new_filename_body + ext}")
                return False

            if os.path.exists(new_path):
                return False

            # Create backup before renaming
            backup_path = f"{file_path}.backup"
            try:
                # Copy file to backup
                shutil.copy2(file_path, backup_path)

                # Attempt rename
                os.rename(file_path, new_path)

                # Remove backup on success
                os.remove(backup_path)

                # Record for undo
                self.rename_history.append((file_path, new_path))

                logger.debug(f"Successfully renamed: {os.path.basename(file_path)} -> {os.path.basename(new_path)}")
                return True
            except Exception as e:
                # Restore from backup if rename failed
                if os.path.exists(backup_path):
                    if not os.path.exists(file_path):
                        shutil.move(backup_path, file_path)
                        logger.info(f"Restored from backup: {os.path.basename(file_path)}")
                    else:
                        os.remove(backup_path)
                logger.error(f"Rename failed, restored backup: {e}")
                raise
        except (OSError, IOError) as e:
            self._warn(f"Error renaming {os.path.basename(file_path)}: {e}")
            return False

    def _notice(self, text):
        """Display an informational message in the status bar.

        Args:
            text: The message to display (shown in dark gray)
        """
        self.status_label.config(text=text, fg='#333333')

    def _warn(self, text):
        """Display a warning or error message in the status bar.

        Args:
            text: The warning message to display (shown in red)
        """
        self.status_label.config(text=text, fg='#d32f2f')

    def _show_progress(self, total, label="Processing..."):
        """Show and initialize the progress bar.

        Disables all user interaction during processing to prevent re-entrancy issues
        while keeping the window responsive.

        Args:
            total: Total number of items to process
            label: Text to display next to the progress bar
        """
        self._progress_total = total
        self._processing = True
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = 0
        self.progress_label.config(text=label)
        self.progress_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 5))

        # Disable all interactive elements
        self._set_ui_enabled(False)
        self.update()

    def _update_progress(self, current, label=None):
        """Update the progress bar value.

        Processes all pending GUI events to keep the application responsive.

        Args:
            current: Current progress value
            label: Optional new label text
        """
        self.progress_bar['value'] = current
        if label:
            self.progress_label.config(text=label)
        # Use update() to process all events and prevent "not responding"
        self.update()

    def _hide_progress(self):
        """Hide the progress bar and re-enable user interaction."""
        self._processing = False
        self.progress_frame.grid_forget()
        self.progress_bar['value'] = 0

        # Re-enable all interactive elements
        self._set_ui_enabled(True)
        self.update()

    def _set_ui_enabled(self, enabled):
        """Enable or disable all interactive UI elements.

        Args:
            enabled: True to enable, False to disable
        """
        state = 'normal' if enabled else 'disabled'

        # Disable/enable tab labels
        self._tabs_enabled = enabled
        if enabled:
            self._update_tab_appearance()
            for lbl in self.tab_buttons.values():
                lbl.config(cursor='hand2')
        else:
            for lbl in self.tab_buttons.values():
                lbl.config(fg='#999999', cursor='')

        # Disable/enable all comboboxes
        comboboxes = [
            'cb_author', 'cb_site', 'cb_activity', 'cb_camera',
            'cb_family', 'cb_genus', 'cb_species',
            'cb_confidence', 'cb_phase', 'cb_colour', 'cb_behaviour'
        ]
        for cb_name in comboboxes:
            cb = getattr(self, cb_name, None)
            if cb:
                cb.config(state=state if enabled else 'disabled')

        # Disable/enable buttons
        buttons = [
            'bt_rename', 'btn_install_exiftool', 'btn_open_website', 'btn_refresh_status'
        ]
        for btn_name in buttons:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.config(state=state)

        # Disable/enable search fields
        for field_name in ['search_entry', 'search_field']:
            field = getattr(self, field_name, None)
            if field:
                field.config(state=state)

        # Disable/enable treeview selection
        if hasattr(self, 'tree'):
            # Prevent selection changes during processing
            if enabled:
                self.tree.config(selectmode='browse')
            else:
                self.tree.config(selectmode='none')

        # Disable/enable drag-and-drop
        if enabled:
            self.drop_target_register(DND_FILES)
        else:
            try:
                self.drop_target_unregister()
            except Exception:
                pass  # May already be unregistered

    def _undo_last_rename(self):
        """Undo the last batch of rename operations.

        Reverses all renames from the most recent rename operation by renaming
        files back to their original names.
        """
        # Ignore during processing
        if self._processing:
            return

        if not self.rename_history:
            self._warn("Nothing to undo")
            return

        undone = 0
        for old_path, new_path in reversed(self.rename_history):
            if os.path.exists(new_path) and not os.path.exists(old_path):
                try:
                    os.rename(new_path, old_path)
                    undone += 1
                    logger.debug(f"Undone: {os.path.basename(new_path)} -> {os.path.basename(old_path)}")
                except OSError as e:
                    logger.warning(f"Failed to undo rename: {e}")

        self.rename_history.clear()
        self._notice(f"Undone {undone} rename(s)")

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
        """Switch between Basic, Identify, Edit, and EXIF modes.

        Adjusts which comboboxes are enabled/disabled and whether the Rename button
        is visible based on the selected mode:
        - Basic: Enable author, site, activity for metadata-only renaming
        - Identify: Enable taxonomy and attributes for adding identification
        - Edit: Disable all fields until files are loaded for batch editing
        - EXIF: Show site selector for GPS coordinate writing

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        mode = self.mode.get()
        is_basic = mode == 'Basic'
        is_identify = mode == 'Identify'
        is_edit = mode == 'Edit'
        is_meta = mode == 'Meta'

        # Mode hints for status bar
        mode_hints = {
            'Basic': "Drop files to add photographer, site, and activity info",
            'Identify': "Search or select a species, then drop files to identify",
            'Edit': "Drop files to batch edit their metadata",
            'Meta': "Drop Basic/Identify format files to auto-extract GPS from filename"
        }

        # Hide EXIF frame by default
        if hasattr(self, 'exif_frame'):
            self.exif_frame.grid_remove()

        if is_basic:
            self._toggle_checkboxes(False, False, False, False, False, False, False, True, True, True, True)
            self._toggle_tree(False)
            self.bt_rename.grid_remove()
            self.bottom_frame.grid()
        elif is_identify:
            self._toggle_checkboxes(True, True, True, True, True, True, True, False, False, False, False)
            self._toggle_tree(True)
            self.bt_rename.grid_remove()
            self.bottom_frame.grid()
        elif is_edit:
            self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False, False)
            self._toggle_tree(True)
            self.bt_rename.grid()
            self.bottom_frame.grid()
        elif is_meta:
            self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False, False)
            self._toggle_tree(False)
            self.bt_rename.grid_remove()
            self.bottom_frame.grid_remove()
            if hasattr(self, 'exif_frame'):
                self.exif_frame.grid()
                self._update_exiftool_status()

        if not is_meta:
            self._reset_info()
        self._notice(mode_hints[mode])
    
    def _toggle_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity, camera):
        """Show or hide comboboxes and their labels based on boolean flags.

        Args:
            family: Show/hide family combobox
            genus: Show/hide genus combobox
            species: Show/hide species combobox
            confidence: Show/hide confidence combobox
            phase: Show/hide phase combobox
            colour: Show/hide colour combobox
            behaviour: Show/hide behaviour combobox
            author: Show/hide author combobox
            site: Show/hide site combobox
            activity: Show/hide activity combobox
            camera: Show/hide camera combobox
        """
        self._toggle_widget(self.cb_family, self.cb_family_label, family)
        self._toggle_widget(self.cb_genus, self.cb_genus_label, genus)
        self._toggle_widget(self.cb_species, self.cb_species_label, species)
        self._toggle_widget(self.cb_confidence, self.cb_confidence_label, confidence)
        self._toggle_widget(self.cb_phase, self.cb_phase_label, phase)
        self._toggle_widget(self.cb_colour, self.cb_colour_label, colour)
        self._toggle_widget(self.cb_behaviour, self.cb_behaviour_label, behaviour)
        self._toggle_widget(self.cb_author, self.cb_author_label, author)
        self._toggle_widget(self.cb_site, self.cb_site_label, site)
        self._toggle_widget(self.cb_activity, self.cb_activity_label, activity)
        self._toggle_widget(self.cb_camera, self.cb_camera_label, camera)
        # Show/hide Google Maps link with site field
        if site:
            self.link.grid()
        else:
            self.link.grid_remove()

    def _toggle_widget(self, widget, label, visible):
        """Show or hide a widget and its associated label.

        Args:
            widget: The widget to show/hide
            label: The label associated with the widget
            visible: If True, show the widget; if False, hide it
        """
        if visible:
            label.grid()
            widget.grid()
        else:
            label.grid_remove()
            widget.grid_remove()
    
    def _toggle_tree(self, visible):
        """Show or hide the tree view, scrollbars, and search field.

        Args:
            visible: If True, show the tree components; if False, hide them
        """
        if visible:
            self.upper_frame.grid()
            self.middle_frame.grid()
        else:
            self.upper_frame.grid_remove()
            self.middle_frame.grid_remove()

    def _set_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity, camera):
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
            camera: Camera full name to set
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
        if camera: self.cb_camera.set(camera)

    def _row_selected(self, event):
        """Handle treeview row selection.

        When user clicks on a fish in the treeview, populate the comboboxes
        with that fish's taxonomy for easy identification.

        Args:
            event: Tkinter event
        """
        if not self.tree.selection(): return
        item = self.tree.selection()[0]
        fam, gen, spec, common_name = self.tree.item(item, 'values')
        # Reset only attribute comboboxes (don't call _reset_info which rebuilds tree)
        self.cb_confidence.set(self.data.confidence_default)
        self.cb_phase.set(self.data.phase_default)
        self.cb_colour.set(self.data.colour_default)
        self.cb_behaviour.set(self.data.behaviour_default)
        # Set taxonomy from selected row
        self.cb_family.set(fam)
        self.cb_genus.set(gen)
        self.cb_species.set(spec)
        self.selection_confident(True)

        fam_df = self.data.filter_fish({'Family': fam})
        fam_gen_df = self.data.filter_fish({'Family': fam, 'Genus': gen})
        self.cb_genus['values'] = [self.data.genus_default] + sorted(fam_df['Genus'].unique())
        self.cb_species['values'] = [self.data.species_default] + sorted(fam_gen_df['Species'].unique())

        # Enable species dropdown when row selected
        self.cb_species.config(state='readonly')

        # Show selected species in status bar
        self._notice(f"Selected: {gen} {spec} ({common_name})")


    def fill_tree(self, items):
        """Populate the treeview with fish data.

        Args:
            items: List of lists containing fish data rows [Family, Genus, Species, Common Name]
        """
        self.clear_tree()
        for item in items:
            self.tree.insert('', 'end', values=item)
        # Update Species header with count
        self.tree.heading('Species', text=f'Species ({len(items)})')

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
        # Ignore placeholder text
        if search_string == SEARCH_PLACEHOLDER:
            search_string = ""
        results = self.data.search_fish(search_string)
        self.fill_tree(results.values.tolist())

        # Show search results count
        count = len(results)
        if search_string:
            self._notice(f"Found {count} species matching '{search_string}'")

    def set_family(self, event):
        """Filter species by selected family and update genus/species dropdowns.

        Triggered when user selects a family from the dropdown. Updates the genus
        and species comboboxes with values that belong to the selected family.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        family = self.cb_family.get()
        if family == self.data.family_default:
            filtered_df = self.data.filter_fish()
            # Disable species when family is default
            self.cb_species.set(self.data.species_default)
            self.cb_species.config(state='disabled')
        else:
            filtered_df = self.data.filter_fish({'Family': family})
        self.cb_genus['values'] = [self.data.genus_default] + sorted(filtered_df['Genus'].unique())
        self.cb_genus.set(self.data.genus_default)
        self.cb_species['values'] = [self.data.species_default] + sorted(filtered_df['Species'].unique())
        if family != self.data.family_default:
            self.cb_species.set(self.data.species_default)
        self.fill_tree(filtered_df.values.tolist())

        if family == self.data.family_default: self.selection_confident(False)

    def set_genus(self, event):
        """Filter species by selected genus and update species dropdown.

        Triggered when user selects a genus from the dropdown. Updates the species
        combobox with values that belong to the selected genus.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        family = self.cb_family.get()
        genus = self.cb_genus.get()

        # Reset and disable species when genus is default
        if genus == self.data.genus_default:
            filtered_df = self.data.filter_fish({'Family': family})
            self.cb_genus['values'] = [self.data.genus_default] + sorted(filtered_df['Genus'].unique())
            self.cb_genus.set(self.data.genus_default)
            self.cb_species.set(self.data.species_default)
            self.cb_species.config(state='disabled')
        else:
            filtered_df = self.data.filter_fish({'Family': family, 'Genus': genus})
            self.cb_species.config(state='readonly')

        self.cb_species['values'] = [self.data.species_default] + sorted(filtered_df['Species'].unique())
        if genus != self.data.genus_default:
            self.cb_species.set(self.data.species_default)
        self.fill_tree(filtered_df.values.tolist())

        if genus == self.data.genus_default: self.selection_confident(False)

    def set_species(self, event):
        """Filter and display only the selected species.

        Triggered when user selects a species from the dropdown. Updates the treeview
        to show only entries matching the selected species.

        Args:
            event: Tkinter event (can be None when called programmatically)
        """
        family = self.cb_family.get()
        genus = self.cb_genus.get()
        species = self.cb_species.get()
        if species == self.data.species_default:
            filtered_df = self.data.filter_fish({'Family': family, 'Genus': genus})
        else:
            filtered_df = self.data.filter_fish({'Family': family, 'Genus': genus, 'Species': species})
        self.fill_tree(filtered_df.values.tolist())
        self.selection_confident(species != self.data.species_default)
    
    def selection_confident(self, is_confident: bool):
        if not is_confident:
            self.cb_confidence.set(self.data.confidence_default)
        else:
            self.cb_confidence.set(self.data.get_active_labels('Confidence')[0])
        
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
        # Ignore during processing
        if self._processing:
            return

        if not hasattr(self, 'editing_files') or len(self.editing_files) == 0:
            self._warn("No files selected for editing")
            return

        # Generate previews
        previews = self._generate_previews_edit(self.editing_files)

        # Show preview dialog if enabled, otherwise proceed with all valid files
        if self._is_preview_enabled():
            from .preview_dialog import BatchPreviewDialog
            dialog = BatchPreviewDialog(self, previews)
            self.wait_window(dialog)

            to_rename = dialog.get_files_to_rename()
            if not to_rename:
                self._notice("Rename cancelled")
                return
        else:
            # Skip errors automatically when preview is disabled
            to_rename = [p for p in previews if not p.get('error')]
            if not to_rename:
                self._notice("No valid files to rename")
                return

        # Clear history for new rename batch
        self.rename_history.clear()

        renamed_count = 0
        total = len(to_rename)
        self._show_progress(total, f"Renaming 0/{total}...")

        for i, mapping in enumerate(to_rename):
            if self._edit_single_file(mapping['path']):
                renamed_count += 1
            self._update_progress(i + 1, f"Renaming {i + 1}/{total}...")

        self._hide_progress()
        # Update UI
        self._notice(f"{renamed_count}/{len(to_rename)} files were renamed successfully.")
        self._cleanup_after_edit()

    def _generate_previews_edit(self, files):
        """Generate preview data for edit mode renames.

        Handles both Basic and Identity format files.

        Args:
            files: List of file paths

        Returns:
            List of dicts with keys: path, original, new, error
        """
        previews = []
        for file_path in files:
            original = os.path.basename(file_path)
            filepath, extension = os.path.splitext(file_path)
            basename = os.path.basename(filepath)

            preview = {'path': file_path, 'original': original, 'new': None, 'error': None}

            if self.editing_format == 'identity':
                # Parse Identity format filename
                match = self.assembler.regex_match_identity(basename)
                if not match:
                    preview['error'] = 'Invalid format'
                    previews.append(preview)
                    continue

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
                    edited_fields['camera'],
                    edited_fields['filename'],
                    extension
                )

            elif self.editing_format == 'basic':
                # Parse Basic format filename: AuthorCode_SiteString_Date_Time_Activity_Camera_OriginalName
                # Remove _G or _N suffix if present
                clean_basename = basename
                if basename.endswith('_G') or basename.endswith('_N'):
                    clean_basename = basename[:-2]
                parts = clean_basename.split('_')
                if len(parts) < 7:
                    preview['error'] = 'Invalid format'
                    previews.append(preview)
                    continue

                # Create info tuple matching Identity format structure (14 elements)
                # [0-6: taxonomy (None), 7: author, 8: site, 9: date, 10: time, 11: activity, 12: camera, 13: original]
                info = (None, None, None, None, None, None, None,
                       parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], '_'.join(parts[6:]))

                # Build new filename from edited/original fields
                edited_fields = self._collect_edited_fields(info)

                new_filename = self.assembler.assemble_edited_basic_filename(
                    edited_fields['author_code'],
                    edited_fields['site_string'],
                    edited_fields['date'],
                    edited_fields['time'],
                    edited_fields['activity'],
                    edited_fields['camera'],
                    edited_fields['filename'],
                    extension
                )
            else:
                preview['error'] = 'Unknown format'
                previews.append(preview)
                continue

            if new_filename:
                preview['new'] = new_filename
            else:
                preview['error'] = 'Failed to generate name'

            previews.append(preview)
        return previews

    def _edit_single_file(self, file_path):
        """Edit a single file based on current UI selections.

        Handles both Basic and Identity format files.

        Returns:
            bool: True if file was renamed successfully, False otherwise
        """
        try:
            filepath, extension = os.path.splitext(file_path)
            basename = os.path.basename(filepath)

            if self.editing_format == 'identity':
                # Parse Identity format filename
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
                    edited_fields['camera'],
                    edited_fields['filename'],
                    extension
                )

            elif self.editing_format == 'basic':
                # Parse Basic format filename: AuthorCode_SiteString_Date_Time_Activity_Camera_OriginalName
                # Remove _G or _N suffix if present
                clean_basename = basename
                if basename.endswith('_G') or basename.endswith('_N'):
                    clean_basename = basename[:-2]
                parts = clean_basename.split('_')
                if len(parts) < 7:
                    return False

                # Create info tuple matching Identity format structure (14 elements)
                # [0-6: taxonomy (None), 7: author, 8: site, 9: date, 10: time, 11: activity, 12: camera, 13: original]
                info = (None, None, None, None, None, None, None,
                       parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], '_'.join(parts[6:]))

                # Build new filename from edited/original fields
                edited_fields = self._collect_edited_fields(info)

                new_filename = self.assembler.assemble_edited_basic_filename(
                    edited_fields['author_code'],
                    edited_fields['site_string'],
                    edited_fields['date'],
                    edited_fields['time'],
                    edited_fields['activity'],
                    edited_fields['camera'],
                    edited_fields['filename'],
                    extension
                )
            else:
                return False

            from pathlib import Path
            from src.app_utils import validate_safe_path
            import shutil

            dir_name = os.path.dirname(file_path)
            new_filepath = os.path.join(dir_name, new_filename)

            # Validate that new path is in the same directory (prevent path traversal)
            if not validate_safe_path(Path(dir_name), Path(new_filename)):
                logger.warning(f"Rejecting unsafe rename path: {new_filename}")
                return False

            # Check if target exists
            if os.path.exists(new_filepath):
                return False

            # Create backup before renaming
            backup_path = f"{file_path}.backup"
            try:
                # Copy file to backup
                shutil.copy2(file_path, backup_path)

                # Attempt rename
                os.rename(file_path, new_filepath)

                # Remove backup on success
                os.remove(backup_path)

                # Record for undo
                self.rename_history.append((file_path, new_filepath))

                logger.debug(f"Successfully edited: {os.path.basename(file_path)} -> {os.path.basename(new_filepath)}")
                return True
            except Exception as e:
                # Restore from backup if rename failed
                if os.path.exists(backup_path):
                    if not os.path.exists(file_path):
                        shutil.move(backup_path, file_path)
                        logger.info(f"Restored from backup: {os.path.basename(file_path)}")
                    else:
                        os.remove(backup_path)
                logger.error(f"Edit failed, restored backup: {e}")
                raise

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
        # Field indices in parsed info tuple (14 elements):
        # 0: family, 1: genus, 2: species, 3: confidence, 4: phase,
        # 5: colour, 6: behaviour, 7: author, 8: site, 9: date,
        # 10: time, 11: activity, 12: camera, 13: original name

        fields = {}

        # Taxonomy fields
        fields['family'] = self.cb_family.get() if self.fields_to_edit[0] else info[0]
        fields['genus'] = self.cb_genus.get() if self.fields_to_edit[1] else info[1]
        fields['species'] = self.cb_species.get() if self.fields_to_edit[2] else info[2]

        # Attribute fields
        fields['confidence'] = self.data.get_abbreviation_reverse('Confidence', self.cb_confidence.get()) if self.fields_to_edit[3] else info[3]
        fields['phase'] = self.data.get_abbreviation_reverse('Phase', self.cb_phase.get()) if self.fields_to_edit[4] else info[4]
        fields['colour'] = self.data.get_abbreviation_reverse('Colour', self.cb_colour.get()) if self.fields_to_edit[5] else info[5]
        fields['behaviour'] = self.data.get_abbreviation_reverse('Behaviour', self.cb_behaviour.get()) if self.fields_to_edit[6] else info[6]


        # # Colour and behaviour (may need reverse lookup for abbreviations)
        # if self.fields_to_edit[5]:
        #     colour_value = self.cb_colour.get()
        #     # Check if it's already an abbreviation or if we need to convert it
        #     colour_abbrev = self.data.get_abbreviation_reverse('Colour', colour_value)
        #     fields['colour'] = colour_abbrev if colour_abbrev else colour_value
        # else:
        #     fields['colour'] = info[5]

        # if self.fields_to_edit[6]:
        #     behaviour_value = self.cb_behaviour.get()
        #     # Check if it's already an abbreviation or if we need to convert it
        #     behaviour_abbrev = self.data.get_abbreviation_reverse('Behaviour', behaviour_value)
        #     fields['behaviour'] = behaviour_abbrev if behaviour_abbrev else behaviour_value
        # else:
        #     fields['behaviour'] = info[6]

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

        # Camera field
        if self.fields_to_edit[12]:
            camera = self.cb_camera.get()
            fields['camera'] = self.data.get_camera_abbreviation(camera)
        else:
            fields['camera'] = info[12]

        # Original filename (never edited)
        fields['filename'] = info[13]

        return fields

    def _cleanup_after_edit(self):
        """Reset UI state after editing operation.

        Clears the list of files being edited, resets all comboboxes to defaults,
        and disables all fields until new files are dropped.
        """
        self._reset_info()
        self.editing_files = []
        self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False, False)