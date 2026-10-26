# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@~/.claude/profiles/python.md

<!-- The import above is a personal profile in the maintainer's home directory; on other machines it resolves to nothing. -->

## Purpose

Dave's Fish Renamer is a desktop GUI for renaming marine-biodiversity field photos (from the Uni Tübingen "Marine Biodiversity: Indonesia" course) into a fixed filename scheme for the university image database. Users drag images onto the window. There are four modes: **Basic** (photographer, site, EXIF date, activity, camera), **Identify** (adds taxonomy and attributes to a Basic name), **Edit** (changes fields of existing Basic/Identity names), and **Meta** (writes GPS from the dive-site table into EXIF via ExifTool and flips `_N_` → `_G_`). Every operation shows a preview first, and the last batch can be undone with Ctrl+Z.

**Anti-scope:** the filename format is set by the external "Fish Images Naming Standard" and is frozen. Don't change the layout, field order, separators, or the `_N_`/`_G_` marker unless the user says the standard has changed. The standard last changed in 2026-10: the marker went from `_N`/`_G` to `_N_`/`_G_`, and anything after it is free user text. New feature requests are collected in `suggestions.pdf` (untracked, repo root).

## Architecture

- `main.py` hides the Windows console (unless `--debug`), sets up stdlib logging, copies the bundled `config/` data into the user data dir, and builds `MainWindow`. If construction throws, it calls `restore_default_files()` (overwrites the data files, deletes `config.ini`), shows a reset warning, and retries.
- `ui/main_window.py` (~2200 lines) is the **composition root and also holds most of the application logic**. It constructs `ConfigManager`, `DataManager`, `FilenameAssembler`, `ExifHandler`, `ExifToolHandler`, and `WebUpdater`. It owns mode dispatch (`_dnd_files` → `_handle_<mode>_mode` → `_generate_previews_<mode>` → preview dialog → `_rename_single_file_*` / `_edit_single_file`), the rename-with-backup logic, and `rename_history` for undo.
- `src/` is the non-UI layer:
  - `constants.py` holds the date/time/GPS-marker regexes and field positions used by the parser, the default data filenames, and the config section names.
  - `filename_assembler.py` builds and parses names. `parse_filename()` splits on `_` and takes fields **by position** (only date and time are validated; family, species, site, photographer, camera are accepted verbatim, as requested by the course lead). It returns a `ParsedName` with a 14-slot `fields` tuple (Basic names leave slots 0–6 as `None`), the GPS marker, the free text after it, and `body` (the name without marker). Legacy `_N`/`_G` and unmarked names are still read; anything written uses `_N_`/`_G_`.
  - `data_manager.py` loads the semicolon-delimited CSVs (`utf-8-sig`) and `Labels*.json` into lists of dicts (pandas was removed on purpose). It also handles lookups such as name ↔ 5-letter code and area/site ↔ site string ↔ lat/lon. Camera models and attribute defaults come from `Labels*.json`, not code.
  - `config_manager.py` reads and writes `config.ini` (sections `USER_PREFS`, `PATHS`, `MISC`). `PATHS` stores bare filenames, which are resolved against the data dir.
  - `exif_handler.py` reads dates with Pillow (plus pillow-heif for HIF), falling back to exifread.
  - `exiftool_handler.py` runs one persistent `exiftool -stay_open` subprocess, guarded by a lock. It handles batch date reads (used for multi-file Basic previews), GPS writes, and downloading/installing ExifTool by scraping exiftool.org.
  - `web_updater.py` pulls newer data files from a public HiDrive share through its REST API (an anonymous share token; no credentials). The newest file is chosen by the `YYYY-MM-DD` in its filename. It runs on a background thread from `ui/preferences_window.py`.
- `src/services/renaming_service.py` is **not wired in** and is stale (it calls `assemble_basic_filename` without `camera`). It is the planned destination for moving rename logic out of `main_window.py`. Bring it up to date before using it.
- Threading: everything runs on the Tk main thread except the data update. Long batches keep the UI alive by calling `self.update()` inside `_update_progress`, and `_processing` / `_set_ui_enabled` block re-entrant drops.

**Runtime data dir** (`app_utils.get_data_path()`): `%APPDATA%\DavesFishRenamer` on Windows, `~/Library/Application Support/DavesFishRenamer` on macOS. It holds the live data files, `config.ini`, and `fish_renamer.log`. The repo's `config/` only seeds it, and only when the dir contains no `.csv`/`.json` files yet. After the first run, edits to `config/` have no effect until you reset or delete those files.

## Environment

