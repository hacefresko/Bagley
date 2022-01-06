# Database variables
DB_USER = 'bagley'
DB_HOST = '127.0.0.1'
DB_NAME = 'bagley'
DB_PASSWORD = ''

DISCORD_TOKEN_ENV_VAR = 'DISCORD_TOKEN'
DISCORD_TERMINAL_CHANNEL = 877376214774472806

# Timeout for selenium
TIMEOUT = 120

# Requests per second
REQ_PER_SEC = 1

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
