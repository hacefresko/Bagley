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
        path = db.query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return Path(path[0], path[1], path[2]) if path else False

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

    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def getPath(id):
        db = DB.getConnection()
        path = db.query('SELECT id, element, parent, domain FROM paths WHERE id = ?', [id]).fetchone()
        return Path(path[0], path[1], path[2]) if path else False

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
            parent = path.parent

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
    def __init__(self, id, protocol, path_id, params, method, data):
        self.id = id
        self.protocol = protocol
        self.path = Path.getPath(path_id)
        self.params = params
        self.method = method
        self.data = data
        self.headers = Header.getHeaders(self)
        self.cookies = Cookie.getCookie(self)
    
class Response:
    def __init__(self, hash, mimeType, body):
        self.hash = hash
        self.mimeType = mimeType
        self.body = body
        self.headers = Header.getHeaders(self)
        self.scripts = Script.getScripts(self)

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
        db = DB.getConnection()
        # Format date and cookie so we don't save all dates and cookies (cookies will be saved apart)
        if key == 'Date' or key == 'Cookie':
            value = '1337'
        header = Header.getHeader(key, value)
        if not header:
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

    # Returns script or False if it does not exist   
    @staticmethod 
    def getCookie(name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority):
        if not Domain.checkDomain(cookie_domain):
            return False
        
        db = DB.getConnection()
        result = db.query('SELECT * FROM scripts WHERE name = ? AND value = ? AND domain = ? AND path = ? AND expires = ? AND size = ? AND httponly = ? AND secure = ? AND samesite = ? AND sameparty = ? AND priority = ?', [name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority]).fetchone()
        if not result:
            return False
        return Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9], result[10], result[11])

    # Returns a list of cookies from the specified request. If request is not a Request object, returns False
    @staticmethod 
    def getCookies(request):
        if not isinstance(request, Request):
            return False

        db = DB.getConnection()
        cookies = db.query('SELECT id, name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority FROM cookies INNER JOIN request_cookies on id = cookie WHERE request = ?', [request.id]).fetchall()

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9], cookie[10], cookie[11]))

        return result

    # Inserts cookie if not already inserted, links it to the corresponding request and returns the cookie
    @staticmethod
    def insertCookie(name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority, request):
        if not isinstance(request, Request):
            return False

        if not Domain.checkDomain(cookie_domain):
            return False

        db = DB.getConnection()
        cookie = Cookie.getCookie(name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority)
        if not cookie:
            id = db.query('INSERT INTO cookies (name, value, domain, path, expires, size, httponly, secure, samesite, sameparty, priority) VALUES (?,?,?,?,?,?,?,?,?,?,?, ?)', [name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority]).lastrowid
            cookie = Cookie(id, name, value, cookie_domain, cookie_path, expires, size, httponly, secure, samesite, sameparty, priority)
        db.query('INSERT INTO request_cookies (request, cookie) VALUES (?,?)', [request.id, cookie.id])

        return cookie 

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