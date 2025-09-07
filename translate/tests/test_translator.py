import unittest
from unittest.mock import patch, Mock
import os
import csv
import xml.etree.ElementTree as ET
import tempfile

from ..core import DrawioParser, LabelCsvWriter, TranslationService, DeepLTranslator
from ..config import Config
from ..exceptions import DrawioParseError, ConfigurationError, TranslationError
import unittest.mock


class TestDrawioParser(unittest.TestCase):
    """Test cases for DrawioParser class."""

    def setUp(self):
        self.drawio_file = os.path.join(
            os.path.dirname(__file__), 'test_resources', 'text.drawio'
        )
        self.nonexistent_file = 'nonexistent.drawio'

    def test_parser_initialization_success(self):
        """Test successful parser initialization."""
        parser = DrawioParser(self.drawio_file)
        # Access protected members for testing purposes
        self.assertIsNotNone(parser._tree)  # noqa: W0212
        self.assertIsNotNone(parser._root)  # noqa: W0212

    def test_parser_initialization_file_not_found(self):
        """Test parser initialization with nonexistent file."""
        with self.assertRaises(DrawioParseError):
            DrawioParser(self.nonexistent_file)

    def test_get_labeled_objects(self):
        """Test extracting labeled objects."""
        parser = DrawioParser(self.drawio_file)
        objects = list(parser.get_labeled_objects('de'))
        self.assertIsInstance(objects, list)
        # Add more specific assertions based on test file content

    def test_get_object_count(self):
        """Test getting object count."""
        parser = DrawioParser(self.drawio_file)
        count = parser.get_object_count()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)
    
    def test_get_labeled_objects_mxcell(self):
        """Test getting labeled objects from mxCell elements."""
        # Create a temporary test file with mxCell elements
        import tempfile
        test_content = '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="cell1" value="Test Text 1" />
        <mxCell id="cell2" value="Test Text 2" />
        <mxCell id="cell3" value="" />
        <mxCell id="cell4" value="-" />
        <mxCell id="cell5" value="=" />
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.drawio', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            parser = DrawioParser(temp_file)
            objects = list(parser.get_labeled_objects('de'))
            
            # Should find 2 text elements (empty, -, and = are filtered out)
            self.assertEqual(len(objects), 2)
            self.assertEqual(objects[0]['id'], 'cell1')
            self.assertEqual(objects[0]['label'], 'Test Text 1')
            self.assertEqual(objects[1]['id'], 'cell2')
            self.assertEqual(objects[1]['label'], 'Test Text 2')
        finally:
            os.unlink(temp_file)


class TestDeepLTranslation(unittest.TestCase):
    """Test cases for DeepL API translation functionality."""

    def setUp(self):
        self.test_text = "Hello, world!"
        self.expected_translation = "Hallo, Welt!"
        self.api_key = "test-api-key"

    @unittest.mock.patch('requests.post')
    def test_deepl_translation_success(self, mock_post):
        """Test successful DeepL translation."""
        # Mock the requests.post call
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'translations': [
                {
                    'detected_source_language': 'EN',
                    'text': self.expected_translation
                }
            ]
        }
        mock_post.return_value = mock_response

        translator = DeepLTranslator(self.api_key)
        result = translator.translate_text(
            self.test_text, 
            source_lang='EN', 
            target_lang='DE'
        )
        
        self.assertEqual(result, self.expected_translation)
        mock_post.assert_called_once()

    @unittest.mock.patch('requests.post')
    def test_deepl_translation_api_error(self, mock_post):
        """Test DeepL translation with API error."""
        # Mock an API error response (e.g., 403 Forbidden)
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            'message': 'Invalid API key'
        }
        mock_post.return_value = mock_response

        translator = DeepLTranslator(self.api_key)
        
        with self.assertRaises(TranslationError):
            translator.translate_text(
                self.test_text, 
                source_lang='EN', 
                target_lang='DE'
            )

    @unittest.mock.patch('requests.post')
    def test_deepl_translation_network_error(self, mock_post):
        """Test DeepL translation with network error."""
        # Mock a network-level error
        mock_post.side_effect = Exception("Network error")

        translator = DeepLTranslator(self.api_key)
        
        with self.assertRaises(TranslationError):
            translator.translate_text(
                self.test_text, 
                source_lang='EN', 
                target_lang='DE'
            )


