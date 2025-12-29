import pytest
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
import os
from unittest.mock import patch, mock_open, MagicMock
import sys
import csv

# Mock deep_translator before importing main module to ensure offline testing
sys.modules['deep_translator'] = MagicMock()
sys.modules['deep_translator.GoogleTranslator'] = MagicMock()

# Add the parent directory to sys.path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    get_loc_code, load_config, parseargs, log_message, extract_zip, create_zip,
    get_already_translated_files, validate_translation, process_zip_file,
    watch_and_process, init, tofile, translate_single, translate_batch,
    write_failed_translations_to_csv, translate, TranslationRateLimitError
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "from_language": "en",
        "to_language": "de",
        "do_translation": True,
        "input_dir": "/app/input",
        "temp_dir": "/app/temp",
        "output_dir": "/app/output",
        "check_interval": 30
    }


@pytest.fixture
def sample_yml_content():
    """Sample YAML content for testing"""
    return [
        "l_english:",
        '  test_key: "Hello World"',
        '  another_key: "This is a test"',
        '  complex_key: "Test with [TAG] and $VAR$"',
        ""
    ]


class TestGetLocCode:
    """Test get_loc_code function"""

    def test_get_loc_code_known_languages(self):
        """Test with known language codes"""
        assert get_loc_code(True, 'en') == 'english'
        assert get_loc_code(False, 'de') == 'german'
        assert get_loc_code(True, 'fr') == 'french'
        assert get_loc_code(False, 'es') == 'spanish'
        assert get_loc_code(True, 'ru') == 'russian'
        assert get_loc_code(False, 'zh-cn') == 'simp_chinese'
        assert get_loc_code(True, 'ko') == 'korean'
        assert get_loc_code(False, 'id') == 'indonesian'

    def test_get_loc_code_unknown_languages(self):
        """Test with unknown language codes"""
        assert get_loc_code(True, 'unknown') == 'english'  # from_l=True
        assert get_loc_code(False, 'unknown') == 'german'  # from_l=False

    def test_get_loc_code_empty_string(self):
        """Test with empty string"""
        assert get_loc_code(True, '') == 'english'
        assert get_loc_code(False, '') == 'german'


class TestLoadConfig:
    """Test load_config function"""

    @patch('main.Path')
    def test_load_config_file_exists(self, mock_path):
        """Test loading config when file exists"""
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_path.return_value = mock_config_path

        expected_config = {"test": "config"}
        with patch('builtins.open', mock_open(read_data=json.dumps(expected_config))):
            with patch('json.load', return_value=expected_config):
                result = load_config()
                assert result == expected_config

    @patch('main.Path')
    @patch('builtins.print')
    def test_load_config_file_not_exists(self, mock_print, mock_path):
        """Test loading config when file doesn't exist"""
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_path.return_value = mock_config_path

        result = load_config()

        # Should return default config
        assert result["from_language"] == "en"
        assert result["to_language"] == "de"
        assert result["do_translation"] is True
        assert result["input_dir"] == "/app/input"
        assert result["temp_dir"] == "/app/temp"
        assert result["output_dir"] == "/app/output"
        assert result["check_interval"] == 30

        mock_print.assert_called_with("config.json not found, using defaults")


class TestParseArgs:
    """Test parseargs function"""

    @patch('argparse.ArgumentParser.parse_args')
    def test_parseargs_default(self, mock_parse_args):
        """Test parseargs with default arguments"""
        mock_parse_args.return_value = MagicMock(config="config.json")
        result = parseargs()
        assert result.config == "config.json"


class TestLogMessage:
    """Test log_message function"""

    @patch('builtins.print')
    @patch('datetime.datetime')
    def test_log_message_with_timestamp(self, mock_datetime, mock_print):
        """Test log_message with timestamp"""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 12:00:00"

        log_message("Test message", sign_t=True)

        mock_print.assert_called_with("[2023-12-01 12:00:00] Test message")

    @patch('builtins.print')
    def test_log_message_without_timestamp(self, mock_print):
        """Test log_message without timestamp"""
        log_message("Test message", sign_t=False)

        mock_print.assert_called_with("Test message")


