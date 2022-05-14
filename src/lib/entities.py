import hashlib, iptools, json, os
from urllib.parse import urlparse, urlunparse
from os.path import splitext

import config
from .database import DB

class Domain:
    def __init__(self, id, name, excluded=None):
        self.id = id
        self.name = name
        self.excluded = excluded.split(";") if excluded else "" 
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
                child = Path(result[0], result[1], result[2], result[3], result[4])
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
            child = Path(result[0], result[1], result[2], result[3], result[4])
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
        return Domain(domain[0], domain[1], domain[2])

    # Returns domain identified by the domain name or None if it does not exist
    @staticmethod
    def get(domain_name):
        db = DB()
        domain = db.query_one('SELECT * FROM domains WHERE name = %s', (domain_name,))
        if not domain:
            return None
        return Domain(domain[0], domain[1], domain[2])

    # Returns all domains
    @staticmethod
    def getAll():
        result = []
        db = DB()
        for d in db.query_all('SELECT * FROM domains', ()):
            result.append(Domain(d[0], d[1], d[2]))
        return result

    # Yields domains or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
        db = DB()
        id = db.query_one('SELECT domains FROM yield_counters', ())[0]
        while True:
            domain = db.query_one('SELECT * FROM domains WHERE id > %d LIMIT 1', (id,))
            if not domain:
                yield None
                continue
            id = domain[0]
            db.exec('UPDATE yield_counters SET domains = %d', (id,))
            yield Domain(domain[0], domain[1], domain[2])

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
            return True if (first in second) or (second in first) else False
        elif first[0] == '.':
            return True if (first in second) or (first[1:] == second) else False
        elif second[0] == '.':
            return True if (second in first) or (second[1:] == first) else False
        else:
            return False

    # Get parents of domain
    def getParents(self):
        parents = []
        
        db = DB()

        # Construct array with starting and interspersed dots i.e example.com => ['.','example','.','com']
        parts = self.name.split('.')
        dot_interspersed_parts = (['.']*(2*len(parts)-1))
        dot_interspersed_parts[::2] = parts
        if dot_interspersed_parts[0] == '':
            dot_interspersed_parts = dot_interspersed_parts[1:]
        elif dot_interspersed_parts[0] != '.':
            dot_interspersed_parts.insert(0, '.')

        for i in range(len(dot_interspersed_parts)):
            check = ''.join(dot_interspersed_parts[i:])
            result = db.query_all('SELECT * FROM domains WHERE name LIKE %s', (check,))
            for domain in result:
                parents.append(Domain(domain[0], domain[1], domain[2]))

        return parents

    # Returns True if domain exists in database (either inside or outside the scope)
    @staticmethod
    def check(domain):
        db = DB()
        return True if (db.query_one('SELECT * FROM domains WHERE name LIKE %s', (domain,)) or db.query_one('SELECT * FROM out_of_scope WHERE name LIKE %s', (domain,))) else False

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
        if db.query_one('SELECT * FROM out_of_scope WHERE name LIKE %s', (domain,)):
            return False

        # If domain is an IP
        if iptools.ipv4.validate_ip(domain.split(':')[0]) and db.query_one('SELECT * FROM domains WHERE name LIKE %s', (domain,)):
            return True

        # Check if any domain fits in the group of subdomains
        if domain[0] == '.' and db.query_one('SELECT * FROM domains WHERE name LIKE %s', ("%"+domain,)):
            return True

        # Construct array with starting and interspersed dots i.e example.com => ['.','example','.','com']
        # In order to check if there is a parent or if any part is out of scope
        parts = domain.split('.')
        dot_interspersed_parts = (['.']*(2*len(parts)-1))
        dot_interspersed_parts[::2] = parts
        if dot_interspersed_parts[0] == '':
            dot_interspersed_parts = dot_interspersed_parts[1:]
        elif dot_interspersed_parts[0] != '.':
            dot_interspersed_parts.insert(0, '.')

        for i in range(len(dot_interspersed_parts)):
            check = ''.join(dot_interspersed_parts[i:])
            if db.query_one('SELECT * FROM out_of_scope WHERE name LIKE %s', (check,)):
                return False
            if db.query_one('SELECT * FROM domains WHERE name LIKE %s', (check,)):
                return True

        return False

    # Inserts array of excluded submodules to domain (removes everything that was before)
    def addExcludedSubmodules(self, excluded_submodules):
        excluded_submodules = ";".join(excluded_submodules).lower()

        db = DB()
        db.exec('UPDATE domains SET excluded_submodules = %s WHERE id = %d', (excluded_submodules, self.id))

    # Inserts domain. If already inserted, returns None. Also links headers and cookies of parents
    @staticmethod
    def insert(domain_name, check=False):
        db = DB()
        if Domain.get(domain_name):
            return None

        if check and not Domain.checkScope(domain_name):
            return None

        domain = Domain(db.exec_and_get_last_id('INSERT INTO domains (name) VALUES (%s)', (domain_name,)), domain_name)

        headers = []
        cookies = []
        excluded = []
        for parent in domain.getParents():
            for exc in parent.excluded:
                if exc not in excluded:
                    excluded.append(exc)
            for header in parent.headers:
                if header not in headers:
                    header.link(domain)
                    headers.append(header)
            for cookie in parent.cookies:
                if cookie not in cookies:
                    cookie.link(domain)
                    cookies.append(cookie)

        domain.headers = headers
        domain.cookies = cookies
        domain.addExcludedSubmodules(excluded)

        return domain

    # Removes domain. If domain is a subdomain, remove all subdomains too. Returns True if succesful else False
    @staticmethod
    def remove(domain_name):
        if not Domain.check(domain_name):
            return False

        db = DB()

        try:
            db.exec('DELETE FROM domains WHERE name = %s', (domain_name,))
            
            if domain_name[0] == '.':
                db.exec('DELETE FROM domains WHERE name LIKE %s', ('%' + domain_name,))

        except Exception as e:
            return False

        return True

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
        self.parent = Path.getById(parent)
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

    # Returns the list of technologies of the path
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

    # Returns a dict with protocol, domain and a list elements with each element from the URL.
    # If there is an error parsing or if extension is blacklisted, returns None
    @staticmethod
    def __parseURL(url):
        result = {}

        if not Path.checkExtension(url):
            return None

        # Convert all pathless urls (i.e example.com) into urls with root dir (i.e example.com/)
        if urlparse(url)[2] == '':
            url += '/'

        # If there is no path but params, adds "/"
        if not urlparse(url).path and urlparse(url).query:
            url_to_parse = list(urlparse(url))
            url_to_parse[2] = "/"
            url = urlunparse(url_to_parse)

        # Get protocol
        result['protocol'] = urlparse(url).scheme.lower()
        # Get domain
        result['domain'] = urlparse(url).netloc
        # Get elements after http://example.com/ and subsitute '' by None
        result['elements'] = [None if i=='' else i for i in urlparse(url).path.split('/')[1:]]

        return result if result['protocol'] != '' and result['domain'] != '' else None

    # Returns False if extension is in blacklist from config.py, else True   
    @staticmethod
    def checkExtension(url):
        return False if splitext(urlparse(url).path)[1].lower() in config.EXTENSIONS_BLACKLIST else True

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
            child = Path.getById(child.parent.id)
            if child and child.parent == path.parent:
                return True

        return False   

    # Returns path corresponding to id or False if it does not exist
    @staticmethod
    def getById(id):
        db = DB()
        path = db.query_one('SELECT id, protocol, element, parent, domain FROM paths WHERE id = %d', (id,))
        return Path(path[0], path[1], path[2], path[3], path[4]) if path else None

    # Yields paths
    @staticmethod
    def yieldAll():
        db = DB()
        id = db.query_one('SELECT paths FROM yield_counters', ())[0]
        while True:
            path = db.query_one('SELECT * FROM paths WHERE id > %d LIMIT 1', (id,))
            if not path:
                yield None
                continue
            id = path[0]
            db.exec('UPDATE yield_counters SET paths = %d', (id,))
            yield Path(path[0], path[1], path[2], path[3], path[4])

    # Yields paths corresponding to directories
    @staticmethod
    def yieldDirectories():
        db = DB()
        id = db.query_one('SELECT directories FROM yield_counters', ())[0]
        while True:
            path = db.query_one('SELECT * FROM paths WHERE element is Null AND id > %d LIMIT 1', (id,))
            if not path:
                yield None
                continue
            id = path[0]
            db.exec('UPDATE yield_counters SET directories = %d', (id,))
            yield Path(path[0], path[1], path[2], path[3], path[4])

    # Returns path corresponding to URL or None if it does not exist in the database
    @staticmethod
    def check(url):
        parsedURL = Path.__parseURL(url)
        if not parsedURL:
            return None

        domain = Domain.get(parsedURL['domain'])
        if not domain:
            return None

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__get(parsedURL['protocol'], element, parent, domain)
            if not path:
                return None
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path

    # Inserts each path inside the URL if not already inserted and returns last path (last element from URL).
    # If domain is not in scope or there is an error parsing url, returns None. If domain is in scope but not in database, inserts it
    @staticmethod
    def insert(url):
        db = DB()
        parsedURL = Path.__parseURL(url)
        if not parsedURL:
            return None

        if not Domain.checkScope(parsedURL['domain']):
            return None

        protocol = parsedURL['protocol']

        domain = Domain.get(parsedURL['domain'])
        if not domain:
            domain = Domain.insert(parsedURL['domain'])

        # Iterate over each domain/file from URL
        parent = None
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__get(protocol, element, parent, domain)
            if not path:
                path = Path.getById(db.exec_and_get_last_id('INSERT INTO paths (protocol, element, parent, domain) VALUES (%s,%s,%d,%d)', (protocol, element, parent.id if parent else None, domain.id)))
            if i == len(parsedURL['elements']) - 1:
                return path
            parent = path
        return None

