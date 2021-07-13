import hashlib, json, time, pathlib
from urllib.parse import urlparse, urlunparse

import lib.config
from lib.database import DB

class Domain:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name

    # Returns the list of headers of the domain
    def __getHeaders(self):
        db = DB()
    
        headers = db.query('SELECT id, key, value FROM headers INNER JOIN domain_headers on id = header WHERE domain = ?', [self.id]).fetchall()

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the domain
    def __getCookies(self):
        db = DB()
    
        cookies = db.query('SELECT * FROM cookies INNER JOIN domain_cookies on id = cookie WHERE domain_cookies.domain = ?', [self.id]).fetchall()

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Returns domain identified by id or False if it does not exist
    @staticmethod
    def getDomainById(id):
        db = DB()
        domain = db.query('SELECT * FROM domains WHERE id = ?', [id]).fetchone()
        if not domain:
            return False
        return Domain(domain[0], domain[1])

    # Returns domain identified by the domain name or False if it does not exist
    @staticmethod
    def getDomain(domain_name):
        db = DB()
        domain = db.query('SELECT * FROM domains WHERE name = ?', [domain_name]).fetchone()
        if not domain:
            return False
        return Domain(domain[0], domain[1])

    # Yields domains or False if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getDomains():
        id = 1
        db = DB()
        while True:
            domain = db.query('SELECT * FROM domains WHERE id = ?', [id]).fetchone()
            if not domain:
                yield False
                continue
            id += 1
            yield Domain(domain[0], domain[1])

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

    # Returns True if domain exists in database (either inside or outside the scope)
    @staticmethod
    def checkDomain(domain):
        db = DB()
        return True if (db.query('SELECT name FROM domains WHERE name LIKE ?', [domain]).fetchone() or db.query('SELECT name FROM out_of_scope WHERE name LIKE ?', [domain]).fetchone()) else False

    # Returns True if domain is inside the scope, else False.
    @staticmethod
    def checkScope(domain):
        if not domain:
            return False

        db = DB()

        # Check if domain is out of scope
        if db.query('SELECT name FROM out_of_scope WHERE name LIKE ?', [domain]).fetchone():
            return False

        # Check if domain is in database (%domain so example.com is in scope in .example.com was specified)
        if db.query('SELECT name FROM domains WHERE name LIKE ?', ['%' + domain]).fetchone():
            return True
        
        # Check if parent domain is in a set of subdomains inside the database
        if len(domain.split('.')) > 2 and db.query('SELECT name FROM domains WHERE name LIKE ?', ['.' + '.'.join(domain.split('.')[-2:])]).fetchone():
            return True

        return False

    # Inserts domain if not already inserted
    @staticmethod
    def insertDomain(domain_name, headers, cookies):
        db = DB()
        if Domain.checkDomain(domain_name):
            return Domain.getDomain(domain_name)

        domain = Domain(db.query('INSERT INTO domains (name) VALUES (?)', [domain_name]).lastrowid, domain_name)
        
        headers = headers if headers else []
        cookies = cookies if cookies else []
        for element in headers + cookies:
            element.link(domain)
        
        return domain

    # Inserts an out of scope domain if not already inserted neither in scope nor out
    @staticmethod
    def insertOutOfScopeDomain(domain):
        db = DB()
        if not Domain.checkDomain(domain):
            db.query('INSERT INTO out_of_scope (name) VALUES (?)', [domain])

