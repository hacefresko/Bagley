import hashlib, pathlib, iptools
from urllib.parse import urlparse, urlunparse

import config, lib.utils as utils
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
    def getById(id):
        db = DB()
        domain = db.query_one('SELECT * FROM domains WHERE id = %d', (id,))
        if not domain:
            return None
        return Domain(domain[0], domain[1])

    # Returns domain identified by the domain name or None if it does not exist
    @staticmethod
    def get(domain_name):
        db = DB()
        domain = db.query_one('SELECT * FROM domains WHERE name = %s', (domain_name,))
        if not domain:
            return None
        return Domain(domain[0], domain[1])

    # Yields domains or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
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
    def compare(first, second):
        if ':' in first:
            first = first.split(':')[0]
        if ':' in second:
            second = second.split(':')[0]
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
    def check(domain):
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
        if iptools.ipv4.validate_ip(domain.split(':')[0]) and db.query_one('SELECT name FROM domains WHERE name LIKE %s', (domain,)):
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
    def insert(domain_name):
        db = DB()
        if Domain.check(domain_name):
            return Domain.get(domain_name)

        domain = Domain(db.exec_and_get_last_id('INSERT INTO domains (name) VALUES (%s)', (domain_name,)), domain_name)
        
        return domain

    # Links cookie or header (element) to domain
    def add(self, element):
        element.link(self)

    # Inserts an out of scope domain if not already inserted neither in scope nor out
    @staticmethod
    def insertOutOfScope(domain):
        db = DB()
        if not Domain.check(domain):
            db.exec('INSERT INTO out_of_scope (name) VALUES (%s)', (domain,))

class Path:
    def __init__(self, id, protocol, element, parent, domain):
        self.id = id
        self.protocol = protocol
        self.element = element
        self.parent = Path.get(parent)
        self.domain = Domain.getById(domain)
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
            result.append(Technology(tech[0], tech[1], tech[2], tech[3]))

        return result

    # Returns path if path specified by protocol, element, parent and domain exists else None
    @staticmethod
    def __get(protocol, element, parent, domain):
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
            child = Path.get(child.parent.id)
            if child and child.parent == path.parent:
                return True

        return False   

    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def get(id):
        db = DB()
        path = db.query_one('SELECT id, protocol, element, parent, domain FROM paths WHERE id = %d', (id,))
        return Path(path[0], path[1], path[2], path[3], path[4]) if path else None

    # Yields paths
    @staticmethod
    def yieldAll():
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
    def yieldDirectories():
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

        domain = Domain.get(parsedURL['domain'])
        if not domain:
            return None

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__get(protocol, element, parent, domain)
            if not path:
                return None
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path

    # Inserts each path inside the URL if not already inserted and returns last inserted path (last element from URL).
    # If domain is not in scope, returns None. If domain is in scope but not in database, inserts it
    @staticmethod
    def insert(url):
        db = DB()
        parsedURL = Path.__parseURL(url)

        protocol = parsedURL['protocol']

        if not Domain.checkScope(parsedURL['domain']):
            return None
        domain = Domain.insert(parsedURL['domain'])

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__get(protocol, element, parent, domain)
            if not path:
                path = Path.get(db.exec_and_get_last_id('INSERT INTO paths (protocol, element, parent, domain) VALUES (%s,%s,%d,%d)', (protocol, element, parent.id if parent else None, domain.id)))
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path
        return None

