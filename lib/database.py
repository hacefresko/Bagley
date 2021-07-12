import sqlite3, threading

DB_NAME = 'bagley.db'

def query_one(query, params):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    result = cursor.fetchone()
    connection.close()

    return result

def query_all(query, params):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    result = cursor.fetchall()
    connection.close()

    return result

def execute(query, params):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    connection.close()

def execute_and_get_id(query, params):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    result = cursor.lastrowid
    connection.close()

    return result