class TestLabelCsvWriter(unittest.TestCase):
    """Test cases for LabelCsvWriter class."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        )
        self.temp_file.close()
        self.csv_file = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_writer_initialization(self):
        """Test writer initialization."""
        writer = LabelCsvWriter(self.csv_file)
        self.assertEqual(writer.output_file, self.csv_file)

    def test_write_csv(self):
        """Test writing data to CSV."""
        writer = LabelCsvWriter(self.csv_file)
        test_data = [
            {'id': '1', 'label': 'Test Label', 'label_de': 'Test Label DE'},
            {'id': '2', 'label': 'Another Label', 'label_de': 'Another Label DE'}
        ]
        writer.write(test_data, 'de')

        self.assertTrue(os.path.exists(self.csv_file))
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['id'], '1')
            self.assertEqual(rows[0]['label'], 'Test Label')
            self.assertEqual(rows[0]['label_de'], 'Test Label DE')


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""

    def setUp(self):
        self.config = Config()

    def test_default_target_language(self):
        """Test default target language."""
        self.assertEqual(self.config.target_language, 'de')

    def test_default_source_language(self):
        """Test default source language."""
        self.assertEqual(self.config.source_language, 'en')

    def test_set_target_language(self):
        """Test setting target language."""
        self.config.set_target_language('fr')
        self.assertEqual(self.config.target_language, 'fr')

    def test_set_invalid_language(self):
        """Test setting invalid language code."""
        with self.assertRaises(ConfigurationError):
            self.config.set_target_language('invalid')


class TestTranslationService(unittest.TestCase):
    """Test cases for TranslationService class."""

    def setUp(self):
        self.config = Config()
        self.service = TranslationService(self.config)
        self.drawio_file = os.path.join(
            os.path.dirname(__file__), 'test_resources', 'text.drawio'
        )
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        )
        self.temp_file.close()
        self.csv_file = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_extract_labels(self):
        """Test extracting labels."""
        result = self.service.extract_labels(self.drawio_file, self.csv_file)
        self.assertIn("Extracted labels", result)
        self.assertTrue(os.path.exists(self.csv_file))

    def test_import_translations(self):
        """Test importing translations back into a .drawio file."""
        # 1. Create a dummy .drawio file
        drawio_content = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile><diagram><mxGraphModel><root>
    <mxCell id="1" value="Hello"/>
    <object id="2" label="World"/>
    <mxCell id="3" value="No translation for this"/>
</root></mxGraphModel></diagram></mxfile>"""
        with open(self.drawio_file, 'w', encoding='utf-8') as f:
            f.write(drawio_content)

        # 2. Create a dummy CSV with translations
        csv_content = (
            "id,label,label_de\n"
            "1,Hello,Hallo\n"
            "2,World,Welt\n"
        )
        with open(self.csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)

        # 3. Run the import service
        with patch.object(self.config, 'target_language', 'de'):
            result = self.service.import_translations(self.csv_file, self.drawio_file)
            self.assertIn("Successfully imported 2 translations", result)

        # 4. Verify the .drawio file was updated
        tree = ET.parse(self.drawio_file)
        root = tree.getroot()
        
        # Find the new object for the translated mxCell
        new_obj1 = root.find(".//*[@id='1']")
        self.assertIsNotNone(new_obj1)
        self.assertEqual(new_obj1.tag, 'object')
        self.assertEqual(new_obj1.get('label'), 'Hello')
        self.assertEqual(new_obj1.get('label_de'), 'Hallo')

        # Check that the original mxCell is now inside the object and has no id/value
        original_cell1 = new_obj1.find('mxCell')
        self.assertIsNotNone(original_cell1)
        self.assertIsNone(original_cell1.get('id'))
        self.assertIsNone(original_cell1.get('value'))

        # Check the existing object
        obj2 = root.find(".//*[@id='2']")
        self.assertIsNotNone(obj2)
        self.assertEqual(obj2.get('label'), 'World')
        self.assertEqual(obj2.get('label_de'), 'Welt')

        # Check the untranslated cell
        cell3 = root.find(".//*[@id='3']")
        self.assertIsNotNone(cell3)
        self.assertEqual(cell3.get('value'), 'No translation for this') # Should be unchanged

    @patch('translate.core.tqdm')
    @patch('translate.core.DeepLTranslator')
    def test_translate_csv_with_skips(self, MockDeepLTranslator, _mock_tqdm):
        """Test CSV translation, including skipping existing translations."""
        # Setup mock translator
        mock_translator_instance = MockDeepLTranslator.return_value
        mock_translator_instance.translate_text.side_effect = ["Hallo Welt", "Ein weiteres Label"]

        # Create a dummy CSV file with one existing translation
        csv_content = (
            "id,label,label_de\n"
            "1,Hello World,\n"  # To be translated
            "2,Already translated,Bereits übersetzt\n"  # To be skipped
            "3,Another Label,\n"  # To be translated
            "4,No Label,"  # To be ignored
        )
        with open(self.csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)

        # Patch config properties for this test
        with patch.object(self.config, 'deepl_api_key', 'fake-key'), \
             patch.object(self.config, 'source_language', 'en'), \
             patch.object(self.config, 'target_language', 'de'):
            # Run the service
            result = self.service.translate_csv(self.csv_file)
            self.assertEqual(result, "Translation complete. Translated: 2, Skipped: 1.")

            # Verify the translation call
            MockDeepLTranslator.assert_called_once_with('fake-key')
            self.assertEqual(mock_translator_instance.translate_text.call_count, 2)
            mock_translator_instance.translate_text.assert_any_call(
                "Hello World", source_lang='en', target_lang='de'
            )
            mock_translator_instance.translate_text.assert_any_call(
                "Another Label", source_lang='en', target_lang='de'
            )

            # Check the content of the updated CSV file
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 4)

                # Row 1: was translated
                self.assertEqual(rows[0]['label_de'], 'Hallo Welt')
                # Row 2: was skipped
                self.assertEqual(rows[1]['label_de'], 'Bereits übersetzt')
                # Row 3: was translated
                self.assertEqual(rows[2]['label_de'], 'Ein weiteres Label')
                # Row 4: was ignored
                self.assertEqual(rows[3]['label_de'], '')

    def test_translate_csv_no_api_key(self):
        """Test translating CSV when API key is missing."""
        # Ensure the API key is not set for this test
        with patch.object(self.config, 'deepl_api_key', None):
            with self.assertRaisesRegex(ConfigurationError, "DeepL API key not found"):
                self.service.translate_csv(self.csv_file)


if __name__ == '__main__':
    unittest.main()
