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
                request = self.db.stringifyRequest(request_id)
            except sqlite3.OperationalError:
                pass

            if request is None or not request:
                time.sleep(1)
                continue
            
            print(request)
            request_id += 1