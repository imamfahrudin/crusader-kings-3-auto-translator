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
from deep_translator import GoogleTranslator

# ---------------------------------------------------
DEBUG = False
INFO = False
translator = None
RE_PATTERN = re.compile(r'\[[^"\]]*]|\$[^$]+\$|#[^$]+#|\\n|@[^!]+!')
REPLACER = '{@}'
LINE_STR = '-----------------------------------------'
BATCH_SIZE = 20  # Translate 20 lines at once
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
        print("config.json not found, using defaults")
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


def create_zip(source_dir, zip_path):
    """Create zip file from directory"""
    try:
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', source_dir)
        print(f"Created zip file: {zip_path}")
        return True
    except Exception as e:
        print(f"Error creating zip {zip_path}: {e}")
        log_message(f"Zip creation error for {zip_path}: {e}")
        return False


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
        print(f"  ✗ File count mismatch!")
        return False
    
    # Check folder structure
    source_dirs = set([str(f.parent.relative_to(source_dir)) for f in source_files])
    target_dirs = set([str(f.parent.relative_to(target_dir)) for f in target_files])
    
    if source_dirs != target_dirs:
        print(f"  ✗ Folder structure mismatch!")
        print(f"    Source folders: {sorted(source_dirs)}")
        print(f"    Target folders: {sorted(target_dirs)}")
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

    # Clean temp directories
    english_subdir = temp_dir / "english"
    if english_subdir.exists():
        shutil.rmtree(english_subdir)
    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # Extract zip
    if not extract_zip(zip_path, temp_dir):
        return False

    # Check if english folder exists
    if not english_subdir.exists():
        print(f"No 'english' folder found in {zip_file}")
        log_message(f"No 'english' folder in {zip_file}")
        return False

    # Process files
    from_language = config['from_language']
    to_language = config['to_language']
    from_naming = get_loc_code(True, from_language)
    to_naming = get_loc_code(False, to_language)

    print(f"\nProcessing: {zip_file}")
    print(f"Translation: {from_language} → {to_language}\n")

    try:
        init(english_subdir, config['do_translation'], from_language, to_language, from_naming, to_naming)

        # Validate translation before zipping
        if not validate_translation(english_subdir, target_dir):
            print(f"\n✗ Validation failed for {zip_file}")
            return False
        
        # Create output zip
        output_zip_name = zip_file.replace('.zip', f'_{to_language}.zip')
        output_zip_path = output_dir / output_zip_name

        if create_zip(str(target_dir), str(output_zip_path)):
            # Move processed zip to processed folder or remove it
            processed_dir = Path(config['input_dir']) / "processed"
            processed_dir.mkdir(exist_ok=True)
            zip_path.rename(processed_dir / zip_file)
            print(f"\n✓ Successfully processed {zip_file}")
            
            # Clear temp directory after successful processing
            print(f"\nCleaning up temporary files...")
            if english_subdir.exists():
                shutil.rmtree(english_subdir)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            print(f"✓ Temp directory cleared\n")
            
            return True
        else:
            return False

    except Exception as e:
        print(f"Error processing {zip_file}: {e}")
        log_message(f"Processing error for {zip_file}: {e}")
        return False


def watch_and_process(config):
    """Process all zip files in input directory and exit"""
    input_dir = Path(config['input_dir'])
    input_dir.mkdir(exist_ok=True)
    Path(config['temp_dir']).mkdir(exist_ok=True)
    Path(config['output_dir']).mkdir(exist_ok=True)

    print("Starting Crusader Kings 3 Auto Translator")
    print(f"Processing zip files from {input_dir}")
    print(f"Target language: {config['to_language']}")

    try:
        # Look for zip files
        zip_files = list(input_dir.glob("*.zip"))
        if zip_files:
            for zip_file in zip_files:
                print(f"Found zip file: {zip_file.name}")
                process_zip_file(zip_file.name, config)
            print(f"\nProcessing complete! Processed {len(zip_files)} file(s)")
        else:
            print("No zip files found in input directory")

    except Exception as e:
        print(f"Error in processing: {e}")
        log_message(f"Processing error: {e}")
        raise

    print("Application finished")


def init(target_dir, do_translation, from_language, to_language, from_naming, to_naming):
    # Set temp directory environment variable for tofile function
    temp_dir = os.environ.get('TEMP_DIR', '/app/temp')
    os.environ['TEMP_DIR'] = temp_dir

    INPUT_DIR = target_dir
    
    # Get all yml files
    all_files = list(INPUT_DIR.rglob("*.yml*"))
    total_files = len(all_files)
    
    print(f"\nFound {total_files} localization file(s) to process\n")

    file: Path
    for file_index, file in enumerate(all_files, 1):
        try:
            filepath = os.path.dirname(os.path.abspath(file))
            filename = file.name  # Fixed: file.name is already just the filename

            # replace text in file
            with open(file, 'r', encoding="utf-8") as f_r:
                print(f"[{file_index}/{total_files}] Processing: {file.name}")

                file_data = f_r.readlines()
                
                # Check if file has content
                if not file_data:
                    print("  Warning: Empty file, skipping...")
                    continue
                
                file_data[0] = file_data[0].replace(from_naming, to_naming)
                if do_translation:
                    translate(file_data, from_language, to_language, filename)
                tofile(filepath, filename, file_data, from_naming, to_naming)
                print(f"  ✓ Completed: {file.name}\n")
        
        except Exception as e:
            print(f"  ✗ Error processing file {file.name}: {str(e)}\n")


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
    """Translate a single text, returning original on failure"""
    try:
        trans = GoogleTranslator(source=from_language, target=to_language).translate(text)
        return trans if trans else text
    except Exception as e:
        print(f"Translation failed for '{text}': {e}")
        return text


def translate_batch(texts, from_language, to_language, delay):
    """
    Translate a batch of texts in parallel.
    Returns tuple of (translations_list, new_delay, success_flag)
    """
    try:
        if DEBUG:
            print(f"Translating batch of {len(texts)} items in parallel")
        
        # Translate in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(texts), 10)) as executor:
            translations = list(executor.map(
                lambda t: translate_single(t, from_language, to_language), 
                texts
            ))
        
        return translations, 0, True
        
    except Exception as e:
        print(f'Error during batch translation: {str(e)}')
        log_message(f"Batch translation error: {str(e)}")
        
        # Return original texts with failure flag
        return texts, 0, False


def translate(file_data, from_language, to_language, filename=""):
    """Translate file data with batching and adaptive rate limiting"""
    
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
        print("  No translatable lines found")
        return
    
    print(f"  Translating {len(translation_queue)} line(s)...")
    
    # Process in batches
    total_lines = len(translation_queue)
    
    for batch_start in range(0, total_lines, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_lines)
        batch = translation_queue[batch_start:batch_end]
        
        # Extract texts to translate
        texts_to_translate = [item['filtered'] for item in batch]
        
        # Translate batch
        translations, _, success = translate_batch(
            texts_to_translate, 
            from_language, 
            to_language, 
            0  # No delay
        )
        
        # Apply translations back to file_data
        for item, translated_text in zip(batch, translations):
            # Only restore tokens and update if translation was successful
            if success:
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
        print(f"  Progress: {batch_end}/{total_lines} lines ({progress_percent}%)")
    
    print(f"  Translation complete: {total_lines} line(s) processed")


if __name__ == "__main__":
    args = parseargs()
    config = load_config()
    watch_and_process(config)