class Request:
    def __init__(self, id, path_id, method, params, data, response_id):
        self.id = id
        self.path = Path.getById(path_id)
        self.method = method
        self.params = params
        self.data = data
        self.response = Response.getById(response_id)
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
            new_params = replaceURLencoded(new_params, word, word)
        return new_params

    # Tries to parse data substituting all keys containing terms in blacklist by those terms. Returns None if data does not exist
    @staticmethod
    def __parseData(content_type, data):
        if not data:
            return None
        new_data = data
        for word in config.PARAMS_BLACKLIST:
            new_data = substitutePOSTData(content_type, new_data, word, word)
        return new_data

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

    # Returns True if request exists in database else False. 
    # If there are already <config.SAME_REQUESTS_ALLOWED> requests that are equal except for some values of the 
    # params or the data, it returns True to avoid filling up the database with same requests with different values 
    # for session tokens, dates, CSRF tokens, etc.
    # If requested file extension belongs to config.EXTENSIONS_BLACKLIST, returns False
    # Content Type can be optionally supplied to better analyze POST data with substitutePOSTData() function
    @staticmethod
    def check(url, method, content_type=None, data=None):
        path = Path.check(url)
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
                query_params.append(replaceURLencoded(params, None, '%'))
            if data:
                query += ' AND data LIKE %s'
                query_params.append(substitutePOSTData(content_type, data, None, '%'))
            result = db.query_all(query, tuple(query_params))

            if len(result) >= config.SAME_REQUESTS_ALLOWED:
                return True

        # Check this request is already inserted
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

        request = db.query_one(query, tuple(query_params))
        if request:
            return True

        return False

    @staticmethod
    def getById(id):
        db = DB()
        request = db.query_one('SELECT * FROM requests WHERE id = %d', (id,))
        if not request:
            return None
        return Request(request[0], request[1], request[2], request[3], request[4], request[5])
    
    # Returns request if exists else None
    @staticmethod
    def get(url, method, content_type=None, data=None):
        path = Path.check(url)
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
        if request:
            return Request(request[0], request[1], request[2], request[3], request[4], request[5])
        
        return None

    # Inserts request and links headers and cookies. If request is already inserted or there are too many requests 
    # to the same path and method but with different data/params values for the same keys, it returns None.
    # Path corresponding to url must already be inserted
    # If requested file extension belongs to config.EXTENSIONS_BLACKLIST, returns None
    @staticmethod
    def insert(url, method, headers, cookies, data):
        path = Path.insert(url)
        if not path:
            return None

        content_type = None
        for header in headers:
            if header.key == 'content-type':
                content_type = header.value

        params = Request.__parseParams(urlparse(url).query)
        data = Request.__parseData(content_type, data) if method == 'POST' else None

        if Request.check(url, method, content_type, data):
            return None

        db = DB()
        request = Request(db.exec_and_get_last_id('INSERT INTO requests (path, params, method, data) VALUES (%d,%s,%s,%s)', (path.id, params, method, data)), path.id, params, method, data, None)

        for h in headers:
            h.link(request)

        for cookie in cookies:
            if cookie.check(url):
                cookie.link(request)

        # Gets again the request in order to update headers, cookies and data from databse
        return Request.get(url, method, content_type, data)

    # Yields requests or None if there are no requests. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
        db = DB()
        id = db.query_one('SELECT requests FROM yield_counters', ())[0]
        while True:
            request = db.query_one('SELECT * FROM requests WHERE id > %d LIMIT 1', (id,))
            if not request:
                yield None
                continue
            id = request[0]
            db.exec('UPDATE yield_counters SET requests = %d', (id,))
            yield Request(request[0], request[1], request[2], request[3], request[4], request[5])

    # Returns a list of requests whose params or data keys are the same as the request the function was called on
    def getSameKeysRequests(self):
        if not self.params and not self.data:
            return []

        requests = []
        query = 'SELECT * FROM requests WHERE path = %d AND method = %s'
        query_params = [self.path.id, self.method]
        if self.params:
            query += ' AND params LIKE %s'
            query_params.append(replaceURLencoded(self.params, None, '%'))
        if self.data:
            query += ' AND data LIKE %s'
            query_params.append(substitutePOSTData(self.getHeader('content-type').value if self.getHeader('content-type') else None, self.data, None, '%'))

        db = DB()
        result = db.query_all(query, tuple(query_params))

        for request in result:
            requests.append(Request(request[0], request[1], request[2], request[3], request[4], request[5]))
        return requests

