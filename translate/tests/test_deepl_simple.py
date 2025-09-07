#!/usr/bin/env python3
"""
Simple test script for DeepL API integration.
This script tests the DeepL API with a real API key.
"""

import os
import sys
from translate import DeepLTranslator, TranslationError

def test_deepl_translation():
    """Test DeepL translation with a simple text."""
    
    # Get API key from environment variable
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ Error: DEEPL_API_KEY environment variable not set")
        print("Please set your DeepL API key:")
        print("export DEEPL_API_KEY='your-api-key-here'")
        return False
    
    try:
        # Initialize translator
        translator = DeepLTranslator(api_key)
        
        # Test text
        test_text = "Hello, world! This is a test of the DeepL API integration."
        print(f"🔤 Original text: {test_text}")
        
        # Translate
        translated_text = translator.translate_text(
            test_text, 
            source_lang='EN', 
            target_lang='DE'
        )
        
        print(f"🌍 Translated text: {translated_text}")
        print("✅ DeepL API test successful!")
        return True
        
    except TranslationError as e:
        print(f"❌ Translation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_deepl_translation()
    sys.exit(0 if success else 1)
