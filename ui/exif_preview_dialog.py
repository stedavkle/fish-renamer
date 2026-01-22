# ui/exif_preview_dialog.py
"""Preview dialog for EXIF GPS writing with Maps links."""

import tkinter as tk
from tkinter import ttk, font as tkFont
import webbrowser


class ExifPreviewDialog(tk.Toplevel):
    """Preview dialog for EXIF GPS writing with clickable Maps links."""

    def __init__(self, parent, file_mappings):
        """Initialize the EXIF preview dialog.

        Args:
            parent: Parent window
            file_mappings: List of dicts with keys:
                path, filename, site_string, site_name, lat, lon, error
        """
        super().__init__(parent)
        self.title("GPS Coordinate Preview")
        self.transient(parent)
        self.grab_set()

        self.file_mappings = file_mappings
        self.result = False
        self.skip_errors = tk.BooleanVar(value=True)
        self.parent = parent

        self._build_ui()
        self._auto_fit_columns()
        self._set_window_size()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        """Build the dialog UI."""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Treeview with columns
        columns = ('filename', 'divesite', 'latitude', 'longitude', 'maps')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)

        self.tree.heading('filename', text='Filename')
        self.tree.heading('divesite', text='Divesite')
        self.tree.heading('latitude', text='Latitude')
        self.tree.heading('longitude', text='Longitude')
        self.tree.heading('maps', text='Maps')

        # Initial minimal widths - will be auto-fitted after populating
        self.tree.column('filename', width=300, minwidth=150)
        self.tree.column('divesite', width=150, minwidth=80)
        self.tree.column('latitude', width=100, minwidth=60)
        self.tree.column('longitude', width=100, minwidth=60)
        self.tree.column('maps', width=60, minwidth=50)

        # Scrollbars
        vsb = ttk.Scrollbar(main_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Bind click event for Maps links
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)

        # Populate tree
        self._populate_tree()

        # Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        # Skip errors checkbox
        skip_cb = ttk.Checkbutton(
            options_frame,
            text="Skip files with errors",
            variable=self.skip_errors
        )
        skip_cb.pack(side='left')

        # Summary label
        valid_count = sum(1 for m in self.file_mappings if not m.get('error'))
        total_count = len(self.file_mappings)
        error_count = total_count - valid_count

        summary_text = f"Files to process: {valid_count}/{total_count}"
        if error_count > 0:
            summary_text += f" ({error_count} with errors)"

        self.summary_label = ttk.Label(options_frame, text=summary_text)
        self.summary_label.pack(side='right')

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky='e', pady=(10, 0))

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_btn.pack(side='left', padx=(0, 5))

        write_btn = ttk.Button(button_frame, text="Write GPS", command=self._on_write)
        write_btn.pack(side='left')

        # Disable write button if no valid files
        if valid_count == 0:
            write_btn.state(['disabled'])

    def _populate_tree(self):
        """Populate the treeview with file mappings."""
        # Define tag styles
        self.tree.tag_configure('error', foreground='#d32f2f')
        self.tree.tag_configure('ok', foreground='#2e7d32')
        self.tree.tag_configure('link', foreground='#1976d2')

        for mapping in self.file_mappings:
            filename = mapping.get('filename', '')
            new_filename = mapping.get('new_filename', '')
            site_name = mapping.get('site_name', '')
            lat = mapping.get('lat')
            lon = mapping.get('lon')
            error = mapping.get('error')

            if error:
                # Error row - show original filename
                self.tree.insert('', 'end',
                    values=(filename, error, '-', '-', '-'),
                    tags=('error',))
            else:
                # Valid row with coordinates - show new filename
                filename_display = new_filename if new_filename else filename
                lat_str = f"{lat:.6f}" if lat is not None else '-'
                lon_str = f"{lon:.6f}" if lon is not None else '-'
                self.tree.insert('', 'end',
                    values=(filename_display, site_name, lat_str, lon_str, 'Open'),
                    tags=('ok',))

    def _on_tree_click(self, event):
        """Handle click on treeview - check if Maps link was clicked."""
        # Identify the clicked region
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return

        # Get the column that was clicked
        column = self.tree.identify_column(event.x)
        if column != '#5':  # Maps column is now the 5th column
            return

        # Get the clicked item
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Find the corresponding mapping
        item_values = self.tree.item(item, 'values')
        if len(item_values) < 5 or item_values[4] != 'Open':
            return

        # Find the mapping with matching filename (could be original or new)
        filename = item_values[0]
        for mapping in self.file_mappings:
            # Match against both original filename and new filename
            original_filename = mapping.get('filename', '')
            new_filename = mapping.get('new_filename', '')
            if (filename == original_filename or filename == new_filename) and not mapping.get('error'):
                lat = mapping.get('lat')
                lon = mapping.get('lon')
                if lat is not None and lon is not None:
                    self._open_maps(lat, lon)
                break

    def _open_maps(self, lat, lon):
        """Open Google Maps at the specified coordinates."""
        webbrowser.open(f"https://maps.google.com/?q={lat},{lon}")

    def _auto_fit_columns(self):
        """Auto-fit column widths based on content."""
        # Get font for measuring text
        tree_font = tkFont.nametofont('TkDefaultFont')
        padding = 20  # Extra padding for column

        # Column headers
        headers = {
            'filename': 'Filename',
            'divesite': 'Divesite',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'maps': 'Maps'
        }

        # Calculate max width for each column
        col_widths = {}
        for col in ('filename', 'divesite', 'latitude', 'longitude', 'maps'):
            # Start with header width
            max_width = tree_font.measure(headers[col]) + padding

            # Check all rows
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                col_idx = {'filename': 0, 'divesite': 1,
                          'latitude': 2, 'longitude': 3, 'maps': 4}[col]
                text = str(values[col_idx]) if col_idx < len(values) else ''
                text_width = tree_font.measure(text) + padding
                max_width = max(max_width, text_width)

            col_widths[col] = max_width

        # Apply calculated widths
        for col, width in col_widths.items():
            self.tree.column(col, width=width)

        self.col_widths = col_widths

    def _set_window_size(self):
        """Set window size to fit content without exceeding screen width."""
        self.update_idletasks()

        # Calculate required width
        total_col_width = sum(self.col_widths.values())
        scrollbar_width = 20
        frame_padding = 40  # Padding from main frame
        required_width = total_col_width + scrollbar_width + frame_padding

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Cap at 90% of screen width
        max_width = int(screen_width * 0.9)
        window_width = min(required_width, max_width)

        # Set height based on number of rows, capped at 70% of screen
        row_height = 20
        header_height = 25
        controls_height = 80  # Options and buttons
        frame_padding_v = 40
        required_height = (len(self.file_mappings) * row_height + header_height +
                          controls_height + frame_padding_v)
        max_height = int(screen_height * 0.7)
        window_height = min(max(required_height, 200), max_height)

        # Set geometry
        self.geometry(f"{window_width}x{window_height}")

        # Center on parent
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - window_width) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - window_height) // 2

        # Ensure window stays on screen
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _on_cancel(self):
        """Handle cancel button or window close."""
        self.result = False
        self.destroy()

    def _on_write(self):
        """Handle write GPS button."""
        self.result = True
        self.destroy()

    def get_files_to_process(self):
        """Get the list of files to process based on user selection.

        Returns:
            List of file mappings to process, or empty list if cancelled
        """
        if not self.result:
            return []

        if self.skip_errors.get():
            return [m for m in self.file_mappings if not m.get('error')]

        return self.file_mappings
