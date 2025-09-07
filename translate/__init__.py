"""
Drawio Translation Module

This module provides comprehensive functionality to extract and translate
text elements from .drawio files. It supports:

- Extraction of text from <object> elements with 'label' attributes
- Extraction of text from <mxCell> elements with 'value' attributes
- Filtering of non-text elements (shapes, data URLs, single characters)
- CSV export for translation workflows
- Support for multiple target languages

The module is designed to capture all translatable text content from
draw.io diagrams, making it suitable for internationalization workflows.

Main components:
- DrawioParser: Parses .drawio files to extract all text elements
- LabelCsvWriter: Writes label data to CSV files
- TranslationService: Main service for translation operations
- Config: Configuration management
"""

from .core import DrawioParser, LabelCsvWriter, TranslationService
from .config import Config
from .exceptions import (
    TranslationError, DrawioParseError, CsvWriteError, ConfigurationError
)
from .cli import show_help

# Version information
__version__ = "1.0.0"
__author__ = "Alex Kempkens"

# Public API
__all__ = [
    # Core classes
    'DrawioParser',
    'LabelCsvWriter',
    'TranslationService',
    'Config',

    # Exceptions
    'TranslationError',
    'DrawioParseError',
    'CsvWriteError',
    'ConfigurationError',

    # Convenience functions
    'extract_labels',
    'translate_csv',
    'show_help',
]

# Convenience functions for backward compatibility


def extract_labels(file_path: str, output_file: str, target_language: str = 'de') -> str:
    """
    Extract labels from a .drawio file and save them to a CSV file.

    This is a convenience function that creates a TranslationService instance
    and calls the extract_labels method.

    Args:
        file_path: Path to the .drawio file.
        output_file: Path to the output CSV file.
        target_language: Target language code (default: 'de').

    Returns:
        Success message.

    Raises:
        TranslationError: If there's an error during the operation.
    """
    config = Config()
    config.set_target_language(target_language)
    service = TranslationService(config)
    return service.extract_labels(file_path, output_file)


def translate_csv(file_path: str, source_language: str = 'en', target_language: str = 'de') -> str:
    """
    Translate a CSV file using a translation service.

    This is a convenience function that creates a TranslationService instance
    and calls the translate_csv method.

    Args:
        file_path: Path to the CSV file to translate.
        source_language: Source language code (default: 'en').
        target_language: Target language code (default: 'de').

    Returns:
        Success message.
    """
    config = Config()
    config.set_source_language(source_language)
    config.set_target_language(target_language)
    service = TranslationService(config)
    return service.translate_csv(file_path)
