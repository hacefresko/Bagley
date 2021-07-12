import sqlite3, threading

DB_NAME = 'bagley.db'

class DB:
    # Dict of tids and their instances
    __instances = {}

    def __new__(cls):
        tid = threading.current_thread().ident

        if DB.__instances.get(tid) is None:
            DB.__instances.update({tid: super(DB, cls).__new__(cls)})
            DB.__instances.get(tid).__connection = sqlite3.connect(DB_NAME)
        return DB.__instances.get(tid)

    def query(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        return cursor

    def close(self):
        self.__connection.close()