- Python 3.12 in `.venv` (CI also builds macOS with 3.11). Dependencies are managed with pip via `requirements.txt`. `requirements-dev.txt` adds pyinstaller and nuitka, and still lists pandas/numpy even though the code no longer uses them.
- Tkinter + tkinterdnd2 (there is a PyInstaller hook in `hooks/`) + tkinter-tooltip.
- ExifTool is optional at runtime and only needed for Meta mode and fast batch date reads. The app can install it on Windows itself.
- Targets: Windows and macOS.

## Commands

```powershell
.venv\Scripts\python.exe main.py            # run (console hidden on Windows)
.venv\Scripts\python.exe main.py --debug    # run with console visible
.venv\Scripts\pip install -r requirements.txt
```

The only tests are `tests/test_filename_assembler.py` (pytest, from `requirements-dev.txt`) for the filename parser and assemblers: `.venv\Scripts\python.exe -m pytest tests`. No linter or type checker is configured. For everything else, run the app and drive the affected mode by hand, using the sample images in the repo root (`DST0960.JPG` is tracked; `copy_images.py` makes 1000 copies of it for batch testing).

Release builds come from `.github/workflows/build.yml`. A `test` job runs pytest first; the builds only start if it passes. It runs Nuitka standalone on Windows (the `main.dist` folder, renamed to `daves-fish-renamer` and shipped as `daves-fish-renamer-<version>-windows.zip`; onefile was dropped because its unpack-to-%TEMP% start triggers Windows Defender) and an app bundle on macOS (`daves-fish-renamer-<version>-macos.app.tar.gz`) for every push or PR to `main`, and pushing a `v*` tag also creates a GitHub release with the version taken from the tag, plus a `SHA256SUMS.txt`. Alternatively, release without a local tag via "Run workflow" (or `gh workflow run build.yml -f version=0.3.8`): only from `main`, version must be `X.Y.Z` and not yet tagged (checked in the `test` job); the release step then creates tag `v<version>` on the built commit. An empty version just builds. Nuitka and Python versions are pinned in the workflow's top-level `env`; bump `NUITKA_VERSION` deliberately. Nuitka's cache (compiled C objects, Dependency Walker download) is kept between runs via `actions/cache` and `NUITKA_CACHE_DIR`. Code signing is not set up. The README has the local Nuitka/PyInstaller commands; `distx64nuitka/` is local build output.

## Conventions and overrides

These are deliberate departures from the Python profile:
- Tkinter, not PySide6.
- stdlib `logging` (`logger = logging.getLogger(__name__)` per module), not Loguru.
- pip/requirements, not uv.
- pytest only for the filename parser; no ruff/mypy. Otherwise the profile's "definition of done" tooling checks don't apply; manual verification does.
- Releases go through GitHub Actions and GitHub Releases, not Gitea.

House rules:
- Filename field patterns/positions and default data filenames live in `src/constants.py`.
- Data files are versioned by the date in their name (`Species_Indopacific 2026-02-22.csv`). When you replace a bundled file in `config/`, update the matching `DEFAULT_*_FILE` constant in `src/constants.py` too, or fresh installs and resets won't find it.

## Gotchas

- Renaming is implemented three times in `main_window.py`: `_rename_single_file_basic`, `_rename_single_file_identity`, and `_edit_single_file` (Edit's name building is shared with its preview via `_build_edited_filename`). Each does validate path → copy to `<file>.backup` → rename → delete backup → append to `rename_history`. A fix to that flow usually has to go into all three, plus the Meta mode path.
- GPS marker handling is easy to break. Always go through `ParsedName.gps`/`.tail`/`.gps_suffix` rather than string-slicing the end of a name; Edit mode has dropped the marker before (commit 81e9a3c). Check that the marker and the free text after it survive every mode (`tests/` covers Identify).
- `PATTERN_DATETIME_IN_FILENAME` in `constants.py` predates the camera field and isn't used.
- `get_app_path()` checks `sys._MEIPASS`, which only exists under PyInstaller. Under Nuitka it falls through to `__file__`-relative paths, so bundled `config/` is found at `get_app_path().parent / 'config'`.
- ExifTool JSON output can contain control characters from odd files. The parser has to tolerate them (fixed in b329d2b).
- Several macOS-specific Tk workarounds exist (dialog focus/timeouts, see 1ef3adc, 5a6cf5d). Anything opened from a menu or drop callback must be deferred with `after(0, …)`; Preferences is non-modal (no `wait_visibility`/`grab_set`) and uses a Combobox instead of an `OptionMenu` because those broke on macOS 27. Test both platforms when you touch dialog or window code.
