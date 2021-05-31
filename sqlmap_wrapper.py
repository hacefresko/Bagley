import threading, time, sqlite3
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

            print(request.get('url'))
            if request.get('method') == 'POST':
                print(request.get('data'))

            request_id += 1