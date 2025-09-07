"""Configuration management for the translate module."""

import os
from typing import Optional
import dotenv
from .exceptions import ConfigurationError


class Config:
    """Configuration class for translation settings."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Optional path to a .env file. If None, looks for .env in current directory.
        """
        if config_file:
            dotenv.load_dotenv(config_file)
        else:
            dotenv.load_dotenv()

    @property
    def target_language(self) -> str:
        """Get the target language for translation."""
        return os.getenv('language_target', 'de')

    @property
    def source_language(self) -> str:
        """Get the source language for translation."""
        return os.getenv('language_source', 'en')

    def set_target_language(self, language: str) -> None:
        """
        Set the target language.
        
        Args:
            language: The target language code (e.g., 'de', 'fr').
        """
        if not language or len(language) != 2:
            raise ConfigurationError(
                f"Invalid language code: {language}"
            )
        os.environ['language_target'] = language

    def set_source_language(self, language: str) -> None:
        """
        Set the source language.
        
        Args:
            language: The source language code (e.g., 'en', 'de').
        """
        if not language or len(language) != 2:
            raise ConfigurationError(
                f"Invalid language code: {language}"
            )
        os.environ['language_source'] = language
