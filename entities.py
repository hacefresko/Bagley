from database import DB
from urllib.parse import urlparse, urlunparse
import hashlib, json

class Domain:
    # Returns True if both domains are equal or if one belongs to a range of subdomains of other, else False
    @staticmethod
    def compareDomains(first, second):
        if first == second:
            return True
        elif first[0] == '.' and second[0] == '.':
            return True if first in second or second in first else False
        elif first[0] == '.':
            return True if first in second or first[1:] == second else False
        elif second[0] == '.':
            return True if second in first or second[1:] == first else False
        else:
            return False

    # Returns True if domain or subdomains exist, else False
    @staticmethod
    def checkDomain(domain):
        db = DB.getConnection()
        # If a group of subdomains is specified like .example.com
        if domain[0] == '.':
            return True if db.query('SELECT name FROM domains WHERE name = ? OR name LIKE ?', [domain[1:], '%' + domain]).fetchone() else False
        else:
            return True if db.query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    # Inserts domain if not already inserted
    @staticmethod
    def insertDomain(domain):
        db = DB.getConnection()
        if not Domain.checkDomain(domain):
            db.query('INSERT INTO domains (name) VALUES (?)', [domain])

class Path:
    def __init__(self, id, element, parent, domain):
        self.id = id
        self.element = element
        self.parent = parent
        self.domain = domain

    def __str__(self):  
        db = DB.getConnection()
        result = ''
        path = [self.element if self.element else '', self.parent]

        while path[1]:
            result = "/" + path[0] + result
            path = db.query('SELECT element, parent FROM paths WHERE id = ?', [path[1]]).fetchone()

        result = self.domain + result

        return result 
    
     # Returns path if path specified by id exists else False

    # Returns path if path specified by element, parent and domain exists else False
    @staticmethod
    def __getPath(element, parent, domain):
        db = DB.getConnection()
        path = db.query('SELECT * FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return Path(path[0], path[1], path[2], path[3]) if path else False

    # Returns a dict with domain and a list elements with each element from the URL. URL must have protocol, domain and elements in order to get parsed correctly.
    @staticmethod
    def __parseURL(url):
        result = {}

        # Support for domains followed by path, without protocol
        if urlparse(url)[1] == '':
            url = 'http://' + url

        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

        # Get domain
        result['domain'] = urlparse(url)[1]
        # Get elements and subsitute '' by False
        result['elements'] = [False if i=='' else i for i in urlparse(url)[2].split('/')]

        return result

    # Returns True if path is parent of current Object, else False
    def checkParent(self, path):
        if not isinstance(path, Path):
            return False
        if self.domain != path.domain:
            return False

        child = self
        while child.parent != '0':
            if child.element == path.element:
                return True
            child = Path.getPath(child.parent)
        return False
        
    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def getPath(id):
        db = DB.getConnection()
        path = db.query('SELECT id, element, parent, domain FROM paths WHERE id = ?', [id]).fetchone()
        return Path(path[0], path[1], path[2], path[3]) if path else False

    # Returns path corresponding to URL or False if it does not exist
    @staticmethod
    def parseURL(url):
        parsedURL = Path.__parseURL(url)

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(element, parent, parsedURL['domain'])
            if not path:
                return False
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path.id

    # Inserts each path inside the URL if not already inserted and returns last inserted path (last element from URL). If domain doesn't exist, return False
    @staticmethod
    def insertAllPaths(url):
        db = DB.getConnection()
        parsedURL = Path.__parseURL(url)

        if not Domain.checkDomain(parsedURL['domain']):
            return False

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(element, parent, parsedURL['domain'])
            if not path:
                path = Path.getPath(db.query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, parent, parsedURL['domain']]).lastrowid)
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path.id