class Path:
    def __init__(self, id, element, parent, domain):
        self.id = id
        self.element = element
        self.parent = Path.getPath(parent)
        self.domain = Domain.getDomainById(domain)

    def __eq__(self, other):
        if not other:
            return False
        return self.id == other.id

    def __str__(self):  
        db = DB()
        result = ''
        element = self.element
        parent_id = self.parent.id if self.parent else 0

        while parent_id != 0:
            result = "/" + (element if element != '0' else '') + result
            element, parent_id = db.query('SELECT element, parent FROM paths WHERE id = ?', [parent_id]).fetchone()
        result = "/" + (element if element != '0' else '') + result
        result = str(self.domain) + result

        return result 

    # Returns path if path specified by element, parent and domain exists else False
    @staticmethod
    def __getPath(element, parent, domain):
        parent_id = parent.id if parent else False
        db = DB()
        path = db.query('SELECT * FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent_id, domain.id]).fetchone()
        return Path(path[0], path[1], path[2], path[3]) if path else False

    # Returns a dict with domain and a list elements with each element from the URL. URL must have protocol, domain and elements in order to get parsed correctly.
    @staticmethod
    def __parseURL(url):
        result = {}

        # Support for domains followed by path, without protocol
        if urlparse(url)[1] == '':
            url = 'http://' + url
        
        # Convert all pathless urls (i.e example.com) into urls with root dir (i.e example.com/)
        if urlparse(url)[2] == '':
            url += '/'

        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

        # Get domain
        result['domain'] = urlparse(url)[1]
        # Get elements after example.com/ and subsitute '' by False
        result['elements'] = [False if i=='' else i for i in urlparse(url)[2].split('/')[1:]]

        return result

    # Returns True if path is parent of current Object, else False
    def checkParent(self, path):
        if not isinstance(path, Path):
            return False
        if self.domain != path.domain:
            return False

        child = self
        if child.parent == path.parent:
            return True
        while child.parent:
            child = Path.getPath(child.parent.id)
            if child.parent == path.parent:
                return True

        return False
        
    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def getPath(id):
        db = DB()
        path = db.query('SELECT id, element, parent, domain FROM paths WHERE id = ?', [id]).fetchone()
        return Path(path[0], path[1], path[2], path[3]) if path else False

    # Yields paths corresponding to directories or False if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getDirectories():
        id = 1
        db = DB()
        while True:
            path = db.query('SELECT * FROM paths WHERE element = 0 AND id > ? LIMIT 1', [id]).fetchone()
            if not path:
                yield False
                continue
            id = path[0]
            yield Path(path[0], path[1], path[2], path[3])

    # Returns path corresponding to URL or False if it does not exist in the database
    @staticmethod
    def parseURL(url):
        parsedURL = Path.__parseURL(url)

        domain = Domain.getDomain(parsedURL['domain'])
        if not domain:
            return False

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(element, parent, domain)
            if not path:
                return False
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path

    # Inserts each path inside the URL if not already inserted and returns last inserted path (last element from URL).
    # If domain is not in scope, returns False. If domain is in scope but not in database, inserts it
    @staticmethod
    def insertPath(url, headers, cookies):
        db = DB()
        parsedURL = Path.__parseURL(url)

        if not Domain.checkScope(parsedURL['domain']):
            return False
        
        domain = Domain.insertDomain(parsedURL['domain'], headers, cookies)

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(element, parent, domain)
            if not path:
                path = Path.getPath(db.query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, parent.id if parent else False, domain.id]).lastrowid)
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path
        return False

