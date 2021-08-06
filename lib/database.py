import threading, mariadb

DB_USER = 'bagley'
DB_HOST = '127.0.0.1'
DB_NAME = 'bagley'

class DB:
    # True when there has been a change in the database (this way, we reset the connection when there are changes so the reader doesn't get stuck, since usually happens although the cursor is closed)
    __dirty = False

    __instances = {}
    __lock = threading.Lock()

    def __new__(cls):
        tid = threading.get_ident()

        if DB.__instances.get(tid) is None:
            with cls.__lock:
                # another thread could have created the instance before we acquired the lock. So check that the instance is still nonexistent.
                if DB.__instances.get(tid) is None:
                    DB.__instances.update({tid: super(DB, cls).__new__(cls)})
                    DB.__instances.get(tid).__connection = mariadb.connect(host=DB_HOST, user=DB_USER, database=DB_NAME, autocommit=True) # autocommit = True -> https://stackoverflow.com/questions/9305669/mysql-python-connection-does-not-see-changes-to-database-made-on-another-connect
                                                                    
        return DB.__instances.get(tid)

    def close(self):
        self.__connection.close()

    def exec(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        cursor.close()

    def exec_and_get_last_id(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        id = cursor.lastrowid
        cursor.close()

        return id

    def query_one(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()

        return result

    def query_all(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()

        return result