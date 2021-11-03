import threading, subprocess, shutil, requests

from config import *
from lib.entities import *

class Searcher (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    @staticmethod
    def __lookupCVEs(tech):
        api = 'https://services.nvd.nist.gov/rest/json/cpes/1.0?addOns=cves&cpeMatchString='
        cpe = tech.cpe + ':' + tech.version if tech.version else tech.cpe
        r = requests.get(api + cpe)
        
        # Get CVEs
        # Insert CVEs in db
        # Link them to technologies

    @staticmethod
    def __wappalyzer(path):
        delay = str(int((1/REQ_PER_SEC) * 1000))
        command = [shutil.which('wappalyzer'), '--probe', '--delay='+delay, str(path)]

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        try:
            for t in json.loads(result.stdout).get('technologies'):
                if t.get('cpe'):
                    tech = Technology.getTech(t.get('cpe'), t.get('version'))
                    if not tech:
                        tech = Technology.insertTech(t.get('cpe'), t.get('name'), t.get('version'))
                        Searcher.__lookupCVEs(tech)
                    tech.link(path)

                    cves = tech.getCVEs()
                    for cve in cves:
                        if tech.version:
                            print('[CVE] Found vulnerability of %s of %s at %s' % (cve, tech.name, str(path)))
                        else:
                            print('[CVE] Some versions of %s are vulnerable to %s at %s' % (tech.name, cve, str(path)))
        except:
            return

    def run(self):
        for path in Path.getPaths():
            if not path:
                time.sleep(5)
                continue

            Searcher.__wappalyzer(path)
