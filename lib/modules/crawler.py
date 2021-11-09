import threading, time, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import config, lib.utils as utils
from lib.entities import *

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
        self.driver.set_page_load_timeout(config.TIMEOUT)

    def addToQueue(self, url):
        self.queue.append(url)

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
        Path.insert(url)

        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                c = Cookie.get(cookie.split('=')[0], cookie.split('=')[1], url)
                if c:
                    request_cookies.append(c)
            del request.headers['cookie']

        request_headers = []
        for k,v in request.headers.items():
            request_headers.append(Header.insert(k, v))

        processed_request = Request.insert(url, request.method, request_headers, request_cookies, request.body.decode('utf-8', errors='ignore'))
        
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
                domain = urlparse(url).netloc if ':' not in urlparse(url).netloc else urlparse(url).netloc.split(':')[0]
                cookie = {'expires':'session', 'max-age':'session', 'domain': domain, 'path': '/', 'secure': False, 'httponly': False, 'samesite':'lax'}
                for attribute in raw_cookie.split(';'):
                    attribute = attribute.strip()
                    if len(attribute.split('=')) == 1:
                        cookie.update({attribute.lower(): True})
                    elif attribute.split('=')[0].lower() in ['expires', 'max-age', 'domain', 'path', 'samesite']:
                        cookie.update({attribute.split('=')[0].lower(): attribute.split('=')[1].lower()})
                    else:
                        cookie.update({'name': attribute.split('=')[0].lower()})
                        cookie.update({'value': attribute.split('=')[1]})
                c = Cookie.insert(cookie.get('name'), cookie.get('value'), cookie.get('domain'), cookie.get('path'), cookie.get('expires'), cookie.get('max-age'), cookie.get('httponly'), cookie.get('secure'), cookie.get('samesite'))
                if c:
                    response_cookies.append(c)

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            response_headers.append(Header.insert(k,v))

        decoded_body = decode(response.body, response.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
        processed_response = Response.insert(response.status_code, decoded_body, response_headers, response_cookies, processed_request)

        return (processed_request, processed_response)

    # Traverse the HTML looking for paths to crawl
    def __parseHTML(self, parent_url, cookies, response):
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

                if Domain.checkScope(domain) and Request.checkExtension(url) and not Request.check(url, 'GET', cookies=cookies):
                    self.__crawl(url, 'GET', cookies=cookies)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method').upper() if element.get('method') else 'GET'
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)
                domain = urlparse(url).netloc

                if Domain.checkScope(domain):
                    # Parse input, select and textarea (textarea may be outside forms, linked by form attribute)
                    data = ''
                    external_textareas = parser('textarea', form=form_id) if form_id is not None else []
                    for input in element(['input','select']):
                        if input.get('name') is not None:
                            if input.get('value') is None or input.get('value') == '':
                                t = input.get('type')
                                if t == 'number':
                                    data += input.get('name') + "=1337&"
                                elif t == 'email':
                                    data += input.get('name') + "=1337@lel.com&"
                                else:
                                    data += input.get('name') + "=lel&"
                            else:
                                data += input.get('name') + "=" + input.get('value') + "&"
                    for input in element(['textarea']) + external_textareas:
                        if input.get('name') is not None:
                            # If value is empty, put '1337'
                            if input.get('value'):
                                data += input.get('name') + "=" + input.get('value') + "&"
                            elif input.string:
                                data += input.get('name') + "=" + input.string + "&"
                            else:
                                data += input.get('name') + "=lel&"
                            
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
                        headers = [Header.insert('content-type', content_type)]

                    if Request.checkExtension(url) and not Request.check(url, method, content_type, data, cookies):
                        self.__crawl(url, method, data, headers, cookies)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    Script.insert(None, element.string, response)
                else:
                    src = urljoin(parent_url, src)
                    domain = urlparse(src).netloc
                    if not Domain.checkScope(domain):
                        continue

                    content = requests.get(src).text
                    Script.insert(src, content, response)

    # Main method of crawler. headers and cookies are extra ones to be appended to the ones corresponding to the domain
    def __crawl(self, parent_url, method, data=None, headers = [], cookies = []):
        if cookies:
            print(('['+method+']').ljust(8) + parent_url + '\t' + str([c.name for c in cookies]))
        else:
            print(('['+method+']').ljust(8) + parent_url)

        # Always inserts path into database since __crawl is only called if the path hasn't been crawled yet
        path = Path.insert(parent_url)
        if not path:
            return
        domain = path.domain

        # Needed for selenium to insert cookies with their domains correctly https://stackoverflow.com/questions/41559510/selenium-chromedriver-add-cookie-invalid-domain-error
        if cookies:
            self.driver.get(parent_url)

        # Delete all previous requests so they don't pollute the results
        del self.driver.requests

        try:
            if method == 'GET':
                # Add headers inputed by the user, associated to the domain via a request interceptor
                if headers:
                    # If we try to acces headers from interceptor by domain.headers, when another variable
                    # named domain is used, it will overwrite driver.headers so it will throw an exception.
                    # We need interceptor_headers to store the headers for the interceptor
                    interceptor_headers = headers
                    def interceptor(request):
                        for header in interceptor_headers:
                            try:
                                del request.headers[header.key]
                            except:
                                pass
                            request.headers[header.key] = header.value
                    self.driver.request_interceptor = interceptor

                # Add cookies  inputed by the user, associated to the domain to request
                if cookies :
                    try:
                        for cookie in cookies:
                            self.driver.add_cookie({"name" : cookie.name, "value" : cookie.value, "domain": cookie.domain})
                    except:
                        # https://developer.mozilla.org/en-US/docs/Web/WebDriver/Errors/InvalidCookieDomain
                        print("[ERROR] %s is a cookie-averse document" % parent_url)

                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data, headers, cookies)
        except Exception as e:
            print('[ERROR] Exception %s ocurred when requesting %s' % (e.__class__.__name__, parent_url))
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
                        print("[ERROR] Received %d but location header is not present" % code)
                    else:
                        redirect_to = urljoin(parent_url, redirect_to)

                        if code != 307 and code != 308:
                            method = 'GET'
                            data = None

                        new_cookies = utils.mergeCookies(cookies, main_response.cookies)
                        if Request.checkExtension(redirect_to) and not Request.check(redirect_to, method, data=data, cookies=new_cookies):
                            if Domain.checkScope(urlparse(redirect_to).netloc):
                                print("[%d]   %s " % (code, redirect_to))
                                self.__crawl(redirect_to, method, data, headers, new_cookies)
                            else:
                                print("[%d]   %s [OUT OF SCOPE]" % (code, redirect_to))
                    
                    return

                responses.append({'url': parent_url, 'response':main_response, 'headers': headers, 'cookies': cookies})

            # Dynamic requests      
            else:
                domain = urlparse(request.url).netloc
                if not Domain.checkScope(domain):
                    continue

                # Append all cookies set via dynamic request, since some websites use dynamic requests to set new cookies
                cookies = utils.mergeCookies(cookies, main_response.cookies)

                # If resource is a JS file
                if request.url[-3:] == '.js':
                    content = requests.get(request.url).text
                    Script.insert(request.url, content, main_response)
                    continue
                # If domain is in scope, request has not been done yet and resource is not an image
                elif Request.checkExtension(request.url) and not Request.check(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore'), cookies):
                    if cookies:
                        print(('['+method+']').ljust(8) + "DYNAMIC REQUEST " + request.url + '\t' + str([c.name for c in cookies]))
                    else:
                        print(('['+method+']').ljust(8) + "DYNAMIC REQUEST " + request.url)
                    req, resp = self.__processRequest(request)
                    
                    # If dynamic request responded with HTML, send it to analize
                    if resp and resp.body and bool(BeautifulSoup(resp.body, 'html.parser').find()):
                        responses.append({'url': request.url, 'response':resp})

        # Analyze all responses
        for response in responses:
            self.__parseHTML(response['url'], cookies, response['response'])

    def run(self):
        # Generator for domains
        domains = Domain.yieldAll()
        while True:
            # Get url from queue. If queue is empty, get domain from database. If it's also
            # empty, sleeps for 5 seconds and starts again
            if len(self.queue) > 0:
                url = self.queue.pop(0)
                path = Path.insert(url)
                if not path:
                    continue
                domain = path.domain

                try:
                    initial_request = requests.get(url, allow_redirects=False)
                except requests.exceptions.SSLError:
                    print("[x] SSL certificate validation failed for %s" % (url))
                    continue
                except:
                    print("[x] Cannot request %s" % (url))
                    continue
            else:
                domain = next(domains)
                if not domain:
                    time.sleep(5)
                    continue
                domain_name = domain.name if domain.name[0] != '.' else domain.name[1:]

                http_request = None
                https_request = None

                # Check for http and https
                try:
                    http_request = requests.get('http://'+domain_name+'/',  allow_redirects=False, timeout=5)
                    if http_request and http_request.is_permanent_redirect and urlparse(http_request.headers.get('Location')).scheme == 'https':
                        http_request = None
                except:
                    pass

                try:
                    https_request = requests.get('https://'+domain_name+'/',  allow_redirects=False, timeout=5)
                except:
                    pass

                # If both http and https are up, start by http and add https to queue, else, start by the one that is up
                if http_request and https_request:
                    url = http_request.url
                    self.addToQueue(https_request.url)
                elif http_request:
                    url = http_request.url
                elif https_request:
                    url = https_request.url
                else:
                    print("[x] Cannot request %s" % domain_name)
                    continue

                if http_request:
                    print("[*] HTTP protocol is used by %s" % http_request.url)

            # If url already in database, skip
            if Request.check(url, 'GET'):
                continue

            try:
                # Add headers/cookies inputed by the user
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
                print()
                
                self.__crawl(url, 'GET', headers=domain.headers, cookies=domain.cookies)
            except Exception as e:
                print('\n[x] Exception %s ocurred when crawling %s' % (e.__class__.__name__, url))
            finally:
                print("\n[+] Finished crawling %s" % url)
                continue
