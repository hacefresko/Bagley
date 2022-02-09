import os

# Log file
LOG_FILE = 'bagley.log'

# Database variables
DB_USER = os.getenv("DB_USER") if os.getenv("DB_USER") else 'bagley'
DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else '127.0.0.1'
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else 'bagley'
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else 'bagley'

# Discord variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print('DISCORD_TOKEN environment variable not found')
    exit()

# Default value for requests per second
REQ_PER_SEC = 5

# Timeout for selenium
TIMEOUT = 120

# Formats that won't be stored
EXTENSIONS_BLACKLIST = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff', '.mp4', '.rar', '.zip', '.pdf', '.apk', '.mp3']

# Params and POST data containing these words, won't be stored
PARAMS_BLACKLIST = ['csrf']

# Headers whose value won't be stored
HEADERS_BLACKLIST = ['date', 'cookie', 'set-cookie', 'content-length']

# Absolute path to screenshot folder
SCREENSHOT_FOLDER = '/tmp/screenshots/'

# Directory fuzzing wordlist
DIR_FUZZING = '/usr/lib/SecLists/Discovery/Web-Content/big.txt'

# Domain fuzzing wordlist
DOMAIN_FUZZING = '/usr/lib/SecLists/Discovery/DNS/subdomains-top1million-110000.txt'