class Request:
    def __init__(self, id, protocol, path_id, params, method, data):
        self.id = id
        self.protocol = protocol
        self.path = Path.getPath(path_id)
        self.params = params
        self.method = method
        self.data = data
        self.headers = Header.getHeaders(self)
        self.cookies = Cookie.getCookies(self)
        self.response = Response.getResponse(self)

    # Substitute all values by newValue inside data. Admits json and text url formats
    @staticmethod
    def __substituteParamsValue(data, newValue):
        def replace(json_data, newValue):
            for k,v in json_data.items():
                if isinstance(v, dict):
                    json_data.update({k:replace(v, newValue)})
                else:
                    json_data.update({k:newValue})
            return json_data


        new_data = ''
        try:
            new_data = json.dumps(replace(json.loads(data), newValue))
        except:
            for p in data.split('&'):
                new_data += p.split('=')[0]
                new_data += '=' + newValue + '&'
            new_data = new_data[:-1]
        finally:
            return new_data

    # Returns True if request exists else False. If there are already some requests with the same path, protocol and method 
    # but different params/data, it returns True to avoid saving same requests with different CSRFs, session values, etc.
    @staticmethod
    def checkRequest(url, method, data):
        path = Path.parseURL(url)
        if not path:
            return False
        protocol = urlparse(url).scheme
        params = urlparse(url).query if urlparse(url).query != '' else False
        data = data if (data is not None and method == 'POST') else False

        db = DB.getConnection()

        if params or data:
            if params and data:
                result = db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND params LIKE ? AND data LIKE ?', [protocol, path, method, Request.__substituteParamsValue(params, '%'), Request.__substituteParamsValue(data, '%')]).fetchall()
            elif data:
                result = db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND data LIKE ?', [protocol, path, method, Request.__substituteParamsValue(data, '%')]).fetchall()
            elif params:
                result = db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ? AND params LIKE ?', [protocol, path, method, Request.__substituteParamsValue(params, '%')]).fetchall()

            if len(result) > 10:
                return True

        return True if db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND params = ? AND method = ? AND data = ?', [protocol, path, params, method, data]).fetchone() else False

    # Returns request if exists else false
    @staticmethod
    def getRequest(url, method, data):
        path = Path.parseURL(url)
        if not path:
            return False
        protocol = urlparse(url).scheme
        params = urlparse(url).query if urlparse(url).query != '' else False
        data = data if (data is not None and method == 'POST') else False

        db = DB.getConnection()
        request = db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND params = ? AND method = ? AND data = ?', [protocol, path.id, params, method, data]).fetchone()
        if not request:
            return False
        return Request(request[0], request[1], request[2], request[3], request[4], request[5])

    # Inserts path and request and links headers and cookies. If there are too many requests with different data/params, it returns false.
    @staticmethod
    def insertRequest(url, method, headers, cookies, data):
        if Request.checkRequest(url, method, data):
            return False
        path = Path.insertAllPaths(url)
        if not path:
            return False

        protocol = urlparse(url).scheme
        params = urlparse(url).query if urlparse(url).query != '' else False
        data = data if (data is not None and method == 'POST') else False

        db = DB.getConnection()
        db.query('INSERT INTO requests (protocol, path, params, method, data) VALUES (?,?,?,?, ?)', [protocol, path.id, params, method, data])
        request = Request.getRequest(url, method, data)

        for element in headers + cookies:
            element.link(request)

        # Gets again the request in order to update headers, cookies and data from databse
        return Request.getRequest(url, method, data)

