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
                print("EXCEPTION")
                continue

            id += 1

            if request.get('method') == 'POST':
                print('[+] Execute: sqlmap --batch -u "%s" --data "%s"' % (request.get('url'), request.get('data')))
            else:
                print('[+] Execute: sqlmap --batch -u "%s"' % (request.get('url')))
           