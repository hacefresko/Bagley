import datetime, signal, os
import shutil
import lib.controller, lib.bot, config

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[SIGINT] Ending execution...')

    lib.controller.stop()
    quit()

def checkDependences():
    dependences = ['chromedriver', 'mariadb', 'chromedriver', 'gobuster', 'subfinder', 'subjack', 'sqlmap', 'dalfox', 'crlfuzz', 'tplmap', 'wappalyzer']
    for d in dependences:
        if not shutil.which(d):
            print("[x] %s not found in PATH" % d)
            return False

    files = [config.DIR_FUZZING, config.DOMAIN_FUZZING]
    for f in files:
        if not os.path.exists(f):
            print("[x] %s from config file not found" % f)
            return False

    return True

# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)

print(lib.controller.title)
print("[+] Starting time: %s" % datetime.datetime.now())

# Check dependences
print("[+] Checking dependences")
if not checkDependences():
    exit()

# Get discord token
token = os.getenv(config.DISCORD_TOKEN_ENV_VAR)
if not token:
    print("[x] %s environment variable not found" % config.DISCORD_TOKEN_ENV_VAR)
    exit()

# Start bot
print("[+] Starting discord bot")
lib.bot.bot.run(token)