class Request:
    def __init__(self, id, protocol, path_id, params, method, data, response_hash):
        self.id = id
        self.protocol = protocol
        self.path = Path.getPath(path_id)
        self.params = params if params != '0' else False
        self.method = method
        self.data = data if data != '0' else False
        self.response = Response.getResponse(response_hash)
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()

    def __str__(self):
        result = "%s %s HTTP/1.1\r\n" % (self.method, urlparse(self.protocol + '://' + str(self.path)).path)
        result += "Host: %s\r\n" % (self.path.domain.name)
        for header in self.headers:
            result += "%s\r\n" % (str(header))
        if len(self.cookies) != 0:
            result += "cookie: "
            for cookie in self.cookies:
                result +=  "%s; " % (str(cookie))
            result += "\r\n"

        if self.data:
            result += "\r\n%s\r\n" % (self.data)

        return result

    # Returns the list of headers of the request
    def __getHeaders(self):
        db = DB()
    
        headers = db.query('SELECT id, key, value FROM headers INNER JOIN request_headers on id = header WHERE request = ?', [self.id]).fetchall()

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the request
    def __getCookies(self):
        db = DB()
    
        cookies = db.query('SELECT * FROM cookies INNER JOIN request_cookies on id = cookie WHERE request = ?', [self.id]).fetchall()

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Parses params substituting all keys containing terms in blacklist by those terms. Returns False if params does not exist
    @staticmethod
    def __parseParams(params):
        if not params:
            return False
        new_params = params
        for word in lib.config.PARAMS_BLACKLIST:
            new_params = Utils.replaceURLencoded(new_params, word, word)
        return new_params

    # Tries to parse data substituting all keys containing terms in blacklist by those terms. Returns False if data does not exist
    @staticmethod
    def __parseData(content_type, data):
        if not data:
            return False
        new_data = data
        for word in lib.config.PARAMS_BLACKLIST:
            new_data = Utils.substitutePOSTData(content_type, new_data, word, word)
        return new_data

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

    # Returns True if request exists in database else False. If there are already some requests with the same path, protocol and method 
    # but different params/data with same key, it returns True to avoid saving same requests with different CSRFs, session values, etc.
    # If requested file extension belongs is in lib.config.EXTENSIONS_BLACKLIST, returns False
    @staticmethod
    def checkRequest(url, method, content_type, data):
        path = Path.parseURL(url)
        if not path:
            return False

        protocol = urlparse(url).scheme
        params = urlparse(url).query if urlparse(url).query else False
        data = data if (data is not None and data and method == 'POST') else False

        db = DB()
        if params or data:
            query = 'SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ?'
            query_params = [protocol, path.id, method]

            if params:
                query += ' AND params LIKE ?'
                query_params.append(Utils.replaceURLencoded(params, None, '%'))

            if data:
                query += ' AND data LIKE ?'
                query_params.append(Utils.substitutePOSTData(content_type, data, None, '%'))

            result = db.query(query, query_params).fetchall()

            if len(result) > 10:
                return True

        return True if db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND params = ? AND method = ? AND data = ?', [protocol, path.id, params, method, data]).fetchone() else False

    # Returns False if extension is in blacklist from config.py, else True   
    @staticmethod
    def checkExtension(url):
        return False if pathlib.Path(url.split('?')[0]).suffix in lib.config.EXTENSIONS_BLACKLIST else True
        
    # Returns request if exists else false
    @staticmethod
    def getRequest(url, method, content_type, data):
        path = Path.parseURL(url)
        if not path:
            return False
        protocol = urlparse(url).scheme
        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else False

        db = DB()
        request = db.query('SELECT * FROM requests WHERE protocol = ? AND path = ? AND params = ? AND method = ? AND data = ?', [protocol, path.id, params, method, data]).fetchone()
        if not request:
            return False
        return Request(request[0], request[1], request[2], request[3], request[4], request[5], request[6])

    # Yields requests or False if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getRequests():
        id = 1
        db = DB()
        while True:
            request = db.query('SELECT * FROM requests WHERE id = ?', [id]).fetchone()
            if not request:
                yield False
                continue
            id += 1
            yield Request(request[0], request[1], request[2], request[3], request[4], request[5], request[6])

    # Inserts request and links headers and cookies. If request is already inserted or there are too many requests 
    # to the same path and method but with different data/params values for the same keys, it returns false.
    # Path corresponding to url must already be inserted
    @staticmethod
    def insertRequest(url, method, headers, cookies, data):
        path = Path.parseURL(url)
        if not path:
            return False

        content_type = None
        for header in headers:
            if header.key == 'content-type':
                content_type = header.value

        if not Request.checkExtension(url) or Request.checkRequest(url, method, content_type, data):
            return False

        protocol = urlparse(url).scheme
        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else False

        db = DB()
        db.query('INSERT INTO requests (protocol, path, params, method, data) VALUES (?,?,?,?,?)', [protocol, path.id, params, method, data])
        request = Request.getRequest(url, method, content_type, data)

        for element in headers + cookies:
            element.link(request)

        # Gets again the request in order to update headers, cookies and data from databse
        return Request.getRequest(url, method, content_type, data)

    # Returns a list of requests whose params or data keys are the same as the request the function was called on
    def getSameKeysRequests(self):
        if not self.params and not self.data:
            return False

        requests = []
        query = 'SELECT * FROM requests WHERE protocol = ? AND path = ? AND method = ?'
        query_params = [self.protocol, self.path.id, self.method]
        if self.params:
            query += ' AND params LIKE ?'
            query_params.append(Utils.replaceURLencoded(self.params, None, '%'))
        if self.data:
            query += ' AND data LIKE ?'
            query_params.append(Utils.substitutePOSTData(self.getHeader('content-type'), self.data, None, '%'))

        db = DB()
        result = db.query(query, query_params).fetchall()

        for request in result:
            requests.append(Request(request[0], request[1], request[2], request[3], request[4], request[5], request[6]))
        return requests