class Response:
    def __init__(self, hash, code, mimeType, body):
        self.hash = hash
        self.code = code
        self.mimeType = mimeType
        self.body = body
        self.headers = Header.getHeaders(self)
        self.cookies = Cookie.getCookies(self)
        self.scripts = Script.getScripts(self)

    # Returns response hash
    @staticmethod
    def __hashResponse(code, mimetype, body, headers, cookies):
        to_hash = mimetype + body + str(code)
        for element in headers + cookies:
            to_hash += str(element)
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    # Returns True if response exists, else False
    @staticmethod
    def checkResponse(code, mimetype, body, headers, cookies):
        if not body:
            body = False

        db = DB.getConnection()
        return True if db.query('SELECT * FROM responses WHERE hash = ?', [Response.__hashResponse(code, mimetype, body, headers, cookies)]).fetchone() else False
    
    # Returns response if exists, else False
    @staticmethod
    def getResponse(response_hash):
        db = DB.getConnection()
        response = db.query('SELECT * FROM responses WHERE hash = ?', [response_hash]).fetchone()
        if not response:
            return False
        return Response(response[0], response[1], response[2], response[3])

    # Returns response hash if response succesfully inserted. Else, returns False. Also links header + cookies.
    @staticmethod
    def insertResponse(code, mimetype, body, headers, cookies, request):
        if not isinstance(request, Request):
            return False
        if Response.checkResponse(code, mimetype, body, headers, cookies):
            return False

        if not body:
            body = False

        response_hash = Response.__hashResponse(code, mimetype, body, headers, cookies)

        db = DB.getConnection()

        db.query('INSERT INTO responses (hash, code, mimetype, content) VALUES (?,?,?,?)', [response_hash, code, mimetype, body])
        db.query('UPDATE requests SET response = ? WHERE id = ?', [response_hash, request.id])

        response = Response.getResponse(response_hash)
        for element in headers + cookies:
            element.link(response)

        return Response.getResponse(response_hash)

class Header:
    def __init__(self, id, key, value):
        self.id = id
        self.key = key
        self.value = value

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.key + ": " + self.value

    # Returns a formatted tupple with key and value
    @staticmethod
    def parseHeader(key, value):
        key = key.lower()
        # Format date and cookie so we don't save all dates and cookies (cookies will be saved apart)
        if key == 'date' or key == 'cookie' or key == 'set-cookie':
            value = '1337'
        return (key, value)

    # Returns header or False if it does not exist  
    @staticmethod
    def getHeader(key, value):
        key, value = Header.parseHeader(key, value)
        db = DB.getConnection()
        result = db.query('SELECT * FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        if not result:
            return False
        
        return Header(result[0], result[1], result[2])

    # Returns a list of headers for specified target. If target is not a request nor a response, returns False
    @staticmethod
    def getHeaders(target):
        db = DB.getConnection()
    
        if isinstance(target, Request):
            headers = db.query('SELECT id, key, value FROM headers INNER JOIN request_headers on id = header WHERE request = ?', [target.id]).fetchall()
        elif isinstance(target, Response):
            headers = db.query('SELECT id, key, value FROM headers INNER JOIN response_headers on id = header WHERE response = ?', [target.hash]).fetchall()
        else:
            return False

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Inserts header if not inserted and returns it
    @staticmethod
    def insertHeader(key, value):
        key, value = Header.parseHeader(key, value)
        header = Header.getHeader(key, value)
        if not header:
            db = DB.getConnection()
            id = db.query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
            header = Header(id, key, value)
        return header

    # Links the header to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB.getConnection()

        if isinstance(target, Request):
            db.query('INSERT INTO request_headers (request, header) VALUES (?,?)', [target.id, self.id])
            return True
        elif isinstance(target, Response):
            db.query('INSERT INTO response_headers (response, header) VALUES (?,?)', [target.hash, self.id])
            return True
        else:
            return False

class Cookie:
    def __init__(self, id, name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority):
        self.id = id
        self.name = name 
        self.domain = cookie_domain
        self.value = value
        self.path = cookie_path
        self.expires = expires
        self.size = size
        self.httponly = httponly
        self.secure = secure
        self.samesite = samesite
        self.sameparty = sameparty
        self.priority = priority

    def __eq__(self, other):
        return self.id == other.id

    # Returns cookie if there is a cookie with name and value whose cookie_path and cookie_domain match with url, else False
    @staticmethod
    def getCookie(name, value, url):
        path = Path.parseURL(url)
        if not path:
            return False

        db = DB.getConnection()
        results = db.query('SELECT * FROM cookies WHERE name = ? AND value = ?', [name, value]).fetchall()
        for result in results:
            cookie = Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9], result[10], result[11])
            # If domain/range of subdomains and range of paths  from cookie match with url
            cookie_path = Path.parseURL(path.domain + cookie.path) if cookie.path != '/' else Path.parseURL(path.domain)
            if Domain.compareDomains(cookie.domain, path.domain) and path.checkParent(cookie_path):
                return cookie
        return False

    # Returns True if exists or False if it does not exist   
    @staticmethod 
    def checkCookie(name, value, cookie_domain, cookie_path):
        if not Domain.checkDomain(cookie_domain):
            return False
        
        db = DB.getConnection()
        return True if db.query('SELECT * FROM cookies WHERE name = ? AND value = ? AND domain = ? AND path = ?', [name, value, cookie_domain, cookie_path]).fetchone() else False

    # Returns a list of cookies for specified target. If target is not a request nor a response, returns False
    @staticmethod 
    def getCookies(target):
        db = DB.getConnection()
    
        if isinstance(target, Request):
            cookies = db.query('SELECT id, name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority FROM cookies INNER JOIN request_cookies on id = cookie WHERE request = ?', [target.id]).fetchall()
        elif isinstance(target, Response):
            cookies = db.query('SELECT id, name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority FROM cookies INNER JOIN response_cookies on id = cookie WHERE response = ?', [target.id]).fetchall()
        else:
            return False

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9], cookie[10], cookie[11]))

        return result

    # Inserts cookie if not already inserted, returns it
    @staticmethod
    def insertCookie(name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority):
        if not Domain.checkDomain(cookie_domain):
            return False

        db = DB.getConnection()
        cookie = Cookie.checkCookie(name, value, cookie_domain, cookie_path)
        if cookie:
            return False
        
        id = db.query('INSERT INTO cookies (name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority) VALUES (?,?,?,?,?,?,?,?,?,?,?)', [name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority]).lastrowid
        return Cookie(id, name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority)

    # Links the cookie to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB.getConnection()

        if isinstance(target, Request):
            db.query('INSERT INTO request_cookies (request, cookie) VALUES (?,?)', [target.id, self.id])
            return True
        elif isinstance(target, Response):
            db.query('INSERT INTO response_cookies (response, cookie) VALUES (?,?)', [target.hash, self.id])
            return True
        else:
            return False

