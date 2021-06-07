import sqlite3, requests, hashlib
from urllib.parse import urlparse, urlunparse
import time

DB_NAME = 'vdt.db'

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
            self.__db = sqlite3.connect(DB_NAME)

    def query(self, query, params):
        cursor = self.__db.cursor()
        cursor.execute(query, params)
        self.__db.commit()
        return cursor

class VDT_DB:
    def connect(self):
        self.db = sqlite3.connect(DB_NAME)

    def close(self):
        self.db.close()

    def __query(self, query, params):
        cursor = self.db.cursor()
        cursor.execute(query, params)
        self.db.commit()
        return cursor

    def stringifyURL(self, protocol, path, params):
        result = ''
        next_path = self.__query('SELECT element, parent, domain FROM paths WHERE id = ?', [path]).fetchone()
        domain = next_path[2]
        while next_path[1] != 0:
            result = "/" + next_path[0] + result
            next_path = self.__query('SELECT element, parent FROM paths WHERE id = ?', [next_path[1]]).fetchone()
        
        result = domain + result
        result = protocol + "://" + result
        if params is not None and params != '0':
            result += '?' + params

        return result 

    def stringifyRequest(self, request_id):
        request = self.__query('SELECT * FROM requests WHERE id = ?', [request_id]).fetchone()
        if not request:
            return False

        headers = self.__query('SELECT key, value FROM headers INNER JOIN request_headers on id=header WHERE request = ?', [request_id]).fetchall()
        
        url = self.stringifyURL(request[1], request[2], request[3] if request[3] != '0' else None)
        domain = urlparse(url).netloc
        uri = urlparse(url).path if urlparse(url).path != '' else '/'
        if urlparse(url).query != '':
            uri += '?' + urlparse(url).query

        result = "%s %s HTTP/1.1\r\n" % (request[4], uri)
        result += "Host: %s\r\n" % (domain)
        for header in headers:
            result += "%s: %s\r\n" % (header[0], header[1])

        if request[5] != "0":
            result += "\r\n%s\r\n" % (request[5])

        return result

    # Returns True if domain exists, else False
    def checkDomain(self, domain):
        return True if self.__query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    # Inserts domain if not already inserted
    def insertDomain(self, domain):
        if not self.checkDomain(domain):
            self.__query('INSERT INTO domains (name) VALUES (?)', [domain])

    # Returns true if path specified by element, parent and domain exists else False
    def __checkPath(self, element, parent, domain):
        result = self.__query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False

    # Returns path corresponding to URL or False if it does not exist
    def __getPath(self, url):
        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

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
        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

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

    # Returns header id or False if it does not exist  
    def __getHeader(self, key, value):
        result = self.__query('SELECT id FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        return result[0] if result else False

    # Inserts header if not already inserted and links it to response
    def __insertResponseHeader(self, key, value, response):
        header = self.__getHeader(key, value)
        if not header:
            header = self.__query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self.__query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response, header])
    
    # Inserts header if not already inserted and links it to request
    def __insertRequestHeader(self, key, value, request):
        header = self.__getHeader(key, value)
        if not header:
            header = self.__query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
        self.__query('INSERT INTO request_headers (request, header) VALUES (?,?)', [request, header])

    # Get all keys from data
    def __getParamKeys(self, data):
        keys = []
        for parameter in data.split('&'):
                keys.append(parameter.split('=')[0])

        return keys

    # Subtitues all values of each param with newValue
    def __subtituteParamsValue(self, params, newValue):
        new_data = ''
        for p in params.split('&'):
            new_data += p.split('=')[0]
            new_data += '=' + newValue + '&'
        return new_data[:-1]

    # Returns True if request exists else False. If there are already some requests with the same path, protocol, method and response 
    # but different params/data, it returns True to avoid saving same requests with different CSRFs, session values, etc.
    def __checkRequest(self, protocol, path, params, method, data):
        if params or data:
            if params and data:
                result = self.__query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND params LIKE ? AND data LIKE ?', [protocol, path, method, self.__subtituteParamsValue(params, '%'), self.__subtituteParamsValue(data, '%')]).fetchall()
            elif data:
                result = self.__query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND data LIKE ?', [protocol, path, method, self.__subtituteParamsValue(data, '%')]).fetchall()
            elif params:
                result = self.__query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND params LIKE ?', [protocol, path, method, self.__subtituteParamsValue(params, '%')]).fetchall()

            if len(result) > 10:
                return True

        return True if self.__query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND params = ? AND method = ? AND data = ?', [protocol, path, params, method, data]).fetchone() else False

    # Returns true if request exists else False
    def checkRequest(self, url, method, data):
        data = data if (data is not None and method == 'POST') else False
        path = self.__getPath(url)
        if not path:
            return False
        protocol = urlparse(url).scheme
        params = urlparse(url).query if urlparse(url).query != '' else False

        return self.__checkRequest(protocol, path, params, method, data)

    # Inserts request. If already inserted or URL not in the database, returns False
    def insertRequest(self, url, method, data):
        path = self.insertPath(url)
        data = data if (data is not None and method == 'POST') else False
        params = urlparse(url).query if urlparse(url).query != '' else False
        protocol = urlparse(url).scheme

        if self.__checkRequest(protocol, path, params, method, data):
            return False

        return self.__query('INSERT INTO requests (protocol, path, params, method, data) VALUES (?,?,?,?,?)', [protocol, path, params, method, data]).lastrowid

    # Returns request dict with url, method and data of request id, else None
    def getRequest(self, id):
        request = self.__query('SELECT * FROM requests WHERE id = ?', [id]).fetchone()
        if not request:
            return None

        result = {}
        result['url'] = self.stringifyURL(request[1], request[2], request[3])
        result['method'] = request[4]
        result['data'] = request[5] if request[5] != '0' else None

        return result

    # Returns a list of request ids with the same keys inside params or data
    def getRequestWithSameKeys(self, id):
        result = []
        request = self.__query('SELECT * FROM requests WHERE id = ?', [id]).fetchone()
        if request:
            # For each request with same path, protocol and method, if it has same params or data keys, skip that request
            similar_requests = self.__query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ?', [request[1], request[2], request[4]]).fetchall()
            for similar_request in similar_requests:
                if self.__getParamKeys(request[3]) == self.__getParamKeys(similar_request[3]) and self.__getParamKeys(request[5]) == self.__getParamKeys(similar_request[5]):
                    result.append(similar_request[0])

        return result

    # Returns response hash
    def __hashResponse(self, response):
        to_hash = response.text + str(response.headers) + str(response.cookies.get_dict())
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    # Returns True if response exists, else False
    def checkResponse(self, response):
        return True if self.__query('SELECT * FROM responses WHERE hash = ?', [self.__hashResponse(response)]).fetchone() else False

    # Returns response hash if response succesfully inserted. Else, returns False. Also inserts response and request headers into the request.
    def insertResponse(self, response, request):
        if self.checkResponse(response):
            return False

        response_hash = self.__hashResponse(response)

        for key, value in response.headers.items():
            self.__insertResponseHeader(key, value, response_hash)

        for key, value in response.request.headers.items():
            self.__insertRequestHeader(key, value, request)

        cookies = str(response.cookies.get_dict()) if str(response.cookies.get_dict()) is not None else False

        self.__query('INSERT INTO responses (hash, content, cookies) VALUES (?,?,?)', [response_hash, response.text, cookies])
        self.__query('UPDATE requests SET response = ? WHERE id = ?', [response_hash, request])

        return response_hash

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