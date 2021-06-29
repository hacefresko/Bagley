import sqlite3, requests, hashlib, time
from urllib.parse import urlparse, urlunparse

DB_NAME = 'bagley.db'

class DB:
    __db = None

    @staticmethod
    def getConnection():
        if DB.__db is None:
            DB()
        return DB().__db

    def __init__(self):
        if self.__db is not None:
            raise Exception("DB is a singleton")
        else:
            self.__connection = sqlite3.connect(DB_NAME)
            self.__db = self

    def query(self, query, params):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        return cursor