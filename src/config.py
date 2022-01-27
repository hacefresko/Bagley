import os, logging

# Log file
LOG_FILE = '/var/log/bagley.log'

# Database variables
DB_USER = os.getenv("DB_USER") if os.getenv("DB_USER") else 'bagley'
DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else '127.0.0.1'
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else 'bagley'
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else ''

# Discord variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    logging.error('DISCORD_TOKEN environment variable not found')
    exit()

DISCORD_TERMINAL = 877376214774472806
DISCORD_ERRORS = 934946181526732811
DISCORD_VULNERABILITIES = 934219838149251122
DISCORD_CRAWLER = 877376384891232376
DISCORD_DYNAMIC_ANALYZER = 934219567167840316
DISCORD_FINDER = 877376449827455017
DISCORD_INJECTOR = 934219638529740800
DISCORD_STATIC_ANALYZER = 934219688240623626

# Timeout for selenium
TIMEOUT = 120

# Requests per second
REQ_PER_SEC = 10

# Formats that won't be stored
EXTENSIONS_BLACKLIST = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff', '.mp4', '.rar', '.zip', '.pdf', '.apk', '.mp3']

# Params and POST data containing these words, won't be stored
PARAMS_BLACKLIST = ['csrf']

# Headers whose value won't be stored
HEADERS_BLACKLIST = ['date', 'cookie', 'set-cookie', 'content-length']

# Directory fuzzing wordlist
DIR_FUZZING = '/usr/lib/SecLists/Discovery/Web-Content/directory-list-2.3-big.txt'

# Domain fuzzing wordlist
DOMAIN_FUZZING = '/usr/lib/SecLists/Discovery/DNS/subdomains-top1million-110000.txt'
