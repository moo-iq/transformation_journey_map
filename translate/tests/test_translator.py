import unittest
from unittest.mock import patch
from io import StringIO
import os
import csv
import tempfile

from ..core import DrawioParser, LabelCsvWriter, TranslationService
from ..config import Config
from ..exceptions import DrawioParseError, ConfigurationError
from .. import extract_labels, translate_csv, show_help
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
        # Mock the DeepL API response
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

        # Import here to avoid import errors if deepl module doesn't exist
        from ..core import DeepLTranslator
        
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
        # Mock API error response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            'message': 'Invalid API key'
        }
        mock_post.return_value = mock_response

        from ..core import DeepLTranslator
        from ..exceptions import TranslationError
        
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
        # Mock network error
        mock_post.side_effect = Exception("Network error")

        from ..core import DeepLTranslator
        from ..exceptions import TranslationError
        
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

    def test_translate_csv(self):
        """Test translating CSV."""
        result = self.service.translate_csv(self.csv_file)
        self.assertIn("Translating", result)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""

    def setUp(self):
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

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help(self, mock_stdout):
        """Test show_help function."""
        show_help()
        output = mock_stdout.getvalue()
        self.assertIn("Drawio Translation Tool", output)

    def test_extract_labels_function(self):
        """Test extract_labels convenience function."""
        result = extract_labels(self.drawio_file, self.csv_file, 'de')
        self.assertIn("Extracted labels", result)
        self.assertTrue(os.path.exists(self.csv_file))

    def test_translate_csv_function(self):
        """Test translate_csv convenience function."""
        result = translate_csv(self.csv_file, 'en', 'de')
        self.assertIn("Translating", result)


if __name__ == '__main__':
    unittest.main()