class Request:
    def __init__(self, id, path_id, params, method, data, response_hash):
        self.id = id
        self.path = Path.get(path_id)
        self.params = params
        self.method = method
        self.data = data
        self.response = Response.get(response_hash)
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()

    def __str__(self):
        result = "%s %s HTTP/1.1\r\n" % (self.method, urlparse(str(self.path)).path + ('?' + self.params) if self.params else '')
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
            new_params = utils.replaceURLencoded(new_params, word, word)
        return new_params

    # Tries to parse data substituting all keys containing terms in blacklist by those terms. Returns None if data does not exist
    @staticmethod
    def __parseData(content_type, data):
        if not data:
            return None
        new_data = data
        for word in config.PARAMS_BLACKLIST:
            new_data = utils.substitutePOSTData(content_type, new_data, word, word)
        return new_data

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

    # Returns True if request exists in database else False. 
    # If there are already some (10) requests with the same path and method but different params/data with same key, it returns True to avoid saving same requests with different CSRFs, session values, etc.
    # If there are already requests to X but without cookies param, it returns False
    # If requested file extension belongs to config.EXTENSIONS_BLACKLIST, returns False
    @staticmethod
    def check(url, method, content_type=None, data=None, cookies=[]):
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
                query_params.append(utils.replaceURLencoded(params, None, '%'))
            if data:
                query += ' AND data LIKE %s'
                query_params.append(utils.substitutePOSTData(content_type, data, None, '%'))
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

        requests = db.query_all(query, tuple(query_params))
        for request in requests:
            existing_cookies = 0
            for c in cookies:
                if db.query_one('SELECT * FROM cookies JOIN request_cookies ON id=cookie WHERE request = %d AND name = %s', (request[0], c.name)):
                    existing_cookies += 1
            if existing_cookies == len(cookies):
                return True
        return False


        for request in requests:
            # Check if there is at least one new cookie that has never been sent with a similar response
            valid = True
            for c in cookies:
                if db.query_one('SELECT * FROM cookies JOIN request_cookies ON id=cookie WHERE request = %d AND name = %s', (request[0], c.name)):
                    valid = False
                    break
            if valid:
                return True
        
        return False

    # Returns False if extension is in blacklist from config.py, else True   
    @staticmethod
    def checkExtension(url):
        return False if pathlib.Path(url.split('?')[0]).suffix in config.EXTENSIONS_BLACKLIST else True
        
    # Returns request if exists else None
    @staticmethod
    def get(url, method, content_type=None, cookies=None, data=None):
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

        requests = db.query_all(query, tuple(query_params))
        for request in requests:
            valid = True
            for c in cookies:
                if not db.query_one('SELECT * FROM cookies JOIN request_cookies ON id=cookie WHERE request = %d AND name = %s', (request[0], c.name)):
                    valid = False
                    break
            if valid:
                return Request(request[0], request[1], request[2], request[3], request[4], request[5])
        return None

    # Yields requests or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
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
    def insert(url, method, headers, cookies, data):
        path = Path.parseURL(url)
        if not path or not Request.checkExtension(url):
            return None

        content_type = None
        for header in headers:
            if header.key == 'content-type':
                content_type = header.value

        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else None

        if Request.check(url, method, content_type, data, cookies):
            return None

        db = DB()
        request = Request(db.exec_and_get_last_id('INSERT INTO requests (path, params, method, data) VALUES (%d,%s,%s,%s)', (path.id, params, method, data)), path.id, params, method, data, None)

        for element in headers + cookies:
            element.link(request)

        # Gets again the request in order to update headers, cookies and data from databse
        return Request.get(url, method, content_type, cookies, data)

    # Returns a list of requests whose params or data keys are the same as the request the function was called on
    def getSameKeys(self):
        if not self.params and not self.data:
            return []

        requests = []
        query = 'SELECT * FROM requests WHERE path = %d AND method = %s'
        query_params = [self.path.id, self.method]
        if self.params:
            query += ' AND params LIKE %s'
            query_params.append(utils.replaceURLencoded(self.params, None, '%'))
        if self.data:
            query += ' AND data LIKE %s'
            query_params.append(utils.substitutePOSTData(self.getHeader('content-type').value if self.getHeader('content-type') else None, self.data, None, '%'))

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
    def check(code, body, headers, cookies):
        if not body:
            body = None

        db = DB()
        return True if db.query_one('SELECT * FROM responses WHERE hash = %s', (Response.__hashResponse(code, body, headers, cookies),)) else False
    
    # Returns response if exists, else False
    @staticmethod
    def get(response_hash):
        db = DB()
        response = db.query_one('SELECT * FROM responses WHERE hash = %s', (response_hash,))
        if not response:
            return None
        return Response(response[0], response[1], response[2])

    # Returns response hash if response succesfully inserted. Else, returns False. Also links header + cookies.
    @staticmethod
    def insert(code, body, headers, cookies, request):
        if not isinstance(request, Request):
            return None

        if not body:
            body = None

        db = DB()

        if Response.check(code, body, headers, cookies):
            response_hash = Response.__hashResponse(code, body, headers, cookies)
        else:
            response_hash = Response.__hashResponse(code, body, headers, cookies)

            db.exec('INSERT INTO responses (hash, code, content) VALUES (%s,%d,%s)', (response_hash, code, body))
            
            response = Response.get(response_hash)
            for element in headers + cookies:
                element.link(response)
            
        db.exec('UPDATE requests SET response = %s WHERE id = %d', (response_hash, request.id))

        return Response.get(response_hash)

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
    def get(key, value):
        key, value = Header.__parseHeader(key, value)
        db = DB()
        result = db.query_one('SELECT * FROM headers WHERE header_key = %s AND value = %s', (key, value))
        if not result:
            return None
        
        return Header(result[0], result[1], result[2])

    # Inserts header if not inserted and returns it
    @staticmethod
    def insert(key, value, blacklist=True):
        key, value = Header.__parseHeader(key, value, blacklist)
        header = Header.get(key, value)
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
    def get(name, value, url):
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
            cookie_path = Path.parseURL(str(path) + cookie.path[1:]) if cookie.path != '/' else path
            if Domain.compare(cookie.domain, path.domain.name) and path.checkParent(cookie_path):
                return cookie
        return None

    # Inserts cookie if not already inserted and returns it. 
    # blacklist parameter indicates if cookie value must be removed if value of cookie is blacklisted
    # check parameter indicates if domain must be checked
    @staticmethod
    def insert(name, value, cookie_domain, cookie_path, expires, maxage, httponly, secure, samesite, blacklist=True):
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
        self.path = Path.get(path_id)

    # Returns hash of the script specified by url and content
    @staticmethod 
    def __getHash(url, content):
        return hashlib.sha1((str(url) + content).encode('utf-8')).hexdigest()

    # Returns script by url and content or False if it does not exist   
    @staticmethod 
    def get(url, content):
        db = DB()

        result = db.query_one('SELECT * FROM scripts WHERE hash = %s', (Script.__getHash(url, content),))
        if not result:
            return None
        return Script(result[0], result[1], result[2])

    # Inserts script if not already inserted, links it to the corresponding response if exists and returns it
    @staticmethod 
    def insert(url, content, response):
        if not isinstance(response, Response):
            return None

        if url is not None:
            path = Path.insert(url)
            # If path does not belong to the scope (stored domains)
            if not path:
                return None
            path = path.id
        else:
            path = None

        db = DB()
        script = Script.get(url, content)
        if not script:
            # Cannot use lastrowid since scripts table does not have INTEGER PRIMARY KEY but TEXT PRIMARY KEY (hash)
            db.exec('INSERT INTO scripts (hash, path, content) VALUES (%s,%d,%s)', (Script.__getHash(url, content), path, content))
            script = Script.get(url, content)
        db.exec('INSERT INTO response_scripts (response, script) VALUES (%s,%s)', (response.hash, script.hash))

        return script

