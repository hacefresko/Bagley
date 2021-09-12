import threading, subprocess, time

from config import *
from lib.entities import *

class Injector (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    @staticmethod
    def __sqli(request):
        url = request.protocol + '://' + str(request.path) + ('?' + request.params if request.params else '')
        delay = str(1/REQ_PER_SEC)
        command = ['sqlmap', '--delay=' + delay, '-v', '0', '--flush-session', '--batch', '-u',  url, '--method', request.method]

        # Add POST data
        if request.method == 'POST' and request.data:
            command.append("--data")
            command.append(request.data)

        # Add headers
        if request.headers:
            headers_string = '--headers='
            for header in request.headers:
                headers_string += str(header) + '\n'
            headers_string = headers_string[:-1]

        # Add cookies
        if request.cookies:
            cookies_string = '--cookie='
            for cookie in request.cookies:
                cookies_string += str(cookie) + '; '
            cookies_string = cookies_string[:-2]
            command.append(cookies_string)
        
        print("[+] Testing SQL injection in %s [%s]" % (url, request.method))

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "---" in result.stdout:
            print("[*] SQL injection found in %s" % url)
            Vulnerability.insertVuln(url, 'SQLi', result.stdout)
            print(result.stdout)

    @staticmethod
    def __xss(request):
        url = request.protocol + '://' + str(request.path) + ('?' + request.params if request.params else '')
        delay = str(1/REQ_PER_SEC)
        command = ['xsstrike.py', '-u', url, '-d', delay]
        
        # Add data
        if request.method == 'POST' and request.data:
            command.append('--data')
            command.append(request.data)

        # Add headers
        command.append('--headers')
        headers_string = ''

        if request.headers:
            for header in request.headers:
                headers_string += str(header) + '\n'

        if request.cookies:
            headers_string += 'Cookie:'
            for cookie in request.cookies:
                headers_string += ' ' + str(cookie) + ';'
            headers_string = headers_string[:-1]
        else:
            headers_string = headers_string[:-1]

        command.append(headers_string)

        print(command)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        while True:
            line = process.stdout.readline().rstrip()
            if not line:
                break
            elif '------------------------------------------------------------' in line:
                process.terminate()
                print("[*] XSS found in %s" % url)
                print(process.stdout)
                break
                
    def run(self):
        tested = []
        for request in Request.getRequests():
            if not request:
                time.sleep(5)
                continue
            if not request.response or request.response.code != 200 or (not request.params and not request.data) or request.id in tested:
                continue

            Injector.__sqli(request)
            Injector.__xss(request)

            # Add request with same keys in POST/GET data to tested list
            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]