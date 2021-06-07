import database
from urllib.parse import urlparse, urlunparse

class Path:
    ################ DOMAIN METHODS ################
    # Returns True if domain exists, else False
    @staticmethod
    def checkDomain(domain):
        db = database.DB.getConnection()
        return True if db.query('SELECT name FROM domains WHERE name = ?', [domain]).fetchone() else False

    # Inserts domain if not already inserted
    @staticmethod
    def insertDomain(domain):
        db = database.DB.getConnection()
        if not Path.checkDomain(domain):
            db.query('INSERT INTO domains (name) VALUES (?)', [domain])

    ################# PATH METHODS ##################
    def __init__(self, id, element, parent, domain):
        self.id = id
        self.element = element
        self.parent = parent
        self.domain = domain
    
    # Returns true if path specified by element, parent and domain exists else False
    @staticmethod
    def __checkPath(element, parent, domain):
        db = database.DB.getConnection()
        result = db.query('SELECT id FROM paths WHERE element = ? AND parent = ? AND domain = ?', [element, parent, domain]).fetchone()
        return result[0] if result else False

    # Returns a dict with domain and a list elements with each
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
        # Get elements
        result['elements'] = urlparse(url)[2].split('/')

        return result

    # Returns path corresponding to URL or False if it does not exist
    @staticmethod
    def getPath(url):
        parsedURL = Path.__parseURL(url)

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__checkPath(element, parent, parsedURL['domain'])
            if not path:
                return False
            if i == len(parsedURL['elements']) - 1:
                return Path(path, element, parent, parsedURL['domain'])
            parent = path

    # Inserts each path inside the URL if not already inserted and returns last inserted path (last element from URL). If domain doesn't exist, return False
    @staticmethod
    def insertPath(url):
        db = database.DB.getConnection()
        parsedURL = Path.__parseURL(url)

        if not Path.checkDomain(parsedURL['domain']):
            return False

        # Iterate over each domain/file from URL
        parent = False
        for i, element in enumerate(parsedURL['elements']):
            path = Path.__checkPath(element, parent, parsedURL['domain'])
            if not path:
                path = db.query('INSERT INTO paths (element, parent, domain) VALUES (?,?,?)', [element, parent, parsedURL['domain']]).lastrowid
            if i == len(parsedURL['elements']) - 1:
                return Path(path, element, parent, parsedURL['domain'])
            parent = path

        