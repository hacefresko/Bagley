import datetime, signal, os, shutil, logging
import lib.controller, lib.bot, config

# Called when Ctrl+C
def sigint_handler(sig, frame):
    logging.info('Ending execution...')

    lib.controller.stop()
    quit()

def checkDependences():
    dependences = ['chromedriver', 'chromedriver', 'gobuster', 'subfinder', 'subjack', 'sqlmap', 'dalfox', 'crlfuzz', 'tplmap', 'wappalyzer']
    for d in dependences:
        if not shutil.which(d):
            logging.error('%s not found in PATH', d)
            return False

    files = [config.DIR_FUZZING, config.DOMAIN_FUZZING]
    for f in files:
        if not os.path.exists(f):
            logging.error('%s from config file not found', f)
            return False

    return True

# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)

logging.basicConfig(filename=config.LOG_FILE, format='[%(asctime)s][%(levelname)s] %(message)s', level=logging.INFO)

logging.info("Starting \n%s", lib.controller.title)

# Check dependences
logging.info("Checking dependences")
if not checkDependences():
    exit()

# Start bot
logging.info("Starting discord bot")
lib.bot.bot.run(config.DISCORD_TOKEN)