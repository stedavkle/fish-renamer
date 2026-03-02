import logging
import sys
import platform
from ui.main_window import MainWindow
from src.app_utils import initialize_data_files, restore_default_files

def handle_console_visibility():
    """Hide console window on Windows unless --debug flag is provided."""
    if platform.system() == 'Windows' and '--debug' not in sys.argv:
        try:
            import ctypes
            # Get handle to console window
            console_window = ctypes.windll.kernel32.GetConsoleWindow()
            if console_window:
                # SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(console_window, 0)
        except Exception:
            # If hiding fails, just continue - not critical
            pass

def setup_logging():
    """Configure application-wide logging."""
    # Create logs directory if it doesn't exist
    from pathlib import Path
    from src.app_utils import get_data_path

    log_dir = get_data_path()

    # Ensure the directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / 'fish_renamer.log'

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Fish Renamer Application Started")
    logger.info("=" * 60)

def show_reset_warning():
    """Show a popup warning the user that config was reset."""
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showwarning(
        "Application Reset",
        "The application experienced an issue during startup and has been "
        "reset to default settings.\n\n"
        "Please update your preferences (photographer, activity, camera) "
        "and verify your data files in the settings."
    )
    root.destroy()

if __name__ == '__main__':
    # 0. Handle console visibility (hide unless --debug flag is present)
    handle_console_visibility()

    # 1. Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)

    # 2. Ensure data directory and default files exist
    initialize_data_files()

    # 3. Create the main application window with startup safeguard
    try:
        app = MainWindow()
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        logger.info("Restoring default configuration files...")
        restore_default_files()
        show_reset_warning()
        # Retry with restored defaults
        app = MainWindow()

    # 4. Start the Tkinter event loop
    app.mainloop()
