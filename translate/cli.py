"""Command-line interface for the translate module."""

import argparse
from .core import TranslationService
from .config import Config
from .exceptions import ConfigurationError, TranslationError


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description='Translate .drawio files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s extract_labels diagram.drawio labels.csv --target-lang de
  %(prog)s translate labels.csv --source-lang en --target-lang de
        """
    )

    subparsers = parser.add_subparsers(
        dest='command', help='Available commands', required=True
    )

    # Extract labels command
    extract_parser = subparsers.add_parser(
        'extract_labels',
        help='Extract labels from a .drawio file to CSV'
    )
    extract_parser.add_argument(
        'drawio_file',
        help='Path to the .drawio file'
    )
    extract_parser.add_argument(
        'csv_file',
        help='Path to the output CSV file'
    )
    extract_parser.add_argument(
        '--target-lang',
        default='de',
        help='Target language code (default: de)'
    )

    # Translate CSV command
    translate_parser = subparsers.add_parser( # Renamed from translate_csv
        'translate',
        help='Translate a CSV file using DeepL, with progress bar'
    )
    translate_parser.add_argument(
        'csv_file',
        help='Path to the CSV file'
    )
    translate_parser.add_argument(
        '--source-lang',
        default='en',
        help='Source language code (default: en)'
    )
    translate_parser.add_argument(
        '--target-lang',
        default='de',
        help='Target language code (default: de)'
    )

    return parser


def main() -> None:
    """Main function for the translator CLI."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Initialize configuration
        config = Config()

        # Override config with command line arguments if provided
        if hasattr(args, 'target_lang'):
            config.set_target_language(args.target_lang)
        if hasattr(args, 'source_lang'):
            config.set_source_language(args.source_lang)

        # Initialize translation service
        service = TranslationService(config)

        if args.command == 'extract_labels':
            result = service.extract_labels(args.drawio_file, args.csv_file)
            print(f"✓ {result}")

        elif args.command == 'translate':
            result = service.translate_csv(args.csv_file)
            print(f"✓ {result}")

    except (TranslationError, ConfigurationError) as e:
        print(f"✗ Error: {e}")
        exit(1)
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled by user")
        exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        exit(1)


if __name__ == '__main__':
    main()
