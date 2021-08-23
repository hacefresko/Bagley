import threading, time, requests, subprocess, sqlite3, json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from seleniumwire import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import lib.config
from lib.entities import *
import traceback

class Crawler (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        # Init queue for other modules to send urls to crawl
        self.queue = []

        # Init selenium driver
        opts = Options()
        opts.headless = True
        opts.add_argument('--no-proxy-server') # https://stackoverflow.com/questions/51503437/headless-chrome-web-driver-too-slow-and-unable-to-download-file
        opts.add_argument("--proxy-server='direct://'")
        opts.add_argument("--proxy-bypass-list=*")
        opts.add_argument("start-maximized"); # https://stackoverflow.com/a/26283818/1689770
        opts.add_argument("enable-automation"); # https://stackoverflow.com/a/43840128/1689770
        opts.add_argument("--no-sandbox"); # https://stackoverflow.com/a/50725918/1689770
        opts.add_argument("--disable-infobars"); # https://stackoverflow.com/a/43840128/1689770
        opts.add_argument("--disable-dev-shm-usage"); # https://stackoverflow.com/a/50725918/1689770
        opts.add_argument("--disable-browser-side-navigation"); # https://stackoverflow.com/a/49123152/1689770
        opts.add_argument("--disable-gpu"); # https://stackoverflow.com/questions/51959986/how-to-solve-selenium-chromedriver-timed-out-receiving-message-from-renderer-exc

        self.driver = webdriver.Chrome(options=opts)

        # Set timeout
        self.driver.set_page_load_timeout(lib.config.TIMEOUT)

    def addToQueue(self, url):
        self.queue.append(url)

    def run(self):
        # Generator for domains
        domains = Domain.getDomains()
        while True:
            # Try to get url from queue. If queue is empty, try to get domain from database. If it's also
            # empty, sleeps for 5 seconds and starts again
            if len(self.queue) > 0:
                url = self.queue.pop(0)
                domain = Path.parseURL(url).domain
                if not domain:
                    continue
                try:
                    initial_request = requests.get(url,  allow_redirects=False)
                except Exception as e:
                    print("[x] Cannot request %s" % (url))
                    traceback.print_tb(e.__traceback__)
                    continue
            else:
                domain = next(domains)
                if not domain:
                    time.sleep(5)
                    continue
                domain_name = domain.name if domain.name[0] != '.' else domain.name[1:]

                # Figure out what protocol to use
                url = 'http://' + domain_name + '/'
                try:
                    initial_request = requests.get(url,  allow_redirects=False)
                    if initial_request.is_permanent_redirect and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                        url = 'https://' + domain_name + '/'
                    elif not initial_request.ok:
                        url = 'https://' + domain_name + '/'
                        requests.get(url,  allow_redirects=False)
                except Exception as e:
                    print("[x] Cannot request %s" % (url))
                    traceback.print_tb(e.__traceback__)
                    continue

            if Request.checkRequest(url, 'GET', None, None):
                continue

            try:
                print("[+] Started crawling %s" % url)
                if domain.headers:
                    print("[+] Headers used:\n")
                    for header in domain.headers:
                        print(header)
                    print()
                if domain.cookies:
                    print("[+] Cookies used:\n")
                    for cookie in domain.cookies:
                        print(cookie)
                    print()

                self.__crawl(url, 'GET', None, domain.headers, domain.cookies)
            except Exception as e:
                print('[x] Exception ocurred when crawling %s' % (url))
                traceback.print_tb(e.__traceback__)
            finally:
                print("[+] Finished crawling %s" % url)
                continue

    # https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
    def __post(self, path, data, headers, cookies):
        headers_dict = {}
        for header in headers:
            headers_dict[header.key] = header.value

        if cookies:
            cookie_header = ''
            for cookie in cookies:
                cookie_header += cookie.name + '=' + cookie.value + '; '
            headers_dict['cookie'] = cookie_header

        # Third argument from open() means to request synchronously so selenium wait for it to be completed
        self.driver.execute_script("""
        function post(path, data, headers) {
            var xhr = new XMLHttpRequest();
            xhr.open("POST", path, false);

            Object.keys(headers).forEach(function(key){
                xhr.setRequestHeader(key, headers[key])
            })

            xhr.send(data)
        }
        
        post(arguments[0], arguments[1], arguments[2]);
        """, path, data, headers_dict)

    # Inserts in the database the request and its response if url belongs to the scope. 
    # Returns (request, response). Headers and cookies params are extra headers and cookies added to the request
    # so the first time a domain is inserted they get inserted with it in the database
    def __processRequest(self, request):
        url = request.url
        Path.insertPath(url)

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
                # Default values for cookie attributes
                cookie = {'expires':'session', 'max-age':'session', 'domain': urlparse(url).netloc, 'path': '/', 'secure': False, 'httponly': False, 'samesite':'lax'}
                for attribute in raw_cookie.split(';'):
                    attribute = attribute.strip()
                    if len(attribute.split('=')) == 1:
                        cookie.update({attribute.lower(): True})
                    elif attribute.split('=')[0].lower() in ['expires', 'max-age', 'domain', 'path', 'samesite']:
                        cookie.update({attribute.split('=')[0].lower(): attribute.split('=')[1].lower()})
                    else:
                        cookie.update({'name': attribute.split('=')[0].lower()})
                        cookie.update({'value': attribute.split('=')[1]})
                c = Cookie.insertCookie(cookie.get('name'), cookie.get('value'), cookie.get('domain'), cookie.get('path'), cookie.get('expires'), cookie.get('max-age'), cookie.get('httponly'), cookie.get('secure'), cookie.get('samesite'))
                if c:
                    response_cookies.append(c)

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            response_headers.append(Header.insertHeader(k,v))

        processed_response = Response.insertResponse(response.status_code, response.body.decode('utf-8', errors='ignore'), response_headers, response_cookies, processed_request)

        return (processed_request, processed_response)

    # Traverse the HTML looking for paths to crawl
    def __parseHTML(self, parent_url, response):
        parser = BeautifulSoup(response.body, 'html.parser')
        for element in parser(['a', 'form', 'script', 'frame']):
            if element.name == 'a':
                path = element.get('href')
                if not path:
                    continue

                # Cut the html id selector from url
                if '#' in path:
                    path = path[:path.find('#')]

                url = urljoin(parent_url, path)
                domain = urlparse(url).netloc

                if Domain.checkScope(domain) and Request.checkExtension(url) and not Request.checkRequest(url, 'GET', None, None):
                    self.__crawl(url, 'GET', None)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method').upper() if element.get('method') else 'GET'
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)
                domain = urlparse(url).netloc

                if Domain.checkScope(domain):
                    # Parse input, select and textarea (textarea is outside forms, linked by form attribute)
                    data = ''
                    textareas = parser('textarea', form=form_id) if form_id is not None else []
                    for input in element(['input','select']) + textareas:
                        if input.get('name') is not None:
                            # If value is empty, put '1337'
                            if input.get('value') is None or input.get('value') == '':
                                data += input.get('name') + "=1337&"
                            else:
                                data += input.get('name') + "=" + input.get('value') + "&"
                    data = data[:-1] if data != '' else None
                        
                    headers = None
                    # If form method is GET, append data to URL as params and set data and content type to None
                    if method == 'GET':
                        content_type = None
                        if data:
                            if url.find('?'):
                                url = url.split('?')[0]
                            url += '?' + data
                            data = None
                    else:
                        content_type = 'application/x-www-form-urlencoded'
                        headers = [Header.insertHeader('content-type', content_type)]

                    if Request.checkExtension(url) and not Request.checkRequest(url, method, content_type, data):
                        self.__crawl(url, method, data, headers)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    Script.insertScript(None, element.string, response)
                else:
                    src = urljoin(parent_url, src)
                    domain = urlparse(src).netloc
                    if not Domain.checkScope(domain):
                        continue

                    content = requests.get(src).text
                    Script.insertScript(src, content, response)

    # Main method of crawler. headers and cookies are extra ones to be appended to the ones corresponding to the domain
    def __crawl(self, parent_url, method, data, headers = [], cookies = []):
        print("[+] Crawling %s [%s]" % (parent_url, method))

        domain = Path.insertPath(parent_url).domain

        # Needed for selenium to insert cookies with their domains correctly https://stackoverflow.com/questions/41559510/selenium-chromedriver-add-cookie-invalid-domain-error
        if cookies or domain.cookies:
            self.driver.get(parent_url)

        # Delete all previous requests so they don't pollute the results
        del self.driver.requests

        try:
            if method == 'GET':
                # Add headers associated to domain to request via a request interceptor
                if headers or domain.headers:
                    # If we try to acces headers from interceptor by domain.headers, when another variable
                    # named domain is used, it will overwrite driver.headers so it will throw an exception
                    interceptor_headers = headers + domain.headers
                    def interceptor(request):
                        for header in interceptor_headers:
                            try:
                                del request.headers[header.key]
                            except:
                                pass
                            request.headers[header.key] = header.value
                    self.driver.request_interceptor = interceptor

                # Add cookies associated to domain to request
                if cookies or domain.cookies:
                    try:
                        for cookie in cookies + domain.cookies:
                            self.driver.add_cookie({"name" : cookie.name, "value" : cookie.value, "domain": cookie.domain})
                    except:
                        # https://developer.mozilla.org/en-US/docs/Web/WebDriver/Errors/InvalidCookieDomain
                        print("[x] %s is a cookie-averse document" % parent_url)

                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data, headers + domain.headers, cookies + domain.cookies)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s' % (parent_url))
            traceback.print_tb(e.__traceback__)
            return

        # List of responses to analyze
        responses = []

        main_request = None
        main_response = None

        # Capture all requests
        for request in self.driver.iter_requests():
            # Main request
            if request.url == parent_url and main_request is None and main_response is None:
                main_request, main_response = self.__processRequest(request)
                if not main_request or not main_response:
                    return

                # Follow redirect if 3xx response is received
                code = main_response.code
                if code//100 == 3:
                    redirect_to = main_response.getHeader('location').value
                    if not redirect_to:
                        print("[x] Received %d but location header is not present" % code)
                    else:
                        redirect_to = urljoin(parent_url, redirect_to)

                        if code != 307 and code != 308:
                            method = 'GET'
                            data = None

                        if Request.checkExtension(redirect_to) and not Request.checkRequest(redirect_to, method, None, data):
                            if Domain.checkScope(urlparse(redirect_to).netloc):
                                print("[+] Following redirection %d to %s [%s]" % (code, redirect_to, method))
                                self.__crawl(redirect_to, method, data, headers, cookies)
                            else:
                                print("[x] Got redirection %d but %s not in scope" % (code, redirect_to))
                    
                    return

                
                responses.append({'url': parent_url, 'response':main_response, 'headers': headers, 'cookies': cookies})

            # Dynamic requests      
            else:
                domain = urlparse(request.url).netloc
                if not Domain.checkScope(domain):
                    continue

                # If resource is a JS file
                if request.url[-3:] == '.js':
                    content = requests.get(request.url).text
                    Script.insertScript(request.url, content, main_response)
                    continue
                # If domain is in scope, request has not been done yet and resource is not an image
                elif Request.checkExtension(request.url) and not Request.checkRequest(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore')):
                    print("[+] Made dynamic request to %s [%s]" % (request.url, request.method))
                    req, resp = self.__processRequest(request)
                    
                    # If dynamic request responded with HTML, send it to analize
                    if resp and resp.body and bool(BeautifulSoup(resp.body, 'html.parser').find()):
                        responses.append({'url': request.url, 'response':resp, 'headers': headers, 'cookies': cookies})

        # Analyze all responses
        for response in responses:
            self.__parseHTML(response['url'], response['response'])
        
class Fuzzer (threading.Thread):
    def __init__(self, crawler):
        threading.Thread.__init__(self)
        self.crawler = crawler

    def __fuzzPath(self, url, headers, cookies):
        # Crawl all urls on the database that has not been crawled
        if not Request.checkRequest(url, 'GET', None, None):
            self.crawler.addToQueue(url)

        delay = str(int((1/lib.config.REQ_PER_SEC) * 1000)) + 'ms'

        command = ['gobuster', 'dir', '-q', '-w', lib.config.DIR_FUZZING, '-u', url, '--delay', delay]

        # Add headers
        for header in headers:
            command.append('-H')
            command.append("'" + str(header) + "'")

        # Add cookies
        if cookies:
            command.append('-c')
            cookies = ''
            for cookie in cookies:
                cookies += str(cookie) + ' '
            command.append(cookies)

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            discovered = urljoin(url, line.split(' ')[0])
            if not Request.checkRequest(discovered, 'GET', None, None):
                print("[*] Path found! Queued %s to crawler" % discovered)
                Path.insertPath(discovered)
                self.crawler.addToQueue(discovered)

    def __fuzzDomain(self, domain):
        command = ['gobuster', 'dns', '-q', '-w', lib.config.DOMAIN_FUZZING, '-d', domain]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            if line == '':
                continue
            discovered = line.split('Found: ')[1]
            print('[*] Domain found! Inserted %s to database' % discovered)
            Domain.insertDomain(discovered)

    def run(self):
        directories = Path.getDirectories()
        domains = Domain.getDomains()
        while True:
            domain = next(domains)
            if domain and domain.name[0] == '.':
                print("[+] Fuzzing domain %s" % domain.name[1:])
                self.__fuzzDomain(domain.name[1:])
            else:
                directory = next(directories)
                if not directory:
                    time.sleep(5)
                    continue
                
                print("[+] Fuzzing path %s" % directory)
                self.__fuzzPath('http://' + str(directory), directory.domain.headers, directory.domain.cookies)
                self.__fuzzPath('https://' + str(directory), directory.domain.headers, directory.domain.cookies)
                    
class Injector (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        tested = []
        for request in Request.getRequests():
            if not request:
                time.sleep(5)
                continue
            if not request.response or request.response.code != 200 or (not request.params and not request.data) or request.id in tested:
                continue

            url = request.protocol + '://' + str(request.path) + ('?' + request.params if request.params else '')
            
            delay = delay = str(1/lib.config.REQ_PER_SEC)
            command = ['sqlmap', '--delay=' + delay, '-v', '0', '--flush-session', '--batch', '-u',  url]

            if request.method == 'POST' and request.data:
                command.append("--data")
                command.append(request.data)

            for cookie in request.path.domain.cookies:
                command.append("--cookie="+str(cookie))
            
            print("[+] Testing SQL injection in %s [%s]" % (url, request.method))

            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[*] SQL injection found in %s" % url)
                Vulnerability.insertVuln(url, 'SQLi', result.stdout)
                print(result.stdout)

            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]