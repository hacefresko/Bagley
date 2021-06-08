from database import DB
from db_classes.Path import Path
import hashlib
from db_classes.Response import Response

class Script:
    def __init__(self, id, hash, content, path):
        self.id = id
        self.hash = hash
        self.content = content
        self.path = path

    # Returns script or False if it does not exist   
    @staticmethod 
    def getScript(script_hash):
        db = DB.getConnection()
        result = db.query('SELECT * FROM scripts WHERE hash = ?', [script_hash]).fetchone()
        if not result:
            return False
        return Script(result[0], result[1], result[2], result[3])

    # Inserts script if not already inserted and links it to the corresponding response if exists
    @staticmethod 
    def insertScript(url, content, response):
        if not isinstance(response, Response):
            return False

        # If path does not belong to the scope (stored domains)
        if url is not None:
            path = Path.insertPath(url)
            if not path:
                return False
            path = path.id
        else:
            path = False

        db = DB.getConnection()
        script_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
        script = Script.getScript(script_hash)

        if not script:
            script = db.query('INSERT INTO scripts (hash, path, content) VALUES (?,?,?)', [script_hash, path, content]).lastrowid
        db.query('INSERT INTO response_scripts (response, script) VALUES (?,?)', [response, script])