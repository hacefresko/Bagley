import os, signal, datetime, getopt, sys, time, json, re, shutil, threading, io

from lib.entities import *
import lib.modules

threads = []
stopThread = threading.Event()

def checkDependences():
    dependences = ['chromedriver', 'mariadb', 'chromedriver', 'gobuster', 'subfinder', 'subjack', 'sqlmap', 'dalfox', 'crlfuzz', 'tplmap', 'wappalyzer']
    for d in dependences:
        if not shutil.which(d):
            print("[x] %s not found in PATH" % d)
            return False
    return True

def initDB():
    db = DB()
    statement = ''
    for line in open(config.DB_SCRIPT):
        if re.match(r'--', line):
            continue
        if not re.search(r';$', line):  # keep appending lines that don't end in ';'
            statement = statement + line
        else:  # when you get a line ending in ';' then exec statement and reset for next statement
            statement = statement + line
            try:
                db.exec(statement)
            except Exception as e:
                print('[x] MySQLError when executing %s' % config.DB_SCRIPT)
            statement = ''

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[SIGINT] Ending execution...')

    # Supress output
    sys.stdout = io.BytesIO()
    sys.stderr = io.BytesIO()

    # Close scope fd
    scope_file.close()

    # Kill threads
    stopThread.set()
    for thread in threads:
        thread.join()

    quit()

title = '''

                  @@@*=*@@@
               @@@%+ =*= +%@@@
           @@@@#=  *%@@@%*  =#@@@@
       @@@@%+  =#@@@@@@@@@@@#=  +%@@@@
     @@@@*=    -*@@@@@@@@@@%*-    =#@@@@ 
 @@@@%+  =#@ *@%+  =#@@@#=  +%@* @#=  +%@@@@
@@*=  *%@@@@ *@@@@@* -+- *@@@@@* @@@@%+  =#@@
@@ =@@@@@@@@ *@@@@@@@# #@@@@@@@* @@@@@@@@* @@
@@ =@@@@@@%  #@@@@@@@# #@@@@@@@#  %@@@@@@* @@
@@ =@@@#  -%@@@@@@@@@# #@@@@@@@@@#  -*%@@* @@
@@ -+  =#@@@@@@@@@@@@# #@@@@@@@@@@@@%+  == @@
@@   #@@@@@@@@@@@@@@@   @@@@@@@@@@@@@@@#   @@
@@ -+-.=*@@@@@@@@#-  %@%  -#@@@@@@@@*  =*+ @@
@@ *@@@#=  %@%+  -#@@@@@@@*-  +%@%  =#@@@* @@
@@ *@@@@@@@   +%@@@@@@@@@@@@@%+   @@@@@@@* @@
@@ *@@@@@@@% *@@@@@@@@@@@@@@@@@* @@@@@@@@* @@
@@ =@@@@@@@# #@@@@@@@#+#@@@@@@@* @@@@@@@@= @@
@@#=  +#@@@# %@@@@%+ =+= +%@@@@* @@@@%+  =#@@
  @@@%*   ** %@*=  *%@@@%+  =#@* @*   *%@@@
    @@@@@#+    +#@@@@@@@@@@@#=    +#@@@@@
       @@@@@*  -*@@@@@@@@@@@*-  *@@@@@
          @@@@@#+  +#@@@%+  +#@@@@@
              @@@@@* =*= *@@@@@
                  @@@*=*@@@

'''
print(title)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'S:')

    for opt, arg in opts:
        if opt == '-S':
            scope_file_name = arg
            scope_found = True

    if not scope_found or scope_file_name == '':
        raise Exception
            
except Exception:
    print('[x] Usage: ' + os.path.basename(__file__) + ' -S <scope file>')
    exit()
print("[+] Starting time: %s" % datetime.datetime.now())

# Check dependences
print("[+] Checking dependences")
if not checkDependences():
    exit()

# Start db
print("[+] Initializing database")
initDB()

# Check if file can be opened (and open it)
try:
    scope_file = open(scope_file_name, 'r')
except FileNotFoundError:
    print('[x] Scope file not found')
    exit()
signal.signal(signal.SIGINT, sigint_handler)

# Init all modules
crawler = lib.modules.Crawler(stopThread)
crawler.start()
threads.append(crawler)

discoverer = lib.modules.Discoverer(stopThread, crawler)
discoverer.start()
threads.append(discoverer)

injector = lib.modules.Injector(stopThread)
injector.start()
threads.append(injector)

searcher = lib.modules.Searcher(stopThread)
searcher.start()
threads.append(searcher)

# Parse scope file
print("[+] Parsing scope file: %s" % scope_file_name)
while True:
    line = scope_file.readline()
    if not line:
        time.sleep(60)
        continue
    try:
        entry = json.loads(line)
    except:
        print("[x] Target couldn't be parsed: %s" % line)
        continue

    # Get domain
    if entry.get('domain'):
        domain = entry.get('domain')
        if not domain:
            continue
        if not Domain.check(domain):
            print("[+] Target found: %s" % domain)

            # Insert domain
            d = Domain.insert(domain)
            if not domain:
                continue
            
            # Get and insert headers
            json_headers = entry.get('headers')
            if json_headers:
                for k,v in json_headers.items():
                    header = Header.insert(k,v, False)
                    if header:
                        d.add(header)

            # Get and insert cookies
            json_cookies = entry.get('cookies')
            if json_cookies:
                for c in json_cookies:
                    cookie = Cookie.insert(c.get('name'), c.get('value'), c.get('domain'), '/', None, None, None, None, None, False)
                    if cookie:
                        d.add(cookie)

            # If group of subdomains specified, get out of scope domains
            if domain[0] == '.':
                excluded = entry.get('excluded')
                if excluded:
                    for e in excluded:
                        Domain.insertOutOfScope(e)

            # Add to queue
            if entry.get("queue"):
                for q in entry.get("queue"):
                    crawler.addToQueue(q)
                    print("[+] %s added to queue" % q)