class Response:
    def __init__(self, hash, code, body):
        self.hash = hash
        self.code = code
        self.body = body
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()
        self.scripts = self.__getScripts()

    # Returns response hash
    @staticmethod
    def __hashResponse(code, body, headers, cookies):
        to_hash = str(body) + str(code)
        for element in headers + cookies:
            to_hash += str(element)
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    # Returns the list of headers of the response
    def __getHeaders(self):
        db = DB()
    
        headers = db.query('SELECT id, key, value FROM headers INNER JOIN response_headers on id = header WHERE response = ?', [self.hash]).fetchall()

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the response
    def __getCookies(self):
        db = DB()
    
        cookies = db.query('SELECT * FROM cookies INNER JOIN response_cookies on id = cookie WHERE response = ?', [self.hash]).fetchall()

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Returns the list of scripts of the response
    def __getScripts(self):
        db = DB()
        scripts = db.query('SELECT hash, content, path FROM scripts INNER JOIN response_scripts on hash = script WHERE response = ?', [self.hash]).fetchall()

        result = []
        for script in scripts:
            result.append(Script(script[0], script[1], script[2]))

        return result

    # Returns True if response exists, else False
    @staticmethod
    def checkResponse(code, body, headers, cookies):
        if not body:
            body = False

        db = DB()
        return True if db.query('SELECT * FROM responses WHERE hash = ?', [Response.__hashResponse(code, body, headers, cookies)]).fetchone() else False
    
    # Returns response if exists, else False
    @staticmethod
    def getResponse(response_hash):
        db = DB()
        response = db.query('SELECT * FROM responses WHERE hash = ?', [response_hash]).fetchone()
        if not response:
            return False
        return Response(response[0], response[1], response[2])

    # Returns response hash if response succesfully inserted. Else, returns False. Also links header + cookies.
    @staticmethod
    def insertResponse(code, body, headers, cookies, request):
        if not isinstance(request, Request):
            return False
        if Response.checkResponse(code, body, headers, cookies):
            return False

        if not body:
            body = False

        response_hash = Response.__hashResponse(code, body, headers, cookies)

        db = DB()

        db.query('INSERT INTO responses (hash, code, content) VALUES (?,?,?)', [response_hash, code, body])
        db.query('UPDATE requests SET response = ? WHERE id = ?', [response_hash, request.id])

        response = Response.getResponse(response_hash)
        for element in headers + cookies:
            element.link(response)

        return Response.getResponse(response_hash)

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

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
    def __parseHeader(key, value):
        key = key.lower()
        if key in lib.config.HEADERS_BLACKLIST:
            value = '1337'
        return (key, value)

    # Returns header or False if it does not exist  
    @staticmethod
    def getHeader(key, value):
        key, value = Header.__parseHeader(key, value)
        db = DB()
        result = db.query('SELECT * FROM headers WHERE key = ? AND value = ?', [key, value]).fetchone()
        if not result:
            return False
        
        return Header(result[0], result[1], result[2])

    # Inserts header if not inserted and returns it
    @staticmethod
    def insertHeader(key, value):
        key, value = Header.__parseHeader(key, value)
        header = Header.getHeader(key, value)
        if not header:
            db = DB()
            id = db.query('INSERT INTO headers (key, value) VALUES (?,?)', [key, value]).lastrowid
            header = Header(id, key, value)
        return header

    # Links the header to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.query('INSERT INTO request_headers (request, header) VALUES (?,?)', [target.id, self.id])
            return True
        elif isinstance(target, Response):
            db.query('INSERT INTO response_headers (response, header) VALUES (?,?)', [target.hash, self.id])
            return True
        elif isinstance(target, Domain):
            db.query('INSERT INTO domain_headers(domain, header) VALUES (?,?)', [target.name, self.id])
        else:
            return False