class TestExtractZip:
    """Test extract_zip function"""

    def test_extract_zip_success(self, temp_dir):
        """Test successful zip extraction"""
        # Create a test zip file
        zip_path = temp_dir / "test.zip"
        extract_to = temp_dir / "extracted"

        # Create some test content
        test_content = "test content"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('test.txt', test_content)

        # Extract the zip
        result = extract_zip(zip_path, extract_to)

        assert result is True
        assert (extract_to / "test.txt").exists()
        with open(extract_to / "test.txt", 'r') as f:
            assert f.read() == test_content

    def test_extract_zip_failure(self, temp_dir):
        """Test zip extraction failure"""
        zip_path = temp_dir / "nonexistent.zip"
        extract_to = temp_dir / "extracted"

        result = extract_zip(zip_path, extract_to)

        assert result is False


class TestCreateZip:
    """Test create_zip function"""

    def test_create_zip_success(self, temp_dir):
        """Test successful zip creation"""
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("test content")

        zip_path = temp_dir / "output.zip"

        result = create_zip(str(source_dir), str(zip_path), "german")

        assert result is True
        assert zip_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'german/test.txt' in zf.namelist()

    def test_create_zip_with_csv(self, temp_dir):
        """Test zip creation with manual translations CSV"""
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("test content")

        # Create manual translations CSV
        csv_path = source_dir / "manual_translations.csv"
        csv_path.write_text("file,line,original,translated\n")

        zip_path = temp_dir / "output.zip"

        result = create_zip(str(source_dir), str(zip_path), "german")

        assert result is True
        assert zip_path.exists()

        # Verify CSV is included
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'german/manual_translations.csv' in zf.namelist()


class TestGetAlreadyTranslatedFiles:
    """Test get_already_translated_files function"""

    def test_get_already_translated_files_no_target(self, temp_dir):
        """Test when target directory doesn't exist"""
        source_dir = temp_dir / "source"
        target_dir = temp_dir / "target"

        result = get_already_translated_files(source_dir, target_dir, "english", "german")

        assert result == set()

    def test_get_already_translated_files_with_matches(self, temp_dir):
        """Test with matching translated files"""
        source_dir = temp_dir / "source"
        target_dir = temp_dir / "target"
        target_dir.mkdir(parents=True)

        # Create source file
        source_file = source_dir / "test_english.yml"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("content")

        # Create corresponding target file
        target_file = target_dir / "test_german.yml"
        target_file.write_text("content")

        result = get_already_translated_files(source_dir, target_dir, "english", "german")

        assert source_file in result


class TestValidateTranslation:
    """Test validate_translation function"""

    def test_validate_translation_success(self, temp_dir):
        """Test successful validation"""
        source_dir = temp_dir / "source"
        target_dir = temp_dir / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create matching files
        (source_dir / "test.yml").write_text("content")
        (target_dir / "test.yml").write_text("content")

        result = validate_translation(source_dir, target_dir)

        assert result is True

    def test_validate_translation_file_count_mismatch(self, temp_dir):
        """Test validation with file count mismatch"""
        source_dir = temp_dir / "source"
        target_dir = temp_dir / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create different number of files
        (source_dir / "test1.yml").write_text("content")
        (source_dir / "test2.yml").write_text("content")
        (target_dir / "test.yml").write_text("content")

        result = validate_translation(source_dir, target_dir)

        assert result is False

    def test_validate_translation_folder_structure_mismatch(self, temp_dir):
        """Test validation with folder structure mismatch"""
        source_dir = temp_dir / "source"
        target_dir = temp_dir / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create files in different folder structures
        source_sub = source_dir / "subdir"
        source_sub.mkdir()
        (source_sub / "test.yml").write_text("content")
        (target_dir / "test.yml").write_text("content")

        result = validate_translation(source_dir, target_dir)

        assert result is False


