import threading, subprocess, shutil

from config import *
from lib.entities import *

class Searcher (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    @staticmethod
    def __wappalyzer(path):
        delay = str(int((1/REQ_PER_SEC) * 1000))
        command = [shutil.which('wappalyzer'), '--probe', '--delay='+delay, str(path)]

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        try:
            for t in json.loads(result.stdout).get('technologies'):
                tech = Technology.insertTech(t.get('slug'), t.get('name'), t.get('version'))
                tech.link(path)
        except:
            return

    def run(self):
        for path in Path.getPaths():
            if not path:
                time.sleep(5)
                continue

            Searcher.__wappalyzer(path)
