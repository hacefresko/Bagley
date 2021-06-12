from database import DB
from urllib.parse import urlparse, urlunparse
import hashlib

class Domain:
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
    
    # Returns id of path if path specified by element, parent and domain exists else False
    @staticmethod
    def __getPath(element, parent, domain):
        db = DB.getConnection()
        result = db.query('SELECT * FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False

    # Returns a dict with domain and a list elements with each element from the URL. URL must have protocol, domain and elements in order to get parsed correctly.
    @staticmethod
    def __parseURL(url):
        result = {}
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

    # Returns path corresponding to URL or False if it does not exist
    @staticmethod
    def getPath(url):
        parsedURL = Path.__parseURL(url)

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(element, parent, parsedURL['domain'])
            if not path:
                return False
            if i == len(parsedURL['elements']) - 1:
                return Path(path, element, parent, parsedURL['domain'])
            parent = path

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
                path = db.query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, parent, parsedURL['domain']]).lastrowid
            if i == len(parsedURL['elements']) - 1:
                return Path(path, element, parent, parsedURL['domain'])
            parent = path

class Request:
    def __init__(self, id, protocol, path, params, method, data, response):
        self.id = id
        self.protocol = protocol
        self.path = path
        self.params = params
        self.method = method
        self.data = data
        self.response = response

class Response:
    def __init__(self, hash, mimeType, body):
        self.hash = hash
        self.mimeType = mimeType
        self.body = body

class Header:
    def __init__(self, id, key, value):
        self.id = id
        self.key = key
        self.value = value

    def __str__(self):
        return self.key + ": " + self.value

    # Returns header or False if it does not exist  
    @staticmethod
    def getHeader(key, value):
        db = DB.getConnection()
        # Format date and cookie so we don't save all dates and cookies (cookies will be saved apart)
        if key == 'Date' or key == 'Cookie':
            value = '1337'
        result = db.query('SELECT * FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        if not result:
            return False
        
        return Header(result[0], result[1], result[2])

    # Inserts header if not inserted and returns it
    @staticmethod
    def insertHeader(key, value):
        db = DB.getConnection()
        # Format date and cookie so we don't save all dates and cookies (cookies will be saved apart)
        if key == 'Date' or key == 'Cookie':
            value = '1337'
        header = Header.getHeader(key, value)
        if not header:
            id = db.query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
            header = Header(id, key, value)
        return header

    # Links the header to the specified request. If request is not a request, returns False
    def linkToRequest(self, request):
        if not isinstance(request, Request):
            return False
        db = DB.getConnection()
        db.query('INSERT INTO request_headers (request, header) VALUES (?,?)', [request.id, self.id])
        return True

    # Links the header to the specified response. If response is not a response, returns False
    def linkToResponse(self, response):
        if not isinstance(response, Response):
            return False
        db = DB.getConnection()
        db.query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response.hash, self.id])
        return True

class Cookie:
    def __init__(self, hash, name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority):
        self.hash = hash
        self.name = name 
        self.domain = path
        self.value = value
        self.path = path
        self.expires = expires
        self.size = size
        self.httponly = httponly
        self.secure = secure
        self.samesite = samesite
        self.sameparty = sameparty
        self.priority = priority

    # Returns hash of the cookie specified by all its attributes
    @staticmethod 
    def __getHash(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority):
        return hashlib.sha1((name + value + path + expires + str(size) + str(httponly) + str(secure) + samesite + sameparty + priority).encode('utf-8')).hexdigest()

    # Returns script or False if it does not exist   
    @staticmethod 
    def getCookie(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority):
        if not Domain.checkDomain(domain):
            return False
        
        db = DB.getConnection()
        result = db.query('SELECT * FROM scripts WHERE hash = ?', [Cookie.__getHash(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority)]).fetchone()
        if not result:
            return False
        return Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9], result[10], result[11])

    # Inserts cookie if not already inserted, links it to the corresponding request and returns the cookie
    @staticmethod
    def insertCookie(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority, request):
        if not isinstance(request, Request):
            return False

        if not Domain.checkDomain(domain):
            return False

        db = DB.getConnection()
        cookie = Cookie.getCookie(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority)
        if not cookie:
            db.query('INSERT INTO cookies (hash, name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority) VALUES (?,?,?,?,?,?,?,?,?,?,?, ?)', [Cookie.__getHash(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority),name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority])
            cookie = Cookie.getCookie(name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority)
        db.query('INSERT INTO request_cookies (request, cookie) VALUES (?,?)', [request.id, cookie.hash])

        return cookie 

class Script:
    def __init__(self, hash, content, path):
        self.hash = hash
        self.content = content
        self.path = path

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

    # Inserts script if not already inserted, links it to the corresponding response if exists and returns it
    @staticmethod 
    def insertScript(url, content, response):
        if not isinstance(response, Response):
            return False

        # If path does not belong to the scope (stored domains)
        if url is not None:
            path = Path.insertAllPaths(url)
            if not path:
                return False
            path = path.id
        else:
            path = False

        db = DB.getConnection()
        script = Script.getScript(url, content)
        if not script:
            # Cannot use lastrowid since scripts table does not have INTEGER PRIMARY KEY
            db.query('INSERT INTO scripts (hash, path, content) VALUES (?,?,?)', [Script.__getHash(url, content), path, content])
            script = Script.getScript(url, content)
        db.query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response.hash, script.hash])

        return script