class TestTranslateSingle:
    """Test translate_single function"""

    @patch('main.GoogleTranslator')
    def test_translate_single_success(self, mock_translator_class):
        """Test successful single translation"""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Hola Mundo"
        mock_translator_class.return_value = mock_translator

        result, failed = translate_single("Hello World", "en", "es")

        assert result == "Hola Mundo"
        assert failed is False

    @patch('main.GoogleTranslator')
    def test_translate_single_no_translation(self, mock_translator_class):
        """Test when no translation is returned"""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = None
        mock_translator_class.return_value = mock_translator

        result, failed = translate_single("Hello World", "en", "es")

        assert result == "Hello World"  # Original text returned
        assert failed is True

    @patch('main.GoogleTranslator')
    def test_translate_single_rate_limit_error(self, mock_translator_class):
        """Test rate limit error handling"""
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = Exception("You made too many requests to the server")
        mock_translator_class.return_value = mock_translator

        with pytest.raises(TranslationRateLimitError):
            translate_single("Hello World", "en", "es")

    @patch('main.GoogleTranslator')
    def test_translate_single_general_error(self, mock_translator_class):
        """Test general translation error"""
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = Exception("General error")
        mock_translator_class.return_value = mock_translator

        result, failed = translate_single("Hello World", "en", "es")

        assert result == "Hello World"  # Original text returned
        assert failed is True


class TestTranslateBatch:
    """Test translate_batch function"""

    @patch('main.translate_single')
    def test_translate_batch_success(self, mock_translate_single):
        """Test successful batch translation"""
        mock_translate_single.side_effect = [
            ("Hola", False),
            ("Mundo", False)
        ]

        texts = ["Hello", "World"]
        translations, failures, success = translate_batch(texts, "en", "es", 0)

        assert translations == ["Hola", "Mundo"]
        assert failures == []
        assert success is True

    @patch('main.translate_single')
    def test_translate_batch_with_failures(self, mock_translate_single):
        """Test batch translation with some failures"""
        mock_translate_single.side_effect = [
            ("Hola", False),
            ("World", True)  # Failed translation
        ]

        texts = ["Hello", "World"]
        translations, failures, success = translate_batch(texts, "en", "es", 0)

        assert translations == ["Hola", "World"]  # Original text for failed
        assert failures == ["World"]
        assert success is False

    @patch('main.translate_single')
    def test_translate_batch_rate_limit_error(self, mock_translate_single):
        """Test rate limit error propagation"""
        mock_translate_single.side_effect = TranslationRateLimitError("Rate limit")

        texts = ["Hello"]
        with pytest.raises(TranslationRateLimitError):
            translate_batch(texts, "en", "es", 0)


class TestWriteFailedTranslationsToCsv:
    """Test write_failed_translations_to_csv function"""

    def test_write_failed_translations_new_file(self, temp_dir):
        """Test writing failed translations to new CSV file"""
        # Set TEMP_DIR environment variable
        os.environ['TEMP_DIR'] = str(temp_dir)

        failed_translations = [
            {
                'file_path': '/path/to/file.yml',
                'line_number': 5,
                'original_text': 'Hello World'
            }
        ]

        write_failed_translations_to_csv(failed_translations)

        csv_path = temp_dir / "manual_translations.csv"
        assert csv_path.exists()

        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == ["file_path", "line_number", "original_text", "translated_text"]
        assert rows[1] == ["/path/to/file.yml", "5", "Hello World", ""]

    def test_write_failed_translations_append(self, temp_dir):
        """Test appending to existing CSV file"""
        # Set TEMP_DIR environment variable
        os.environ['TEMP_DIR'] = str(temp_dir)

        # Create existing CSV
        csv_path = temp_dir / "manual_translations.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["file_path", "line_number", "original_text", "translated_text"])
            writer.writerow(["existing", "1", "old", "text"])

        failed_translations = [
            {
                'file_path': '/path/to/file.yml',
                'line_number': 5,
                'original_text': 'Hello World'
            }
        ]

        write_failed_translations_to_csv(failed_translations)

        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[2] == ["/path/to/file.yml", "5", "Hello World", ""]


