import datetime
import time
import argparse
from pathlib import Path
import os
import re
import concurrent.futures
import zipfile
import json
import shutil
import sys
from deep_translator import GoogleTranslator

# Custom exception for rate limiting
class TranslationRateLimitError(Exception):
    """Raised when Google Translate rate limit is exceeded"""
    pass

# ---------------------------------------------------
DEBUG = False
INFO = False
translator = None
RE_PATTERN = re.compile(r'\[[^"\]]*]|\$[^$]+\$|#[^$]+#|\\n|@[^!]+!')
REPLACER = '{@}'
LINE_STR = '-----------------------------------------'
BATCH_SIZE = 25  # Translate 25 lines at once (safe with 0.25s delays)
# ---------------------------------------------------

def get_loc_code(from_l: bool, pars_arg: str):
    locale_codes = {
        'en': 'english',
        'de': 'german',
        'fr': 'french',
        'es': 'spanish',
        'ru': 'russian',
        'zh-cn': 'simp_chinese',
        'ko': 'korean',
        'id': 'indonesian'
    }
    locale = locale_codes.get(pars_arg)
    if not locale:
        locale = 'english' if from_l else 'german'
    return locale


def load_config():
    """Load configuration from config.json"""
    config_path = Path("config.json")
    if not config_path.exists():
        log("config.json not found, using defaults")
        return {
            "from_language": "en",
            "to_language": "de",
            "do_translation": True,
            "input_dir": "/app/input",
            "temp_dir": "/app/temp",
            "output_dir": "/app/output",
            "check_interval": 30
        }

    with open(config_path, 'r') as f:
        return json.load(f)


def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    args = parser.parse_args()
    return args


def log_message(message, sign_t=True):
    """Print log message to console (Docker logs)"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if sign_t:
        print("[{}] {}".format(timestamp, message))
    else:
        print("{}".format(message))
    sys.stdout.flush()  # Force immediate flush for Docker logging


def log(message):
    """Print log message with timestamp and immediate flush for Docker compatibility"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{}] {}".format(timestamp, message))
    sys.stdout.flush()


