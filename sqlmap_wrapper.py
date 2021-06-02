import threading, time, sqlite3, subprocess

import database

class Sqlmap (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        self.db = database.VDT_DB()
        try:
            self.db.connect()
        except:
            print('[x] Couldn\'t connect to the database')


        requests_to_skip = []
        id = 1
        while True:
            try:
                if id in requests_to_skip:
                    id += 1
                    continue
                request = self.db.getRequest(id)
                if request is None:
                    time.sleep(2)
                    continue
                if len(request.get('url').split('?')) < 2 and request.get('data') is None:
                    id += 1
                    continue
                # Merge both lists
                requests_to_skip = [*self.db.getRequestWithSameKeys(id), *requests_to_skip]
            except sqlite3.OperationalError:
                continue

            id += 1

            if request.get('method') == 'POST':
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  request.get("url"), '--data', request.get("data")]
            else:
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  request.get("url")]

            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[+] SQL injection found in %s" % request.get('url'))
                print(result.stdout)
           