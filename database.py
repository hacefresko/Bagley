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

    def stringifyURL(self, protocol, path, params):
        result = ''
        next_path = self._query('SELECT element, parent, domain FROM paths WHERE id = ?', [path]).fetchone()
        domain = next_path[2]
        while next_path[1] != 0:
            result = "/" + next_path[0] + result
            next_path = self._query('SELECT element, parent FROM paths WHERE id = ?', [next_path[1]]).fetchone()
        
        result = domain + result

        result = protocol + "://" + result
        result += '?' + params

        return result 

    # Returns True if domain exists, else False
    def checkDomain(self, protocol, domain):
        return  True if self._query('SELECT name FROM domains WHERE protocl = ? AND name = ?', [protocol, domain]).fetchone() else False

    def insertDomain(self, protocol, domain):
        self._query('INSERT INTO domains (protocol, name) VALUES (?, ?)', [protocol, domain])

    # Returns true if path specified by element, parent and domain exists else False
    def _checkPath(self, element, parent, domain):
        result = self._query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False

    # Returns path corresponding to URL or False if it does not exist
    def _getPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        prevElem = False
        for element in urlparse(url)[2].split('/'):
            path = self._checkPath(element, prevElem, domain)
            if not path:
                return False
            prevElem = path

        return prevElem

    # Inserts each path inside the URL if not already inserted and returns id of the last one
    def insertPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        # Iterate over each domain/file from URL
        prevElem = False
        for element in urlparse(url)[2].split('/'):
            path = self._checkPath(element, prevElem, domain)
            if not path:
                path = self._query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain]).lastrowid
            prevElem = path

        return prevElem

    # Returns True if request exists else False
    def _checkRequest(self, path, params, method, data):
        return True if self._query('SELECT * FROM requests WHERE path = ? AND parmas = ? AND method = ? AND data = ?', [path, params, method, data]).fetchone() else False

    # Returns True if request exists else False
    def getRequest(self, url, method, data):
        path = self._getPath(url)
        if not path:
            return False

        params = urlparse(url).query
        return self._checkRequest(path, params, method, data)        

    # Inserts request. If already inserted or URL not in the database, returns False
    def insertRequest(self, url, method, data):
        path = self._getPath(url)
        if not path:
            return False

        params = urlparse(url).query
        if self._checkRequest(path, params, method, data):
            return False

        self._query('INSERT INTO requests (path, params, method, data) VALUES (?,?,?,?)', [path, params, method, data])

    # Checks if header exists and returns id or False if it does not exist  
    def _checkHeader(self, key, value):
        result = self._query('SELECT id FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        return result[0] if result else False

    # Inserts header if not already inserted and links it to response
    def _insertHeader(self, key, value, response):
        header = self._checkHeader(key, value)
        if not header:
            header = self._query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self._query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response, header])
    

    # Inserts script if not already inserted and links it to the corresponding response if exists
    def insertScript(self, url, content, response):
        script_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()

        if not self._query('SELECT id FROM scripts WHERE hash = ?', [script_hash]).fetchone():
            script = self._query('INSERT INTO scripts (hash, url, content) VALUES (?,?,?)', [script_hash, url, content]).lastrowid
        self._query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response, script])



    # Returns response hash
    def _hashResponse(self, response):
        to_hash = response.text + json.dumps(response.headers) + json.dumps(response.cookies.get_dict())
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    # Returns True if response exists, else False
    def checkResponse(self, response):
        return True if self._query('SELECT * FROM responses WHERE hash = ?', [self._hashResponse(response)]).fetchone() else False

    # Returns response hash if response succesfully inserted. Else, returns False
    def insertResponse(self, response, request):
        if self.checkResponse(response):
            return False

        response_hash = self._hashResponse(response)

        for key, value in response.headers.items():
            self._insertHeader(key, value, response_hash)

        self._query('INSERT INTO responses (hash, content, cookies) VALUES (?,?,?)', [response_hash, response.text, json.dumps(response.cookies.get_dict())])

        return response_hash

    # Checks if body exists and returns id or False
    def checkBody(self, body_hash):
        result = self._query('SELECT id FROM bodies WHERE hash = ?', [body_hash]).fetchone()
        return result[0] if result else False

    # Inserts body if not already inserted and links it to response
    def insertBody(self, content, response):
        body_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
        body = self.checkBody(body_hash)

        if not body:
            body = self._query('INSERT INTO bodies (hash, content) VALUES (?,?)', [body_hash, content]).lastrowid
        self._query('INSERT INTO response_bodies (response, body) VALUES (?,?)', [response, body])


    def insertResponse(self, path, method, response, data):
        params = urlparse(response.url).query
        cookies = json.dumps(response.cookies.get_dict())

        if method == 'POST' and data is not None:
            data = json.dumps(data)
        else:
            data = None

        response_id = self._query('INSERT INTO responses (path, params, method, cookies, data) VALUES (?,?,?,?,?)', [path, params, method, cookies, data]).lastrowid

        self.insertBody(response.text, response_id)

        for key, value in response.headers.items():
            self._insertHeader(key, value, response_id)

        return response_id

    def getResponse(self, response_id):
        return self._query('SELECT r.path FROM responses r WHERE id = ?', [response_id]).fetchone()