class Response:
    def __init__(self, response_id, response_hash, code, body):
        self.id = response_id
        self.hash = response_hash
        self.code = code
        self.body = body
        self.headers = self.__getHeaders()
        self.cookies = self.__getCookies()
        self.scripts = self.__getScripts()

    def __eq__(self, other):
        if not other:
            return False
        return self.hash == other.hash

    @staticmethod
    def __hash(code, body):
        return hashlib.sha1((str(body) + str(code)).encode('utf-8')).hexdigest()

    # Returns the list of headers of the response
    def __getHeaders(self):
        db = DB()
        headers = db.query_all('SELECT * FROM headers INNER JOIN response_headers on id = header WHERE response = %d', (self.id,))

        result = []
        for header in headers:
            result.append(Header(header[0], header[1], header[2]))

        return result

    # Returns the list of cookies of the response
    def __getCookies(self):
        db = DB()
        cookies = db.query_all('SELECT * FROM cookies INNER JOIN response_cookies on id = cookie WHERE response = %d', (self.id,))

        result = []
        for cookie in cookies:
            result.append(Cookie(cookie[0], cookie[1], cookie[2], cookie[3], cookie[4], cookie[5], cookie[6], cookie[7], cookie[8], cookie[9]))

        return result

    # Returns the list of scripts of the response
    def __getScripts(self):
        db = DB()
        scripts = db.query_all('SELECT id, hash FROM scripts INNER JOIN response_scripts on id = script WHERE response = %d', (self.id,))

        result = []
        for script in scripts:
            result.append(Script(script[0], script[1]))

        return result

    # Returns True if response exists, else False
    @staticmethod
    def check(code, body):
        db = DB()
        return True if db.query_one('SELECT * FROM responses WHERE hash = %s', (Response.__hash(code, body),)) else False
    
    # Returns response if exists, else False
    @staticmethod
    def getById(response_id):
        db = DB()
        response = db.query_one('SELECT * FROM responses WHERE id = %d', (response_id,))
        if not response:
            return None
        return Response(response[0], response[1], response[2], response[3])

    # Returns response if exists, else False
    @staticmethod
    def get(code, body):
        db = DB()
        response = db.query_one('SELECT * FROM responses WHERE hash = %s', (Response.__hash(code, body),))
        if not response:
            return None
        return Response(response[0], response[1], response[2], response[3])

    # Returns response if response succesfully inserted. 
    # If request is not a Request object or response already inserted, returns None. 
    # Also links header + cookies.
    @staticmethod
    def insert(code, body, headers, cookies, request):
        if not isinstance(request, Request):
            return None

        db = DB()

        if Response.check(code, body):
            return None

        response_hash = Response.__hash(code, body)

        response_id = db.exec_and_get_last_id('INSERT INTO responses (hash, code, body) VALUES (%s,%d,%s)', (response_hash, code, body))
        
        response = Response.getById(response_id)
        for element in headers + cookies:
            element.link(response)

        return Response(response_id, response_hash, code, body)

    # Links response to request. If target not a request, return False, else True
    def link(self, request):
        if not isinstance(request, Request):
            return False

        db = DB()
        db.exec('UPDATE requests SET response = %d WHERE id = %d', (self.id, request.id))
        return True

    # Returns specified header if request has it, else None
    def getHeader(self, key):
        for header in self.headers:
            if header.key == key:
                return header
        return None

    # Returns list of request that responded with this response
    def getRequests(self):
        result = []
        db = DB()
        requests = db.query_all("SELECT id FROM requests WHERE response = %d", (self.id,))
        for r in requests:
            result.append(Request.getById(r[0]))
        return result

    # Yields response or None if there are no responses. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
        db = DB()
        id = db.query_one('SELECT responses FROM yield_counters', ())[0]
        while True:
            response = db.query_one('SELECT * FROM responses WHERE id > %d LIMIT 1', (id,))
            if not response:
                yield None
                continue
            id = response[0]
            db.exec('UPDATE yield_counters SET responses = %d', (id,))
            yield Response(response[0], response[1], response[2], response[3])

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

    # Returns header or None if it does not exist  
    @staticmethod
    def get(key, value):
        key, value = Header.__parseHeader(key, value)
        db = DB()
        result = db.query_one('SELECT * FROM headers WHERE name = %s AND value = %s', (key, value))
        if not result:
            return None
        
        return Header(result[0], result[1], result[2])

    # Inserts header and returns it. If header already inserted, return None
    @staticmethod
    def insert(key, value, blacklist=True):
        key, value = Header.__parseHeader(key, value, blacklist)
        if Header.get(key, value):
            return None
        db = DB()
        header = Header(db.exec_and_get_last_id('INSERT INTO headers (name, value) VALUES (%s,%s)', (key, value)), key, value)
        return header

    # Links the header to the specified target. If target is not a request nor a response, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.exec('INSERT INTO request_headers (request, header) VALUES (%d, %d)', (target.id, self.id))
            return True
        elif isinstance(target, Response):
            db.exec('INSERT INTO response_headers (response, header) VALUES (%s,%d)', (target.id, self.id))
            return True
        elif isinstance(target, Domain):
            db.exec('INSERT INTO domain_headers(domain, header) VALUES (%s,%d)', (target.id, self.id))
            return True
        else:
            return False

