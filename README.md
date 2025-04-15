# ![icon](https://github.com/user-attachments/assets/09d4ebb3-550c-4d3a-94d0-a6e376b0bec1) Dave's Fish Renamer
A specialized tool for renaming and organizing marine biodiversity images collected during field courses at the Eberhard-Karls Universität Tübingen.
## 🐠 About
This program was developed during the "Marine Biodiversity: Indonesia" 2025 field course to streamline the process of integrating marine species images into the university's database. It automates the file renaming process according to specific formatting requirements, saving researchers time and ensuring consistency across the collection.

![Main Interface](https://github.com/user-attachments/assets/592df31e-0e43-4930-9e88-b597153ddc58)

## ✨ Features
- Three operational modes: Basic, Identify, and Edit
- Batch renaming of multiple images
- Integration with course-specific databases
- User-friendly drag-and-drop interface
- Intelligent filename validation
- Support for various image formats

## 🔧 Usage
### Renaming Modes
The program offers three specialized modes to fit your workflow:

- **Basic Mode**: Quickly adds essential metadata to your images
  - Automatically incorporates photographer name, dive site, activity type, and file creation date
  - Perfect for initial organization immediately after dives
  - Example output: `DaKle_IDN-Bangka-HRS_2025-03-31_10-15-53_snork_DST0875.JPG`


- **Identify Mode**: For species identification and classification
  - Complete taxonomic information (Family, Genus, Species)
  - Add behavioral observations and life stage information
  - Supports special notation for uncertain identifications
  - Example output: `Acanthuridae_Naso_brachycentron_B_ok_ad_ty_zz_DaKle_IDN-Bangka-HRS_2025-03-31_10-15-53_snork_DST0875.JPG`


- **Edit Mode**: For correcting or updating existing filenames
  - Modify any field without affecting other parts of the filename
  - Batch-edit specific fields across multiple images
  - Preserves original creation dates and other metadata

### Working with Multiple Files
- Select multiple images by dragging and dropping them anywhere in the application window
- Apply the same naming pattern to all selected images in one operation


## 🔄 Updating Reference Data

### When to Update

- Before each new field trip or course
- When working with newly discovered species
- When new divesites are added
- Upon receiving data updates from course instructors

### Required Data Files

The application uses CSV files to populate dropdown menus and autocompletion fields:

| File | Purpose | Required Format |
|------|---------|-----------------|
| `Species.csv` | Taxonomic database | ﻿Family;Genus;Species;Popular name |
| `Divesites.csv` | Location information | Site string;Country;Location;Site;Site code;latitude;longitude |
| `Photographers.csv` | Participant registry | Namecode;Full name |
| `Activities.csv` | Activity types | activity;description |

### Update Process

1. Obtain the latest CSV files from your course instructor
2. Navigate to **Settings** → **Preferences** in the application
3. In the Data Management tab, ~~click **Update Files** or~~ simply drag and drop the new files
4. Verify the update by checking the "Last Updated" timestamp
5. Restart the application to ensure changes take effect

## 👨‍💻 Development
1. Clone the repository:
```bash
git clone https://github.com/stedavkle/fish-renamer.git
cd fish-renamer
```
2. Set up a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
3. Install required packages:
```bash
pip install -r requirements.txt
```
4. Run the script:
```bash
python daves-fish-renamer.py
```

### 🏗️ Build Executables
Build for x86/x64 (download [upx](https://upx.github.io/))
```bash
python -m nuitka --standalone --onefile --output-dir=distx64nuitka --windows-icon-from-ico=config/icon.png --include-data-dir="config=config" --windows-console-mode=disable --plugin-enable=upx --upx-binary="upx-5.0.0-win64/upx.exe" --enable-plugin=tk-inter daves-fish-renamer.py
pyinstaller --clean -y -F -n "Daves Fish Renamer" --distpath distx64 --icon=config/icon.png --add-data="config/icon.png;config" -w --optimize 2 --additional-hooks-dir=hooks --upx-dir=upx-5.0.0-win64 daves-fish-renamer.py
```
Build for MacOS MIPS
```
pyinstaller --clean -y -F -n "Daves Fish Renamer" --distpath distmips --icon=config/icon.png --add-data="config:config" -w --optimize 2 --additional-hooks-dir=hooks daves-fish-renamer.py
python -m nuitka --standalone --onefile --output-dir=distmipsnuitka --macos-create-app-bundle --macos-app-icon=config/icon.png --include-data-dir="config=config" --enable-plugin=tk-inter daves-fish-renamer.py
```
