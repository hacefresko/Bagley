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

        request_id = 1
        while True:
            try:
                request = self.db.getRequest(request_id)
            except sqlite3.OperationalError:
                pass

            if request is None:
                time.sleep(1)
                continue

            if '?' in request.get('url'):
                params = request.get('url').split('?')[1]
                keys = self.db.getParamKeys(params)




                if request.get('method') == 'POST':
                    print('sqlmap --batch -u "%s" --data "%s"' % (request.get('url'), request.get('data')))
                else:
                    print('sqlmap --batch -u "%s"' % (request.get('url')))

            request_id += 1