class Cookie:
    def __init__(self, id, name, value, domain, path, expires, maxage, httponly, secure, samesite):
        self.id = id
        self.name = name 
        self.domain = domain
        self.value = value
        self.path = path
        self.expires = expires
        self.maxage = maxage
        self.httponly = True if httponly == 1 or httponly == True else False
        self.secure = True if secure == 1 or secure == True else False
        self.samesite = samesite

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name + '=' + self.value

    def getDict(self):
        return {
            'name': self.name,
            'value': self.value if self.value else '',
            'domain': self.domain,
            'path': self.path,
            'expires': self.expires,
            'max-age': self.maxage,
            'httponly': self.httponly,
            'secure': self.secure,
            'samesite': self.samesite
        }

    # Check if cookie matches url (just an object function wrapper for checkPath)
    def check(self, url):
        return Cookie.checkPath(self.getDict(), url)

    # Inserts cookie as a dictionary. If already inserted, returns None.
    @staticmethod
    def insert(c):
        if c.get("name") is None or c.get("value") is None or c.get("domain") is None:
            return None

        if c.get("path") is None:
            c['path'] = '/'

        if c.get('expires') is None:
            c['expires'] = "session"

        if c.get('max-age') is None:
            c['max-age'] = "session"

        if c.get("httponly") is None :
            c['httponly'] = False

        if c.get("secure") is None :
            c['secure'] = False

        if c.get("samesite") is None:
            c['samesite'] = "lax"

        db = DB()

        # Check if there is already a cookie with same name, value, domain and path
        cookie = db.query_one('SELECT * FROM cookies WHERE name = %s AND value = %s AND domain = %s AND path = %s', (c["name"], c["value"], c["domain"], c["path"]))
        if cookie:
            return None
        
        id = db.exec_and_get_last_id('INSERT INTO cookies (name, value, domain, path, expires, maxage, httponly, secure, samesite) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (c["name"], c["value"], c["domain"], c["path"], c["expires"], c["max-age"], c["httponly"], c["secure"], c["samesite"]))
        return Cookie(id, c["name"], c["value"], c["domain"], c["path"], c["expires"], c["max-age"], c["httponly"], c["secure"], c["samesite"])

    # Check if cookie as a dictionary matches url
    @staticmethod
    def checkPath(cookie_dictionary, url):
        if not cookie_dictionary:
            return False

        path = Path.check(url)
        if not path:
            return False

        # Check domain
        if not Domain.compare(cookie_dictionary.get("domain"), str(path.domain)):
            return False

        # Check path
        cookie_url = path.protocol + '://' + str(path.domain)
        if (cookie_dictionary.get("path") is not None) and (cookie_dictionary.get("path") != '/'):
            cookie_url += cookie_dictionary.get("path")[1:]
        cookie_path = Path.insert(cookie_url)
        if (not cookie_path) or (not cookie_path.checkParent(path)):
            return False

        return True

    # Inserts cookie from the raw string. If already inserted or domain/path does not match with url, returns None.
    @staticmethod
    def insertRaw(cookie_string, url):
        if not cookie_string:
            return None

        path = Path.check(url)
        if not path:
            return None
        domain = str(path.domain)
        
        # Default values for cookie attributes
        cookie = {"domain": domain}
        for attribute in cookie_string.split(';'):
            attribute = attribute.strip()
            if len(attribute.split('=')) == 1:
                cookie[attribute.lower()] = True
            elif attribute.split('=')[0].lower() in ['expires', 'max-age', 'domain', 'path', 'samesite']:
                cookie[attribute.split('=')[0].lower()] = attribute.split('=')[1].lower()
            else:
                cookie['name'] = attribute.split('=')[0]
                cookie['value'] = attribute.split('=')[1]

        if cookie.get('expires') and cookie.get('expires') != 'session':
            cookie['expires'] = 'date'

        if not cookie.get('secure'):
            cookie['secure'] = False

        if Cookie.checkPath(cookie, url):
            cookie_path = Path.insert(str(path.domain)+cookie["path"])
            if cookie_path:
                Cookie.insert(cookie)

        return None

    # Return cookie with specified name and value or None if it doe smnot exist
    # If URL is specified, url must macth domain and path of the cookie
    @staticmethod
    def get(name, value, url=None):
        db = DB()

        results = db.query_all('SELECT * FROM cookies WHERE name = %s AND value = %s', (name,value))

        for result in results:
            cookie = Cookie(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9])
            
            if url is None:
                return cookie
            elif url and cookie.check(url):
                return cookie

        return None

    # Links the cookie to the specified target. If target is not a request nor a respone nor a domain, returns False
    def link(self, target):
        db = DB()

        if isinstance(target, Request):
            db.exec('INSERT INTO request_cookies (request, cookie) VALUES (%d,%d)', (target.id, self.id))
            return True
        elif isinstance(target, Response):
            db.exec('INSERT INTO response_cookies (response, cookie) VALUES (%s,%d)', (target.id, self.id))
            return True
        elif isinstance(target, Domain):
            db.exec('INSERT INTO domain_cookies(domain, cookie) VALUES (%s,%d)', (target.id, self.id))
            return True
        else:
            return False

