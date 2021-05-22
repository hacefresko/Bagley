import sqlite3, requests
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

    def checkDomain(self, domain):
        return  True if self._query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    def insertDomain(self, domain):
        self._query('INSERT INTO domains (name) VALUES (?)', [domain])

    # Checks if path specified by element, parent and domain exists and returns id
    def checkPath(self, element, parent, domain):
        result = self._query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False
    
    # Inserts each path inside the URL in db and returns its id. If already inserted, returns None
    def insertPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        # Iterate over each domain/file from URL
        prevElem = ''
        for element in urlparse(url)[2].split('/'):
            path = self.checkPath(element, prevElem, domain)
            if not path:
                self._query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain])
            prevElem = path

        return prevElem if prevElem != '' else None

    def checkHeader(self, key, value):
        result = self._query('SELECT id FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        return result[0] if result else False

    # Inserts header into response
    def insertHeader(self, response, key, value):
        header = self.checkHeader(key, value)
        if not header:
            header = self._query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self._query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response, header])

    # Insert an object CookieJar into response
    def insertCookie(self, response, key, value):
        cookie_id = self._query('INSERT INTO cookies (key, value) VALUES (?,?)', [key, value]).lastrowid
        self._query('INSERT INTO response_cookies (response, cookie) VALUES (?,?)', [response, cookie_id])

    # Inserts a new response from url, with type (GET, POST, etc.),a dictionary of headers and strings for cookies and body
    def insertResponse(self, path, type, response):
        params = urlparse(response.url).query
        result = self._query('INSERT INTO responses (path, params, type, body) VALUES (?,?,?,?)', [path, params, type, response.text])
        response_id = result.lastrowid

        for key, value in response.headers.items():
            self.insertHeader(response_id, key, value)

        for key, value in response.cookies.get_dict().items():
            self.insertCookie(response_id, key, value)