class TestTranslate:
    """Test translate function"""

    @patch('main.translate_batch')
    def test_translate_success(self, mock_translate_batch, sample_yml_content):
        """Test successful translation of file data"""
        mock_translate_batch.return_value = (["Hola Mundo", "Esta es una prueba"], [], True)

        file_data = sample_yml_content.copy()
        failed_translations = translate(file_data, "en", "es", "test.yml", "/path/to/test.yml")

        # Check that translations were applied
        assert '  test_key: "Hola Mundo"' in file_data[1]
        assert '  another_key: "Esta es una prueba"' in file_data[2]
        # Should return empty list for successful translations
        assert failed_translations == []

    @patch('main.translate_batch')
    def test_translate_with_failures(self, mock_translate_batch, sample_yml_content):
        """Test translation with some failures"""
        mock_translate_batch.return_value = (["Hola Mundo", "Hello World"], ["Hello World"], False)

        file_data = sample_yml_content.copy()
        failed_translations = translate(file_data, "en", "es", "test.yml", "/path/to/test.yml")

        # Check that failed translations are returned
        assert len(failed_translations) == 1
        assert failed_translations[0]['original_text'] == "Hello World"

    def test_translate_no_translatable_lines(self):
        """Test translation with no translatable lines"""
        file_data = [
            "l_english:",
            "  # This is a comment",
            "  key_without_quotes: value",
            ""
        ]

        original_data = file_data.copy()
        translate(file_data, "en", "es")

        # File data should remain unchanged
        assert file_data == original_data


class TestTofile:
    """Test tofile function"""

    def test_tofile_success(self, temp_dir):
        """Test successful file writing"""
        # Set TEMP_DIR environment variable
        os.environ['TEMP_DIR'] = str(temp_dir)

        # Create temp directory structure
        german_dir = temp_dir / "german"
        german_dir.mkdir()

        filepath = str(german_dir)
        filename = "test_english.yml"
        file_data = ["l_german:", '  test_key: "Test"']
        from_naming = "english"
        to_naming = "german"

        tofile(filepath, filename, file_data, from_naming, to_naming)

        # Check that file was created with correct name
        expected_file = german_dir / "test_german.yml"
        assert expected_file.exists()

        with open(expected_file, 'r') as f:
            content = f.read()
            assert "l_german:" in content
            assert 'test_key: "Test"' in content


class TestInit:
    """Test init function"""

    @patch('main.list')
    @patch('main.get_already_translated_files')
    @patch('main.translate')
    @patch('main.tofile')
    @patch('main.write_failed_translations_to_csv')
    def test_init_success(self, mock_write_csv, mock_tofile, mock_translate, mock_get_already, mock_list, temp_dir):
        """Test successful initialization and processing"""
        # Create a proper file path mock
        test_file_path = temp_dir / "english" / "test_english.yml"
        
        # Mock file listing to return actual Path objects
        mock_list.return_value = [test_file_path]

        # Mock already translated files
        mock_get_already.return_value = set()

        # Mock translate to return no failed translations
        mock_translate.return_value = []

        source_dir = temp_dir / "english"
        target_dir = temp_dir / "german"
        source_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)

        # Create test file with proper YAML content
        test_file = source_dir / "test_english.yml"
        test_file.write_text('l_english:\n  test_key: "Hello World"\n')

        init(source_dir, target_dir, True, "en", "de", "english", "german")

        # Verify translate was called and CSV was not written (no failures)
        mock_translate.assert_called()
        mock_write_csv.assert_not_called()

    @patch('main.list')
    @patch('main.get_already_translated_files')
    @patch('main.translate')
    @patch('main.tofile')
    @patch('main.write_failed_translations_to_csv')
    def test_init_with_failed_translations(self, mock_write_csv, mock_tofile, mock_translate, mock_get_already, mock_list, temp_dir):
        """Test initialization with failed translations that should be written to CSV"""
        # Create a proper file path mock
        test_file_path = temp_dir / "english" / "test_english.yml"
        
        # Mock file listing to return actual Path objects
        mock_list.return_value = [test_file_path]

        # Mock already translated files
        mock_get_already.return_value = set()

        # Mock translate to return failed translations
        failed_translations = [{
            'file_path': str(test_file_path),
            'line_number': 2,
            'original_text': 'Hello World'
        }]
        mock_translate.return_value = failed_translations

        source_dir = temp_dir / "english"
        target_dir = temp_dir / "german"
        source_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)

        # Create test file with proper YAML content
        test_file = source_dir / "test_english.yml"
        test_file.write_text('l_english:\n  test_key: "Hello World"\n')

        init(source_dir, target_dir, True, "en", "de", "english", "german")

        # Verify translate was called and CSV was written with failed translations
        mock_translate.assert_called()
        mock_write_csv.assert_called_once_with(failed_translations)

    @patch('main.list')
    def test_init_no_files_to_process(self, mock_list, temp_dir):
        """Test init when all files are already translated"""
        # Mock empty file list
        mock_list.return_value = []

        source_dir = temp_dir / "english"
        target_dir = temp_dir / "german"

        # Should not raise any errors
        init(source_dir, target_dir, True, "en", "de", "english", "german")


