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
        # https://stackoverflow.com/questions/51503437/headless-chrome-web-driver-too-slow-and-unable-to-download-file
        opts.add_argument('--no-proxy-server')
        opts.add_argument("--proxy-server='direct://'")
        opts.add_argument("--proxy-bypass-list=*")
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

            try:
                if Request.checkRequest(url, 'GET', None, None):
                    continue

                print("[+] Started crawling %s" % url)
                if domain.headers:
                    print("[+] Headers used:")
                    for header in domain.headers:
                        print(header)
                    print()
                if domain.cookies:
                    print("[+] Cookies used:")
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
    def __post(self, path, params):
        self.driver.execute_script("""
        function post(path, params, method='post', headers, cookies) {
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

    # Inserts in the database the request and its response. Returns (request, response). Headers and cookies params
    # are the extra headers and cookies that were added to the request
    def __processRequest(self, request, headers, cookies):
        url = request.url
        Path.insertPath(url, headers, cookies)

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
                for attribute in raw_cookie.split('; '):
                    if len(attribute.split('=')) == 1:
                        cookie.update({attribute.lower(): True})
                    elif attribute.split('=')[0].lower() in ['expires', 'max-age', 'domain', 'path', 'samesite']:
                        cookie.update({attribute.split('=')[0].lower(): attribute.split('=')[1]})
                    else:
                        cookie.update({'name': attribute.split('=')[0].lower()})
                        cookie.update({'value': attribute.split('=')[1]})
                response_cookies.append(Cookie.insertCookie(cookie.get('name'), cookie.get('value'), cookie.get('domain'), cookie.get('path'), cookie.get('expires'), cookie.get('max-age'), cookie.get('httponly'), cookie.get('secure'), cookie.get('samesite')))

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            response_headers.append(Header.insertHeader(k,v))

        processed_response = Response.insertResponse(response.status_code, response.body.decode('utf-8', errors='ignore'), response_headers, response_cookies, processed_request)

        return (processed_request, processed_response)

    def __crawl(self, parent_url, method, data, headers, cookies):
        print("Crawling %s [%s]" % (parent_url, method))

        domain = Path.insertPath(parent_url, headers, cookies).domain

        # Delete all previous requests so they don't pollute the results
        del self.driver.requests

        # Add headers associated to domain to request via a request interceptor
        if domain.headers:
            def interceptor(request):
                for header in domain.headers:
                    try:
                        del request.headers[header.key]
                    except:
                        pass
                    request.headers[k] = header.value
            self.driver.request_interceptor = interceptor

        # Add cookies associated to damain to request
        if domain.cookies:
            try:
                for cookie in domain.cookies:
                    self.driver.add_cookie({"name" : cookie.name, "value" : cookie.value, "domain": cookie.domain})
            except:
                # https://developer.mozilla.org/en-US/docs/Web/WebDriver/Errors/InvalidCookieDomain
                print("%s is a cookie-averse document" % parent_url)

        try:
            if method == 'GET':
                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s' % (parent_url))
            traceback.print_tb(e.__traceback__)
            return

        # Capture all requests, where first will be the request made and the rest all the dynamic ones
        for i, request in enumerate(self.driver.iter_requests()):
            if i == 0:
                first_request, first_response = self.__processRequest(request, headers, cookies)
                if not first_request or not first_response:
                    return

                code = first_response.code

                # Follow redirect if 3xx response is received
                if code//100 == 3:
                    redirect_to = first_response.getHeader('location').value
                    if not redirect_to:
                        print("Received %d but location header is not present" % code)
                        return

                    if code != 307 and code != 308:
                        method = 'GET'
                        data = None

                    if Domain.checkScope(urlparse(redirect_to).netloc) and Request.checkExtension(redirect_to) and not Request.checkRequest(redirect_to, method, None, data):
                        print("Following redirection %d to %s [%s]" % (code, redirect_to, method))
                        self.__crawl(redirect_to, method, data, headers, cookies)
                        return
                    else:
                        print("Got redirection %d but %s not in scope" % (code, redirect_to))
                        return

            else:
                domain = urlparse(request.url).netloc
                if not Domain.checkScope(domain):
                    continue

                # If resource is a JS file
                if request.url[-3:] == '.js':
                    content = requests.get(request.url).text
                    Script.insertScript(request.url, headers, cookies, content, first_response)
                # If domain is in scope, request has not been done yet and resource is not an image
                elif Request.checkExtension(request.url) and not Request.checkRequest(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore')):
                    print("Made dynamic request to %s [%s]" % (request.url, request.method))
                    self.__processRequest(request, headers, cookies)

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

                if Domain.checkScope(domain) and Request.checkExtension(url) and not Request.checkRequest(url, 'GET', None, None):
                    self.__crawl(url, 'GET', None, headers, cookies)
                
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

                    if Request.checkExtension(url) and not Request.checkRequest(url, method, None, data):
                        self.__crawl(url, method, data, headers, cookies)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    Script.insertScript(None, None, None, element.string, first_response)
                else:
                    src = urljoin(parent_url, src)
                    domain = urlparse(src).netloc
                    if not Domain.checkScope(domain):
                        continue

                    content = requests.get(src).text
                    Script.insertScript(src, headers, cookies, content, first_response)

class Fuzzer (threading.Thread):
    def __init__(self, crawler):
        threading.Thread.__init__(self)
        self.crawler = crawler

    @staticmethod
    def __processResult(result):
        if result.returncode != 0:
            return

    def run(self):
        directories = Path.getDirectories()
        domains = Domain.getDomains()
        while True:
            directory = next(directories)
            if directory:
                print("[+] Fuzzing path %s" % directory)

                command = ['gobuster', 'dir', '-q', '-w', lib.config.DIR_FUZZING]

                # Add headers
                for header in directory.domain.headers:
                    command.append('-H')
                    command.append("'" + str(header) + "'")

                # Add cookies
                if directory.domain.cookies:
                    command.append('-c')
                    cookies = ''
                    for cookie in directory.domain.cookies:
                        cookies += str(cookie) + ' '
                    command.append(cookies)

                Fuzzer.__processResult(subprocess.run(command + ['-u', 'http://' + str(directory)], capture_output=True, encoding='utf-8'))
                Fuzzer.__processResult(subprocess.run(command + ['-u', 'https://' + str(directory)], capture_output=True, encoding='utf-8'))
            else:
                domain = next(domains)
                if domain:
                    print("[+] Fuzzing domain %s" % domain)
                else:
                    time.sleep(5)
                    continue

class SqlInjection (threading.Thread):
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
            command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  url]

            if request.method == 'POST' and request.data:
                command.append("--data")
                command.append(request.data)
            
            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[+] SQL injection found in %s" % url)
                print(result.stdout)

            tested = [*[request.id for request in request.getSameKeysRequests()], *tested]