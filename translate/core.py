"""Core business logic for the translate module."""

import xml.etree.ElementTree as ET
import csv
import os
import time
import tempfile
import requests
from tqdm import tqdm
from typing import Dict, Iterable, Iterator, Optional
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
        Translate a CSV file using the DeepL API, with progress bar and rate limiting.

        This method reads a CSV file row-by-row, translates rows where the 'label' column
        is filled but the 'label_<target_lang>' column is empty. It writes results
        incrementally to a temporary file to prevent data loss. A 1-second delay
        is added after each API call to avoid rate-limiting.

        Args:
            file_path: Path to the CSV file to translate.

        Returns:
            A success message with the count of translated and skipped labels.

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

        # Use pro_api=True if you have a Pro key
        translator = DeepLTranslator(api_key, pro_api=False)
        target_lang = self.config.target_language
        source_lang = self.config.source_language
        target_header = f'label_{target_lang}'

        # Use a temporary file to write results incrementally
        temp_fd, temp_path = tempfile.mkstemp(suffix=".csv", text=True)
        os.close(temp_fd)

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile, \
                 open(temp_path, 'w', newline='', encoding='utf-8') as temp_csvfile:

                reader = csv.DictReader(csvfile)
                original_fieldnames = reader.fieldnames
                if not original_fieldnames:
                    return "CSV file is empty. Nothing to translate."

                new_fieldnames = original_fieldnames[:]
                if target_header not in new_fieldnames:
                    new_fieldnames.append(target_header)

                writer = csv.DictWriter(temp_csvfile, fieldnames=new_fieldnames, restval='')
                writer.writeheader()

                # Convert reader to list to get total for progress bar
                rows = list(reader)
                translated_count = 0
                skipped_count = 0

                with tqdm(total=len(rows), desc="Translating CSV", unit="row") as pbar:
                    for row in rows:
                        text_to_translate = row.get('label', '').strip()
                        existing_translation = row.get(target_header, '').strip()

                        if text_to_translate and not existing_translation:
                            # Translate if source text exists and target is empty
                            row[target_header] = translator.translate_text(
                                text_to_translate, source_lang=source_lang, target_lang=target_lang
                            )
                            translated_count += 1
                            time.sleep(1)  # Wait for 1 second to avoid rate limiting
                        elif text_to_translate and existing_translation:
                            skipped_count += 1

                        writer.writerow(row)
                        pbar.set_postfix({
                            'translated': translated_count,
                            'skipped': skipped_count
                        })
                        pbar.update(1)

        except (Exception, KeyboardInterrupt) as e:
            os.remove(temp_path)  # Clean up temp file on error
            raise e

        # On success, replace the original file with the new one
        os.replace(temp_path, file_path)

        return f"Translation complete. Translated: {translated_count}, Skipped: {skipped_count}."


class DeepLTranslator:
    """Translator using DeepL API."""

    def __init__(self, api_key: str, pro_api: bool = False):
        """
        Initialize the DeepL translator.

        Args:
            api_key: DeepL API key.
            pro_api: If True, use the Pro API endpoint. Defaults to False.
        """
        self.api_key = api_key
        self.base_url = "https://api.deepl.com/v2/translate" if pro_api \
            else "https://api-free.deepl.com/v2/translate"

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
                timeout=15
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
