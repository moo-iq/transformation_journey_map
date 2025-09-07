"""Core business logic for the translate module."""

import xml.etree.ElementTree as ET
import csv
import os
from typing import Dict, Iterable, Iterator, Optional
from .exceptions import DrawioParseError, CsvWriteError


class DrawioParser:
    """Parses a .drawio file to extract labeled objects."""

    def __init__(self, file_path: str) -> None:
        """
        Initialize the parser with the path to the .drawio file.

        Args:
            file_path: The path to the .drawio file.
            
        Raises:
            DrawioParseError: If the file cannot be parsed.
        """
        self.file_path = file_path
        self._tree: Optional[ET.ElementTree] = None
        self._root: Optional[ET.Element] = None
        self._parse_file()

    def _parse_file(self) -> None:
        """Parse the .drawio file and set up the XML tree."""
        try:
            self._tree = ET.parse(self.file_path)
            self._root = self._tree.getroot()
        except ET.ParseError as e:
            raise DrawioParseError(
                f"Error parsing XML file {self.file_path}: {e}"
            ) from e
        except FileNotFoundError as e:
            raise DrawioParseError(f"File not found: {self.file_path}") from e
        except Exception as e:
            raise DrawioParseError(
                f"Unexpected error reading file {self.file_path}: {e}"
            ) from e

    def get_labeled_objects(self, target_language: str) -> Iterator[Dict[str, str]]:
        """
        Find all text elements in the drawio file and yield them as dictionaries.

        This method searches for:
        1. <object> elements with 'label' attributes
        2. <mxCell> elements with 'value' attributes that contain text
        3. Any other text-containing elements

        Args:
            target_language: The target language for translation (e.g., 'de').

        Yields:
            A dictionary for each text element containing 'id', 'label',
            and target language label.
        """
        if not self._root:
            raise DrawioParseError("File not properly parsed")

        label_target_attr = f'label_{target_language}'

        # Find all text elements with unique IDs
        seen_ids = set()

        # 1. Search for <object> elements with 'label' attributes
        for obj in self._root.findall('.//object'):
            obj_id = obj.get('id')
            label = obj.get('label')

            if label and obj_id and obj_id not in seen_ids:
                seen_ids.add(obj_id)
                yield {
                    'id': obj_id,
                    'label': label,
                    label_target_attr: obj.get(label_target_attr, '')
                }

        # 2. Search for <mxCell> elements with 'value' attributes containing text
        for cell in self._root.findall('.//mxCell'):
            cell_id = cell.get('id')
            value = cell.get('value', '').strip()

            # Skip empty values, single characters, and non-text elements
            if (value and cell_id and cell_id not in seen_ids and
                len(value) > 1 and not value.startswith('data:') and
                not value.startswith('shape=') and value != '-' and
                value != '='):

                seen_ids.add(cell_id)
                yield {
                    'id': cell_id,
                    'label': value,
                    label_target_attr: cell.get(label_target_attr, '')
                }

    def get_object_count(self) -> int:
        """
        Get the total number of text elements in the file.

        Returns:
            The number of text elements found in the file.
        """
        if not self._root:
            return 0

        count = 0
        seen_ids = set()

        # Count <object> elements with 'label' attributes
        for obj in self._root.findall('.//object'):
            obj_id = obj.get('id')
            label = obj.get('label')
            if label and obj_id and obj_id not in seen_ids:
                seen_ids.add(obj_id)
                count += 1

        # Count <mxCell> elements with 'value' attributes containing text
        for cell in self._root.findall('.//mxCell'):
            cell_id = cell.get('id')
            value = cell.get('value', '').strip()

            if (value and cell_id and cell_id not in seen_ids and
                len(value) > 1 and not value.startswith('data:') and
                not value.startswith('shape=') and value != '-' and
                value != '='):
                seen_ids.add(cell_id)
                count += 1

        return count


class LabelCsvWriter:
    """Writes label data to a CSV file."""

    def __init__(self, output_file: str) -> None:
        """
        Initialize the writer with the output file path.

        Args:
            output_file: The path to the output CSV file.
        """
        self.output_file = output_file

    def write(self, objects_data: Iterable[Dict[str, str]], target_language: str) -> None:
        """
        Write the provided object data to the CSV file.

        Args:
            objects_data: An iterable of object data dictionaries.
            target_language: The target language used for the header.
            
        Raises:
            CsvWriteError: If there's an error writing to the file.
        """
        label_target_attr = f'label_{target_language}'
        fieldnames = ['id', 'label', label_target_attr]

        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(objects_data)
        except IOError as e:
            raise CsvWriteError(
                f"Error writing to file {self.output_file}: {e}"
            ) from e
        except Exception as e:
            raise CsvWriteError(
                f"Unexpected error writing to file {self.output_file}: {e}"
            ) from e

    def append(self, objects_data: Iterable[Dict[str, str]], target_language: str) -> None:
        """
        Append the provided object data to the CSV file.

        Args:
            objects_data: An iterable of object data dictionaries.
            target_language: The target language used for the header.
            
        Raises:
            CsvWriteError: If there's an error writing to the file.
        """
        label_target_attr = f'label_{target_language}'
        fieldnames = ['id', 'label', label_target_attr]

        try:
            # Check if file exists to determine if we need to write header
            file_exists = os.path.exists(self.output_file)

            with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(objects_data)
        except IOError as e:
            raise CsvWriteError(
                f"Error appending to file {self.output_file}: {e}"
            ) from e
        except Exception as e:
            raise CsvWriteError(
                f"Unexpected error appending to file {self.output_file}: {e}"
            ) from e


class TranslationService:
    """Service class for handling translation operations."""

    def __init__(self, config) -> None:
        """
        Initialize the translation service.

        Args:
            config: Configuration object.
        """
        self.config = config

    def extract_labels(self, file_path: str, output_file: str) -> str:
        """
        Extract labels from a .drawio file and save them to a CSV file.

        Args:
            file_path: Path to the .drawio file.
            output_file: Path to the output CSV file.

        Returns:
            Success message.

        Raises:
            DrawioParseError: If there's an error parsing the .drawio file.
            CsvWriteError: If there's an error writing the CSV file.
        """
        parser = DrawioParser(file_path)
        labeled_objects = parser.get_labeled_objects(
            self.config.target_language
        )
        writer = LabelCsvWriter(output_file)
        writer.write(labeled_objects, self.config.target_language)

        return f"Extracted labels from {file_path} to {output_file}"

    def translate_csv(self, file_path: str) -> str:
        """
        Translate a CSV file using a translation service.

        Args:
            file_path: Path to the CSV file to translate.

        Returns:
            Success message.
        """
        # This is a placeholder for the actual translation logic
        return f"Translating {file_path}"
