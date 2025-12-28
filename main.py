import datetime
import time
import argparse
from pathlib import Path
import os
import re
from deep_translator import GoogleTranslator

# ---------------------------------------------------
DEBUG = False
INFO = False
translator = None
RE_PATTERN = re.compile(r'\[[^"\]]*]|\$[^$]+\$|#[^$]+#|\\n|@[^!]+!')
REPLACER = '{@}'
LINE_STR = '-----------------------------------------'
BATCH_SIZE = 10  # Translate 10 lines at once
INITIAL_DELAY = 0.1  # Start with minimal delay
MAX_DELAY = 5.0  # Max delay on rate limit errors
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


def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l1", type=str, default="en")
    parser.add_argument("-l2", type=str, default="de")
    parser.add_argument("-trans", type=int, default=1)
    parser.add_argument("path")

    args = parser.parse_args()
    from_language = args.l1
    to_language = args.l2
    from_naming = get_loc_code(True, from_language)
    to_naming = get_loc_code(False, to_language)

    if args.trans == 1:
        do_translation = True
    else:
        do_translation = False
    target_dir = Path(args.path)

    if not target_dir.exists():
        print("The target directory doesn't exist")
        raise SystemExit(1)
    log_message(
        LINE_STR + "\nNew Translation " + from_language + " --> " + to_language + "\n" + LINE_STR,
        False)
    init(target_dir, do_translation, from_language, to_language, from_naming, to_naming)


def log_message(message, sign_t=True):
    log_file = "error_log.txt"
    if not os.path.exists(log_file):
        open(log_file, "w").close()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as file:
        if sign_t:
            file.write("[{}] {}\n".format(timestamp, message))
        else:
            file.write("{}\n".format(message))


def init(target_dir, do_translation, from_language, to_language, from_naming, to_naming):
    INPUT_DIR = target_dir
    print("INPUT_DIR " + INPUT_DIR.__str__())

    file: Path
    for file in list(INPUT_DIR.rglob("*.yml*")):
        try:
            filepath = os.path.dirname(os.path.abspath(file))
            filename = file.name  # Fixed: file.name is already just the filename

            # replace text in file
            with open(file, 'r', encoding="utf-8") as f_r:
                print(LINE_STR)
                print("current File: " + file.name)
                log_message("\n" + file.name, False)

                file_data = f_r.readlines()
                
                # Check if file has content
                if not file_data:
                    print("Warning: Empty file, skipping...")
                    log_message(f"Empty file skipped: {file.name}")
                    continue
                
                file_data[0] = file_data[0].replace(from_naming, to_naming)
                if do_translation:
                    translate(file_data, from_language, to_language)
                tofile(filepath, filename, file_data, from_naming, to_naming)
        
        except Exception as e:
            print(f"Error processing file {file.name}: {str(e)}")
            log_message(f"File processing error in {file.name}: {str(e)}")


def tofile(filepath, filename, file_data, from_naming, to_naming):
    try:
        newfileName = filename.replace(from_naming, to_naming, 1)
        new_filepath = filepath.replace(from_naming, to_naming, 1)
        new_file = os.path.join(new_filepath, newfileName)

        new_path = Path(new_file)
        if not os.path.exists(new_filepath):
            os.makedirs(new_filepath)

        with open(new_path, 'w', encoding="utf-8") as f_w:
            f_w.writelines(file_data)
    
    except Exception as e:
        print(f"Error writing file {newfileName}: {str(e)}")
        log_message(f"File write error for {newfileName}: {str(e)}")
        raise


def translate_batch(texts, from_language, to_language, delay):
    """
    Translate a batch of texts with exponential backoff on errors.
    Returns tuple of (translations_list, new_delay, success_flag)
    """
    try:
        if DEBUG:
            print(f"Translating batch of {len(texts)} items with delay {delay}s")
        
        translations = []
        for text in texts:
            time.sleep(delay)
            try:
                trans = GoogleTranslator(source=from_language, target=to_language).translate(text)
                if trans is None:
                    trans = text  # Keep original if translation fails
                translations.append(trans)
            except Exception as e:
                print(f"Translation failed for '{text}': {e}")
                translations.append(text)  # Keep original
        
        # Successful translation - reduce delay
        new_delay = max(INITIAL_DELAY, delay * 0.8)
        
        return translations, new_delay, True
        
    except Exception as e:
        # On error, increase delay exponentially
        new_delay = min(MAX_DELAY, delay * 2)
        print(f'Error during batch translation: {str(e)}, increasing delay to {new_delay}s')
        log_message(f"Batch translation error: {str(e)}, new delay: {new_delay}s")
        
        # Return original texts with failure flag
        return texts, new_delay, False


def translate(file_data, from_language, to_language):
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
        print("No lines to translate")
        return
    
    print(f"Found {len(translation_queue)} lines to translate")
    
    # Process in batches with adaptive delay
    current_delay = INITIAL_DELAY
    total_lines = len(translation_queue)
    
    for batch_start in range(0, total_lines, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_lines)
        batch = translation_queue[batch_start:batch_end]
        
        # Extract texts to translate
        texts_to_translate = [item['filtered'] for item in batch]
        
        # Translate batch
        translations, current_delay, success = translate_batch(
            texts_to_translate, 
            from_language, 
            to_language, 
            current_delay
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
        
        print(f"Completed lines {batch_start + 1}-{batch_end} of {total_lines} (delay: {current_delay:.2f}s)")
    
    print(f"Translation complete! Total lines processed: {total_lines}")


if __name__ == "__main__":
    parseargs()