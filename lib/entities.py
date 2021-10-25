import hashlib, json, time, pathlib, socket
from urllib.parse import urlparse, urlunparse

import config
from .database import DB

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
    
        headers = db.query_all('SELECT * FROM headers INNER JOIN domain_headers on id = header WHERE domain = %d', (self.id,))

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the domain
    def __getCookies(self):
        db = DB()
    
        cookies = db.query_all('SELECT * FROM cookies INNER JOIN domain_cookies on id = cookie WHERE domain_cookies.domain = %d', (self.id,))

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Returns string containing the tree structure of all paths in the domain
    def getStructure(self):
        db = DB()

        # Lats indicates if the current element is the last children to draw the tree
        def recursion(path, last, tabs):
            string = tabs + '+---' + path.element + '\n'

            results = db.query_all('SELECT * FROM paths WHERE parent = %d and element is not Null', (path.id,))
            for i, result in enumerate(results):
                child = Path(result[0], result[1], result[2], result[3])
                if i != len(results)-1:
                    nextLast = False
                else:
                    nextLast = True
                if last:
                    newTabs = tabs + '    '
                else:
                    newTabs = tabs + '|   '
                string += recursion(child, nextLast, newTabs)

            return string

        string = "+" + "-"*len(self.name) + "+\n"
        string += "|" + self.name + "|\n"
        string += "+" + "-"*len(self.name) + "+\n"
        string += "|\n"

        results = db.query_all('SELECT * FROM paths WHERE parent is Null and element is not Null AND domain = %d', (self.id,))
        for i, result in enumerate(results):
            child = Path(result[0], result[1], result[2], result[3])
            if i != len(results)-1:
                string += recursion(child, False, '')
            else:
                string += recursion(child, True, '')

        return string

    # Returns domain identified by id or None if it does not exist
    @staticmethod
    def getDomainById(id):
        db = DB()
        domain = db.query_one('SELECT * FROM domains WHERE id = %d', (id,))
        if not domain:
            return None
        return Domain(domain[0], domain[1])

    # Returns domain identified by the domain name or None if it does not exist
    @staticmethod
    def getDomain(domain_name):
        db = DB()
        domain = db.query_one('SELECT * FROM domains WHERE name = %s', (domain_name,))
        if not domain:
            return None
        return Domain(domain[0], domain[1])

    # Yields domains or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getDomains():
        id = 1
        db = DB()
        while True:
            domain = db.query_one('SELECT * FROM domains WHERE id = %d', (id,))
            if not domain:
                yield None
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
        return True if (db.query_one('SELECT name FROM domains WHERE name LIKE %s', (domain,)) or db.query_one('SELECT name FROM out_of_scope WHERE name LIKE %s', (domain,))) else False

    # Returns True if domain is inside the scope, else False. strict parameter indicates if port must be checked or not.
    # i.e if strict = False, then 127.0.0.1 == 127.0.0.1:5000
    @staticmethod
    def checkScope(domain, strict=True):
        if not domain:
            return False

        if not strict:
            domain = domain.split(':')[0]
            # Check if domain exists in database with any specified port
            if Domain.checkScope(domain + ':%'):
                return True

        db = DB()

        # Check if domain is out of scope
        if db.query_one('SELECT name FROM out_of_scope WHERE name LIKE %s', (domain,)):
            return False

        # If domain is an IP
        if Utils.isIP(domain.split(':')[0]) and db.query_one('SELECT name FROM domains WHERE name LIKE %s', (domain,)):
            return True
        # If it is a domain name
        else:
            # Check if any domain fits in the group of subdomains
            if domain[0] == '.' and db.query_one('SELECT name FROM domains WHERE name LIKE %s', ("%"+domain,)):
                return True

            # Construct array with starting and interspersed dots i.e example.com => ['.','example','.','com']
            parts = domain.split('.')
            dot_interspersed_parts = (['.']*(2*len(parts)-1))
            dot_interspersed_parts[::2] = parts
            if dot_interspersed_parts[0] == '':
                dot_interspersed_parts = dot_interspersed_parts[1:]
            elif dot_interspersed_parts[0] != '.':
                dot_interspersed_parts.insert(0, '.')

            for i in range(len(dot_interspersed_parts)):
                check = ''.join(dot_interspersed_parts[i:])
                if db.query_one('SELECT name FROM out_of_scope WHERE name LIKE %s', (check,)):
                    return False
                if db.query_one('SELECT name FROM domains WHERE name LIKE %s', (check,)):
                    return True
        return False

    # Inserts domain if not already inserted
    @staticmethod
    def insertDomain(domain_name):
        db = DB()
        if Domain.checkDomain(domain_name):
            return Domain.getDomain(domain_name)

        domain = Domain(db.exec_and_get_last_id('INSERT INTO domains (name) VALUES (%s)', (domain_name,)), domain_name)
        
        return domain

    # Links cookie or header (element) to domain
    def add(self, element):
        element.link(self)

    # Inserts an out of scope domain if not already inserted neither in scope nor out
    @staticmethod
    def insertOutOfScopeDomain(domain):
        db = DB()
        if not Domain.checkDomain(domain):
            db.exec('INSERT INTO out_of_scope (name) VALUES (%s)', (domain,))

