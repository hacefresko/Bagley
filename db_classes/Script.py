from database import DB
from db_classes.Path import Path
import hashlib
from db_classes.Response import Response

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
        db.query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response, script.hash])

        return script