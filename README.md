
# ck3-Translator

This Project allows the user to automatically translate ck3 (Crusader Kings 3) localisation files to other languages supported by the game and the translator API.

**ATTENTION!**
**This project is pretty new and there might be some cornercases I haven't adressed yet**
**If you find a Bug please let me know and provide the files to reproduce the Error**

## Authors

- [@CyberNord](https://github.com/CyberNord)
- [@Martin220799](https://github.com/Martin220799)    (Powershell Controls)

## Installation

### Docker Setup (Recommended)

1. **Clone or download** the project
2. **Navigate** to the project directory
3. **Configure** the target language in `config.json`:
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
4. **Build and run** with Docker Compose:
   ```bash
   docker-compose up -d
   ```

The service will automatically watch the `input/` folder for zip files containing 'english' folders and process them.

### Manual Setup

#### Requirements
Before Starting make sure the following libraries are installed.

- [Python 3.10](https://www.python.org/downloads/) (or higher)
- [deep-translator](https://libraries.io/pypi/deep-translator)

#### First Steps
Download the project folder from github and unpack it in a Location of your desire. Start a command prompt (e.g. PowerShell) in the path where the main.py is located.
The default setting is translating from english to german and it will look like that.

```bash
  python main.py D:\the\path\to\english\loc\folder
```

## Usage

### Docker Usage

1. **Place zip files** containing 'english' folders in the `input/` directory
2. **Wait** for automatic processing (check interval defined in config.json)
3. **Find translated zip files** in the `output/` directory with `_{language}.zip` suffix
4. **Processed zip files** are moved to `input/processed/`

### Manual Usage

Below you can see the general Syntax

```bash
python main.py [-h] [-l1 L1] [-l2 L2] [-trans TRANS] path
```
The following parts are mandatory
 - **python main.py**&nbsp;&nbsp;&nbsp;&nbsp;call of the programm
 - **path**&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;path to the folder to be translated

Optional information
- **[-h]**&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; no function for now
- **[-l1 L1]**&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;given input language (default = en)
- **[-l2 L2]**&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;desired output language (default = de)
- **[-trans TRANS]**&nbsp;&nbsp;(default = 1) If this value is set to 0 there will be no translation. The Programm wil only convert the files to the disired output language so that it is supported by the game (e.g. results in english text in german localisation)

#### Supported languages 
The list is limited by the possible localisations supported in CK3.
- 'en' english
- 'de' german
- 'fr' french
- 'es' spanish
- 'ru' russian
- 'zh-cn' simplified chinese
- 'ko' korean
- 'id' indonesian

### Docker Commands

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Configuration

Edit `config.json` to change settings:

- `from_language`: Source language code (default: "en")
- `to_language`: Target language code (default: "de") 
- `do_translation`: Enable/disable translation (default: true)
- `check_interval`: Seconds between checking for new files (default: 30)

## Examples

### Docker Examples

1. **Basic usage**: Place a zip file containing an 'english' folder in `input/`
2. **Multiple languages**: Change `to_language` in config.json and restart
3. **No translation**: Set `do_translation: false` for file conversion only

### Manual Examples

this will translate from english (default) to french
```bash
python main.py -l2 fr D:\the\path\to\english\loc\folder
```
this will translate from french to german (default)
```bash
python main.py -l1 fr D:\the\path\to\english\loc\folder
```

this will just alter the first line and filename so that the localisation is detected by the game
```bash
python main.py -trans 0 D:\the\path\to\english\loc\folder
```
## FAQ

#### Why is this taking so long? 

The translator now uses **batch processing** with **adaptive rate limiting** for optimal speed:
- Translates 10 lines at once instead of one-by-one
- Starts with minimal delay (0.1s) and only increases if the API blocks requests
- Automatically reduces delay when translations succeed
- **Up to 20x faster** than the old line-by-line approach while still avoiding API blocks

#### Why are some lines not translated at all? 

The API has problems translating certain sentences or very long strings correctly.
In order to avoid complete crap, the default language is retained in such cases.
Especially translations from English into Spanish are very prone to this.


#### Will this translator work for other iterations of the pdx genere? 

Some tests were made with the "Stellaris" localization files, which turned out to be satisfactory on the whole.
I strongly assume that most of the titles are compatible since the syntax is similar or even identical.
So yes, you can probably use this translator for "Stellaris" or other titles from the developer Paradox.

#### What kind of Syntax is currently supported in the translation files?
 - Square Bracket Content: Text enclosed in square brackets, including the brackets themselves. For example, `[example]` would be filtered.
 - Dollar Sign Enclosed Text: Text enclosed between dollar signs ($), including the dollar signs themselves. For example, `$example$` would be filtered. 
 - Hashtag Enclosed Text: Text enclosed between hashtags (#), including the hashtags themselves. For example, `#example#` would be filtered. 
 - Newline Sequence: The newline character `\n`, which represents a line break in a text. 
 - @-Prefixed Text: Text that starts with @ and ends with an exclamation mark (!). For example, `@example!` would be filtered.