class Cookie:
    def __init__(self, id, name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite):
        self.id = id
        self.name = name 
        self.domain = cookie_domain
        self.value = value
        self.path = cookie_path
        self.expires = expires
        self.maxage = maxage
        self.httponly = httponly
        self.secure = secure
        self.samesite = samesite

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name + '=' + self.value

    # Returns a formatted tupple with name and value
    @staticmethod
    def __parseCookie(name, value):
        name = name.lower()
        if name in lib.config.COOKIES_BLACKLIST:
            value = '1337'
        for term in lib.config.PARAMS_BLACKLIST:
            if term in name:
                value = term
        return (name, value)

    # Returns True if exists or False if it does not exist   
    @staticmethod 
    def __getCookie(name, value, cookie_domain, cookie_path):
        if cookie_domain and not Domain.checkScope(cookie_domain):
            return False
        
        db = DB()
        cookie = db.query('SELECT * FROM cookies WHERE name = ? AND value = ? AND domain = ? AND path = ?', [name, value, cookie_domain, cookie_path]).fetchone()
        if not cookie:
            return False
        return Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9])

    # Returns cookie if there is a cookie with name and value whose cookie_path and cookie_domain match with url, else False
    @staticmethod
    def getCookie(name, value, url):
        path = Path.parseURL(url)
        if not path:
            return False

        name, value = Cookie.__parseCookie(name, value)

        db = DB()
        results = db.query('SELECT * FROM cookies WHERE name = ? AND value = ?', [name, value]).fetchall()
        for result in results:
            cookie = Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9])
            # If domain/range of subdomains and range of paths  from cookie match with url
            cookie_path = Path.parseURL(path.domain.name + cookie.path) if cookie.path != '/' else Path.parseURL(path.domain.name)
            if Domain.compareDomains(cookie.domain, path.domain.name) and path.checkParent(cookie_path):
                return cookie
        return False

    # Inserts cookie if not already inserted and returns it
    @staticmethod
    def insertCookie(name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite):
        if not Domain.checkScope(cookie_domain):
            return False

        name, value = Cookie.__parseCookie(name, value)
        cookie = Cookie.__getCookie(name, value, cookie_domain, cookie_path)
        if not cookie:
            db = DB()
            id = db.query('INSERT INTO cookies (name, value, domain, path, expires, maxage, httponly, secure, samesite) VALUES (?,?,?,?,?,?,?,?,?)', [name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite]).lastrowid
            cookie = Cookie(id, name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite)
        return cookie

    # Links the cookie to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.query('INSERT INTO request_cookies (request, cookie) VALUES (?,?)', [target.id, self.id])
            return True
        elif isinstance(target, Response):
            db.query('INSERT INTO response_cookies (response, cookie) VALUES (?,?)', [target.hash, self.id])
            return True
        elif isinstance(target, Domain):
            db.query('INSERT INTO domain_cookies(domain, cookie) VALUES (?,?)', [target.name, self.id])
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
        return hashlib.sha1((str(url) + content).encode('utf-8')).hexdigest()

    # Returns script by url and content or False if it does not exist   
    @staticmethod 
    def getScript(url, content):
        db = DB()

        result = db.query('SELECT * FROM scripts WHERE hash = ?', [Script.__getHash(url, content)]).fetchone()
        if not result:
            return False
        return Script(result[0], result[1], result[2])

    # Inserts script if not already inserted, links it to the corresponding response if exists and returns it
    @staticmethod 
    def insertScript(url, headers, cookies, content, response):
        if not isinstance(response, Response):
            return False

        if url is not None:
            path = Path.insertPath(url, headers, cookies)
            # If path does not belong to the scope (stored domains)
            if not path:
                return False
            path = path.id
        else:
            path = False

        db = DB()
        script = Script.getScript(url, content)
        if not script:
            # Cannot use lastrowid since scripts table does not have INTEGER PRIMARY KEY but TEXT PRIMARY KEY (hash)
            db.query('INSERT INTO scripts (hash, path, content) VALUES (?,?,?)', [Script.__getHash(url, content), path, content])
            script = Script.getScript(url, content)
        db.query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response.hash, script.hash])

        return script

