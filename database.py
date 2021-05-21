import sqlite3
from urllib.parse import urlparse

class VDT_DB:
    def connect(self, db):
        self.db = sqlite3.connect(db)

    def __query(self, query, params):
        cursor = self.db.cursor()
        cursor.execute(query, params)
        self.db.commit()
        return cursor

    def close(self):
        self.db.close()

    # Checks if domain exists in db
    def checkDomain(self, domain):
        return  True if self.__query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    # Inserts the domain in db
    def insertDomain(self, domain):
        self.__query('INSERT INTO domains (name) VALUES (?)', [domain])

    # Checks if path exists in db
    def checkPath(self, element, domain, parent):
        return  True if self.__query('SELECT * FROM paths WHERE element = ? AND domain = ? AND parent = ?', [element, domain, parent]).fetchone() else False
    
    # Inserts each path inside the URL in db if not already inserted
    def insertPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        # Iterate over each domain/file from URL
        prevElem = None
        for element in urlparse(url)[2].split('/'):
            if not self.checkPath(element, domain, prevElem):
                self.__query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain])
            prevElem = element