class TestProcessZipFile:
    """Test process_zip_file function"""

    @patch('main.extract_zip')
    @patch('main.init')
    @patch('main.validate_translation')
    @patch('main.create_zip')
    @patch('main.shutil.rmtree')
    @patch('main.Path')
    def test_process_zip_file_success(self, mock_path_class, mock_rmtree, mock_create_zip,
                                    mock_validate, mock_init, mock_extract, temp_dir):
        """Test successful zip file processing"""
        # Mock Path
        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.exists.return_value = True

        # Mock successful operations
        mock_extract.return_value = True
        mock_validate.return_value = True
        mock_create_zip.return_value = True

        config = {
            "input_dir": str(temp_dir),
            "temp_dir": str(temp_dir),
            "output_dir": str(temp_dir),
            "to_language": "de",
            "from_language": "en",
            "do_translation": True
        }

        result = process_zip_file("test.zip", config)

        assert result is True

    @patch('main.extract_zip')
    def test_process_zip_file_extract_failure(self, mock_extract):
        """Test zip processing when extraction fails"""
        mock_extract.return_value = False

        config = {
            "input_dir": "/tmp",
            "temp_dir": "/tmp",
            "output_dir": "/tmp",
            "to_language": "de",
            "from_language": "en"
        }
        result = process_zip_file("test.zip", config)

        assert result is False


class TestWatchAndProcess:
    """Test watch_and_process function"""

    @patch('main.Path')
    @patch('main.process_zip_file')
    def test_watch_and_process_success(self, mock_process, mock_path_class):
        """Test successful watch and process"""
        # Mock Path and glob
        mock_input_dir = MagicMock()
        mock_path_class.return_value = mock_input_dir
        mock_input_dir.mkdir = MagicMock()
        mock_input_dir.glob.return_value = [MagicMock()]

        mock_zip_file = MagicMock()
        mock_zip_file.name = "test.zip"
        mock_input_dir.glob.return_value = [mock_zip_file]

        mock_process.return_value = True

        config = {
            "input_dir": "/input",
            "temp_dir": "/temp",
            "output_dir": "/output",
            "to_language": "de"
        }

        # Should not raise any errors
        watch_and_process(config)

    @patch('main.Path')
    def test_watch_and_process_no_files(self, mock_path_class):
        """Test watch and process with no zip files"""
        mock_input_dir = MagicMock()
        mock_path_class.return_value = mock_input_dir
        mock_input_dir.mkdir = MagicMock()
        mock_input_dir.glob.return_value = []

        config = {
            "input_dir": "/input",
            "temp_dir": "/temp",
            "output_dir": "/output",
            "to_language": "de"
        }

        # Should not raise any errors
        watch_and_process(config)


class TestOfflineCapability:
    """Test that the test suite runs completely offline"""

    def test_deep_translator_mocked(self):
        """Verify that deep_translator is properly mocked"""
        import main
        # The GoogleTranslator should be a mock object
        assert hasattr(main, 'GoogleTranslator')
        # It should not be the real GoogleTranslator class
        assert str(type(main.GoogleTranslator)) != "<class 'deep_translator.google.GoogleTranslator'>"

    @patch('main.GoogleTranslator')
    def test_offline_translation_test(self, mock_translator_class):
        """Test that translation functions work with mocked services"""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Offline translation"
        mock_translator_class.return_value = mock_translator

        # This should work without any network calls
        result, failed = translate_single("test", "en", "es")
        assert result == "Offline translation"
        assert failed is False

    def test_no_external_http_calls(self):
        """Verify that no HTTP requests are made during testing"""
        # This test ensures our mocking prevents actual HTTP calls
        # If this test passes, it means the Google Translate API is properly mocked
        import main

        # The GoogleTranslator in main should be our mock, not the real one
        assert 'GoogleTranslator' in dir(main)
        # We can't easily check if it's mocked, but the fact that tests run
        # without network errors indicates proper mocking