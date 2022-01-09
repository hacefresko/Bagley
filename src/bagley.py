import datetime, signal, os, shutil, sys
import lib.controller, lib.bot, config

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[SIGINT] Ending execution...')

    lib.controller.stop()
    quit()

def checkDependences():
    dependences = ['chromedriver', 'chromedriver', 'gobuster', 'subfinder', 'subjack', 'sqlmap', 'dalfox', 'crlfuzz', 'tplmap', 'wappalyzer']
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

# Duplicate stdout and stderr to log them into a file
#log_fd = open(config.LOG_FILE, "w", 1)
#os.dup2(1, log_fd)
#os.dup2(2, log_fd)

print(lib.controller.title)
print("[+] Starting time: %s" % datetime.datetime.now())

# Check dependences
print("[+] Checking dependences")
if not checkDependences():
    exit()

# Start bot
print("[+] Starting discord bot")
lib.bot.bot.run(config.DISCORD_TOKEN)