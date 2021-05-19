from urllib.parse import urljoin, urlparse

path = 'http://127.0.0.1/img/?C=N;O=D'

params = urlparse(path).query.split('&')
if params:
    new_params = ''
    for param in params:
        value = param.split('=')[0]
        new_params += value + "=1337&"
    new_params = new_params[:-1]
print(urlparse(path)._replace(query=new_params).geturl())