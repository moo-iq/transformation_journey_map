"""Core business logic for the translate module."""

import xml.etree.ElementTree as ET
import csv
import os
import requests
from typing import Dict, Iterable, Iterator, List, Optional
from .exceptions import ConfigurationError, CsvWriteError, DrawioParseError, TranslationError


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

    @staticmethod
    def _is_valid_label(value: str) -> bool:
        """Check if a cell value is a valid, translatable label."""
        value = value.strip()
        return (
            len(value) > 1 and
            not value.startswith('data:') and
            not value.startswith('shape=') and
            value not in ('-', '=')
        )

    def update_labels(self, translations: Dict[str, str], target_language: str) -> int:
        """
        Update labels in the XML tree from a dictionary of translations.

        This method adds a 'label_<lang>' attribute with the translated text.
        For mxCell elements, it wraps them in a new <object> tag, moving the
        id and value to the new object's attributes.
        Args:
            translations: A dictionary mapping element IDs to translated text.
            target_language: The target language code (e.g., 'de').

        Returns:
            The number of updated elements.
        """
        if not self._root:
            raise DrawioParseError("File not properly parsed")

        updated_count = 0
        target_attr = f'label_{target_language}'

        # Create a parent map to allow modifying the tree while iterating
        parent_map = {c: p for p in self._root.iter() for c in p}

        # Find all elements with an ID that needs translation.
        # We iterate over a copy, as we'll be modifying the tree.
        elements_to_process = [
            elem for elem in self._root.iter() if elem.get('id') in translations
        ]

        for element in elements_to_process:
            element_id = element.get('id')
            # The element might have been processed already (e.g. moved)
            if element_id is None or element_id not in translations:
                continue

            translated_text = translations[element_id]

            if element.tag == 'object':
                # For existing objects, just add the new label attribute
                element.set(target_attr, translated_text)
                updated_count += 1

            elif element.tag == 'mxCell':
                # For mxCells, wrap them in a new <object> element
                parent = parent_map.get(element)
                if parent is None:
                    continue  # Should not happen for valid files

                original_value = element.get('value', '')

                # Create the new <object> element and set its attributes
                new_object = ET.Element('object')
                new_object.set('id', element_id)
                new_object.set('label', original_value)
                new_object.set(target_attr, translated_text)

                # The mxCell no longer needs id and value
                del element.attrib['id']
                if 'value' in element.attrib:
                    del element.attrib['value']

                # Replace the mxCell with the new object in the tree
                index = list(parent).index(element)
                parent.remove(element)
                new_object.append(element)
                parent.insert(index, new_object)
                parent_map[element] = new_object  # Update parent map for moved element
                updated_count += 1

        return updated_count

    def save(self, output_path: str) -> None:
        """Save the modified XML tree to a file."""
        if self._tree:
            self._tree.write(output_path, encoding='utf-8', xml_declaration=True)

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
            if value and cell_id and cell_id not in seen_ids and self._is_valid_label(value):
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
        return sum(1 for _ in self.get_labeled_objects(''))


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

    def import_translations(self, csv_file_path: str, drawio_file_path: str) -> str:
        """
        Import translations from a CSV file back into a .drawio file.

        Args:
            csv_file_path: Path to the CSV file containing translations.
            drawio_file_path: Path to the .drawio file to be updated.

        Returns:
            A success message with the count of imported translations.
        """
        target_lang = self.config.target_language
        target_header = f'label_{target_lang}'
        translations = {}

        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if target_header not in reader.fieldnames:
                    raise CsvWriteError(
                        f"Target language column '{target_header}' not found in {csv_file_path}"
                    )
                for row in reader:
                    if row.get(target_header):
                        translations[row['id']] = row[target_header]
        except FileNotFoundError:
            raise CsvWriteError(f"CSV file not found: {csv_file_path}")

        parser = DrawioParser(drawio_file_path)
        updated_count = parser.update_labels(translations, target_lang)
        
        # Save the changes back to the original .drawio file
        parser.save(drawio_file_path)

        return f"Successfully imported {updated_count} translations into {drawio_file_path}"

    def translate_csv(self, file_path: str) -> str:
        """
        Translate a CSV file using the DeepL API.

        This method reads a CSV file, translates the 'label' column,
        and writes the translation to the 'label_<target_lang>' column,
        overwriting the original file.

        Args:
            file_path: Path to the CSV file to translate.

        Returns:
            Success message with the count of translated labels.

        Raises:
            ConfigurationError: If the DeepL API key is not configured.
            CsvWriteError: If there are issues reading or writing the CSV file.
            TranslationError: If the translation API call fails.
        """
        api_key = self.config.deepl_api_key
        if not api_key:
            raise ConfigurationError(
                "DeepL API key not found. Please set DEEPL_API_KEY."
            )

        translator = DeepLTranslator(api_key)
        target_lang = self.config.target_language
        source_lang = self.config.source_language
        target_header = f'label_{target_lang}'

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                original_fieldnames = reader.fieldnames
                if not original_fieldnames:
                    return "CSV file is empty. Nothing to translate."
                rows = list(reader)
        except FileNotFoundError as e:
            raise CsvWriteError(f"File not found: {file_path}") from e
        except Exception as e:
            raise CsvWriteError(f"Error reading CSV file {file_path}: {e}") from e

        translated_count = 0
        for row in rows:
            if text_to_translate := row.get('label', ''):
                row[target_header] = translator.translate_text(
                    text_to_translate, source_lang=source_lang, target_lang=target_lang
                )
                translated_count += 1

        new_fieldnames = original_fieldnames[:]
        if target_header not in new_fieldnames:
            new_fieldnames.append(target_header)

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=new_fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except IOError as e:
            raise CsvWriteError(f"Error writing to CSV file {file_path}: {e}") from e

        return f"Successfully translated {translated_count} labels in {file_path}"


class DeepLTranslator:
    """Translator using DeepL API."""

    def __init__(self, api_key: str):
        """
        Initialize the DeepL translator.

        Args:
            api_key: DeepL API key.
        """
        self.api_key = api_key
        self.base_url = "https://api-free.deepl.com/v2/translate"

    def translate_text(self, text: str, source_lang: str = 'EN', 
                      target_lang: str = 'DE') -> str:
        """
        Translate text using DeepL API.

        Args:
            text: Text to translate.
            source_lang: Source language code (e.g., 'EN').
            target_lang: Target language code (e.g., 'DE').

        Returns:
            Translated text.
            

        Raises:
            TranslationError: If translation fails.
        """
        if not text.strip():
            return text

        try:
            response = requests.post(
                self.base_url,
                data={
                    'auth_key': self.api_key,
                    'text': text,
                    'source_lang': source_lang,
                    'target_lang': target_lang
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'translations' in result and result['translations']:
                    return result['translations'][0]['text']
                else:
                    raise TranslationError("No translation returned from DeepL API")
            else:
                error_msg = f"DeepL API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                except ValueError:
                    error_msg += f" - {response.text}"
                raise TranslationError(error_msg)

        except requests.exceptions.RequestException as e:
            raise TranslationError(f"Network error calling DeepL API: {e}") from e
        except Exception as e:
            raise TranslationError(f"Unexpected error during translation: {e}") from e
