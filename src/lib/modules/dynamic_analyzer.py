import subprocess, shutil, requests, time, json, traceback

import config, lib.controller
from lib.entities import *
from lib.modules.module import Module

class Dynamic_Analyzer (Module):
    def __init__(self, controller, stop, rps, active_modules, lock):
        super().__init__(["subjack", "wappalyzer"], controller, stop, rps, active_modules, lock, ["cve_finder", "subdomain_takeover", "bypass403"])

    def __lookupCVEs(self, tech):
        vulns = []
        api = 'https://services.nvd.nist.gov/rest/json/cpes/1.0?addOns=cves&startIndex=%d&cpeMatchString=%s&resultsPerPage=5'
        cpe = tech.cpe + ':' + tech.version
        fetched = 0
        total_results = 1

        self.send_msg("Searching for known vulnerabilites for %s %s [ID: %d]" % (tech.name, tech.version, tech.id), "dynamic-analyzer")

        while fetched < total_results:
            url = api % (fetched, cpe)
            r = requests.get(url)
            if not r.ok:
                self.send_error_msg('There was a problem requesting %s for CVE looking' % url, "dynamic-analyzer")
                break
            j = json.loads(r.text)

            total_results = j.get('totalResults')

            for c in j.get('result').get('cpes'):
                fetched += 1
                for v in c.get('vulnerabilities'):
                    if v != '' and v not in vulns:
                        vulns.append(v)
        
        s = ""
        for v in vulns:
            if CVE.insert(v, tech):
                s += "\t" + v + "\n"
        
        if s != '':
            self.send_vuln_msg('CVE: Vulnerabilities found at %s %s [ID: %d]\n%s' % (tech.name, tech.version, tech.id, s), "dynamic-analyzer")

    def __wappalyzer(self, path):
        command = [shutil.which('wappalyzer'), str(path), '--probe', "-t", str(self.getDelay())]

        self.send_msg("Getting technologies used by %s" % str(path), "dynamic-analyzer")

        self.applyDelay()

        result = subprocess.run(command, capture_output=True, encoding='utf-8')
        
        self.updateLastRequest()

        try:
            for t in json.loads(result.stdout).get('technologies'):
                if t.get('cpe'):
                    tech = Technology.get(t.get('cpe'), t.get('version'))
                    if not tech:
                        tech = Technology.insert(t.get('cpe'), t.get('name'), t.get('version'))

                        # Only techs with version will be scanned for vulns
                        if tech and t.get('version'):
                            self.__lookupCVEs(tech)

                    if tech:
                        tech.link(path)
        except:
            self.send_error_msg(traceback.format_exc(), "dynamic-analyzer")

    def __subdomainTakeover(self, domain):
        command = [shutil.which('subjack'), '-a', '-m', '-d', str(domain)]

        self.send_msg("Testing subdomain takeover for domain %s" % str(domain), "dynamic-analyzer")

        self.applyDelay()

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        self.updateLastRequest()

        if result.stdout != '':
            Vulnerability.insert('Subdomain Takeover', result.stdout, str(domain))
            self.send_vuln_msg('TAKEOVER: Subdomain Takeover found at %s!\n\n%s\n' % (str(domain), result.stdout), "dynamic-analyzer")

    def __bypass403(self, request):
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

        if request.response.code == 403:
            headers = {}
            for h in request.headers:
                headers[h.key] = h.value

            cookies = {}
            for c in request.cookies:
                cookies[c.name] = c.value

            self.send_msg("Trying to bypass 403 in %s" % str(request.path), "dynamic-analyzer")

            for method in methods:
                self.applyDelay()

                r = requests.request(method, str(request.path), params=request.params, data=request.data, headers=headers, cookies=cookies, verify=False)

                self.updateLastRequest()

                if r.status_code//100 == 2:
                    Vulnerability.insert('Broken Access Control', "Method: " + method, str(request.path))
                    self.send_vuln_msg('ACCESS CONTROL: Got code %d for %s using method "%s" (original was %d)' % (r.status_code, request.path, method, request.response.code), "dynamic-analyzer")

            for k,v in bypass_headers.items():
                req_headers = headers
                req_headers[k] = v

                self.applyDelay()

                r = requests.request(request.method, str(request.path), params=request.params, data=request.data, headers=headers, cookies=cookies, verify=False)
                
                self.updateLastRequest()

                if r.status_code//100 == 2:
                    Vulnerability.insert('Broken Access Control', k+": "+v, str(request.path))
                    self.send_vuln_msg('ACCESS CONTROL: Got code %d for %s using header "%s: %s" (original was %d)' % (r.status_code, request.path, k,v, request.response.code), "dynamic-analyzer")

            time.sleep(1/config.REQ_PER_SEC)

    def run(self):
        paths = Path.yieldAll()
        domains = Domain.yieldAll()
        requests = Request.yieldAll()
        while not self.stop.is_set():
            try:
                executed = False
                path = next(paths)
                if path:
                    self.setActive()
                    self.__wappalyzer(path)
                    self.setInactive()
                    executed = True

                domain = next(domains)
                if (domain is not None) and (str(domain)[0] != '.'):
                    self.setActive()
                    self.__subdomainTakeover(domain)
                    self.setInactive()
                    executed = True

                request = next(requests)
                if (request) and (request.response) and (request.response.code == 403):
                    self.setActive()
                    self.__bypass403(request)
                    self.setInactive()
                    executed = True

                if not executed:
                    time.sleep(5)

            except Exception as e:
                self.send_error_msg(traceback.format_exc(), "dynamic-analyzer")
