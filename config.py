# Timeout for selenium
TIMEOUT = 120

# Requests per second
REQ_PER_SEC = 10

# Formats that won't be stored
EXTENSIONS_BLACKLIST = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff', '.mp4', '.rar', '.pdf', '.pdf']

# Common session cookies whose values won't be stored
COOKIES_BLACKLIST = ['PHPSESSID', 'JSESSIONID', 'CFID', 'CFTOKEN', 'ASP.NET_SessionId']

# Terms that will be searched inside params, data and cookie keys not to store them
PARAMS_BLACKLIST = ['csrf', 'sess', 'token']

# Headers whose value won't be stored
HEADERS_BLACKLIST = ['date', 'cookie', 'set-cookie', 'content-length']

# Directory fuzzing wordlist inside Seclists directory
DIR_FUZZING = '/Users/hacefresko/Tools/SecLists//Discovery/Web-Content/big.txt'

# Domain fuzzing wordlist inside Seclists directory
DOMAIN_FUZZING = '/Users/hacefresko/Tools/SecLists/Discovery/DNS/subdomains-top1million-20000.txt'
