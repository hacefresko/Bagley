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

            if request.get('method') == 'POST':
                print('sqlmap -u "%s" --data "%s"' % (request.get('url'), request.get('data')))
            else:
                print('sqlmap -u "%s"' % (request.get('url')))
                
            request_id += 1