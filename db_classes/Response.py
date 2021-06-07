class Response:
    def __init__(self, mimeType, body):
        to_hash = mimeType + body
        self.hash = hashlib.sha1(to_hash.encode('utf-8')).hexdigest()
        self.mimeType = mimeType
        self.body = body