class Script:
    def __init__(self, hash, content, path_id):
        self.hash = hash
        self.content = content
        self.path = Path.getPath(path_id)

    # Returns hash of the script specified by url and content
    @staticmethod 
    def __getHash(url, content):
        return hashlib.sha1((url + content).encode('utf-8')).hexdigest()

    # Returns script by url and content or False if it does not exist   
    @staticmethod 
    def getScript(url, content):
        db = DB.getConnection()

        result = db.query('SELECT * FROM scripts WHERE hash = ?', [Script.__getHash(url, content)]).fetchone()
        if not result:
            return False
        return Script(result[0], result[1], result[2])

    # Returns a list of scripts from the specified response. If response is not a Response object, returns False   
    @staticmethod 
    def getScripts(response):
        if not isinstance(response, Response):
            return False

        db = DB.getConnection()
        scripts = db.query('SELECT hash, content, path FROM scripts INNER JOIN response_scripts on hash = script WHERE response = ?', [response.hash]).fetchall()

        result = []
        for script in scripts:
            result.append(Script(script[0], script[1], script[2]))

        return result

    # Inserts script if not already inserted, links it to the corresponding response if exists and returns it
    @staticmethod 
    def insertScript(url, content, response):
        if not isinstance(response, Response):
            return False

        if url is not None:
            path = Path.insertAllPaths(url)
            # If path does not belong to the scope (stored domains)
            if not path:
                return False
            path = path.id
        else:
            path = False

        db = DB.getConnection()
        script = Script.getScript(url, content)
        if not script:
            # Cannot use lastrowid since scripts table does not have INTEGER PRIMARY KEY but TEXT PRIMARY KEY (hash)
            db.query('INSERT INTO scripts (hash, path, content) VALUES (?,?,?)', [Script.__getHash(url, content), path, content])
            script = Script.getScript(url, content)
        db.query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response.hash, script.hash])

        return script