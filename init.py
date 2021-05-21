import os, signal, datetime, getopt, sys, time
import crawler, database

db = database.VDT_DB()
try:
    db.connect()
except:
    print('[x] Couldn\'t connect to the database')

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[x] SIGINT: Exiting...')

    scope_file.close()
    db.close()

    quit()
signal.signal(signal.SIGINT, sigint_handler)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'D:')

    for opt, arg in opts:
        if opt == '-D':
            scope_file_name = arg
            scope_found = True

    if not scope_found or scope_file_name == '':
        raise Exception
            
except Exception:
    print(os.path.basename(__file__) + ' -D <scope file>')
    exit()

print("[+] Starting time: %s" % datetime.datetime.now())
print("[+] Scope file: %s" % scope_file_name)

try:
    scope_file = open(scope_file_name, 'r')
except FileNotFoundError:
    print('[x] Scope file not found')
    exit()

crawler = crawler.Crawler(db)

while True:
    line = scope_file.readline()
    if not line:
        time.sleep(5)
        continue

    domain = line.split(' ')[0]

    if not db.checkDomain(domain):
        db.insertDomain(domain)
            
    crawler.run(domain)