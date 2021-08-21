import os, signal, datetime, getopt, sys, time
from lib.modules import *

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[x] SIGINT: Exiting...')

    scope_file.close()

    quit()
signal.signal(signal.SIGINT, sigint_handler)

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

#try:
#    opts, args = getopt.getopt(sys.argv[1:], 'S:')
#
#    for opt, arg in opts:
#        if opt == '-S':
#            scope_file_name = arg
#            scope_found = True
#
#    if not scope_found or scope_file_name == '':
#        raise Exception
#            
#except Exception:
#    print('[x] Usage: ' + os.path.basename(__file__) + ' -S <scope file>')
#    exit()

scope_file_name = 'scope.txt'

print("[+] Starting time: %s" % datetime.datetime.now())
print("[+] Parsing scope file: %s" % scope_file_name)

try:
    scope_file = open(scope_file_name, 'r')
except FileNotFoundError:
    print('[x] Scope file not found')
    exit()

# Init all modules
crawler = Crawler()
crawler.start()

fuzzer = Fuzzer(crawler)
fuzzer.start()

injector = Injector()
injector.start()

# Parse scope file
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
    domain = entry.get('domain')
    if not domain:
        continue
    if not Domain.checkDomain(domain):
        print("[+] Target found: %s" % domain)
        
        json_headers = entry.get('headers')
        headers = []
        if json_headers:
            for k,v in json_headers.items():
                header = Header.insertHeader(k,v)
                headers.append(header)

        json_cookies = entry.get('cookies')
        cookies = []
        if json_cookies:

            for c in json_cookies:
                cookie = Cookie.insertCookie(c.get('name'), c.get('value'), c.get('domain'), '/', None, None, None, None, None)
                if cookie:
                    cookies.append(cookie)

        Domain.insertDomain(domain, headers, cookies)

    if domain[0] == '.':
        # Insert out of scope domains
        excluded = entry.get('excluded')
        if excluded:
            for e in excluded:
                Domain.insertOutOfScopeDomain(e)

