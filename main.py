import logging
import sys
import platform
from ui.main_window import MainWindow
from src.app_utils import initialize_data_files

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

if __name__ == '__main__':
    # 0. Handle console visibility (hide unless --debug flag is present)
    handle_console_visibility()

    # 1. Setup logging
    setup_logging()

    # 2. Ensure data directory and default files exist
    initialize_data_files()

    # 3. Create the main application window
    #    The MainWindow class now handles creating all its own components.
    app = MainWindow()

    # 4. Start the Tkinter event loop
    app.mainloop()