class Script:
    def __init__(self, script_id, script_hash, content=None):
        self.id = script_id
        self.hash = script_hash
        self.file = config.SCRIPTS_FOLDER + str(script_id) + ".js"
        folder = config.SCRIPTS_FOLDER + str(script_id)
        self.folder = folder if os.path.isdir(folder) else None
        self.content = content if content is not None else self.__getContent() # If content is not provided, it's read from file

    def __eq__(self, other):
        if not other:
            return False
        return self.hash == other.hash

    def __getContent(self):
        fd = open(self.file)
        content = fd.read()
        fd.close()

        return content

    # Returns responses associated to script if any, else an empty list
    def getResponses(self):
        db = DB()
        responses = db.query_all('SELECT * FROM responses INNER JOIN response_scripts on id = response WHERE script = %d', (self.id,))

        result = []
        for response in responses:
            result.append(Response(response[0], response[1], response[2], response[3]))

        return result

    # Returns responses associated to script if any, else an empty list
    def getPaths(self):
        db = DB()
        paths = db.query_all('SELECT * FROM paths INNER JOIN script_paths on id = path WHERE script = %d', (self.id,))

        result = []
        for path in paths:
            result.append(Path(path[0], path[1], path[2], path[3], path[4]))

        return result

    @staticmethod
    def __hash(content):
        return hashlib.sha1(content.encode('utf-8')).hexdigest()

    # Returns script by content or None if it does not exist   
    @staticmethod 
    def get(content):
        db = DB()

        result = db.query_one('SELECT * FROM scripts WHERE hash = %s', (Script.__hash(content),))
        if not result:
            return None
        return Script(result[0], result[1])

    # Returns script by id or None if it does not exist   
    @staticmethod 
    def getById(script_id):
        db = DB()

        result = db.query_one('SELECT * FROM scripts WHERE id = %d', (script_id,))
        if not result:
            return None
        return Script(result[0], result[1])

    # Inserts script. If already inserted, returns None
    @staticmethod 
    def insert(content):
        if Script.get(content):
            return None
        
        db = DB()
        script_id = int(db.query_one("SELECT count(*) FROM scripts")[0]) + 1

        # Save script in <scripts_folder>/<id>.js
        filename = config.SCRIPTS_FOLDER + str(script_id) + '.js'
        script_file = open(filename, 'w')
        script_file.write(content)
        script_file.close()

        script_hash = Script.__hash(content)
        script_id = db.exec_and_get_last_id('INSERT INTO scripts (hash) VALUES (%s)', (script_hash,))
        
        return Script(script_id, script_hash, content)

    # Links script to response or to path. If everything is correct, returns Truee
    def link(self, element):
        db = DB()

        if (isinstance(element, Response)) and (element not in self.getResponses()):
            db.exec('INSERT INTO response_scripts (response, script) VALUES (%d,%d)', (element.id, self.id))
            return True
        
        elif (isinstance(element, Path)) and (element not in self.getPaths()):
            db.exec('INSERT INTO script_paths (path, script) VALUES (%d, %d)', (element.id, self.id))
            return True

        else:
            return False

    # Yields scripts or None if there are no scripts. It continues infinetly until program stops
    @staticmethod
    def yieldAll():
        db = DB()
        id = db.query_one('SELECT scripts FROM yield_counters', ())[0]
        while True:
            script = db.query_one('SELECT * FROM scripts WHERE id > %d LIMIT 1', (id,))
            if not script:
                yield None
                continue
            id = script[0]
            db.exec('UPDATE yield_counters SET scripts = %d', (id,))
            yield Script(script[0], script[1])

