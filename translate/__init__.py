"""
Drawio Translation Module

This module provides comprehensive functionality to extract and translate
text elements from .drawio files. It supports:

- Extraction of text from <object> elements with 'label' attributes
- Extraction of text from <mxCell> elements with 'value' attributes
- Filtering of non-text elements (shapes, data URLs, single characters)
- CSV export/import for translation workflows
- Translation using the DeepL API

The module is designed to capture all translatable text content from
draw.io diagrams, making it suitable for internationalization workflows.

Main components:
- DrawioParser: Parses .drawio files to extract all text elements
- LabelCsvWriter: Writes label data to CSV files
- TranslationService: Main service for translation operations
- DeepLTranslator: A client for the DeepL API.
- Config: Configuration management
"""

from .core import DrawioParser, LabelCsvWriter, TranslationService, DeepLTranslator
from .config import Config
from .exceptions import (
    ConfigurationError, CsvWriteError, DrawioParseError, TranslationError
)

# Version information
__version__ = "1.0.0"
__author__ = "Alex Kempkens"

# Public API
__all__ = [
    # Core classes
    'DrawioParser',
    'LabelCsvWriter',
    'TranslationService',
    'DeepLTranslator',
    'Config',

    # Exceptions
    'TranslationError',
    'DrawioParseError',
    'CsvWriteError',
    'ConfigurationError',
]
