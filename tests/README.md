# Crusader Kings 3 Auto Translator - Test Suite

This directory contains comprehensive unit tests for the Crusader Kings 3 Auto Translator application.

## Test Coverage

The test suite covers all 16 functions in `main.py` with 36 individual test cases:

### Functions Tested
- `get_loc_code()` - Language code conversion
- `load_config()` - Configuration loading
- `parseargs()` - Command line argument parsing
- `log_message()` - Logging functionality
- `extract_zip()` - ZIP file extraction
- `create_zip()` - ZIP file creation
- `get_already_translated_files()` - Translation progress tracking
- `validate_translation()` - Translation validation
- `process_zip_file()` - Single ZIP file processing
- `watch_and_process()` - Main processing workflow
- `init()` - Translation initialization
- `tofile()` - File writing functionality
- `translate_single()` - Single text translation
- `translate_batch()` - Batch text translation
- `write_failed_translations_to_csv()` - Error logging
- `translate()` - Main translation function

## Test Structure

### Test Classes
- `TestGetLocCode` - Language code mapping tests
- `TestLoadConfig` - Configuration loading tests
- `TestParseArgs` - CLI argument parsing tests
- `TestLogMessage` - Logging functionality tests
- `TestExtractZip` - ZIP extraction tests
- `TestCreateZip` - ZIP creation tests
- `TestGetAlreadyTranslatedFiles` - File tracking tests
- `TestValidateTranslation` - Validation tests
- `TestTranslateSingle` - Single translation tests
- `TestTranslateBatch` - Batch translation tests
- `TestWriteFailedTranslationsToCsv` - CSV writing tests
- `TestTranslate` - Main translation tests
- `TestTofile` - File output tests
- `TestInit` - Initialization tests
- `TestProcessZipFile` - ZIP processing tests
- `TestWatchAndProcess` - Main workflow tests

## Running Tests

### Basic Test Run
```bash
python -m pytest tests/
```

### With Coverage Report
```bash
python -m pytest tests/ --cov=main --cov-report=term-missing
```

### Verbose Output
```bash
python -m pytest tests/ -v
```

## Test Dependencies

Install test dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- pytest==7.4.3
- pytest-mock==3.12.0
- pytest-cov==4.1.0

## Coverage Report

Current test coverage: **81%**

Missing lines are primarily in:
- Error handling edge cases
- Debug print statements
- Rare execution paths
- Docker-specific logging

## Test Features

- **Comprehensive mocking** of external dependencies (Google Translate API, file operations)
- **Temporary directories** for safe file operations during testing
- **Edge case coverage** including error conditions and rate limiting
- **Real file operations** for ZIP creation/extraction testing
- **Environment variable mocking** for proper test isolation
- **CSV file testing** with both new and append scenarios

## Test Fixtures

- `temp_dir` - Temporary directory for file operations
- `sample_config` - Standard configuration dictionary
- `sample_yml_content` - Sample YAML localization content

## Mocking Strategy

- **GoogleTranslator** - Mocked to avoid API calls and test error handling
- **File operations** - Mixed real files and mocks based on test needs
- **Path operations** - Mocked for controlled testing
- **Environment variables** - Properly isolated per test
- **External dependencies** - Fully mocked for reliable testing

## Test Categories

### Unit Tests
- Individual function testing with mocked dependencies
- Error condition testing
- Edge case validation

### Integration Tests
- File processing workflows
- ZIP file operations
- Translation pipeline testing

### Error Handling Tests
- Rate limiting scenarios
- File operation failures
- Network error simulation
- Invalid input handling

## Offline Testing Capability

The test suite is designed to run **completely offline** without requiring any internet connection. This ensures reliable testing in environments with limited or no network access.

### How Offline Testing Works

1. **Module-Level Mocking**: The `deep_translator` module is mocked at the Python module level before importing the main application code
2. **Google Translate API Mocking**: All calls to Google Translate are intercepted and return predetermined mock responses
3. **Local File Operations**: All file operations use temporary directories and local filesystem only
4. **No External Dependencies**: Tests don't rely on external services, databases, or network resources

### Running Tests Offline

```bash
# Standard pytest (automatically offline due to mocking)
python -m pytest tests/

# Explicit offline verification
python test_offline.py
```

### Offline Test Features

- **Network Independence**: Tests run without internet connectivity
- **Deterministic Results**: Mock responses ensure consistent test outcomes
- **Fast Execution**: No network latency or API rate limiting
- **Reliable CI/CD**: Tests work in isolated build environments
- **Error Simulation**: Tests can simulate network failures and API errors without actual network issues

### Mocking Strategy

- **deep_translator.GoogleTranslator**: Fully mocked with configurable responses
- **Translation API calls**: Return mock translations or simulate failures
- **Rate limiting**: Can simulate API quota exceeded errors
- **Network timeouts**: Can simulate connection failures

This offline-first approach ensures the test suite is robust, fast, and reliable across all deployment scenarios.