class Path:
    def __init__(self, id, protocol, element, parent, domain):
        self.id = id
        self.protocol = protocol
        self.element = element
        self.parent = Path.getPath(parent)
        self.domain = Domain.getDomainById(domain)
        self.technologies = self.__getTechs()

    def __eq__(self, other):
        if not other:
            return False
        return self.id == other.id

    def __str__(self):  
        db = DB()
        result = ''
        element = self.element
        parent_id = self.parent.id if self.parent else None

        while parent_id:
            result = "/" + (element if element else '') + result
            element, parent_id = db.query_one('SELECT element, parent FROM paths WHERE id = %d', (parent_id,))
        result = "/" + (element if element else '') + result
        result = self.protocol + '://' + str(self.domain) + result

        return result 

    # Returns the list of technologies of the
    def __getTechs(self):
        db = DB()
    
        techs = db.query_all('SELECT * FROM technologies INNER JOIN path_technologies on technologies.id = tech WHERE path = %d', (self.id,))

        result = []
        for tech in techs:
            result.append(Technology(tech[0], tech[1], tech[2]))

        return result

    # Returns path if path specified by protocol, element, parent and domain exists else None
    @staticmethod
    def __getPath(protocol, element, parent, domain):
        db = DB()

        query = 'SELECT * FROM paths WHERE protocol = %s AND domain = %s '
        query_params = [protocol, domain.id]

        if element:
            query += 'AND element = %s '
            query_params.append(element)
        else:
            query += 'AND element is Null '

        if parent:
            query += 'AND parent = %d '
            query_params.append(parent.id)
        else:
            query += 'AND parent is Null '

        path = db.query_one(query, tuple(query_params))
        
        return Path(path[0], path[1], path[2], path[3], path[4]) if path else None

    # Returns a dict with protocol, domain and a list elements with each element from the URL. URL must have protocol, domain and elements in order to get parsed correctly.
    @staticmethod
    def __parseURL(url):
        result = {}
        
        # Convert all pathless urls (i.e example.com) into urls with root dir (i.e example.com/)
        if urlparse(url)[2] == '':
            url += '/'

        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

        # Get protocol
        result['protocol'] = urlparse(url).scheme
        # Get domain
        result['domain'] = urlparse(url).netloc
        # Get elements after http://example.com/ and subsitute '' by None
        result['elements'] = [None if i=='' else i for i in urlparse(url).path.split('/')[1:]]

        return result

    # Returns True if path is parent of current Object, else False
    def checkParent(self, path):
        if not isinstance(path, Path):
            return False
        if self.domain != path.domain:
            return False
        if self.protocol != path.protocol:
            return False

        child = self
        if child.parent == path.parent:
            return True
        while child.parent:
            child = Path.getPath(child.parent.id)
            if child and child.parent == path.parent:
                return True

        return False   

    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def getPath(id):
        db = DB()
        path = db.query_one('SELECT id, protocol, element, parent, domain FROM paths WHERE id = %d', (id,))
        return Path(path[0], path[1], path[2], path[3], path[4]) if path else None

    # Yields paths
    @staticmethod
    def getPaths():
        id = 0
        db = DB()
        while True:
            path = db.query_one('SELECT * FROM paths WHERE id > %d LIMIT 1', (id,))
            if not path:
                yield None
                continue
            id = path[0]
            yield Path(path[0], path[1], path[2], path[3], path[4])

    # Yields paths corresponding to directories or False if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getDirectories():
        id = 0
        db = DB()
        while True:
            path = db.query_one('SELECT * FROM paths WHERE element is Null AND id > %d LIMIT 1', (id,))
            if not path:
                yield None
                continue
            id = path[0]
            yield Path(path[0], path[1], path[2], path[3], path[4])

    # Returns path corresponding to URL or None if it does not exist in the database
    @staticmethod
    def parseURL(url):
        parsedURL = Path.__parseURL(url)

        protocol = parsedURL['protocol']
        if not protocol:
            return None

        domain = Domain.getDomain(parsedURL['domain'])
        if not domain:
            return None

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(protocol, element, parent, domain)
            if not path:
                return None
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path

    # Inserts each path inside the URL if not already inserted and returns last inserted path (last element from URL).
    # If domain is not in scope, returns None. If domain is in scope but not in database, inserts it
    @staticmethod
    def insertPath(url):
        db = DB()
        parsedURL = Path.__parseURL(url)

        protocol = parsedURL['protocol']

        if not Domain.checkScope(parsedURL['domain']):
            return None
        domain = Domain.insertDomain(parsedURL['domain'])

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__getPath(protocol, element, parent, domain)
            if not path:
                path = Path.getPath(db.exec_and_get_last_id('INSERT INTO paths (protocol, element, parent, domain) VALUES (%s,%s,%d,%d)', (protocol, element, parent.id if parent else None, domain.id)))
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path
        return None

