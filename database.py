import sqlite3, requests, json, hashlib
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

    # Checks if path specified by element, parent and domain exists and returns id or False if it doesn't
    def checkPath(self, element, parent, domain):
        result = self._query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False
    
    # Inserts each path inside the URL and returns id of the last one. If already inserted, returns False
    def insertPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        # Iterate over each domain/file from URL
        prevElem = False
        for element in urlparse(url)[2].split('/'):
            path = self.checkPath(element, prevElem, domain)
            if not path:
                path = self._query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain]).lastrowid
            prevElem = path

        return prevElem

    # Stringifies a path
    def stringifyPath(self, path):
        string = ''
        next_path = self._query('SELECT element, parent, domain FROM paths WHERE id = ?', [path]).fetchone()
        domain = next_path[2]
        while next_path[1] != 0:
            string = "/" + next_path[0] + string
            next_path = self._query('SELECT element, parent FROM paths WHERE id = ?', [next_path[1]]).fetchone()
        
        string = domain + string
        return string 

    # Checks if header exists and returns id or False if it does not exist  
    def checkHeader(self, key, value):
        result = self._query('SELECT id FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        return result[0] if result else False

    # Inserts header into response
    def insertHeader(self, response, key, value):
        header = self.checkHeader(key, value)
        if not header:
            header = self._query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self._query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response, header])
    
    def checkScript(self, script_hash):
        result = self._query('SELECT id FROM scripts WHERE hash = ?', [script_hash]).fetchone()
        return result[0] if result else False

    def insertScript(self, url, content, used_by):
        script_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
        script = self.checkScript(script_hash)

        if not script:
            script = self._query('INSERT INTO scripts (hash, url, content) VALUES (?,?,?)', [script_hash, url, content]).lastrowid
        self._query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [used_by, script])

    # Inserts a new response from path, with method (GET, POST, etc.) and POST data or None. Returns response id
    def insertResponse(self, path, method, response, data):
        params = urlparse(response.url).query
        cookies = json.dumps(response.cookies.get_dict())

        if method == 'POST' and data is not None:
            data = json.dumps(data)
        else:
            data = None

        response_id = self._query('INSERT INTO responses (path, params, method, cookies, data, body) VALUES (?,?,?,?,?,?)', [path, params, method, cookies, data, response.text]).lastrowid

        for key, value in response.headers.items():
            self.insertHeader(response_id, key, value)

        return response_id