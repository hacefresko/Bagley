import threading, subprocess, time

from config import *
from lib.entities import *

class Injector (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        tested = []
        for request in Request.getRequests():
            if not request:
                time.sleep(5)
                continue
            if not request.response or request.response.code != 200 or (not request.params and not request.data) or request.id in tested:
                continue

            url = request.protocol + '://' + str(request.path) + ('?' + request.params if request.params else '')
            
            delay = delay = str(1/REQ_PER_SEC)
            command = ['sqlmap', '--delay=' + delay, '-v', '0', '--flush-session', '--batch', '-u',  url]

            if request.method == 'POST' and request.data:
                command.append("--data")
                command.append(request.data)

            for cookie in request.path.domain.cookies:
                command.append("--cookie="+str(cookie))
            
            print("[+] Testing SQL injection in %s [%s]" % (url, request.method))

            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[*] SQL injection found in %s" % url)
                Vulnerability.insertVuln(url, 'SQLi', result.stdout)
                print(result.stdout)

            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]