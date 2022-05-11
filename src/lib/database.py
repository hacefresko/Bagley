import threading, mariadb
from tabulate import tabulate
import config

#
# Singleton module to manage database access
#

class DB:
    __connectionPool = mariadb.ConnectionPool(
        host=config.DB_HOST, 
        user=config.DB_USER, 
        database=config.DB_NAME, 
        password=config.DB_PASSWORD, 
        autocommit=True,
        pool_name="bagley",
        pool_size=6 )


    __instances = {}

    def __new__(cls):
        tid = threading.get_ident()

        # If the thred hasn't called DB() yet
        if DB.__instances.get(tid) is None:

            # Create an instance of DB
            instance = super(DB, cls).__new__(cls)

            # Assign a connection to this instance
            instance.__connectin = DB.__connectionPool.get_connection()

            # Assign this instance to the thread calling DB()
            DB.__instances[tid] = instance

        return DB.__instances.get(tid)

    def close(self):
        self.__connection.close()

    def exec(self, query, params=()):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        cursor.close()

    def exec_and_get_last_id(self, query, params=()):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        id = cursor.lastrowid
        cursor.close()

        return id

    def query_one(self, query, params=()):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()

        return result

    def query_all(self, query, params=()):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()

        return result

    def query_string_like(self, query=()):
        cursor = self.__connection.cursor()
        cursor.execute(query, ())
        results = cursor.fetchall()
        headers = []
        for cd in cursor.description:
            headers.append(cd[0])

        cursor.close()

        string = tabulate(results, headers, tablefmt='psql')
        return string