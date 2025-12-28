╔═══════════════════════════════════════════════════════════════════════════════╗
║                 CRUSADER KINGS 3 AUTO TRANSLATOR - INPUT FOLDER              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📁 PLACE YOUR ZIP FILES HERE

This folder is monitored by the CK3 Auto Translator application.
Place your localization zip files here and they will be automatically translated.

═══════════════════════════════════════════════════════════════════════════════

📋 ZIP FILE REQUIREMENTS:

1. ZIP STRUCTURE:
   Your zip file must contain an "english" folder at the root level:
   
   ✓ CORRECT:
   your_mod.zip
   └── english/
       ├── file1_english.yml
       ├── file2_english.yml
       └── subfolder/
           └── file3_english.yml
   
   ✗ INCORRECT:
   your_mod.zip
   └── file1_english.yml  (missing "english" folder)

2. FILE FORMAT:
   - Only .yml and .yaml files will be processed
   - Files must be valid YAML localization files
   - First line should contain language code (e.g., "l_english:")

3. NAMING:
   - Zip files can have any name (e.g., "my_mod.zip")
   - Output will be named: "my_mod_<language>.zip"
   - Example: "my_mod.zip" → "my_mod_de.zip" (for German)

═══════════════════════════════════════════════════════════════════════════════

⚙️ PROCESSING WORKFLOW:

1. Place your zip file in this folder
2. Application extracts and translates all .yml files
3. Validates that all files were translated correctly
4. Creates output zip in the "output" folder
5. Moves original zip to "processed" subfolder
6. Cleans up temporary files

═══════════════════════════════════════════════════════════════════════════════

🔧 CONFIGURATION:

Edit config.json to change:
- Source language (from_language): default "en"
- Target language (to_language): default "de"
- Translation enable/disable (do_translation): default true

Supported languages:
- en: English
- de: German
- fr: French
- es: Spanish
- ru: Russian
- zh-cn: Simplified Chinese
- ko: Korean
- id: Indonesian

═══════════════════════════════════════════════════════════════════════════════

📊 MONITORING:

Watch Docker logs to see real-time progress:
  docker logs ck3-translator -f

Or use Docker Compose:
  docker-compose logs -f

═══════════════════════════════════════════════════════════════════════════════

❗ IMPORTANT NOTES:

- The application processes all zip files found in this folder
- Each zip must contain ONLY the "english" folder structure
- Files are validated before output creation
- Original files are preserved in the "processed" subfolder
- Temporary files are automatically cleaned after processing

═══════════════════════════════════════════════════════════════════════════════
