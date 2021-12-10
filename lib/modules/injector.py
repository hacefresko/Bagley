import threading, subprocess, time, shutil

import config
from lib.entities import *

class Injector (threading.Thread):
    def __init__(self, stop):
        threading.Thread.__init__(self)
        self.stop = stop

    @staticmethod
    def __sqli(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        delay = str(1/config.REQ_PER_SEC)
        command = [shutil.which('sqlmap'), '--level', '3', '--delay=' + delay, '-v', '0', '--flush-session', '--batch', '-u',  url, '--method', request.method]

        # Add POST data
        if request.method == 'POST' and request.data:
            command.append("--data")
            command.append(request.data)

        # Add only headers added by the user since otherwise it would try SQLi on each header (too much time)
        if request.path.domain.headers:
            headers_string = '--headers='
            for header in request.path.domain.headers:
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
            Vulnerability.insert('SQLi', result.stdout, str(request.path))
            print("[SQLi] SQL injection found in %s!\n\n%s\n" % (url, result.stdout), command)
        elif "[WARNING] false positive or unexploitable injection point detected" in result.stdout:
            Vulnerability.insert('pSQLi', result.stdout, str(request.path), command)
            print("[SQLi] Possible SQL injection found in %s! But sqlmap couldn't exploit it\n\n%s\n" % (url, result.stdout))

    @staticmethod
    def __xss(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        delay = str(int(1/config.REQ_PER_SEC * 1000))
        command = [shutil.which('dalfox'), 'url', url, '-S', '--skip-bav', '--skip-grepping', '--no-color', '--delay', delay]
        
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
            Vulnerability.insert('XSS', result.stdout, str(request.path), command)
            print("[XSS] Cross Site Scripting found in %s!\n\n%s\n" % (url, result.stdout))

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
            Vulnerability.insert('CRLFi', result.stdout, str(request.path), command)
            print("[CRLFi] Carriage Return Line Feed injection found in %s!\n\n%s\n" % (url, result.stdout))

    @staticmethod
    def __ssti(request):
        url = str(request.path) + ('?' + request.params if request.params else '')
        # Added delay 1 by default since it only accepts integer and it's a large enough delay
        command = [shutil.which('tplmap'), '-u', url]
        
        # Add POST data
        if request.method == 'POST' and request.data:
            command.append('-d')
            command.append(request.data)

        # Add headers
        if request.headers:
            for header in request.headers:
                # Tplmap detects char * as an injection point, so Headers containing that won't be added
                if '*' in str(header):
                    continue
                command.append('-H')
                command.append(str(header))

        # Add cookies
        if request.cookies:
            for cookie in request.cookies:
                command.append('-c')
                command.append(str(cookie))
        
        print("[+] Testing SSTI in %s [%s]" % (url, request.method))

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "Tplmap identified the following injection point" in result.stdout:
            Vulnerability.insert('SSTI', result.stdout, str(request.path), command)
            print("[SSTI] Server Side Template Injection found in %s!\n\n%s\n" % (url, result.stdout))

    def run(self):
        tested = []
        requests = Request.yieldAll()
        while not self.stop.is_set():
            request = next(requests)
            if not request:
                time.sleep(5)
                continue
            if not request.response or request.id in tested or request.response.code != 200: 
                continue
                
            Injector.__crlf(request)

            if request.params or request.data:
                content_type = request.getHeader('content-type')
                if content_type and 'text/html' in str(content_type):
                    Injector.__xss(request)
                Injector.__ssti(request)
                Injector.__sqli(request)

            # Add request with same keys in POST/GET data to tested list
            tested = [*[request.id for request in request.getSameKeys()], *tested]