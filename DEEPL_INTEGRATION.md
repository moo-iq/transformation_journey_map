# DeepL API Integration

This document explains how to use the DeepL API integration in the translate module.

## Setup

### 1. Install Dependencies

```bash
pip install requests
```

### 2. Configure API Key

Create a `.env` file in the `translate/` directory:

```bash
# DeepL API Configuration
deepl_api=your-deepl-api-key-here

# Language Configuration (optional)
language_source=en
language_target=de
```

Or set the environment variable:

```bash
export DEEPL_API_KEY="your-deepl-api-key-here"
```

## Usage

### Basic Translation

```python
from translate import DeepLTranslator

# Initialize translator
translator = DeepLTranslator("your-api-key")

# Translate text
result = translator.translate_text(
    "Hello, world!", 
    source_lang='EN', 
    target_lang='DE'
)
print(result)  # "Hallo, Welt!"
```

### Using Configuration

```python
from translate import DeepLTranslator, Config

# Load configuration from .env
config = Config()
translator = DeepLTranslator(config.deepl_api_key)

# Translate text
result = translator.translate_text(
    "Hello, world!", 
    source_lang='EN', 
    target_lang='DE'
)
```

## Testing

Run the DeepL integration tests:

```bash
python -m pytest translate/tests/test_translator.py::TestDeepLTranslation -v
```

## Error Handling

The `DeepLTranslator` raises `TranslationError` for various error conditions:

- Invalid API key
- Network errors
- API rate limits
- Invalid language codes

```python
from translate import DeepLTranslator, TranslationError

try:
    translator = DeepLTranslator("invalid-key")
    result = translator.translate_text("Hello", "EN", "DE")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

## API Endpoints

The integration uses the DeepL Free API endpoint:
- URL: `https://api-free.deepl.com/v2/translate`
- Rate limits: 500,000 characters per month
- Supported languages: See DeepL documentation

For production use, consider upgrading to DeepL Pro API for higher rate limits.