class Technology:
    def __init__(self, id, cpe, name, version):
        self.id = id
        self.cpe = cpe
        self.name = name
        self.version = version

    def getCVEs(self):
        db = DB()
        cves = db.query_all("SELECT * FROM cves WHERE tech = %d", (self.id,))
        
        result = []
        for cve in cves:
            result.append(CVE(cve[0], cve[1]))
        return result

    def getPaths(self):
        db = DB()
        paths = db.query_all("SELECT * FROM path_technologies WHERE tech = %d", (self.id,))
        
        result = []
        for path in paths:
            result.append(Path(path[0], path[1], path[2], path[3], path[4]))
        return result

    @staticmethod
    def get(cpe, version=None):
        db = DB()
        query = 'SELECT * FROM technologies WHERE cpe = %s '
        if version:
            query += 'AND version = %s'
            args = (cpe, version)
        else:
            query += 'AND version is Null'
            args = (cpe,)
            
        tech = db.query_one(query, args)
        return Technology(tech[0], tech[1], tech[2], tech[3]) if tech else None

    @staticmethod
    def getById(id):
        db = DB()
        tech = db.query_one('SELECT * FROM technologies WHERE id = %d', (id,))
        return Technology(tech[0], tech[1], tech[2], tech[3]) if tech else None

    @staticmethod
    def insert(cpe, name, version=None):
        if Technology.get(name, version):
            return None
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
    def getById(id):
        db = DB()
        cve = db.query_one('SELECT * FROM cves WHERE id = %s', (id,))
        return CVE(cve[0]) if cve else None

    @staticmethod
    def insert(id, tech):
        if CVE.getById(id):
            return None
        db = DB()
        cve = CVE(db.exec_and_get_last_id('INSERT INTO cves (id, tech) VALUES (%s, %d)', (id, tech.id)), tech.id)
        return cve

