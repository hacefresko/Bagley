class Request:
    def __init__(self, id, protocol, path, params, method, data, response):
        self.id = id
        self.protocol = protocol
        self.path = path
        self.params = params
        self.method = method
        self.data = data if data != '0' else None
        self.response = response