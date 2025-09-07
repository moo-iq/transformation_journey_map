"""Custom exceptions for the translate module."""


class TranslationError(Exception):
    """Base exception for translation-related errors."""


class DrawioParseError(TranslationError):
    """Raised when there's an error parsing a .drawio file."""


class CsvWriteError(TranslationError):
    """Raised when there's an error writing to a CSV file."""


class ConfigurationError(TranslationError):
    """Raised when there's a configuration error."""