class Request:
    def __init__(self, id, path_id, params, method, data, response_hash):
        self.id = id
        self.path = Path.getPath(path_id)
        self.params = params
        self.method = method
        self.data = data
        self.response = Response.getResponse(response_hash)
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()

    def __str__(self):
        result = "%s %s HTTP/1.1\r\n" % (self.method, urlparse(str(self.path)).path + ('?' + params) if params else '')
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
    
        headers = db.query_all('SELECT * FROM headers INNER JOIN request_headers on id = header WHERE request = %d', (self.id,))

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the request
    def __getCookies(self):
        db = DB()
    
        cookies = db.query_all('SELECT * FROM cookies INNER JOIN request_cookies on id = cookie WHERE request = %d', (self.id,))

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Parses params substituting all keys containing terms in blacklist by those terms. Returns None if params does not exist
    @staticmethod
    def __parseParams(params):
        if not params:
            return None
        new_params = params
        for word in config.PARAMS_BLACKLIST:
            new_params = Utils.replaceURLencoded(new_params, word, word)
        return new_params

    # Tries to parse data substituting all keys containing terms in blacklist by those terms. Returns None if data does not exist
    @staticmethod
    def __parseData(content_type, data):
        if not data:
            return None
        new_data = data
        for word in config.PARAMS_BLACKLIST:
            new_data = Utils.substitutePOSTData(content_type, new_data, word, word)
        return new_data

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

    # Returns True if request exists in database else False. If there are already some (10) requests with the same path and method 
    # but different params/data with same key, it returns True to avoid saving same requests with different CSRFs, session values, etc.
    # If requested file extension belongs is in config.EXTENSIONS_BLACKLIST, returns False
    @staticmethod
    def checkRequest(url, method, content_type, data):
        path = Path.parseURL(url)
        if not path:
            return False

        params = Request.__parseParams(urlparse(url).query) if urlparse(url).query else None
        data = data if (data is not None and data and method == 'POST') else None

        db = DB()

        # Check requests with same keys for params and data
        if params or data:
            query = 'SELECT * FROM requests WHERE path = %d AND method = %s'
            query_params = [path.id, method]

            if params:
                query += ' AND params LIKE %s'
                query_params.append(Utils.replaceURLencoded(params, None, '%'))
            if data:
                query += ' AND data LIKE %s'
                query_params.append(Utils.substitutePOSTData(content_type, data, None, '%'))
            result = db.query_all(query, tuple(query_params))

            if len(result) >= 10:
                return True

        query = 'SELECT * FROM requests WHERE path = %d AND method = %s '
        query_params = [path.id, method]

        if params:
            query += ' AND params = %s'
            query_params.append(params)
        else:
            query += ' AND params is Null'

        if data:
            query += ' AND data = %s'
            query_params.append(data)
        else:
            query += ' AND data is Null'

        return True if db.query_one(query, tuple(query_params)) else False

    # Returns False if extension is in blacklist from config.py, else True   
    @staticmethod
    def checkExtension(url):
        return False if pathlib.Path(url.split('?')[0]).suffix in config.EXTENSIONS_BLACKLIST else True
        
    # Returns request if exists else None
    @staticmethod
    def getRequest(url, method, content_type, data):
        path = Path.parseURL(url)
        if not path:
            return None
        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else None

        db = DB()

        query = 'SELECT * FROM requests WHERE path = %d AND method = %s '
        query_params = [path.id, method]

        if params:
            query += 'AND params = %s '
            query_params.append(params)
        else:
            query += ' AND params is Null '

        if data:
            query += 'AND data = %s '
            query_params.append(data)
        else:
            query += ' AND data is Null '

        request = db.query_one(query, tuple(query_params))
        if not request:
            return None
        return Request(request[0], request[1], request[2], request[3], request[4], request[5])

    # Yields requests or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def getRequests():
        id = 1
        db = DB()
        while True:
            request = db.query_one('SELECT * FROM requests WHERE id = %d', (id,))
            if not request:
                yield None
                continue
            id += 1
            yield Request(request[0], request[1], request[2], request[3], request[4], request[5])

    # Inserts request and links headers and cookies. If request is already inserted or there are too many requests 
    # to the same path and method but with different data/params values for the same keys, it returns None.
    # Path corresponding to url must already be inserted
    @staticmethod
    def insertRequest(url, method, headers, cookies, data):
        path = Path.parseURL(url)
        if not path or not Request.checkExtension(url):
            return None

        content_type = None
        for header in headers:
            if header.key == 'content-type':
                content_type = header.value

        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else None

        if Request.checkRequest(url, method, content_type, data):
            return None

        db = DB()
        db.exec('INSERT INTO requests (path, params, method, data) VALUES (%d,%s,%s,%s)', (path.id, params, method, data))
        request = Request.getRequest(url, method, content_type, data)

        for element in headers + cookies:
            element.link(request)

        # Gets again the request in order to update headers, cookies and data from databse
        return Request.getRequest(url, method, content_type, data)

    # Returns a list of requests whose params or data keys are the same as the request the function was called on
    def getSameKeysRequests(self):
        if not self.params and not self.data:
            return []

        requests = []
        query = 'SELECT * FROM requests WHERE path = %d AND method = %s'
        query_params = [self.path.id, self.method]
        if self.params:
            query += ' AND params LIKE %s'
            query_params.append(Utils.replaceURLencoded(self.params, None, '%'))
        if self.data:
            query += ' AND data LIKE %s'
            query_params.append(Utils.substitutePOSTData(self.getHeader('content-type').value if self.getHeader('content-type') else None, self.data, None, '%'))

        db = DB()
        result = db.query_all(query, tuple(query_params))

        for request in result:
            requests.append(Request(request[0], request[1], request[2], request[3], request[4], request[5]))
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
    
        headers = db.query_all('SELECT * FROM headers INNER JOIN response_headers on id = header WHERE response = %s', (self.hash,))

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the response
    def __getCookies(self):
        db = DB()
    
        cookies = db.query_all('SELECT * FROM cookies INNER JOIN response_cookies on id = cookie WHERE response = %s', (self.hash,))

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Returns the list of scripts of the response
    def __getScripts(self):
        db = DB()
        scripts = db.query_all('SELECT hash, content, path FROM scripts INNER JOIN response_scripts on hash = script WHERE response = %s', (self.hash,))

        result = []
        for script in scripts:
            result.append(Script(script[0], script[1], script[2]))

        return result

    # Returns True if response exists, else False
    @staticmethod
    def checkResponse(code, body, headers, cookies):
        if not body:
            body = None

        db = DB()
        return True if db.query_one('SELECT * FROM responses WHERE hash = %s', (Response.__hashResponse(code, body, headers, cookies),)) else False
    
    # Returns response if exists, else False
    @staticmethod
    def getResponse(response_hash):
        db = DB()
        response = db.query_one('SELECT * FROM responses WHERE hash = %s', (response_hash,))
        if not response:
            return None
        return Response(response[0], response[1], response[2])

    # Returns response hash if response succesfully inserted. Else, returns False. Also links header + cookies.
    @staticmethod
    def insertResponse(code, body, headers, cookies, request):
        if not isinstance(request, Request):
            return None

        if not body:
            body = None

        db = DB()

        if Response.checkResponse(code, body, headers, cookies):
            response_hash = Response.__hashResponse(code, body, headers, cookies)
        else:
            response_hash = Response.__hashResponse(code, body, headers, cookies)

            db.exec('INSERT INTO responses (hash, code, content) VALUES (%s,%d,%s)', (response_hash, code, body))
            
            response = Response.getResponse(response_hash)
            for element in headers + cookies:
                element.link(response)
            
        db.exec('UPDATE requests SET response = %s WHERE id = %d', (response_hash, request.id))

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
    def __parseHeader(key, value, blacklist=True):
        # Header names are case-insensitive
        key = key.lower()
        if blacklist and key in config.HEADERS_BLACKLIST:
                value = '1337'
        return (key, value)

    # Returns header or False if it does not exist  
    @staticmethod
    def getHeader(key, value):
        key, value = Header.__parseHeader(key, value)
        db = DB()
        result = db.query_one('SELECT * FROM headers WHERE header_key = %s AND value = %s', (key, value))
        if not result:
            return None
        
        return Header(result[0], result[1], result[2])

    # Inserts header if not inserted and returns it
    @staticmethod
    def insertHeader(key, value, blacklist=True):
        key, value = Header.__parseHeader(key, value, blacklist)
        header = Header.getHeader(key, value)
        if not header:
            db = DB()
            header = Header(db.exec_and_get_last_id('INSERT INTO headers (header_key, value) VALUES (%s,%s)', (key, value)), key, value)
        return header

    # Links the header to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.exec('INSERT INTO request_headers (request, header) VALUES (%d, %d)', (target.id, self.id))
            return True
        elif isinstance(target, Response):
            db.exec('INSERT INTO response_headers (response, header) VALUES (%s,%d)', (target.hash, self.id))
            return True
        elif isinstance(target, Domain):
            db.exec('INSERT INTO domain_headers(domain, header) VALUES (%s,%d)', (target.id, self.id))
            return True
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
        if name in config.COOKIES_BLACKLIST:
            value = '1337'
        else:
            for term in config.PARAMS_BLACKLIST:
                if term in name:
                    value = term
        return (name, value)

    # Returns True if exists or None if it does not exist   
    @staticmethod 
    def __getCookie(name, value, cookie_domain, cookie_path):
        if cookie_domain and not Domain.checkScope(cookie_domain, False):
            return None
        
        db = DB()
        cookie = db.query_one('SELECT * FROM cookies WHERE name = %s AND value = %s AND domain = %s AND path = %s', (name, value, cookie_domain, cookie_path))
        if not cookie:
            return None
        return Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9])

    # Returns cookie if there is a cookie with name and value whose cookie_path and cookie_domain match with url, else None
    @staticmethod
    def getCookie(name, value, url):
        path = Path.parseURL(url)
        if not path:
            return None
        db = DB()

        # First, try to get cookie as is, in case it was a session cookie added in the beggining in the scope file.
        # In case there is no such cookie in db, try to get it parsed
        results = db.query_all('SELECT * FROM cookies WHERE name = %s AND value = %s', (name, value))
        if not results:
            name, value = Cookie.__parseCookie(name, value)
            results = db.query_all('SELECT * FROM cookies WHERE name = %s AND value = %s', (name, value))
        
        for result in results:
            cookie = Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9])
            # If domain/range of subdomains and range of paths from cookie match with url
            cookie_path = Path.parseURL(path.domain.name + cookie.path) if cookie.path != '/' else Path.parseURL(path.domain.name)
            if Domain.compareDomains(cookie.domain, path.domain.name) and path.checkParent(cookie_path):
                return cookie
        return None

    # Inserts cookie if not already inserted and returns it. 
    # blacklist parameter indicates if cookie value must be removed if value of cookie is blacklisted
    # checkDomain parameter indicates if domain must be checked
    @staticmethod
    def insertCookie(name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite, blacklist=True):
        if not Domain.checkScope(cookie_domain, False):
            return None

        if blacklist:
            name, value = Cookie.__parseCookie(name, value)
        cookie = Cookie.__getCookie(name, value, cookie_domain, cookie_path)
        if not cookie:
            db = DB()
            id = db.exec_and_get_last_id('INSERT INTO cookies (name, value, domain, path, expires, maxage, httponly, secure, samesite) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', [name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite])
            cookie = Cookie(id, name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite)
        return cookie

    # Links the cookie to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.exec('INSERT INTO request_cookies (request, cookie) VALUES (%d,%d)', (target.id, self.id))
            return True
        elif isinstance(target, Response):
            db.exec('INSERT INTO response_cookies (response, cookie) VALUES (%s,%d)', (target.hash, self.id))
            return True
        elif isinstance(target, Domain):
            db.exec('INSERT INTO domain_cookies(domain, cookie) VALUES (%s,%d)', (target.id, self.id))
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
        return hashlib.sha1((str(url) + content).encode('utf-8')).hexdigest()

    # Returns script by url and content or False if it does not exist   
    @staticmethod 
    def getScript(url, content):
        db = DB()

        result = db.query_one('SELECT * FROM scripts WHERE hash = %s', (Script.__getHash(url, content),))
        if not result:
            return None
        return Script(result[0], result[1], result[2])

    # Inserts script if not already inserted, links it to the corresponding response if exists and returns it
    @staticmethod 
    def insertScript(url, content, response):
        if not isinstance(response, Response):
            return None

        if url is not None:
            path = Path.insertPath(url)
            # If path does not belong to the scope (stored domains)
            if not path:
                return None
            path = path.id
        else:
            path = None

        db = DB()
        script = Script.getScript(url, content)
        if not script:
            # Cannot use lastrowid since scripts table does not have INTEGER PRIMARY KEY but TEXT PRIMARY KEY (hash)
            db.exec('INSERT INTO scripts (hash, path, content) VALUES (%s,%d,%s)', (Script.__getHash(url, content), path, content))
            script = Script.getScript(url, content)
        db.exec('INSERT INTO response_scripts (response, script) VALUES (%s,%s)', (response.hash, script.hash))

        return script

