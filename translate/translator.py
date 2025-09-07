"""
Legacy translator module.

This module provides backward compatibility for the old translator interface.
For new code, use the classes and functions from the main module directly.

Deprecated: This module will be removed in a future version.
Use: from translate import DrawioParser, LabelCsvWriter, TranslationService, extract_labels, translate_csv
"""

import warnings
from . import (
    DrawioParser,
    LabelCsvWriter,
    TranslationService,
    extract_labels,
    translate_csv,
    show_help
)

# Issue deprecation warning
warnings.warn(
    "The translator module is deprecated. Import directly from the main module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
__all__ = [
    'DrawioParser',
    'LabelCsvWriter',
    'TranslationService',
    'extract_labels',
    'translate_csv',
    'show_help'
]