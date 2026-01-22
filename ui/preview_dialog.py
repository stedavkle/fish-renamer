# ui/preview_dialog.py
"""Batch preview dialog for showing rename operations before execution."""

import tkinter as tk
from tkinter import ttk, font as tkFont


class BatchPreviewDialog(tk.Toplevel):
    """Dialog showing a preview of files to be renamed with options to skip errors."""

    def __init__(self, parent, file_mappings):
        """Initialize the batch preview dialog.

        Args:
            parent: Parent window
            file_mappings: List of dicts with keys: path, original, new, error
        """
        super().__init__(parent)
        self.title("Rename Preview")
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
        columns = ('filename', 'status')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)

        self.tree.heading('filename', text='Filename')
        self.tree.heading('status', text='Status')

        # Initial minimal widths - will be auto-fitted after populating
        self.tree.column('filename', width=200, minwidth=100)
        self.tree.column('status', width=80, minwidth=50)

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

        summary_text = f"Files to rename: {valid_count}/{total_count}"
        if error_count > 0:
            summary_text += f" ({error_count} with errors)"

        self.summary_label = ttk.Label(options_frame, text=summary_text)
        self.summary_label.pack(side='right')

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky='e', pady=(10, 0))

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_btn.pack(side='left', padx=(0, 5))

        rename_btn = ttk.Button(button_frame, text="Rename", command=self._on_rename)
        rename_btn.pack(side='left')

        # Disable rename button if no valid files
        if valid_count == 0:
            rename_btn.state(['disabled'])

    def _populate_tree(self):
        """Populate the treeview with file mappings."""
        # Define tag styles
        self.tree.tag_configure('error', foreground='#d32f2f')
        self.tree.tag_configure('ok', foreground='#2e7d32')

        for mapping in self.file_mappings:
            original = mapping.get('original', '')
            new = mapping.get('new', '')
            error = mapping.get('error')

            if error:
                status = error
                tag = 'error'
                # Show original filename for errors
                filename_display = original
            else:
                status = 'OK'
                tag = 'ok'
                # Show new filename for successful renames
                filename_display = new if new else original

            self.tree.insert('', 'end', values=(filename_display, status), tags=(tag,))

    def _auto_fit_columns(self):
        """Auto-fit column widths based on content."""
        # Get font for measuring text
        tree_font = tkFont.nametofont('TkDefaultFont')
        padding = 20  # Extra padding for column

        # Column headers
        headers = {
            'filename': 'Filename',
            'status': 'Status'
        }

        # Calculate max width for each column
        col_widths = {}
        for col in ('filename', 'status'):
            # Start with header width
            max_width = tree_font.measure(headers[col]) + padding

            # Check all rows
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                col_idx = {'filename': 0, 'status': 1}[col]
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

    def _on_rename(self):
        """Handle rename button."""
        self.result = True
        self.destroy()

    def get_files_to_rename(self):
        """Get the list of files to rename based on user selection.

        Returns:
            List of file mappings to rename, or empty list if cancelled
        """
        if not self.result:
            return []

        if self.skip_errors.get():
            return [m for m in self.file_mappings if not m.get('error')]

        return self.file_mappings
