import sqlite3, requests, hashlib
from urllib.parse import urlparse

DB_NAME = 'vdt.db'

class VDT_DB:
    def connect(self):
        self.db = sqlite3.connect(DB_NAME)

    def __query(self, query, params):
        cursor = self.db.cursor()
        cursor.execute(query, params)
        self.db.commit()
        return cursor

    def close(self):
        self.db.close()

    def stringifyURL(self, protocol, path, params):
        result = ''
        next_path = self.__query('SELECT element, parent, domain FROM paths WHERE id = ?', [path]).fetchone()
        domain = next_path[2]
        while next_path[1] != 0:
            result = "/" + next_path[0] + result
            next_path = self.__query('SELECT element, parent FROM paths WHERE id = ?', [next_path[1]]).fetchone()
        
        result = domain + result

        result = protocol + "://" + result
        result += '?' + params

        return result 

    # Returns True if domain exists, else False
    def checkDomain(self, domain):
        return  True if self.__query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    def insertDomain(self, domain):
        self.__query('INSERT INTO domains (name) VALUES (?)', [domain])

    # Returns true if path specified by element, parent and domain exists else False
    def __checkPath(self, element, parent, domain):
        result = self.__query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False

    # Returns path corresponding to URL or False if it does not exist
    def __getPath(self, url):
        # Get domain
        domain = urlparse(url)[1]

        # Get last directory/file from URL
        element = urlparse(url)[2].split('/')[-1]

        prevElem = False
        for element in urlparse(url)[2].split('/'):
            path = self.__checkPath(element, prevElem, domain)
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
            path = self.__checkPath(element, prevElem, domain)
            if not path:
                path = self.__query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, prevElem, domain]).lastrowid
            prevElem = path

        return prevElem

    # Returns True if request exists else False
    def __checkRequest(self, path, params, method, data):
        return True if self.__query('SELECT * FROM requests WHERE path = ? AND params = ? AND method = ? AND data = ?', [path, params, method, data]).fetchone() else False

    # Returns true if request exists else False
    def checkRequest(self, url, method, data):
        path = self.__getPath(url)
        if not path:
            return False

        if data is None or method != 'POST':
            data = False
        else:
            data = str(data)

        params = urlparse(url).query if urlparse(url).query != '' else False

        return True if self.__query('SELECT id FROM requests WHERE path = ? AND params = ? AND method = ? AND data = ?', [path, params, method, data]).fetchone() else False

    # Inserts request. If already inserted or URL not in the database, returns False
    def insertRequest(self, url, method, data):
        path = self.insertPath(url)

        if data is None or method != 'POST':
            data = False
        else:
            data = str(data)

        params = urlparse(url).query if urlparse(url).query != '' else False

        if self.__checkRequest(path, params, method, data):
            return False

        return self.__query('INSERT INTO requests (path, params, method, data) VALUES (?,?,?,?)', [path, params, method, data]).lastrowid

    # Returns header id or False if it does not exist  
    def __getHeader(self, key, value):
        result = self.__query('SELECT id FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        return result[0] if result else False

    # Inserts header if not already inserted and links it to response
    def __insertHeader(self, key, value, response):
        header = self.__getHeader(key, value)
        if not header:
            header = self.__query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self.__query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response, header])
    
    # Returns script id or False if it does not exist    
    def __getScript(self, script_hash):
        result = self.__query('SELECT id FROM scripts WHERE hash = ?', [script_hash]).fetchone()
        return result[0] if result else False

    # Inserts script if not already inserted and links it to the corresponding response if exists
    def insertScript(self, url, content, response):
        script_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()

        url = url if url is not None else False

        script = self.__getScript(script_hash)

        if not script:
            script = self.__query('INSERT INTO scripts (hash, url, content) VALUES (?,?,?)', [script_hash, url, content]).lastrowid
        self.__query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response, script])

    # Returns response hash
    def __hashResponse(self, response):
        to_hash = response.text + str(response.headers) + str(response.cookies.get_dict())
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    # Returns True if response exists, else False
    def checkResponse(self, response):
        return True if self.__query('SELECT * FROM responses WHERE hash = ?', [self.__hashResponse(response)]).fetchone() else False

    # Returns response hash if response succesfully inserted. Else, returns False
    def insertResponse(self, response, request):
        if self.checkResponse(response):
            return False

        response_hash = self.__hashResponse(response)

        for key, value in response.headers.items():
            self.__insertHeader(key, value, response_hash)

        cookies = str(response.cookies.get_dict()) if str(response.cookies.get_dict()) is not None else False

        self.__query('INSERT INTO responses (hash, content, cookies) VALUES (?,?,?)', [response_hash, response.text, cookies])
        self.__query('UPDATE requests SET response = ? WHERE id = ?', [response_hash, request])

        return response_hash