class Vulnerability:
    def __init__(self, id, path_id, vuln_type, description):
        self.id = id
        self.path = Path.getPath(path_id)
        self.type = vuln_type
        self.description = description

    @staticmethod
    def __getVuln(path_id, vuln_type):
        db = DB()
        vuln = db.query_one('SELECT * FROM vulnerabilities WHERE path = %d AND type = %s', (path_id, vuln_type))
        return Vulnerability(vuln[0], vuln[1], vuln[2], vuln[3]) if vuln else None

    @staticmethod
    def getVuln(url, vuln_type):
        path = Path.parseURL(url)
        if not path:
            return None
        return Vulnerability.__getVuln(path.id, vuln_type)

    @staticmethod
    def insertVuln(url, vuln_type, description):
        path = Path.parseURL(url)
        if not path:
            return None

        vuln = Vulnerability.__getVuln(path.id, vuln_type)
        if vuln:
            return vuln

        db = DB()
        return Vulnerability(db.exec_and_get_last_id('INSERT INTO vulnerabilities (path, type, description) VALUES (%d,%s,%s)', (path.id, vuln_type, description)), path.id, vuln_type, description)

class Technology:
    def __init__(self, id, slug, name, version):
        self.id = id
        self.slug = slug
        self.name = name
        self.version = version

    @staticmethod
    def getTech(slug, version):
        db = DB()
        query = 'SELECT * FROM technologies WHERE slug = %s '
        if version:
            query += 'AND version = %s'
        else:
            query += 'AND version is Null'
            
        tech = db.query_one(query, (slug, version))
        return Technology(tech[0], tech[1], tech[2], tech[3]) if tech else None

    @staticmethod
    def insertTech(slug, name, version):
        tech = Technology.getTech(name, version)
        if not tech:
            db = DB()
            tech = Technology(db.exec_and_get_last_id('INSERT INTO technologies (slug, name, version) VALUES (%s, %s, %s)', (slug, name, version)), slug, name, version)
        return tech

    def link(self, path):
        db = DB()
        db.exec('INSERT INTO path_technologies (path, tech) VALUES (%d, %d)', (path.id, self.id))

class Utils:
    @staticmethod
    def isIP(ip):
        try:
            socket.inet_aton(ip)
            return True
        except:
            return False

    @staticmethod
    def replaceURLencoded(data, match, newValue):
        if not data:
            return None
        new_data = ''
        for p in data.split('&'):
            if len(p.split('=')) == 1:
                return data
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
            return None
        
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
            else:
                try:
                    return json.dumps(Utils.replaceJSON(json.loads(data), match, newValue)).replace('"%"', '%') # If  match is %, then it must match all values in db, no tonly strings, so quotes must be removed
                except:
                    return  Utils.replaceURLencoded(data, match, newValue)
                
        except Exception as e:
            print('[x] Exception %s ocurred when parsing POST data' % (e.__class__.__name__))
            return data