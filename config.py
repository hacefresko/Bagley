# Database variables
DB_SCRIPT = 'sql/bagley.sql'
DB_USER = 'bagley'
DB_HOST = '127.0.0.1'
DB_NAME = 'bagley'

# Timeout for selenium
TIMEOUT = 120

# Requests per second
REQ_PER_SEC = 10

# Formats that won't be stored
EXTENSIONS_BLACKLIST = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff', '.mp4', '.rar', '.zip', '.pdf', '.apk']

# Params and POST data containing these words, won't be stored
PARAMS_BLACKLIST = ['csrf']

# Headers whose value won't be stored
HEADERS_BLACKLIST = ['date', 'cookie', 'set-cookie', 'content-length']

# Directory fuzzing wordlist
DIR_FUZZING = '/Users/hacefresko/Tools/SecLists//Discovery/Web-Content/big.txt'

# Domain fuzzing wordlist
DOMAIN_FUZZING = '/Users/hacefresko/Tools/SecLists/Discovery/DNS/subdomains-top1million-20000.txt'