class Vulnerability:
    def __init__(self, id, vuln_type, description):
        self.id = id
        self.type = vuln_type
        self.description = description

    @staticmethod
    def get(id):
        db = DB()
        vuln = db.query_one('SELECT * FROM vulnerabilities WHERE id = %d', (id,))
        return Vulnerability(vuln[0], vuln[1], vuln[2]) if vuln else None

    @staticmethod
    def getByType(vuln_type):
        db = DB()
        vuln = db.query_one('SELECT * FROM vulnerabilities WHERE type = %s', (vuln_type,))
        return Vulnerability(vuln[0], vuln[1], vuln[2]) if vuln else None


    @staticmethod
    def insert(vuln_type, description):
        db = DB()
        return Vulnerability(db.exec_and_get_last_id('INSERT INTO vulnerabilities (type, description) VALUES (%s,%s)', (vuln_type, description)), vuln_type, description)

class Technology:
    def __init__(self, id, cpe, name, version):
        self.id = id
        self.cpe = cpe
        self.name = name
        self.version = version

    @staticmethod
    def get(cpe, version):
        db = DB()
        query = 'SELECT * FROM technologies WHERE cpe = %s '
        if version:
            query += 'AND version = %s'
        else:
            query += 'AND version is Null'
            
        tech = db.query_one(query, (cpe, version))
        return Technology(tech[0], tech[1], tech[2], tech[3]) if tech else None

    @staticmethod
    def getById(id):
        db = DB()
        tech = db.query_one('SELECT * FROM technologies WHERE id = %d', (id,))
        return Technology(tech[0], tech[1], tech[2], tech[3]) if tech else None

    def getCVEs(self):
        db = DB()
        cves = db.query_all("SELECT * FROM cves WHERE tech = %d", (self.id,))
        
        result = []
        for cve in cves:
            result.append(cve)
        return result

    @staticmethod
    def insert(cpe, name, version=None):
        tech = Technology.get(name, version)
        if not tech:
            db = DB()
            tech = Technology(db.exec_and_get_last_id('INSERT INTO technologies (cpe, name, version) VALUES (%s, %s, %s)', (cpe, name, version)), cpe, name, version)
        return tech

    def link(self, path):
        db = DB()
        db.exec('INSERT INTO path_technologies (path, tech) VALUES (%d, %d)', (path.id, self.id))

class CVE:
    def __init__(self, id, tech):
        self.id = id
        self.tech = Technology.getById(tech)

    @staticmethod
    def get(id):
        db = DB()
        cve = db.query_one('SELECT * FROM cves WHERE id = %s', (id,))
        return CVE(cve[0], cve[1]) if cve else None

    @staticmethod
    def insert(id, tech):
        db = DB()
        cve = CVE.get(id)
        if not cve:
            db = DB()
            cve = CVE(db.exec_and_get_last_id('INSERT INTO cves (id, tech) VALUES (%s, %d)', (id, tech.id)), tech.id)
        return cve