class Vulnerability:
    def __init__(self, id, vuln_type, description, element, command):
        self.id = id
        self.type = vuln_type
        self.description = description
        self.path = element
        self.command = command

    @staticmethod
    def get(id):
        db = DB()
        vuln = db.query_one('SELECT * FROM vulnerabilities WHERE id = %d', (id,))
        return Vulnerability(vuln[0], vuln[1], vuln[2], vuln[3], vuln[4]) if vuln else None

    @staticmethod
    def getByType(vuln_type):
        db = DB()
        vuln = db.query_one('SELECT * FROM vulnerabilities WHERE type = %s', (vuln_type,))
        return Vulnerability(vuln[0], vuln[1], vuln[2], vuln[3], vuln[4]) if vuln else None

    @staticmethod
    def insert(vuln_type, description, element, command=None):
        db = DB()
        return Vulnerability(db.exec_and_get_last_id('INSERT INTO vulnerabilities (type, description, element, command) VALUES (%s,%s, %d, %s)', (vuln_type, description, element, command)), vuln_type, description, element, command)


# Util functions

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

def replaceJSON(data, match, newValue):
    if isinstance(data, dict):
        for k,v in data.items():
            if isinstance(v, dict):
                data.update({k:replaceJSON(v, match, newValue)})
            else:
                if match is None or match.lower() in k.lower():
                    data.update({k:newValue})
    elif isinstance(data, list):
        for e in data:
            replaceJSON(e, match, newValue)

    return data

