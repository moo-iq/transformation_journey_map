import unittest
from unittest.mock import patch
from io import StringIO
from ..translator import show_help, set_language, extract_labels, translate_csv
import os
import csv

class TestTranslator(unittest.TestCase):

    def setUp(self):
        self.drawio_file = os.path.join(os.path.dirname(__file__), 'test_resources', 'text.drawio')
        self.csv_file = os.path.join(os.path.dirname(__file__), 'test_resources', 'test.csv')

    def tearDown(self):
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help(self, mock_stdout):
        show_help()
        self.assertEqual(mock_stdout.getvalue().strip(), 'This is the help message.')

    def test_set_language(self):
        source, target = set_language('en', 'de')
        self.assertEqual(source, 'Source language set to: en')
        self.assertEqual(target, 'Target language set to: de')

    def test_extract_labels(self):
        result = extract_labels(self.drawio_file, self.csv_file)
        self.assertEqual(result, f"Extracted labels from {self.drawio_file} to {self.csv_file}")
        self.assertTrue(os.path.exists(self.csv_file))
        with open(self.csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, ['id', 'label', 'label_de'])
            # Add more assertions here to check the content of the CSV file
            # based on the content of the test.drawio file.

    def test_translate_csv(self):
        result = translate_csv(self.csv_file)
        self.assertEqual(result, f"Translating {self.csv_file}")

if __name__ == '__main__':
    unittest.main()
