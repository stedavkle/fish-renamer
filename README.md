# ![icon](https://github.com/user-attachments/assets/09d4ebb3-550c-4d3a-94d0-a6e376b0bec1) Dave's Fish Renamer

A specialized tool for renaming and organizing marine biodiversity images collected during field courses at the Eberhard-Karls Universität Tübingen.

## 🐠 About

This program was developed during the "Marine Biodiversity: Indonesia" 2025 field course to streamline the process of integrating marine species images into the university's database. It automates the file renaming process according to specific formatting requirements, saving researchers time and ensuring consistency across the collection.

The application features a clean, layered architecture with comprehensive error handling, professional logging, and type-safe code for reliability and maintainability.

![Main Interface](https://github.com/user-attachments/assets/592df31e-0e43-4930-9e88-b597153ddc58)

*The interface features four mode tabs: Basic (green), Identify (blue), Edit (orange), and Meta (purple).*

## ✨ Features

### User Features
- **Four operational modes**: Basic, Identify, Edit, and Meta (GPS)
- **Batch renaming** of multiple images via drag-and-drop
- **Preview dialogs** - Review all changes before applying them
- **Undo support** - Revert the last batch of renames with Ctrl+Z
- **Integration** with course-specific databases (species, dive sites, photographers, activities)
- **User-friendly interface** with searchable species database
- **GPS coordinate embedding** - Automatically write location data to image EXIF from filenames
- **Intelligent filename validation** and error handling
- **Support for various image formats** (JPG, PNG, RAW, HIF) with EXIF metadata extraction
- **Persistent preferences** - remembers your photographer, site, and activity selections

### Technical Features
- **Layered architecture** separating UI, business logic, and data layers
- **Preview-first workflow** - All operations show detailed previews before execution
- **Transaction safety** - File operations use backup-and-restore pattern
- **Undo support** - Maintains rename history for easy rollback
- **Comprehensive logging** for debugging and troubleshooting
- **Type-safe code** with full type hints for better IDE support
- **Robust error handling** with specific exception types and graceful degradation
- **Professional EXIF handling** using PIL for reading and ExifTool for writing GPS
- **Centralized configuration** with no magic numbers or hardcoded values
- **Smart filename parsing** with regex-based validation for multiple format types

## 🔧 Usage
### Renaming Modes
The program offers four specialized modes to fit your workflow:

- **Basic Mode**: Quickly adds essential metadata to your images
  - Automatically incorporates photographer name, dive site, activity type, and file creation date
  - Perfect for initial organization immediately after dives
  - Example output: `DaKle_IDN-Bangka-HRS_2025-03-31_10-15-53_snork_DST0875.JPG`


- **Identify Mode**: For species identification and classification
  - Complete taxonomic information (Family, Genus, Species)
  - Add behavioral observations and life stage information
  - Supports special notation for uncertain identifications
  - Searchable species database with filtering by family/genus
  - Example output: `Acanthuridae_Naso_brachycentron_B_ok_ad_ty_zz_DaKle_IDN-Bangka-HRS_2025-03-31_10-15-53_snork_DST0875.JPG`


- **Edit Mode**: For correcting or updating existing filenames
  - Supports both Basic and Identity format files
  - Modify any field without affecting other parts of the filename
  - Batch-edit specific fields across multiple images
  - Only editable fields are enabled based on file format
  - Preserves original creation dates and other metadata


- **Meta Mode (Beta)**: For embedding GPS coordinates into image EXIF data
  - Automatically extracts dive site from Basic or Identify format filenames
  - Writes GPS coordinates to image EXIF data using the divesites database
  - Adds "_G_" marker to filename after successful GPS write
  - Optional camera model tag (e.g., S-A7IV) in filename
  - Requires ExifTool installation (Windows installer provided)
  - Example: `dive_NKM08085.JPG` → `dive_G_S-A7IV_NKM08085.JPG` (with GPS data embedded)
  - Files with existing GPS markers can be updated or have camera model added/removed

### Working with Multiple Files
- Select multiple images by dragging and dropping them anywhere in the application window
- Apply the same naming pattern to all selected images in one operation
- Preview all changes before confirming (shows original and new filenames)
- Files with errors are highlighted and can be optionally skipped

### Preview and Undo
- **Preview Dialog**: Before any rename operation, review all changes in a detailed preview
  - See original and new filenames side-by-side
  - Identify errors (missing EXIF data, invalid formats, etc.)
  - Option to skip files with errors
  - For Meta mode: View extracted site information, GPS coordinates, and clickable Maps links

- **Undo Last Rename**: Accidentally renamed files? Use Edit → Undo Last Rename (Ctrl+Z)
  - Reverts all files from the most recent rename batch
  - Works across all modes (Basic, Identify, Edit, Meta)


## 🗺️ Meta Mode Setup (GPS Embedding)

The Meta mode requires ExifTool to write GPS coordinates to image files.

### Installing ExifTool

**Windows:**
1. Open the Meta mode tab in the application
2. Click "Install ExifTool (Windows)" button
3. The application will download and install ExifTool automatically
4. Alternatively, download manually from [exiftool.org](https://exiftool.org/) and add to PATH

**macOS/Linux:**
1. Install via package manager:
   - macOS: `brew install exiftool`
   - Ubuntu/Debian: `sudo apt-get install libimage-exiftool-perl`
2. Or download from [exiftool.org](https://exiftool.org/)

### Using Meta Mode

1. Ensure your files are already in Basic or Identify format (containing site information)
2. Switch to the Meta mode tab
3. Optionally select a camera model from the dropdown
4. Drag and drop your image files
5. Review the preview showing:
   - Extracted dive site information
   - GPS coordinates to be written
   - New filename with "_G_" marker
   - Clickable Google Maps links to verify coordinates
6. Click "Write GPS" to embed coordinates and rename files

**Note:** Files already containing GPS markers ("_G_") can be processed again to add/change/remove camera model tags.

## 🔄 Updating Reference Data

### When to Update

- Before each new field trip or course
- When working with newly discovered species
- When new divesites are added
- Upon receiving data updates from course instructors

### Required Data Files

The application uses CSV files to populate dropdown menus and autocompletion fields:

| File | Purpose | Required Format | Example |
|------|---------|-----------------|---------|
| `Species.csv` | Taxonomic database with location filtering | `Family;Genus;Species;Species English;Bangka;Red Sea;Both;All` | `Acanthuridae;Acanthurus;gahhm;Black Surgeonfish;1;1;1;1` |
| `Divesites.csv` | Dive site information with GPS coordinates | `Site string;Country;Province;Base;Area;Site;Code;Type of DIVE;latitude;longitude;Bangka;Red Sea` | `IDN-Bangka-AKP;IDN;Sulawesi Utara;Bangka;Bangka;Areng Kambing Pasir;AKP;sand;1.76885;125.17675;1;0` |
| `Photographers.csv` | Participant registry | `Namecode;Full name` | `Anony;Anonymous` |
| `Activities.csv` | Activity types | `activity;description` | `dive;diving` |
| `Labels.json` | Attribute labels/abbreviations | JSON format | `{"Confidence": {"ok": "confident", "cf": "uncertain"}, ...}` |

**Notes:**
- The `Species.csv` location columns (Bangka, Red Sea, Both, All) are binary flags (1/0) used for filtering species by location in the Preferences.
- The `Divesites.csv` location columns enable filtering dive sites by field course location.
- The `Labels.json` file contains abbreviations for confidence levels, life phases, colour variations, and behaviours used in Identify mode.
- CSV files use semicolon (`;`) as the delimiter.

### Update Process

1. Obtain the latest CSV/JSON files from your course instructor
   - Files typically include version dates in their names (e.g., `Species_Indopacific 2025-04-15.csv`)
2. Navigate to **Settings** → **Preferences** in the application
3. In the Data Management tab, ~~click **Update Files** or~~ simply drag and drop the new files
4. The application will automatically use the most recent version of each file type
5. Verify the update by checking the "Last Updated" timestamp
6. Restart the application to ensure changes take effect

**File Naming Convention**: Data files should follow the pattern `[Type]_[Location] [Date].csv` where:
- Type: Species, Divesites, Photographers
- Location: Optional location identifier (e.g., Indopacific, all)
- Date: Version date in YYYY-MM-DD format

## 👨‍💻 Development

### Getting Started

1. Clone the repository:
```bash
git clone https://github.com/stedavkle/fish-renamer.git
cd fish-renamer
```

2. Set up a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

### Project Structure

```
fish-renamer/
├── main.py                      # Application entry point
├── src/
│   ├── app_utils.py            # Utility functions (paths, data initialization)
│   ├── config_manager.py       # Configuration and user preferences
│   ├── constants.py            # Centralized constants and regex patterns
│   ├── data_manager.py         # CSV/JSON data loading and querying
│   ├── exif_handler.py         # EXIF metadata extraction (dates)
│   ├── exiftool_handler.py     # ExifTool wrapper for GPS writing
│   ├── filename_assembler.py   # Filename generation and validation
│   └── web_updater.py          # HiDrive data file updates
├── ui/
│   ├── main_window.py          # Main application window with 4 modes
│   ├── preferences_window.py   # Preferences dialog
│   ├── preview_dialog.py       # Batch rename preview dialog
│   └── exif_preview_dialog.py  # GPS/Meta mode preview dialog
├── config/
│   ├── Species_Indopacific 2025-04-15.csv     # Taxonomic database
│   ├── Divesites_Indopacific 2025-04-15.csv   # Dive site coordinates
│   ├── Photographers_all 2025-04-15.csv       # Photographer registry
│   ├── Activities.csv                         # Activity types
│   ├── Labels 2025-04-15.json                 # Attribute abbreviations
│   └── icon.png                               # Application icon
└── README.md
```

**Note:** Data files include version dates (e.g., "2025-04-15") for tracking updates. The application automatically uses the most recent version of each file type.

### Code Quality

The codebase follows Python best practices:
- **PEP 8** compliant naming conventions
- **Type hints** throughout for static analysis
- **Comprehensive docstrings** in Google style
- **Professional logging** instead of print statements
- **No commented-out code** or magic numbers
- **Separation of concerns** with clear layer boundaries

### 🏗️ Build Executables

#### Windows x86/x64

Download [UPX](https://upx.github.io/) for compression, then build with Nuitka or PyInstaller:

**Nuitka** (recommended for performance):
```bash
python -m nuitka --standalone --onefile --output-dir=distx64nuitka \
  --windows-icon-from-ico=config/icon.png \
  --include-data-dir="config=config" \
  --windows-console-mode=disable \
  --plugin-enable=upx \
  --upx-binary="upx-5.0.0-win64/upx.exe" \
  --enable-plugin=tk-inter \
  main.py
```

**PyInstaller**:
```bash
pyinstaller --clean -y -F -n "Daves Fish Renamer" \
  --distpath distx64 \
  --icon=config/icon.png \
  --add-data="config/icon.png;config" \
  -w --optimize 2 \
  --additional-hooks-dir=hooks \
  --upx-dir=upx-5.0.0-win64 \
  main.py
```

#### macOS (Apple Silicon)

**PyInstaller**:
```bash
pyinstaller --clean -y -F -n "Daves Fish Renamer" \
  --distpath distmips \
  --icon=config/icon.png \
  --add-data="config:config" \
  -w --optimize 2 \
  --additional-hooks-dir=hooks \
  main.py
```

**Nuitka**:
```bash
python -m nuitka --standalone --onefile --output-dir=distmipsnuitka \
  --macos-create-app-bundle \
  --macos-app-icon=config/icon.png \
  --include-data-dir="config=config" \
  --enable-plugin=tk-inter \
  main.py
```

### 📝 Logging

The application creates a log file at `~/.DavesFishRenamer/fish_renamer.log` for troubleshooting. The log captures:
- Data loading and validation errors
- File renaming operations (including undo operations)
- Backup and restore operations for safety
- EXIF extraction issues
- GPS coordinate writing operations
- ExifTool installation and version checks
- Configuration changes
- Web update activities
- Unsafe path rejections (security)

Log levels can be adjusted in `main.py` by changing the `logging.basicConfig()` level parameter.

### 🔒 Safety Features

The application includes multiple safety mechanisms to prevent data loss:

- **Backup-Restore Pattern**: Before renaming any file, a backup copy is created. If the rename fails, the backup is automatically restored.
- **Path Validation**: All file operations are validated to prevent path traversal attacks and ensure files stay in their original directory.
- **Preview Before Action**: All rename operations show a detailed preview dialog before making any changes.
- **Undo Support**: The last batch of renames can be undone with Ctrl+Z.
- **Error Isolation**: Errors in individual files don't stop batch operations; other files continue processing.
- **Skip Errors Option**: In preview dialogs, you can choose to skip files with errors.