def extract_zip(zip_path, extract_to):
    """Extract zip file to specified directory, normalizing filenames"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract files with proper path handling
            for member in zip_ref.namelist():
                # Normalize the path - replace any weird characters
                normalized_path = member.replace('\\', '/')
                
                # Extract to the target directory
                source = zip_ref.open(member)
                target_path = Path(extract_to) / normalized_path
                
                # Create parent directories if needed
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the file if it's not a directory
                if not member.endswith('/'):
                    with open(target_path, 'wb') as target:
                        target.write(source.read())
                
                source.close()
        
        print(f"Extracted {zip_path} to {extract_to}")
        return True
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        log_message(f"Zip extraction error for {zip_path}: {e}")
        return False


def create_zip(source_dir, zip_path, target_language):
    """Create zip file from directory with target language folder structure"""
    try:
        # Create a temporary directory to build the proper structure
        temp_zip_dir = Path(source_dir).parent / "zip_temp"
        temp_zip_dir.mkdir(exist_ok=True)
        
        # Create target language folder inside temp directory
        target_folder = temp_zip_dir / target_language
        if target_folder.exists():
            shutil.rmtree(target_folder)
        shutil.copytree(source_dir, target_folder)
        
        # Check for manual translations CSV and include it if it exists
        temp_dir = Path(source_dir).parent
        csv_path = temp_dir / "manual_translations.csv"
        if csv_path.exists():
            # Copy CSV to the target language folder
            shutil.copy2(csv_path, target_folder / "manual_translations.csv")
            print(f"Included manual translations CSV in output zip")
        
        # Create zip with the folder structure
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', temp_zip_dir)
        
        # Clean up temp directory
        shutil.rmtree(temp_zip_dir)
        
        print(f"Created zip file: {zip_path}")
        return True
    except Exception as e:
        print(f"Error creating zip {zip_path}: {e}")
        log_message(f"Zip creation error for {zip_path}: {e}")
        return False


def get_already_translated_files(source_dir, target_dir, from_naming, to_naming):
    """Get set of files that have already been translated"""
    if not target_dir.exists():
        return set()
    
    translated_files = set()
    target_files = list(target_dir.rglob("*.yml*"))
    
    for target_file in target_files:
        # Get relative path from target directory
        rel_path = target_file.relative_to(target_dir)
        
        # Convert target filename back to source filename
        source_filename = str(rel_path).replace(to_naming, from_naming, 1)
        source_file_path = source_dir / source_filename
        
        # Add to set if source file exists (valid translation)
        if source_file_path.exists():
            translated_files.add(source_file_path)
    
    return translated_files


def validate_translation(source_dir, target_dir):
    """Validate that all files were translated correctly"""
    source_files = list(source_dir.rglob("*.yml*"))
    target_files = list(target_dir.rglob("*.yml*"))
    
    source_count = len(source_files)
    target_count = len(target_files)
    
    print(f"\nValidation:")
    print(f"  Source files: {source_count}")
    print(f"  Target files: {target_count}")
    
    if source_count != target_count:
        # Get relative paths for comparison
        source_rel_paths = set(str(f.relative_to(source_dir)) for f in source_files)
        target_rel_paths = set(str(f.relative_to(target_dir)) for f in target_files)
        
        missing_in_target = source_rel_paths - target_rel_paths
        extra_in_target = target_rel_paths - source_rel_paths
        
        print(f"  ✗ File count mismatch!")
        if missing_in_target:
            print(f"    Missing in target: {sorted(missing_in_target)}")
        if extra_in_target:
            print(f"    Extra in target: {sorted(extra_in_target)}")
        return False
    
    # Check folder structure
    source_dirs = set([str(f.parent.relative_to(source_dir)) for f in source_files])
    target_dirs = set([str(f.parent.relative_to(target_dir)) for f in target_files])
    
    if source_dirs != target_dirs:
        print(f"  ✗ Folder structure mismatch!")
        print(f"    Source folders: {sorted(source_dirs)}")
        print(f"    Target folders: {sorted(target_dirs)}")
        missing_dirs = source_dirs - target_dirs
        extra_dirs = target_dirs - source_dirs
        if missing_dirs:
            print(f"    Missing directories in target: {sorted(missing_dirs)}")
        if extra_dirs:
            print(f"    Extra directories in target: {sorted(extra_dirs)}")
        return False
    
    print(f"  ✓ All files translated successfully")
    return True


def process_zip_file(zip_file, config):
    """Process a single zip file"""
    zip_path = Path(config['input_dir']) / zip_file
    temp_dir = Path(config['temp_dir'])
    output_dir = Path(config['output_dir'])

    # Set temp directory for tofile function
    os.environ['TEMP_DIR'] = str(temp_dir)

    # Create temp subdirectories
    target_dir = temp_dir / get_loc_code(False, config['to_language'])
    english_subdir = temp_dir / "english"

    log("   📦 Zip file: {}".format(zip_file))
    log("   📂 Extracting to: {}".format(temp_dir))

    # Check if we're resuming from previous run
    is_resuming = english_subdir.exists() and target_dir.exists()

    if is_resuming:
        log("   🔄 Resume detected - continuing previous translation")
        log("      Source: {}".format(english_subdir))
        log("      Target: {}".format(target_dir))
    else:
        # Clean temp directories for fresh start
        if english_subdir.exists():
            shutil.rmtree(english_subdir)
        if target_dir.exists():
            shutil.rmtree(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)

        # Extract zip
        log("   📦 Extracting {}...".format(zip_file))
        if not extract_zip(zip_path, temp_dir):
            log("   ❌ Failed to extract {}".format(zip_file))
            return False
        log("   ✅ Extraction completed")

    # Check if english folder exists (should exist from extraction or previous run)
    if not english_subdir.exists():
        log("   ❌ No 'english' folder found in {}".format(zip_file))
        log_message("No 'english' folder in {}".format(zip_file))
        return False

    # Process files
    from_language = config['from_language']
    to_language = config['to_language']
    from_naming = get_loc_code(True, from_language)
    to_naming = get_loc_code(False, to_language)

    log("   🚀 Starting translation process...")
    log("      From: {} ({})".format(from_language, from_naming))
    log("      To: {} ({})".format(to_language, to_naming))
    log("      Mode: {}".format('Translation enabled' if config['do_translation'] else 'Structure conversion only'))

    try:
        init(english_subdir, target_dir, config['do_translation'], from_language, to_language, from_naming, to_naming, is_resuming)

        # Validate translation before zipping
        log("   🔍 Validating translation results...")
        if not validate_translation(english_subdir, target_dir):
            log("   ❌ Validation failed for {}".format(zip_file))
            return False
        log("   ✅ Validation passed")

        # Create output zip
        output_zip_name = zip_file.replace('.zip', '_{}.zip'.format(to_language))
        output_zip_path = output_dir / output_zip_name

        log("   📦 Creating output zip: {}".format(output_zip_name))
        if create_zip(str(target_dir), str(output_zip_path), to_naming):
            # Move processed zip to processed folder or remove it
            processed_dir = Path(config['input_dir']) / "processed"
            processed_dir.mkdir(exist_ok=True)
            zip_path.rename(processed_dir / zip_file)
            log("   ✅ Successfully processed {}".format(zip_file))
            log("      Output: {}".format(output_zip_path))
            log("      Moved to processed: {}".format(processed_dir / zip_file))

            # Clear temp directory after successful processing
            log("   🧹 Cleaning up temporary files...")
            if english_subdir.exists():
                shutil.rmtree(english_subdir)
            if target_dir.exists():
                shutil.rmtree(target_dir)

            # Clean up manual translations CSV if it exists
            csv_path = temp_dir / "manual_translations.csv"
            if csv_path.exists():
                csv_path.unlink()
                log("      ✓ Cleaned up manual translations CSV")

            log("   ✅ Cleanup completed")
            return True
        else:
            log("   ❌ Failed to create output zip")
            return False

    except TranslationRateLimitError:
        # Exit the entire application on rate limiting
        log("   🚨 FATAL: Google Translate rate limit exceeded")
        log("      Application will now exit to prevent further charges or bans")
        log_message("FATAL RATE LIMIT - APPLICATION EXITING")
        exit(1)
    except Exception as e:
        log("   ❌ Error processing {}: {}".format(zip_file, e))
        log_message("Processing error for {}: {}".format(zip_file, e))
        return False


def watch_and_process(config):
    """Process all zip files in input directory and exit"""
    input_dir = Path(config['input_dir'])
    input_dir.mkdir(exist_ok=True)
    Path(config['temp_dir']).mkdir(exist_ok=True)
    Path(config['output_dir']).mkdir(exist_ok=True)

    log("🚀 Starting Crusader Kings 3 Auto Translator")
    log("📁 Input directory: {}".format(input_dir))
    log("📁 Temp directory: {}".format(config['temp_dir']))
    log("📁 Output directory: {}".format(config['output_dir']))
    log("🌐 Translation: {} → {}".format(config['from_language'], config['to_language']))
    log("⚙️  Translation enabled: {}".format(config['do_translation']))
    log("⏰ Check interval: {} seconds".format(config['check_interval']))
    log(LINE_STR)

    try:
        # Look for zip files
        zip_files = list(input_dir.glob("*.zip"))
        if zip_files:
            log("📦 Found {} zip file(s) to process:".format(len(zip_files)))
            for zip_file in zip_files:
                log("   • {}".format(zip_file.name))
            log(LINE_STR)

            for zip_file in zip_files:
                log("\n🔄 Processing: {}".format(zip_file.name))
                process_zip_file(zip_file.name, config)
            log("\n✅ Processing complete! Processed {} file(s)".format(len(zip_files)))
        else:
            log("❌ No zip files found in input directory")

    except Exception as e:
        log("❌ Error in processing: {}".format(e))
        log_message("Processing error: {}".format(e))
        raise

    log("🏁 Application finished")


def init(source_dir, target_dir, do_translation, from_language, to_language, from_naming, to_naming, is_resuming=False):
    # Set temp directory environment variable for tofile function
    temp_dir = os.environ.get('TEMP_DIR', '/app/temp')
    os.environ['TEMP_DIR'] = temp_dir

    log("🔍 Analyzing localization files...")
    log("   Source directory: {}".format(source_dir))
    log("   Target directory: {}".format(target_dir))
    log("   Translation mode: {}".format('Enabled' if do_translation else 'Disabled (file structure only)'))
    log("   Language pair: {} ({}) → {} ({})".format(from_language, from_naming, to_language, to_naming))

    INPUT_DIR = source_dir

    # Get all yml files
    all_files = list(INPUT_DIR.rglob("*.yml*"))
    total_files_found = len(all_files)

    log("   📊 Total YAML files found: {}".format(total_files_found))

    # Get already translated files if resuming
    already_translated = set()
    if is_resuming:
        already_translated = get_already_translated_files(source_dir, target_dir, from_naming, to_naming)
        skipped_count = len(already_translated)

        if skipped_count > 0:
            log("   🔄 Resume mode: Found {} already translated file(s)".format(skipped_count))
            log("   ⏭️  Will skip these and continue with remaining files")
        else:
            log("   🔄 Resume mode: No previously translated files found")

    # Filter out already translated files
    files_to_process = [f for f in all_files if f not in already_translated]
    
    # Sort files by size (smallest first) for faster feedback and better rate limit management
    files_to_process.sort(key=lambda f: os.path.getsize(f))
    
    total_files = len(files_to_process)

    log(LINE_STR)
    if is_resuming:
        log("📝 TRANSLATION RESUME SUMMARY:")
        log("   📁 Total files in source: {}".format(total_files_found))
        log("   ✅ Already translated: {}".format(len(already_translated)))
        log("   🔄 Remaining to process: {}".format(total_files))
    else:
        log("📝 TRANSLATION INITIATION SUMMARY:")
        log("   📁 Files to process: {}".format(total_files))
        log("   🎯 Target language: {} ({})".format(to_language, to_naming))

    if total_files > 0:
        log("   📋 Translation queue: {} file(s)".format(total_files))
        log("   📏 Processing order: Smallest files first (for faster feedback)")
        if do_translation:
            log("   🤖 AI translation: Enabled (Google Translate)")
            log("   ⚡ Batch size: {} lines per batch".format(BATCH_SIZE))
            log("   🛡️  Rate limiting: 4 requests/second max")
        else:
            log("   📋 File structure conversion only (no translation)")
    log(LINE_STR)

    if total_files == 0:
        log("✅ All files already translated! Nothing to do.")
        log(LINE_STR)
        return

    file: Path
    for file_index, file in enumerate(files_to_process, 1):
        try:
            filepath = os.path.dirname(os.path.abspath(file))
            filename = file.name  # Fixed: file.name is already just the filename

            # replace text in file
            with open(file, 'r', encoding="utf-8") as f_r:
                log("[{}/{}] 🔄 Processing: {}".format(file_index, total_files, file.name))

                file_data = f_r.readlines()

                # Check if file has content
                if not file_data:
                    log("   ⚠️  Warning: Empty file, creating empty target file...")
                    tofile(filepath, filename, file_data, from_naming, to_naming)
                    continue

                file_data[0] = file_data[0].replace(from_naming, to_naming)
                if do_translation:
                    failed_translations = translate(file_data, from_language, to_language, filename, str(file))
                    # Write failed translations to CSV immediately after file completion
                    if failed_translations:
                        write_failed_translations_to_csv(failed_translations)
                tofile(filepath, filename, file_data, from_naming, to_naming)
                log("   ✅ Completed: {}".format(file.name))

        except TranslationRateLimitError:
            # Re-raise rate limiting errors to stop the application
            raise
        except Exception as e:
            log("   ❌ Error processing file {}: {}".format(file.name, str(e)))

    # Add completion summary
    if total_files > 0:
        log(LINE_STR)
        log("🎉 Translation phase completed!")
        log("   📊 Files processed: {}".format(total_files))
        log("   🎯 Language: {} → {}".format(from_language, to_language))
        if do_translation:
            log("   🤖 Translation method: Google Translate API")
        log(LINE_STR)


def tofile(filepath, filename, file_data, from_naming, to_naming):
    try:
        # For the new structure, we need to create the target path in the temp directory
        # filepath is relative to the english folder, we need to create the same structure in target folder
        temp_dir = Path(os.environ.get('TEMP_DIR', '/app/temp'))
        target_dir = temp_dir / to_naming

        # Get relative path from english folder
        english_dir = temp_dir / from_naming
        rel_path = os.path.relpath(filepath, str(english_dir))

        # Create target path
        if rel_path == '.':
            target_filepath = target_dir
        else:
            target_filepath = target_dir / rel_path

        target_filepath.mkdir(parents=True, exist_ok=True)

        # Create new filename
        newfileName = filename.replace(from_naming, to_naming, 1)
        new_file = target_filepath / newfileName

        with open(new_file, 'w', encoding="utf-8") as f_w:
            f_w.writelines(file_data)

    except Exception as e:
        print(f"Error writing file {filename}: {str(e)}")
        log_message(f"File write error for {filename}: {str(e)}")
        raise


def translate_single(text, from_language, to_language):
    """Translate a single text, returning translation and failure status"""
    try:
        trans = GoogleTranslator(source=from_language, target=to_language).translate(text)
        if trans:
            return trans, False  # Success: (translated_text, failed=False)
        else:
            return text, True    # No translation found: (original_text, failed=True)
    except Exception as e:
        error_msg = str(e)
        # Check for rate limiting error (any rate limit violation)
        if "You made too many requests to the server" in error_msg:
            print(f"🚨 RATE LIMIT EXCEEDED: {error_msg}")
            log_message(f"RATE LIMIT EXCEEDED: {error_msg}")
            raise TranslationRateLimitError(f"Google Translate rate limit exceeded: {error_msg}")
        
        print(f"Translation failed for '{text}': {e}")
        return text, True  # Failed: (original_text, failed=True)


def translate_batch(texts, from_language, to_language, delay):
    """
    Translate a batch of texts sequentially with rate limiting.
    Returns tuple of (translations_list, failed_translations_list, success_flag)
    """
    try:
        if DEBUG:
            print(f"Translating batch of {len(texts)} items sequentially")

        translations = []
        failed_translations = []

        # Translate sequentially to respect rate limits (max 5 requests/second)
        for i, text in enumerate(texts):
            try:
                # Add delay between requests to stay under rate limit (max 5/sec)
                if i > 0:  # No delay for first request
                    time.sleep(0.25)  # 0.25s delay = max 4 requests/second (conservative)

                translated_text, failed = translate_single(text, from_language, to_language)

                if failed:
                    failed_translations.append(text)
                    translations.append(text)  # Keep original text for failed translations
                else:
                    translations.append(translated_text)

            except TranslationRateLimitError:
                # On rate limit, immediately stop and re-raise to halt the application
                print(f"🚨 Rate limit hit during batch translation, stopping immediately")
                raise
            except Exception as e:
                print(f"Translation failed for text #{i+1}: {e}")
                failed_translations.append(text)
                translations.append(text)  # Keep original text

        success = len(failed_translations) == 0
        return translations, failed_translations, success

    except TranslationRateLimitError:
        # Re-raise rate limiting errors to stop the application
        raise
    except Exception as e:
        print(f'Error during batch translation: {str(e)}')
        log_message(f"Batch translation error: {str(e)}")

        # Return original texts with all marked as failed
        return texts, texts, False


def write_failed_translations_to_csv(failed_translations):
    """Write failed translations to CSV file in temp directory"""
    try:
        import csv
        temp_dir = Path(os.environ.get('TEMP_DIR', '/app/temp'))
        csv_path = temp_dir / "manual_translations.csv"
        
        # Check if file exists to determine if we need to write header
        file_exists = csv_path.exists()
        
        with open(csv_path, 'a', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header if file is new
            if not file_exists:
                writer.writerow(["file_path", "line_number", "original_text", "translated_text"])
            
            # Write failed translations
            for failure in failed_translations:
                writer.writerow([
                    failure['file_path'],
                    failure['line_number'],
                    failure['original_text'],
                    ""  # Empty translated_text field for manual filling
                ])
        
        print(f"  📝 Recorded {len(failed_translations)} failed translation(s) to {csv_path}")
        
    except Exception as e:
        print(f"Error writing failed translations to CSV: {e}")
        log_message(f"CSV write error: {e}")


def translate(file_data, from_language, to_language, filename="", file_path=""):
    """Translate file data with batching and adaptive rate limiting
    
    Returns:
        list: List of failed translation dictionaries with file_path, line_number, and original_text
    """
    
    # Collect all translatable lines with their indices
    translation_queue = []
    
    for i, lines in enumerate(file_data[1:]):
        matches = re.findall('"([^"]*)"', lines)
        if len(matches) == 1 and matches[0] != '':
            tokens = re.findall(RE_PATTERN, matches[0])
            match = matches[0]
            filtered_text = re.sub(RE_PATTERN, REPLACER, matches[0])
            
            translation_queue.append({
                'line_index': i + 1,
                'original': match,
                'filtered': filtered_text,
                'tokens': tokens,
                'line_num': len(translation_queue) + 1
            })
    
    if not translation_queue:
        print("     No translatable lines found")
        return
    
    print(f"     📝 Translating {len(translation_queue)} text line(s)...")
    print(f"     ⚡ Batch processing: {BATCH_SIZE} lines per batch")
    print(f"     🛡️  Rate limit protection: 4 requests/second max")
    
    # Process in batches
    total_lines = len(translation_queue)
    failed_translations = []
    
    try:
        for batch_start in range(0, total_lines, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_lines)
            batch = translation_queue[batch_start:batch_end]
            
            # Extract texts to translate
            texts_to_translate = [item['filtered'] for item in batch]
            
            # Translate batch
            translations, batch_failures, success = translate_batch(
                texts_to_translate, 
                from_language, 
                to_language, 
                0  # No delay
            )
            
            # Collect failed translations with context
            for failure_text in batch_failures:
                # Find the corresponding item in the batch
                for item in batch:
                    if item['filtered'] == failure_text:
                        failed_translations.append({
                            'file_path': file_path,
                            'line_number': item['line_index'] + 1,  # +1 because we skip first line
                            'original_text': item['original']
                        })
                        break
            
            # Apply translations back to file_data
            for item, translated_text in zip(batch, translations):
                # Only restore tokens and update if translation was successful
                if item['filtered'] not in batch_failures:
                    # Restore tokens
                    padded_translation = translated_text
                    for token in item['tokens']:
                        padded_translation = padded_translation.replace(REPLACER, token, 1)
                    
                    # Update file data
                    original_line = file_data[item['line_index']]
                    file_data[item['line_index']] = original_line.replace(
                        "\"" + item['original'] + "\"", 
                        "\"" + padded_translation + "\"", 
                        1
                    )
                    
                    if INFO:
                        print(f"{item['original']} <- {padded_translation}")
                    
                    if DEBUG:
                        print(f"Line #{item['line_num']}: {padded_translation}")
                else:
                    # On error, keep original text (no translation)
                    if INFO or DEBUG:
                        print(f"Skipped line #{item['line_num']}: {item['original']} (translation failed)")
                    log_message(f"Skipped translation for: {item['original']}")
            
            progress_percent = int((batch_end / total_lines) * 100)
            print(f"     📊 Progress: {batch_end}/{total_lines} lines ({progress_percent}%)")
        
        success_rate = ((total_lines - len(failed_translations)) / total_lines) * 100 if total_lines > 0 else 100
        print(f"     ✅ Translation complete: {total_lines} line(s) processed")
        print(f"     📈 Success rate: {success_rate:.1f}% ({total_lines - len(failed_translations)}/{total_lines} successful)")
        
        if failed_translations:
            print(f"     ⚠️  Failed translations: {len(failed_translations)} (saved to manual_translations.csv)")
        
        # Return failed translations for caller to handle
        return failed_translations
    
    except TranslationRateLimitError:
        # Re-raise rate limiting errors to stop the application
        print(f"🚨 ABORTING FILE {filename} DUE TO RATE LIMIT")
        log_message(f"RATE LIMIT EXCEEDED - ABORTING FILE {filename}")
        raise


if __name__ == "__main__":
    log("🚀 Application starting...")
    args = parseargs()
    config = load_config()
    watch_and_process(config)