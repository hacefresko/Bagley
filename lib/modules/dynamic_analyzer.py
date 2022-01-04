import threading, subprocess, shutil, requests, time, json

import config
from lib.entities import *

class Dynamic_Analyzer (threading.Thread):
    def __init__(self, stop):
        threading.Thread.__init__(self)
        self.stop = stop

    @staticmethod
    def __lookupCVEs(tech):
        vulns = []
        api = 'https://services.nvd.nist.gov/rest/json/cpes/1.0?addOns=cves&startIndex=%d&cpeMatchString=%s&resultsPerPage=5'
        cpe = tech.cpe + ':' + tech.version
        fetched = 0
        total_results = 1

        while fetched < total_results:
            url = api % (fetched, cpe)
            r = requests.get(url)
            if not r.ok:
                print('[ERROR] There was a problem requesting %s' % url)
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
            print('[CVE] Vulnerabilities found at %s %s\n' % (tech.name, tech.version))
            print(str)

    @staticmethod
    def __wappalyzer(path):
        delay = str(int((1/config.REQ_PER_SEC) * 1000))
        command = [shutil.which('wappalyzer'), '--probe', '--delay='+delay, str(path)]

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        try:
            for t in json.loads(result.stdout).get('technologies'):
                if t.get('cpe') and t.get('version'):
                    tech = Technology.get(t.get('cpe'), t.get('version'))
                    if not tech:
                        tech = Technology.insert(t.get('cpe'), t.get('name'), t.get('version'))
                        if tech:
                            Dynamic_Analyzer.__lookupCVEs(tech)

                    if tech:
                        tech.link(path)
        except:
            return

    @staticmethod
    def __subdomainTakeover(domain):
        command = [shutil.which('subjack'), '-a', '-m', '-d', str(domain)]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.stdout != '':
            Vulnerability.insert('Subdomain Takeover', result.stdout, str(domain))
            print('[TAKEOVER] Subdomain Takeover found at %s!\n\n%s\n' % (str(domain), result.stdout))

    @staticmethod
    def __bypass403(request):
        bypass_headers = {
            "X-Client-IP": "127.0.0.1",
            "Host": "127.0.0.1",
            "Referer": "127.0.0.1"
        }

        if request.response.code == 403:
            headers = {}
            for h in request.headers:
                headers[h.key] = h.value

            cookies = {}
            for c in request.cookies:
                cookies[c.name] = c.value

            for k,v in bypass_headers.items():
                req_headers = headers
                req_headers[k] = v
                if request.method == 'GET':
                    r = requests.get(str(request.path), params=request.params, data=request.data, headers=headers, cookies=cookies)
                elif request.method == 'POST':
                    r = requests.get(str(request.url), request.params, request.data, headers, cookies)
                
                if r.status_code != 403:
                    Vulnerability.insert('Broken Access Control', k+": "+v, str(request.path))
                    print("[Access Control] Got code %d for %s using header %s: %s", r.status_code, request.url, k,v)
            
            time.sleep(str(1/config.REQ_PER_SEC))

    def run(self):
        paths = Path.yieldAll()
        domains = Domain.yieldAll()
        requests = Request.yieldAll()
        while not self.stop.is_set():
            path = next(paths)
            if path:
                self.__wappalyzer(path)
            else:
                domain = next(domains)
                if domain:
                    self.__subdomainTakeover(domain)
                else:
                    request = next(requests)
                    if request and request.response.code == 403:
                        self.__bypass403(request)
                    else:
                        time.sleep(5)
