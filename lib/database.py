import threading, mysql.connector

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
                    DB.__instances.get(tid).__connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, database=DB_NAME)
        return DB.__instances.get(tid)

    def reset_conn(self):
        self.__connection.close()
        self.__connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, database=DB_NAME)

    def close(self):
        self.__connection.close()

    def exec(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        cursor.close()

        with self.__lock:
            DB.__dirty = True

    def exec_and_get_last_id(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        id = cursor.lastrowid
        cursor.close()

        with self.__lock:
            DB.__dirty = True

        return id

    def query_one(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        
        if DB.__dirty:
            self.reset_conn()

        return result

    def query_all(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()

        if DB.__dirty:
            self.reset_conn()

        return result