from ui.main_window import MainWindow
from src.app_utils import initialize_data_files

if __name__ == '__main__':
    # 1. Ensure data directory and default files exist
    initialize_data_files()

    # 2. Create the main application window
    #    The MainWindow class now handles creating all its own components.
    app = MainWindow()

    # 3. Start the Tkinter event loop
    app.mainloop()