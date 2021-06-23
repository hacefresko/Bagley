import threading, time, requests, subprocess, sqlite3, json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from database import DB
from entities import *
from seleniumwire import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

class Crawler (threading.Thread):
    blacklist_formats = ['.css', '.avif', '.gif', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.bmp', '.ico', '.tiff', '.woff2', '.woff']

    def __init__(self, scope_file):
        threading.Thread.__init__(self)
        self.scope = scope_file

        # Init selenium driver
        opts = Options()
        opts.headless = True
        # https://stackoverflow.com/questions/51503437/headless-chrome-web-driver-too-slow-and-unable-to-download-file
        opts.add_argument('--no-proxy-server')
        opts.add_argument("--proxy-server='direct://'")
        opts.add_argument("--proxy-bypass-list=*")
        self.driver = webdriver.Chrome(options=opts)

    def run(self):
        db = DB.getConnection()
        self.__insertDomains()
        while True:
            line = self.scope.readline()
            if not line:
                time.sleep(5)
                continue
            try:
                entry = json.loads(line)
            except:
                time.sleep(5)
                continue
            domain = entry.get('domain')
            if not domain:
                time.sleep(5)
                continue
            if not Domain.checkDomain(domain):
                Domain.insertDomain(domain)
            if domain[0] == '.':
                domain = domain[1:]

            try:
                protocol = 'http'
                initial_request = requests.get(protocol + '://' + domain,  allow_redirects=False)
                if initial_request.is_permanent_redirect and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                    protocol = 'https'

                print("[+] Started crawling %s" % domain)

                self.__crawl(protocol + '://' + domain, 'GET', None)
            except Exception as e:
                print('[x] Exception ocurred when crawling %s: %s' % (protocol + '://' + domain, e))
                continue
            finally:
                print("[+] Finished crawling %s" % domain)

    def __insertDomains(self):
        for line in self.scope.readlines():
            try:
                entry = json.loads(line)
            except:
                continue
            domain = entry.get('domain')
            if not domain:
                continue
            Domain.insertDomain(domain)
        self.scope.seek(0)

    # https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
    def __post(self, path, params):
        self.driver.execute_script("""
        function post(path, params, method='post') {
            const form = document.createElement('form');
            form.method = method;
            form.action = path;
        
            for (const key in params) {
                if (params.hasOwnProperty(key)) {
                    const hiddenField = document.createElement('input');
                    hiddenField.type = 'hidden';
                    hiddenField.name = key;
                    hiddenField.value = params[key];
            
                    form.appendChild(hiddenField);
                }
            }
        
            document.body.appendChild(form);
            form.submit();
        }
        
        post(arguments[1], arguments[0]);
        """, params, path)

    # Inserts in the database the request and its response. Returns (request, response)
    def __processRequest(self, request):
        url = request.url

        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                c = Cookie.getCookie(cookie.split('=')[0], cookie.split('=')[1], url)
                if c:
                    request_cookies.append(c)
            del request.headers['cookie']

        request_headers = []
        for k,v in request.headers.items():
            request_headers.append(Header.insertHeader(k, v))

        processed_request = Request.insertRequest(url, request.method, request_headers, request_cookies, request.body.decode('utf-8', errors='ignore'))
        
        if not processed_request:
            return (False, False)

        response = request.response
        if not response:
            time.sleep(5)
            response = request.response
            if not response:
                return (processed_request, False)

        response_cookies = []
        if response.headers.get_all('set-cookie'):
            for raw_cookie in response.headers.get_all('set-cookie'):
                raw_cookie = raw_cookie.lower()
                # Default values for cookie attributes
                cookie = {'expires':'session', 'max-age':'session', 'domain': urlparse(url).netloc, 'path': '/', 'secure': False, 'httponly': False, 'samesite':'lax'}
                for attribute in raw_cookie.split('; '):
                    if len(attribute.split('=')) == 1:
                        cookie.update({attribute: True})
                    elif attribute.split('=')[0] in ['expires', 'max-age', 'domain', 'path', 'samesite']:
                        cookie.update({attribute.split('=')[0]: attribute.split('=')[1]})
                    else:
                        cookie.update({'name': attribute.split('=')[0]})
                        cookie.update({'value': attribute.split('=')[1]})
                response_cookies.append(Cookie.insertCookie(cookie.get('name'), cookie.get('value'), cookie.get('domain'), cookie.get('path'), cookie.get('expires'), cookie.get('max-age'), cookie.get('httponly'), cookie.get('secure'), cookie.get('samesite')))

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            response_headers.append(Header.insertHeader(k,v))

        processed_response = Response.insertResponse(response.status_code, response.body.decode('utf-8', errors='ignore'), response_headers, response_cookies, processed_request)

        return (processed_request, processed_response)

    def __crawl(self, parent_url, method, data):
        print("[+] Crawling %s [%s]" % (parent_url, method))

        try:
            # Delete all previous requests so they don't pollute the results
            del self.driver.requests
            if method == 'GET':
                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (parent_url, e))
            return

        # Capture all requests, where first will be the request made and the rest all the dynamic ones
        for i, request in enumerate(self.driver.iter_requests()):
            if i == 0:
                first_request, first_response = self.__processRequest(request)
                if not first_request or not first_response:
                    return
            else:
                domain = urlparse(request.url).netloc
                if not Domain.checkDomain(domain):
                    continue

                # If resource is a JS file
                if request.url[-3:] == '.js':
                    content = requests.get(request.url).text
                    Script.insertScript(request.url, content, first_response)
                # If domain is in scope, request has not been done yet and resource is not an image
                elif not Request.checkRequest(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore')) \
                and not request.url[-4:] in self.blacklist_formats \
                and not request.url[-5:] in self.blacklist_formats \
                and not request.url[-6:] in self.blacklist_formats:
                    print("[+] Made dynamic request to %s [%s]" % (request.url, request.method))
                    self.__processRequest(request)

        # Parse first response body
        parser = BeautifulSoup(first_response.body, 'html.parser')
        for element in parser(['a', 'form', 'script']):
            if element.name == 'a':
                path = element.get('href')
                if path is None:
                    continue

                # Cut the html id selector from url
                if '#' in path:
                    path = path[:path.find('#')]

                url = urljoin(parent_url, path)
                domain = urlparse(url).netloc

                if Domain.checkDomain(domain) and not Request.checkRequest(url, 'GET', None, None):
                    self.__crawl(url, 'GET', None)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method').upper() if element.get('method') else 'GET'
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)
                domain = urlparse(url).netloc

                if Domain.checkDomain(domain):
                    # Parse input, select and textarea (textarea is outside forms, linked by form attribute)
                    data = ''
                    textareas = parser('textarea', form=form_id) if form_id is not None else []
                    for input in element(['input','select']) + textareas:
                        # Skip submit buttons
                        if input.get('type') != 'submit' and input.get('name') is not None:
                            # If value is empty, put '1337'
                            if input.get('value') is None or input.get('value') == '':
                                data += input.get('name') + "=1337&"
                            else:
                                data += input.get('name') + "=" + input.get('value') + "&"
                    data = data[:-1]
                        
                    # If form method is GET, append data to URL as params and set data to None
                    if method == 'GET' and len(data):
                        if url.find('?'):
                            url = url.split('?')[0]
                        url += '?' + data
                        data = None

                    if not Request.checkRequest(url, method, None, data):
                        self.__crawl(url, method, data)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    Script.insertScript(None, element.string, first_response)
                else:
                    src = urljoin(parent_url, src)
                    domain = urlparse(src).netloc
                    if not Domain.checkDomain(domain):
                        continue

                    content = requests.get(src).text
                    Script.insertScript(src, content, first_response)

class Sqlmap (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        tested = []
        id = 1
        while True:
            try:
                request = Request.getRequestById(id)
                if not request:
                    time.sleep(2)
                    continue
                if (not request.params and not request.data) or request.id in tested:
                    id += 1
                    continue
            except sqlite3.OperationalError:
                continue

            url = request.protocol + '://' + str(request.path) + ('?' + request.params if request.params else '')
            if request.method == 'POST':
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  url, '--data', request.data]
            else:
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  url]

            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[+] SQL injection found in %s" % url)
                print(result.stdout)

            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]
            id += 1