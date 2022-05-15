import subprocess, time, shutil, traceback

from lib.modules.module import Module
from lib.entities import *

class Injector (Module):
    def __init__(self, controller, stop, rps, active_modules, lock):
        super().__init__(["sqlmap", "dalfox", "crlfuzz"], controller, stop, rps, active_modules, lock, ["sqli", "xss"])

    def __sqli(self, request):
        url = str(request.path) + ('?' + request.params if request.params else '')

        # Sqlmap options:
        # --random-agent: use a random user agent on every request
        # --batch: automatically choose the default options when something is asked to the user
        # -u: URL to test
        # --method: HTTP method to use
        # --delay: delay between requests
        # -v: verbosity level
        # -o: Turn on all optimization switches

        command = [shutil.which('sqlmap'), '--random-agent', '--batch', '-u',  url, '--method', request.method, "--delay="+str(self.getDelay()), '-v', '0', '-o']

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
        
        self.send_msg("Testing SQL injection in %s\n\n%s" % (url, str(request)), "injector")

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "---" in result.stdout:
            Vulnerability.insert('SQLi', result.stdout, str(request.path))
            self.send_vuln_msg("SQL INJECTION: Found in %s!\n%s\n%s" % (url, result.stdout, " ".join(command)), "injector")
        elif "[WARNING] false positive or unexploitable injection point detected" in result.stdout:
            Vulnerability.insert('pSQLi', result.stdout, str(request.path), command)
            self.send_vuln_msg("SQL INJECTION: Possible SQL injection in %s! But sqlmap couldn't exploit it\n\n%s\n%s" % (url, result.stdout, " ".join(command)), "injector")
        if result.stderr != '':
            self.send_error_msg(result.stderr, "injector")

    def __xss(self, request):
        url = str(request.path)

        # Dalfox options:
        # url: use single target
        # -S: silent mode
        # -F: follow redirects
        # --skip-bav: don't test for other vulnerabilities (it's not good at it)
        # --skip-grepping: don't grep for credentials, known error messages, etc.
        # --waf-evasion: try evasion techniques if WAF is detected
        # --no-color: no color in output
        # --delay: delay between requests
        # -X: method to use

        command = [shutil.which('dalfox'), 'url', url, '-S', '-F', '--skip-bav', '--skip-grepping', '--waf-evasion', '--no-color', "--delay", str(int(self.getDelay()*1000)), "-X", request.method]

        # Add URL params
        if request.params:
            command.append('-p')
            params = []
            for p in request.params.split("&"):
                params.append(p.split("=")[0])
            params = ",".join(params)
            command.append(params)

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
        
        self.send_msg("Testing XSS in %s [%s]" % (url if request.params is None else url + '?' + request.params, request.method), "injector")

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "[POC]" in result.stdout:
            Vulnerability.insert('XSS', result.stdout, str(request.path), command)
            self.send_vuln_msg("XSS: %s\n%s\n" % (url, result.stdout), "injector")
        if result.stderr != '':
            self.send_error_msg(result.stderr, "injector")

    def __crlf(self, request):
        url = str(request.path) + ('?' + request.params if request.params else '')
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
        
        self.send_msg("Testing CRLF injection in %s [%s]" % (url, request.method), "injector")

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if "[VLN]" in result.stdout:
            Vulnerability.insert('CRLFi', result.stdout, str(request.path), command)
            self.send_vuln_msg("CRLF INJECTION: %s\n%s\n" % (url, result.stdout), "injector")
        if result.stderr != '':
            self.send_error_msg(result.stderr, "injector")

    def run(self):
        tested = []
        requests = Request.yieldAll()
        while not self.stop.is_set():
            try:
                request = next(requests)
                if (request is None):
                    time.sleep(5)
                    continue

                response = request.response
                if (request.id in tested) or \
                (response is None) or \
                (response.code == 404) or \
                (response.code == 500) or \
                (response.code // 100 == 3) or \
                ((request.params is None) and (request.data is None)):
                    continue

                self.setActive()

                if response:
                    content_type = response.getHeader('content-type')
                    if (content_type is not None) and ('text/html' in str(content_type)) and ("xss" not in request.path.domain.excluded):
                        self.__xss(request)
                
                if ("sqli" not in request.path.domain.excluded):
                    self.__sqli(request)

                self.setInactive()

                # Add request with same keys in POST/GET data to tested list
                tested = [*[request.id for request in request.getSameKeysRequests()], *tested]
            except:
                self.send_error_msg(traceback.format_exc(), "injector")

