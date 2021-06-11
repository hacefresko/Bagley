from database import DB
from db_classes.Request import Request
from db_classes.Response import Response

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
        db.query('INSERT INTO response_headers (response, header) VALUES (?,?)', [response.id, self.id])
        return True


    