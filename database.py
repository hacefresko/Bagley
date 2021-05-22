import sqlite3
from urllib.parse import urlparse

DB_NAME = 'vdt.db'

class VDT_DB:
    def connect(self):
        self.db = sqlite3.connect(DB_NAME)

    def _query(self, query, params):
        cursor = self.db.cursor()
        cursor.execute(query, params)
        self.db.commit()
        return cursor

    def close(self):
        self.db.close()

    # Checks if domain exists in db
    def checkDomain(self, domain):
        return  True if self._query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    # Inserts the domain in db
    def insertDomain(self, domain):
        self._query('INSERT INTO domains (name) VALUES (?)', [domain])

    # Checks if path exists in db
    def checkPath(self, element, parent, domain):
        return  True if self._query('SELECT * FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone() else False
    
    # Inserts each path inside the URL in db if not already inserted
    def insertPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        # Iterate over each domain/file from URL
        prevElem = ''
        for element in urlparse(url)[2].split('/'):
            if not self.checkPath(element, prevElem, domain):
                self._query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain])
            prevElem = element