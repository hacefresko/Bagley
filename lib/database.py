import sqlite3, threading

DB_NAME = 'bagley.db'

class DB:
    # Dict of tids and their instances
    __instance = None
    __lock = threading.Lock()

    def __new__(cls):
        if DB.__instance is None:
            DB.__instance = super(DB, cls).__new__(cls)
        return DB.__instance

    def __init__(self):
        self.__connection = sqlite3.connect(DB_NAME, check_same_thread=False)

    def query(self, query, params):
        DB.__lock.acquire()
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        DB.__lock.release()

        return cursor

    def close(self):
        self.__connection.close()