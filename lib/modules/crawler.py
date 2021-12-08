import threading, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import config, lib.utils as utils
from lib.entities import *

class Crawler (threading.Thread):
    def __init__(self, stop):
        threading.Thread.__init__(self)

        self.stop = stop

        # Init queue for other modules to send urls to crawl
        self.queue = []

        # Init selenium driver http://www.assertselenium.com/java/list-of-chrome-driver-command-line-arguments/
        opts = Options()
        opts.headless = True
        opts.incognito = True
        opts.add_argument("--incognito")
        opts.add_argument("--no-proxy-server") # https://stackoverflow.com/questions/51503437/headless-chrome-web-driver-too-slow-and-unable-to-download-file
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

        self.driver.execute_script("""
        function post(path, data, headers) {
            fetch(path, {
                method: 'POST',
                headers: headers,
                body: data
            }).then((result)=>{return result;});
        }
        
        post(arguments[0], arguments[1], arguments[2]);
        """, path, data, headers_dict)

    # Inserts in the database the request if url belongs to the scope
    # If an error occur, returns None
    # request is a request selenium-wire object
    def __processRequest(self, request):
        url = request.url
        if not Path.insert(url):
            return None

        # Add cookies to request. If not already inserted, insert them (cookies may be set via set-cookie or via JavaScript)
        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                c = Cookie.get(cookie.split('=')[0], cookie.split('=')[1], url)
                if not c:
                    c = Cookie.insertRaw(url, cookie)
                request_cookies.append(c)
            del request.headers['cookie']

        request_headers = []
        for k,v in request.headers.items():
            h = Header.get(k,v)
            if not h:
                h = Header.insert(k,v)
            if h:
                request_headers.append(h)


        return Request.insert(url, request.method, request_headers, request_cookies, request.body.decode('utf-8', errors='ignore'))

    # Inserts in the database the response if url belongs to the scope
    # request is a request selenium-wire object
    # If main is True and code != 3xx, response body will be gotten by self.driver.page_source (selenium always follows 
    # redirects, so even though the response is 3xx, body given by self.driver.page_source will be the final one, and
    # we want the inmediate response)
    def __processResponse(self, request, processed_request, main=False):
        response = request.response
        if not response:
            time.sleep(5)
            response = request.response
            if not response:
                return False

        # Insert cookies set by set-cookie header
        response_cookies = []
        if response.headers.get_all('set-cookie'):
            for raw_cookie in response.headers.get_all('set-cookie'):
                c = Cookie.insertRaw(request.url, raw_cookie)
                if c:
                    response_cookies.append(c)

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            h = Header.get(k,v)
            if not h:
                h = Header.insert(k,v)
            if h:
                response_headers.append(h)

        if main and response.status_code//100 != 3:
            body = self.driver.page_source
        else:
            body = decode(response.body, response.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
        
        response_hash = Response.hash(response.status_code, response.body, response_headers, response_cookies)
        resp = Response.get(response_hash)
        if not resp:
            resp = Response.insert(response.status_code, body, response_headers, response_cookies, processed_request)
        if resp:
            resp.link(processed_request)

        return resp

    # Traverse the HTML looking for paths to crawl
    def __parseHTML(self, parent_url, cookies, response):
        parser = BeautifulSoup(response.body, 'html.parser')
        for element in parser(['a', 'form', 'script', 'iframe', 'button']):
            if element.name == 'a':
                path = element.get('href')
                if not path:
                    continue

                # If href is not a url to another web page (http or https or a valid path -> https://www.rfc-editor.org/rfc/rfc3986#section-3.3)
                if path.find(':') != -1 and path.split(':')[0].find('/') == -1 and path.split(':')[0] != 'http' and path.split(':')[0] != 'https':
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
                        h = Header.get('content-type', content_type)
                        if not h:
                            h = Header.insert('content-type', content_type)
                        
                        headers = [h] if h else []

                    if Request.checkExtension(url) and not Request.check(url, method, content_type, data, cookies):
                        self.__crawl(url, method, data, headers, cookies)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    s = Script.get(None, element.string)
                    if not s:
                        s = Script.insert(None, element.string)
                    if s:
                        s.link(response)

                else:
                    src = urljoin(parent_url, src)
                    domain = urlparse(src).netloc
                    if not Domain.checkScope(domain):
                        continue
                    try:
                        content = requests.get(src).text
                        s = Script.get(src, content)
                        if not s:
                            s = Script.insert(src, content)
                        if s:
                            s.link(response)
                    except:
                        print("[x] Error fething script %s" % src)
                        continue

            elif element.name == 'iframe':
                path = element.get('src')
                if not path:
                    continue

                url = urljoin(parent_url, path)
                domain = urlparse(url).netloc

                if Domain.checkScope(domain) and Request.checkExtension(url) and not Request.check(url, 'GET', cookies=cookies):
                    self.__crawl(url, 'GET', cookies=cookies)

            elif element.name == 'button':
                # If button belongs to a form                
                if element.get('form') or element.get('type') == 'submit' or element.get('type') == 'reset':
                    continue
                
                try:
                    # Click the button and check if url has changed
                    if element.get('id'):
                        button_id = element.get('id')

                        self.driver.get(parent_url)
                        self.driver.execute_script("document.getElementById(arguments[0]).click();", button_id)

                    elif element.get('class'):
                        button_class = element.get('class')

                        self.driver.get(parent_url)
                        self.driver.execute_script("document.getElementsByClassName(arguments[0])[0].click();", button_class)
                    
                    if self.driver.current_url != parent_url:
                        domain = urlparse(self.driver.current_url).netloc
                        if Domain.checkScope(domain) and Request.checkExtension(self.driver.current_url) and not Request.check(self.driver.current_url, 'GET', cookies=cookies):
                            self.__crawl(self.driver.current_url, 'GET', cookies=cookies)

                except Exception as e:
                    continue

    # Main method of crawler. Cookies is the collection of cookies gathered
    def __crawl(self, parent_url, method, data=None, headers = [], cookies = []):
        # If execution is stopped
        if self.stop.is_set():
            return

        # Always inserts path into database since __crawl is only called if the path hasn't been crawled yet
        path = Path.insert(parent_url)
        if not path:
            return
        domain = path.domain
        
        # Supplied cookies that can be sent in this request
        req_cookies = []
        for cookie in cookies:
            cookie_path = Path.parseURL(str(path) + cookie.path[1:]) if cookie.path != '/' else path
            if Domain.compare(cookie.domain, str(path.domain)) and path.checkParent(cookie_path):
                req_cookies.append(cookie)

        # Request resource
        try:
            # Delete all previous requests so they don't pollute the results
            del self.driver.requests

            if method == 'GET':
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

                if cookies :
                    try:
                        for cookie in req_cookies:
                            cookie_path = Path.parseURL(str(path) + cookie.path[1:]) if cookie.path != '/' else path
                            if Domain.compare(cookie.domain, str(path.domain)) and path.checkParent(cookie_path):
                                self.driver.add_cookie({"name" : cookie.name, "value" : cookie.value})
                    except:
                        print("[ERROR] Couldn't insert cookie %s for %s" % (str(cookie), parent_url))

                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data, headers, req_cookies)
        except Exception as e:
            print('[ERROR] Exception %s ocurred when requesting %s' % (e.__class__.__name__, parent_url))
            return

        # List of responses to analyze
        responses = []

        main_request = None
        main_response = None

        # Process all requests
        for request in self.driver.iter_requests():

            # Main request
            if request.url == parent_url and main_request is None and main_response is None:
                main_request = self.__processRequest(request)
                if not main_request:
                    return
                cookies = utils.mergeCookies(cookies, main_request.cookies)

                if cookies:
                    print(('['+method+']').ljust(8) + parent_url + '\t' + str([cookie.name for cookie in cookies]))
                else:
                    print(('['+method+']').ljust(8) + parent_url)

                main_response = self.__processResponse(request, main_request, main=True)
                if not main_response:
                    return
                cookies = utils.mergeCookies(cookies, main_response.cookies)

                # Follow redirect if 3xx response is received
                code = main_response.code
                if code//100 == 3:
                    if code == 304:
                        print("[304] Chached response")
                    else:
                        redirect_to = main_response.getHeader('location').value
                        if not redirect_to:
                            print("[ERROR] Received %d but location header is not present" % code)
                        else:
                            redirect_to = urljoin(parent_url, redirect_to)

                            if code != 307 and code != 308:
                                method = 'GET'
                                data = None

                            if Request.checkExtension(redirect_to) and not Request.check(redirect_to, method, data=data, cookies=cookies):
                                if Domain.checkScope(urlparse(redirect_to).netloc):
                                    print("[%d]   %s " % (code, redirect_to))
                                    self.__crawl(redirect_to, method, data, headers, cookies)
                                else:
                                    print("[%d]   %s [OUT OF SCOPE]" % (code, redirect_to))
                    return

                responses.append({'url': parent_url, 'response':main_response})

            # Dynamic requests      
            else:
                domain = urlparse(request.url).netloc
                if Domain.checkScope(domain):

                    # If resource is a JS file
                    if pathlib.Path(request.url.split('?')[0]).suffix.lower() == '.js':
                        resp = request.response
                        content = decode(resp.body, resp.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
                        s = Script.get(request.url, content)
                        if not s:
                            s = Script.insert(request.url, content)
                        if s:
                            s.link(main_response)
                            
                        continue

                    elif Request.checkExtension(request.url) and not Request.check(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore'), cookies):
                        req_cookies = []
                        for cookie in cookies:
                            cookie_path = Path.parseURL(str(path) + cookie.path[1:]) if cookie.path != '/' else path
                            if Domain.compare(cookie.domain, str(path.domain)) and path.checkParent(cookie_path):
                                req_cookies.append(cookie)
                        if req_cookies:
                            print(('['+request.method+']').ljust(8) + "DYNAMIC REQUEST " + request.url + '\t' + str([cookie.name for cookie in req_cookies]))
                        else:
                            print(('['+request.method+']').ljust(8) + "DYNAMIC REQUEST " + request.url)
                        
                        req = self.__processRequest(request)
                        if req:
                            cookies = utils.mergeCookies(cookies, req.cookies)

                        resp = self.__processResponse(request, req)
                        if resp: 
                            cookies = utils.mergeCookies(cookies, resp.cookies)

                            # If dynamic request responded with HTML, send it to analize
                            if resp.body and bool(BeautifulSoup(resp.body, 'html.parser').find()):
                                responses.append({'url': request.url, 'response':resp})
                        continue

        # Analyze all responses
        for response in responses:
            self.__parseHTML(response['url'], cookies, response['response'])

    def run(self):
        # Generator for domains
        domains = Domain.yieldAll()
        while not self.stop.is_set():
            # Get url from queue. If queue is empty, get domain from database. If it's also
            # empty, sleeps for 5 seconds and starts again
            if len(self.queue) > 0:
                url = self.queue.pop(0)
                path = Path.insert(url)
                if not path:
                    continue
                domain = path.domain

                try:
                    requests.get(url, allow_redirects=False)
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
                
                self.__crawl(url, 'GET', headers=domain.headers, cookies=domain.cookies)
            except Exception as e:
                print('[ERROR] Exception %s ocurred when crawling %s' % (e.__class__.__name__, url))
            finally:
                print("[+] Finished crawling %s" % url)
                continue