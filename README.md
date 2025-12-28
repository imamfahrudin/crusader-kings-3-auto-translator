
# Crusader Kings 3 Auto Translator 🌍🔄

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automatically translate Crusader Kings 3 localization files to multiple languages using Google Translate API. Features Docker support, automatic validation, batch processing, and intelligent cleanup for seamless mod translation workflows.

## ⚠️ Notice

This project is actively maintained but may have edge cases. If you encounter a bug, please open an issue with the files needed to reproduce the error.

## 👥 Authors

- [@CyberNord](https://github.com/CyberNord) - Main developer
- [@Martin220799](https://github.com/Martin220799) - PowerShell controls
- [@imamfahrudin](https://github.com/imamfahrudin) - Docker implementation, validation system, and enhanced logging

## 🌟 Features

- **Docker Support**: Ready-to-deploy containerized application with Docker Compose
- **Automatic Processing**: Watches input folder for zip files and processes automatically
- **Validation System**: Ensures all files are translated correctly before creating output
- **Smart Cleanup**: Automatic temporary file cleanup after successful processing
- **Batch Translation**: Processes multiple lines at once for 20x faster translation
- **Progress Tracking**: Real-time progress indicators with file-by-file tracking
- **Multi-Language**: Support for 8 languages (English, German, French, Spanish, Russian, Chinese, Korean, Indonesian)
- **Intelligent Extraction**: Handles zip files with proper path normalization
- **Error Handling**: Robust error handling with comprehensive logging
- **Compatible**: Works with other Paradox titles (Stellaris, EU4, etc.)

## 📋 Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- Internet connection for Google Translate API access

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/crusader-kings-3-auto-translator.git
   cd crusader-kings-3-auto-translator
   ```

2. **Configure the target language**
   
   Edit `config.json` with your desired settings:
   ```json
   {
     "from_language": "en",
     "to_language": "de",
     "do_translation": true,
     "input_dir": "/app/input",
     "temp_dir": "/app/temp",
     "output_dir": "/app/output",
     "check_interval": 30
   }
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

The service will process zip files placed in the `input/` folder and output translated files to `output/`.

### Option 2: Local Python Deployment

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/crusader-kings-3-auto-translator.git
   cd crusader-kings-3-auto-translator
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**
   
   Edit `config.json` with your target language preferences

5. **Run the application**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Configuration File

Edit `config.json` to customize translation settings:

```json
{
  "from_language": "en",        // Source language code
  "to_language": "de",          // Target language code
  "do_translation": true,       // Enable/disable translation
  "input_dir": "/app/input",    // Input directory path
  "temp_dir": "/app/temp",      // Temporary files directory
  "output_dir": "/app/output",  // Output directory path
  "check_interval": 30          // Seconds between checks (Docker mode)
}
```

**Configuration Options:**
- **from_language**: Source language code (default: "en")
- **to_language**: Target language code (default: "de")
- **do_translation**: Enable/disable translation (default: true)
- **input_dir**: Input directory path (default: "/app/input")
- **temp_dir**: Temporary files directory (default: "/app/temp")
- **output_dir**: Output directory path (default: "/app/output")
- **check_interval**: Seconds between input folder checks in Docker mode (default: 30)

### Supported Languages

The translator supports all languages available in Crusader Kings 3:

| Code | Language |
|------|----------|
| `en` | English |
| `de` | German |
| `fr` | French |
| `es` | Spanish |
| `ru` | Russian |
| `zh-cn` | Simplified Chinese |
| `ko` | Korean |
| `id` | Indonesian |

## 🔧 How It Works

1. **Input Detection**: Application monitors `input/` folder for zip files
2. **Extraction**: Extracts zip contents with path normalization
3. **Validation**: Checks for required `english/` folder structure
4. **Translation**: Processes all `.yml` files using batch translation
5. **Validation**: Verifies all source files have corresponding translated files
6. **Output**: Creates translated zip file in `output/` folder
7. **Cleanup**: Moves original zip to `processed/` and clears temporary files

## 📊 Usage

### Docker Mode

1. **Place zip files** in the `input/` directory
2. **Monitor progress** via Docker logs:
   ```bash
   docker-compose logs -f
   ```
3. **Retrieve translated files** from the `output/` directory
4. **Original files** are moved to `input/processed/`

### Zip File Requirements

Your zip file must follow this structure:

```
your_mod.zip
└── english/
    ├── file1_english.yml
    ├── file2_english.yml
    └── subfolder/
        └── file3_english.yml
```

✅ **Correct**: Contains `english/` folder at root
❌ **Incorrect**: Files directly at root without `english/` folder

See `input/README.txt` for detailed requirements.

### Manual Mode (Legacy)

For command-line usage without Docker:

```bash
python main.py
```

The application will process zip files once and exit.

### Docker Commands

```bash
# Start the service
docker-compose up -d

# View real-time logs
docker-compose logs -f

# Stop the service
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Restart the service
docker-compose restart
```

## 📈 Translation Performance

The translator uses **batch processing** for optimal speed:

- **Batch Size**: 20 lines per batch
- **Parallel Processing**: Translates multiple lines simultaneously
- **Speed**: Up to 20x faster than line-by-line translation
- **Reliability**: Automatic retry on API failures
- **Validation**: Ensures translation quality before output

### Progress Tracking

Real-time progress indicators show:
- File processing status (`[1/5] Processing: file.yml`)
- Translation progress (`Progress: 15/15 lines (100%)`)
- Validation results (✓ All files translated successfully)
- Cleanup status (✓ Temp directory cleared)

## 💡 Examples

### Docker Deployment Example
**Scenario**: Translate a mod from English to German

1. Place `my_mod.zip` in `input/` folder
2. Set `"to_language": "de"` in `config.json`
3. Run `docker-compose up -d`
4. Check logs: `docker-compose logs -f`
5. Find `my_mod_de.zip` in `output/` folder
6. Original moved to `input/processed/my_mod.zip`

### Multiple Language Translation

**Scenario**: Translate the same mod to French and Spanish

1. Process with German (as above)
2. Stop service: `docker-compose down`
3. Change config: `"to_language": "fr"`
4. Restore zip: Copy from `input/processed/` back to `input/`
5. Restart: `docker-compose up -d`
6. Repeat for Spanish with `"to_language": "es"`

### File Conversion Only

**Scenario**: Create localization structure without translation

1. Set `"do_translation": false` in `config.json`
2. Place zip in `input/` folder
3. Output will have proper structure with English text

## 📝 Logging

The application provides detailed console logging for monitoring:

**Log Levels:**
- **INFO**: General status and progress updates
- **ERROR**: Critical errors requiring attention
- **File Progress**: Per-file processing status
- **Translation Progress**: Line-by-line translation completion

**View Logs:**
```bash
# Docker deployment
docker-compose logs -f

# Local Python
# Logs appear in console where you ran python main.py
```

**Example Log Output:**
```
Starting Crusader Kings 3 Auto Translator
Processing zip files from /app/input
Found zip file: my_mod.zip

Processing: my_mod.zip
Translation: en → de

Found 3 localization file(s) to process

[1/3] Processing: events_english.yml
  Translating 45 line(s)...
  Progress: 45/45 lines (100%)
  ✓ Completed: events_english.yml

[2/3] Processing: decisions_english.yml
  Translating 32 line(s)...
  Progress: 32/32 lines (100%)
  ✓ Completed: decisions_english.yml

[3/3] Processing: triggers_english.yml
  Translating 18 line(s)...
  Progress: 18/18 lines (100%)
  ✓ Completed: triggers_english.yml

Validation:
  Source files: 3
  Target files: 3
  ✓ All files translated successfully

✓ Successfully processed my_mod.zip
✓ Temp directory cleared

Processing complete! Processed 1 file(s)
```

## 🐛 Troubleshooting

### Issue: Application doesn't start

**Symptoms**: Container fails to start or exits immediately

**Solutions:**
- Check Docker installation: `docker --version`
- Verify config.json syntax (valid JSON format)
- Check file permissions on input/temp/output folders
- View error logs: `docker-compose logs`

### Issue: No 'english' folder found

**Symptoms**: Error message "No 'english' folder found in {file}.zip"

**Solutions:**
- Verify zip structure contains `english/` folder at root level
- Extract and inspect zip contents manually
- Ensure folder name is exactly "english" (lowercase)
- See `input/README.txt` for correct structure

### Issue: Translation fails midway

**Symptoms**: Process stops during translation, incomplete output

**Solutions:**
- Check internet connection (required for Google Translate API)
- Verify no rate limiting from Google Translate
- Check Docker logs for specific error messages
- Try reducing batch size in code if needed

### Issue: File count mismatch

**Symptoms**: "File count mismatch!" during validation

**Solutions:**
- Check for empty .yml files (skipped during translation)
- Ensure all source files have valid YAML syntax
- Verify no hidden files or system files in source zip
- Check logs for specific files that failed

### Issue: Output zip not created

**Symptoms**: No file appears in `output/` folder

**Solutions:**
- Check validation passed (logs show ✓ All files translated successfully)
- Verify write permissions on `output/` folder
- Check available disk space
- Review Docker logs for zip creation errors

## 📊 Supported Syntax

The translator preserves special CK3 localization syntax:

| Syntax Type | Example | Description |
|-------------|---------|-------------|
| **Square Brackets** | `[example]` | Variable references |
| **Dollar Signs** | `$example$` | Scope references |
| **Hashtags** | `#example#` | Color/formatting codes |
| **Newlines** | `\n` | Line break sequences |
| **@-Prefixes** | `@example!` | Icon references |

These elements are **preserved** during translation and **not translated**.

## 🔬 Technical Details

### Translation Engine

- **API**: Google Translate (via deep-translator library)
- **Method**: Batch processing with parallel execution
- **Batch Size**: 20 lines per batch
- **Concurrency**: Up to 10 parallel translation workers
- **Error Handling**: Automatic retry with original text fallback

### File Processing

- **Supported Formats**: `.yml`, `.yaml`
- **Encoding**: UTF-8
- **Path Handling**: Cross-platform compatible (Windows/Linux)
- **Normalization**: Automatic path separator conversion

### Validation System

- **File Count**: Source and target must match
- **Folder Structure**: Directory hierarchy must be identical
- **Empty Files**: Skipped with warning message

## 🤝 Contributing

Contributions are welcome! To contribute:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

Please ensure:
- Code follows existing style conventions
- Changes are tested with Docker deployment
- Commit messages follow conventional commit format
- Documentation is updated for new features

## 🧪 Testing

Test the application with various scenarios:

1. **Single file translation**: Simple mod with one localization file
2. **Multi-file translation**: Complex mod with subfolder structure
3. **Large files**: Files with 100+ translatable lines
4. **Special characters**: Test syntax preservation
5. **Error cases**: Invalid zip structure, missing folders

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [deep-translator](https://libraries.io/pypi/deep-translator) - Google Translate API wrapper
- [Docker](https://www.docker.com/) - Containerization platform
- Paradox Development Studio - Crusader Kings 3 game engine
- Community contributors and testers

## 💬 Support

**Issues**: [Report bugs or request features](https://github.com/yourusername/crusader-kings-3-auto-translator/issues)

**Discussions**: Share your translations and get help from the community

---

Made with ❤️ for the Crusader Kings 3 modding community
