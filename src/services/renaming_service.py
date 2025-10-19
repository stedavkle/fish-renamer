# services/renaming_service.py
"""Service layer for file renaming operations."""

import os
import logging
from typing import List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RenamingResult:
    """Result of a renaming operation."""

    def __init__(self, total: int, success: int, failures: List[str] = None):
        self.total = total
        self.success = success
        self.failures = failures or []

    @property
    def failed(self) -> int:
        """Number of failed renames."""
        return self.total - self.success

    def __str__(self) -> str:
        """String representation of the result."""
        return f"{self.success}/{self.total} files renamed successfully"


class RenamingService:
    """Orchestrates file renaming operations.

    This service layer separates business logic from UI concerns,
    making the code more testable and maintainable.
    """

    def __init__(self, filename_assembler, exif_handler, data_manager):
        """Initialize the renaming service.

        Args:
            filename_assembler: FilenameAssembler instance
            exif_handler: ExifHandler instance
            data_manager: DataManager instance
        """
        self.assembler = filename_assembler
        self.exif = exif_handler
        self.data = data_manager

    def rename_files_basic(
        self,
        files: List[str],
        author: str,
        site_tuple: Tuple[str, str],
        activity: str
    ) -> RenamingResult:
        """Rename files with basic metadata.

        Args:
            files: List of file paths to rename
            author: Photographer's full name
            site_tuple: Tuple of (area, site)
            activity: Activity type

        Returns:
            RenamingResult with success/failure counts
        """
        renamed_count = 0
        failures = []

        for file_path in files:
            try:
                if self._rename_single_file_basic(file_path, author, site_tuple, activity):
                    renamed_count += 1
                else:
                    failures.append(os.path.basename(file_path))
            except Exception as e:
                logger.error(f"Unexpected error renaming {file_path}: {e}")
                failures.append(os.path.basename(file_path))

        return RenamingResult(len(files), renamed_count, failures)

    def rename_files_identity(
        self,
        files: List[str],
        family: str,
        genus: str,
        species: str,
        confidence: str,
        phase: str,
        colour: str,
        behaviour: str
    ) -> RenamingResult:
        """Rename files with taxonomic identification.

        Args:
            files: List of file paths to rename
            family: Taxonomic family
            genus: Taxonomic genus
            species: Species name
            confidence: Confidence level
            phase: Life phase
            colour: Colour variant
            behaviour: Observed behaviour

        Returns:
            RenamingResult with success/failure counts
        """
        renamed_count = 0
        failures = []

        for file_path in files:
            try:
                if self._rename_single_file_identity(
                    file_path, family, genus, species, confidence, phase, colour, behaviour
                ):
                    renamed_count += 1
                else:
                    failures.append(os.path.basename(file_path))
            except Exception as e:
                logger.error(f"Unexpected error renaming {file_path}: {e}")
                failures.append(os.path.basename(file_path))

        return RenamingResult(len(files), renamed_count, failures)

    def _rename_single_file_basic(
        self,
        file_path: str,
        author: str,
        site_tuple: Tuple[str, str],
        activity: str
    ) -> bool:
        """Rename a single file with basic metadata.

        Args:
            file_path: Path to file to rename
            author: Photographer name
            site_tuple: Tuple of (area, site)
            activity: Activity type

        Returns:
            True if file was renamed successfully, False otherwise
        """
        try:
            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            file_date = self.exif.get_creation_date_str(file_path)
            new_filename_body = self.assembler.assemble_basic_filename(
                original_name, file_date, author, site_tuple, activity
            )

            if not new_filename_body:
                logger.debug(f"Skipping {original_name}: already processed or missing data")
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)
            if os.path.exists(new_path):
                logger.warning(f"Target file already exists: {new_path}")
                return False

            os.rename(file_path, new_path)
            logger.info(f"Renamed: {os.path.basename(file_path)} -> {new_filename_body + ext}")
            return True

        except (OSError, IOError) as e:
            logger.error(f"Error renaming {os.path.basename(file_path)}: {e}")
            return False

    def _rename_single_file_identity(
        self,
        file_path: str,
        family: str,
        genus: str,
        species: str,
        confidence: str,
        phase: str,
        colour: str,
        behaviour: str
    ) -> bool:
        """Rename a single file with identity metadata.

        Args:
            file_path: Path to file to rename
            family: Taxonomic family
            genus: Taxonomic genus
            species: Species name
            confidence: Confidence level
            phase: Life phase
            colour: Colour variant
            behaviour: Observed behaviour

        Returns:
            True if file was renamed successfully, False otherwise
        """
        try:
            dir_name = os.path.dirname(file_path)
            original_name, ext = os.path.splitext(os.path.basename(file_path))

            new_filename_body = self.assembler.assemble_identity_filename(
                original_name, family, genus, species, confidence, phase, colour, behaviour
            )

            if not new_filename_body:
                logger.debug(f"Skipping {original_name}: not in basic format or already has identity")
                return False

            new_path = os.path.join(dir_name, new_filename_body + ext)
            if os.path.exists(new_path):
                logger.warning(f"Target file already exists: {new_path}")
                return False

            os.rename(file_path, new_path)
            logger.info(f"Renamed: {os.path.basename(file_path)} -> {new_filename_body + ext}")
            return True

        except (OSError, IOError) as e:
            logger.error(f"Error renaming {os.path.basename(file_path)}: {e}")
            return False

    def validate_basic_inputs(
        self,
        author: str,
        site: str,
        activity: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate inputs for basic renaming.

        Args:
            author: Photographer name
            site: Site string
            activity: Activity type

        Returns:
            Tuple of (is_valid, error_message)
        """
        from src.constants import (
            DEFAULT_PHOTOGRAPHER_TEXT,
            DEFAULT_SITE_TEXT,
            DEFAULT_ACTIVITY_TEXT
        )

        if not author or author == DEFAULT_PHOTOGRAPHER_TEXT:
            return False, "Please select a photographer."

        if not site or site == DEFAULT_SITE_TEXT or ', ' not in site:
            return False, "Please select a dive site."

        if not activity or activity == DEFAULT_ACTIVITY_TEXT:
            return False, "Please select an activity."

        return True, None
