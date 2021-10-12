import threading, subprocess, time, shutil

from config import *
from lib.entities import *

class Injector (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    @staticmethod
    def __sqli(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        delay = str(1/REQ_PER_SEC)
        command = [shutil.which('sqlmap'), '--level', '3', '--delay=' + delay, '-v', '0', '--flush-session', '--batch', '-u',  url, '--method', request.method]

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
            command.append(headers_string)

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
            Vulnerability.insertVuln(url, 'SQLi', result.stdout)
            print("[*] SQL injection found in %s\n\n%s\n" % (url, result.stdout))

    @staticmethod
    def __xss(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        # Added delay 1 by default since it only accepts integer and it's a large enough delay
        command = [shutil.which('dalfox'), 'url', url, '-S', '--no-color', '--delay', '1']
        
        # Add POST data
        if request.method == 'POST' and request.data:
            command.append('-d')
            command.append(request.data)

        # Add headers
        if request.headers:
            for header in request.headers:
                # Does not work well when specifying accept-encoding
                if header.key == 'accept-encoding':
                    continue
                command.append('-H')
                command.append(str(header))

        # Add cookies
        if request.cookies:
            command.append('-C')
            cookies_string = ''
            for cookie in request.cookies:
                cookies_string += str(cookie) + '; '
            cookies_string = cookies_string[:-2]
            command.append(cookies_string)
        
        print("[+] Testing XSS in %s [%s]" % (url, request.method))

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "[POC]" in result.stdout:
            Vulnerability.insertVuln(url, 'XSS', result.stdout)
            print("[*] XSS found in %s\n\n%s\n" % (url, result.stdout))

    @staticmethod
    def __crlf(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        # Added delay 1 by default since it only accepts integer and it's a large enough delay
        command = [shutil.which('crlfuzz'), '-u', url, '-s', '-c', '10']
        
        # Add POST data
        if request.method == 'POST' and request.data:
            command.append('-X')
            command.append('POST')
            command.append('-d')
            command.append(request.data)

        # Add headers
        if request.headers:
            for header in request.headers:
                command.append('-H')
                command.append(str(header))

        # Add cookies
        if request.cookies:
            command.append('-H')
            cookies_string = 'Cookie: '
            for cookie in request.cookies:
                cookies_string += str(cookie) + '; '
            cookies_string = cookies_string[:-2]
            command.append(cookies_string)
        
        print("[+] Testing CRLF injection in %s [%s]" % (url, request.method))

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "[VLN]" in result.stdout:
            Vulnerability.insertVuln(url, 'CRLF', result.stdout)
            print("[*] CRLF injection found in %s\n\n%s\n" % (url, result.stdout))


    def run(self):
        tested = []
        for request in Request.getRequests():
            if not request:
                time.sleep(5)
                continue
            if not request.response or request.response.code != 200 or (not request.params and not request.data) or request.id in tested:
                continue

            Injector.__xss(request)
            Injector.__sqli(request)
            Injector.__crlf(request)

            # Add request with same keys in POST/GET data to tested list
            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]