class Utils:
    @staticmethod
    def replaceURLencoded(data, match, newValue):
        if not data:
            return False
        new_data = ''
        for p in data.split('&'):
            if len(p.split('=')) == 1:
                return None
            elif match is None or match.lower() in p.split('=')[0].lower():
                new_data += p.split('=')[0]
                new_data += '=' + newValue + '&'
            else:
                new_data += p + '&'
        return new_data[:-1]

    @staticmethod
    def replaceJSON(data, match, newValue):
        for k,v in data.items():
            if isinstance(v, dict):
                data.update({k:Utils.replaceJSON(v, match, newValue)})
            else:
                if match is None or match.lower() in k.lower():
                    data.update({k:newValue})
        return data

    # Substitutes all values whose keys match with match parameter to newValue. If match is None, it will substitute all values.
    # It uses content_type header to know what type of POST data is, so it can be more precise
    # For multipart/form-data, it also substitutes the boundary since its value is usually random/partially random
    # If an exception occurs, a copy of the original data is returned
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type
    @staticmethod
    def substitutePOSTData(content_type, data, match, newValue):
        boundary_substitute = 'BOUNDARY'

        if not data:
            return False
        
        if not content_type:
            try:
                return json.dumps(Utils.replaceJSON(json.loads(data), match, newValue))
            except:
                return  Utils.replaceURLencoded(data, match, newValue)

        try:
            if 'multipart/form-data' in content_type:

                # If data has already been parsed so boundary has changed
                if '--'+boundary_substitute in data:
                    boundary = '--'+boundary_substitute
                else:
                    boundary = '--' + content_type.split('; ')[1].split('=')[1]

                new_data = '--'+boundary_substitute
                for fragment in data.split(boundary)[1:-1]:
                    name = fragment.split('\r\n')[1].split('; ')[1].split('=')[1].strip('"')
                    content = fragment.split('\r\n')[3]

                    try:
                        new_content = json.dumps(Utils.replaceJSON(json.loads(content), match, newValue))
                    except:
                        new_content = Utils.replaceURLencoded(content, match, newValue)
                    
                    if not new_content:
                        if match.lower() in name.lower() or match is None:
                            new_content = newValue
                        else:
                            new_content = content
                    
                    new_data += fragment.split('name="')[0] + 'name="' + name + '"; ' + "; ".join(fragment.split('\r\n')[1].split('; ')[2:]) + '\r\n\r\n' + new_content + '\r\n--'+boundary_substitute
                new_data += '--'

                return new_data

            elif 'application/json' in content_type:
                return json.dumps(Utils.replaceJSON(json.loads(data), match, newValue))

            elif 'application/x-www-form-urlencoded' in content_type:
                return Utils.replaceURLencoded(data, match, newValue)

        except Exception as e:
            return data