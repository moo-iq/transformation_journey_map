#!/usr/bin/env python3
"""
Test script for DeepL API using .env file configuration.
This script tests the DeepL API using the deepl_api key from .env file.
"""

import os
import sys
from translate import DeepLTranslator, TranslationError, Config

def test_deepl_with_env():
    """Test DeepL translation using .env configuration."""
    
    try:
        # Load configuration from .env file
        config = Config()
        api_key = config.deepl_api_key
        
        if not api_key:
            print("❌ Error: deepl_api key not found in .env file")
            print("Please add your DeepL API key to translate/.env:")
            print("deepl_api=your-api-key-here")
            return False
        
        print(f"🔑 Using API key: {api_key[:8]}...")
        
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
        print("✅ DeepL API test with .env configuration successful!")
        return True
        
    except TranslationError as e:
        print(f"❌ Translation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_deepl_with_env()
    sys.exit(0 if success else 1)
