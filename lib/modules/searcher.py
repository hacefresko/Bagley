import threading, subprocess, shutil, requests, time, json

import config
from lib.entities import *

class Searcher (threading.Thread):
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
        
        if len(vulns) > 0:
            str = '[CVE] Vulnerabilities found at %s %s\n' % (tech.name, tech.version)
            for v in vulns:
                if CVE.insert(v, tech):
                    str += v + "\n"
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
                            Searcher.__lookupCVEs(tech)

                    if tech:
                        tech.link(path)

                        cves = tech.getCVEs()
                        if len(cves) > 0:
                            print("[CVE] %s uses vulnerable %s %s" % (str(path), tech.name, tech.version))
        except:
            return

    def run(self):
        paths = Path.yieldAll()
        while not self.stop.is_set():
            path = next(paths)
            if not path:
                time.sleep(5)
                continue

            Searcher.__wappalyzer(path)
