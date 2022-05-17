import os

# Default value for requests per second
REQ_PER_SEC = 10

# Timeout for selenium
TIMEOUT = 30

# Number of same requests with different values for params or data that are allowed to be saved in the database (Request.check() function for more info)
SAME_REQUESTS_ALLOWED = 5

# Log file
LOG_FILE = '/var/log/bagley.log'

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

# Formats that won't be stored
EXTENSIONS_BLACKLIST = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff', '.mp4', '.rar', '.zip', '.pdf', '.apk', '.mp3', '.otf']

# Scripts extensions
SCRIPT_EXTENSIONS = ['.js', '.ts']

# Values for params and POST data containing these words will be substituted in order to not save the
PARAMS_BLACKLIST = ['csrf']

# Headers whose value won't be stored
HEADERS_BLACKLIST = ['date', 'cookie', 'set-cookie', 'content-length']

# Absolute path for screenshot folder
SCREENSHOT_FOLDER = '/tmp/screenshots/'

# Absolute path for scripts folder
SCRIPTS_FOLDER = '/tmp/scripts/'

# Absolute path for rempotal files
FILES_FOLDER = '/tmp/'

# Directory fuzzing wordlist
DIR_FUZZING = '/usr/lib/SecLists/Discovery/Web-Content/common.txt'

# Domain fuzzing wordlist
DOMAIN_FUZZING = '/usr/lib/SecLists/Discovery/DNS/subdomains-top1million-5000.txt'

# Suite for codeql
CODEQL_SUITE = '/root/bagley/lib/modules/config/bagley_codeql.qls'