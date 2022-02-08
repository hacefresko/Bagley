import datetime, subprocess, shutil, requests, time, json

import config
from lib.entities import *
from lib.modules.module import Module
import lib.controller

class Dynamic_Analyzer (Module):
    def __init__(self, stop, rps, active_modules, lock):
        super().__init__(["subjack", "wappalyzer"], stop, rps, active_modules, lock)
        self.t = datetime.datetime.now()

    def __lookupCVEs(self, tech):
        vulns = []
        api = 'https://services.nvd.nist.gov/rest/json/cpes/1.0?addOns=cves&startIndex=%d&cpeMatchString=%s&resultsPerPage=5'
        cpe = tech.cpe + ':' + tech.version
        fetched = 0
        total_results = 1

        lib.controller.Controller.send_msg("Searching for known vulnerabilites for %s %s" % (tech.name, tech.version), "dynamic-analyzer")

        while fetched < total_results:
            url = api % (fetched, cpe)
            r = requests.get(url)
            if not r.ok:
                lib.controller.Controller.send_error_msg('There was a problem requesting %s for CVE looking' % url, "dynamic-analyzer")
                break
            j = json.loads(r.text)

            total_results = j.get('totalResults')

            for c in j.get('result').get('cpes'):
                fetched += 1
                for v in c.get('vulnerabilities'):
                    if v != '' and v not in vulns:
                        vulns.append(v)
        
        str = ""
        for v in vulns:
            if CVE.insert(v, tech):
                str += "\t" + v + "\n"
        
        if str != '':
            lib.controller.Controller.send_vuln_msg('CVE: Vulnerabilities found at %s %s\n%s' % (tech.name, tech.version, str), "dynamic-analyzer")

    def __wappalyzer(self, path):
        command = [shutil.which('wappalyzer'), str(path), '--probe', "-t", str(self.getDelay())]

        lib.controller.Controller.send_msg("Getting technologies used by %s" % str(path), "dynamic-analyzer")

        if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
            time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

        result = subprocess.run(command, capture_output=True, encoding='utf-8')
        
        self.t = datetime.datetime.now()

        try:
            for t in json.loads(result.stdout).get('technologies'):
                if t.get('cpe') and t.get('version'):
                    tech = Technology.get(t.get('cpe'), t.get('version'))
                    if not tech:
                        tech = Technology.insert(t.get('cpe'), t.get('name'), t.get('version'))
                        if tech:
                            self.__lookupCVEs(tech)

                    if tech:
                        tech.link(path)
        except:
            lib.controller.Controller.send_error_msg(utils.getExceptionString(), "dynamic-analyzer")

    def __subdomainTakeover(self, domain):
        command = [shutil.which('subjack'), '-a', '-m', '-d', str(domain)]

        lib.controller.Controller.send_msg("Testing subdomain takeover for domain %s" % str(domain), "dynamic-analyzer")

        if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
            time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        self.t = datetime.datetime.now()

        if result.stdout != '':
            Vulnerability.insert('Subdomain Takeover', result.stdout, str(domain))
            lib.controller.Controller.send_vuln_msg('TAKEOVER: Subdomain Takeover found at %s!\n\n%s\n' % (str(domain), result.stdout), "dynamic-analyzer")

    def __bypass4xx(self, request):
        bypass_headers = {
            "Host": "127.0.0.1",
            "Referer": "127.0.0.1",
            "Referer": "localhost",
            "Client-IP": "127.0.0.1",
            "Forwarded-For-Ip": "127.0.0.1",
            "Forwarded-For": "127.0.0.1",
            "Forwarded-For": "localhost",
            "Forwarded": "127.0.0.1",
            "Forwarded": "localhost",
            "True-Client-IP": "127.0.0.1",
            "X-Client-IP": "127.0.0.1",
            "X-Custom-IP-Authorization": "127.0.0.1",
            "X-Forward-For": "127.0.0.1",
            "X-Forward": "127.0.0.1",
            "X-Forward": "localhost",
            "X-Forwarded-By": "127.0.0.1",
            "X-Forwarded-By": "localhost",
            "X-Forwarded-For-Original": "127.0.0.1",
            "X-Forwarded-For-Original": "localhost",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-For": "localhost",
            "X-Forwarded-Server": "127.0.0.1",
            "X-Forwarded-Server": "localhost",
            "X-Forwarded": "127.0.0.1",
            "X-Forwarded": "localhost",
            "X-Forwarded-Host": "127.0.0.1",
            "X-Forwarded-Host": "localhost",
            "X-Host": "127.0.0.1",
            "X-Host": "localhost",
            "X-HTTP-Host-Override": "127.0.0.1",
            "X-Originating-IP": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "X-Remote-Addr": "127.0.0.1",
            "X-Remote-Addr": "localhost",
            "X-Remote-IP": "127.0.0.1",
            "X-Original-URL": "/admin",
            "X-Override-URL": "/admin",
            "X-Rewrite-URL": "/admin",
            "Referer": "/admin",
            "X-HTTP-Method-Override": "PUT"
        }

        methods = {
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "DELETE",
            "CONNECT",
            "OPTIONS",
            "TRACE",
            "PATCH"
        }

        if request.response.code//100 == 4:
            headers = {}
            for h in request.headers:
                headers[h.key] = h.value

            cookies = {}
            for c in request.cookies:
                cookies[c.name] = c.value

            for method in methods:
                if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
                    time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

                r = requests.request(method, str(request.path), params=request.params, data=request.data, headers=headers, cookies=cookies, verify=False)

                self.t = datetime.datetime.now()

                if r.status_code//100 == 2:
                    Vulnerability.insert('Broken Access Control', "Method: " + method, str(request.path))
                    lib.controller.Controller.send_vuln_msg('ACCESS CONTROL: Got code %d for %s using method "%s" (original was %d)' % (r.status_code, request.path, method, request.response.code), "dynamic-analyzer")

            for k,v in bypass_headers.items():
                req_headers = headers
                req_headers[k] = v

                if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
                    time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

                if request.method == 'GET':
                    r = requests.get(str(request.path), params=request.params, data=request.data, headers=headers, cookies=cookies, verify=False)
                elif request.method == 'POST':
                    r = requests.get(str(request.url), request.params, request.data, headers, cookies, verify=False)
                
                self.t = datetime.datetime.now()

                if r.status_code//100 == 2:
                    Vulnerability.insert('Broken Access Control', k+": "+v, str(request.path))
                    lib.controller.Controller.send_vuln_msg('ACCESS CONTROL: Got code %d for %s using header "%s: %s" (original was %d)' % (r.status_code, request.path, k,v, request.response.code), "dynamic-analyzer")

            time.sleep(1/config.REQ_PER_SEC)

    def run(self):
        try:
            paths = Path.yieldAll()
            domains = Domain.yieldAll()
            requests = Request.yieldAll()
            while not self.stop.is_set():
                executed = False
                path = next(paths)
                if path:
                    self.setActive()
                    self.__wappalyzer(path)
                    executed = True

                domain = next(domains)
                if domain:
                    self.setActive()
                    self.__subdomainTakeover(domain)
                    executed = True

                request = next(requests)
                if request and request.response and request.response.code//100 == 4:
                    self.setActive()
                    self.__bypass4xx(request)
                    executed = True

                if not executed:
                    self.setInactive()
                    time.sleep(5)

        except Exception as e:
            lib.controller.Controller.send_error_msg(utils.getExceptionString(), "dynamic-analyzer")