# Substitutes all values whose keys match with match parameter for newValue. If match is None, it will substitute all values.
# It uses content_type header to know what type of POST data is, so it can be more precise
# For multipart/form-data, it also substitutes the boundary since its value is usually random/partially random
# If an exception occurs, a copy of the original data is returned
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type
def substitutePOSTData(content_type, data, match, newValue):
    boundary_substitute = 'BOUNDARY'

    if not data:
        return None
    
    # If content type is multipart/form-data, parse it. Else, try with JSON and if exception, try with URL encoded
    if (content_type is not None) and ('multipart/form-data' in content_type):
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
                    new_content = json.dumps(replaceJSON(json.loads(content), match, newValue))
                except:
                    new_content = replaceURLencoded(content, match, newValue)
                
                if not new_content:
                    if match.lower() in name.lower() or match is None:
                        new_content = newValue
                    else:
                        new_content = content
                
                new_data += fragment.split('name="')[0] + 'name="' + name + '"; ' + "; ".join(fragment.split('\r\n')[1].split('; ')[2:]) + '\r\n\r\n' + new_content + '\r\n--'+boundary_substitute
            new_data += '--'

            return new_data

    try:
        return json.dumps(replaceJSON(json.loads(data, strict=False), match, newValue)).replace('"%"', '%') # If  match is %, then it must match all values in db, not only strings, so quotes must be removed
    except Exception as e:
        return  replaceURLencoded(data, match, newValue)
