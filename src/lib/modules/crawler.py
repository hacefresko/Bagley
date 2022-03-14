import time, requests, datetime, random, string, os, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chrome.options import Options

import config
from lib.entities import *
from lib.modules.module import Module
import lib.controller

class Crawler (Module):
    def __init__(self, stop, rps, active_modules, lock):
        super().__init__(["chromedriver"], stop, rps, active_modules, lock)

        # Init time for applying delay
        self.t = datetime.datetime.now()

        # Init queue for other modules to send urls to crawler
        self.queue = []

        # Cookies inside the scope that the browser has stored
        self.cookies = []

        # Initial local storage to be maintained along the crawl
        self.localStorage = {}

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

    def checkDependences(self):
        if not os.path.exists(config.SCREENSHOT_FOLDER):
            raise Exception('%s not found' % config.SCREENSHOT_FOLDER)
        
        super().checkDependences()

    def addToQueue(self, url):
        self.queue.append(url)

    # https://stackoverflow.com/questions/46361494/how-to-get-the-localstorage-with-python-and-selenium-webdriver
    def addToLocalStorage(self, url, d):
        self.localStorage[url] = d

    # https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
    def __post(self, path, data, headers):
        current_requests = len(self.driver.requests)

        headers_dict = {}
        for header in headers:
            headers_dict[header.key] = header.value

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

        # Wait until request is received by selenium
        while len(self.driver.requests) == current_requests:
            time.sleep(1)

    # Inserts in the database the request if url belongs to the scope
    # If an error occur, returns None
    # request is a request selenium-wire object
    def __processRequest(self, request):
        url = request.url
        if not Path.insert(url):
            return None

        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                cookie_name = cookie.split('=')[0]
                c = Cookie.get(cookie_name, url)
                if c and c.value == cookie.split('=')[1]:
                    request_cookies.append(c)
                else:
                    for dc in self.cookies:
                        if dc.name == cookie_name:
                            request_cookies.append(dc)
                        
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
            time.sleep(3)
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
        
        body = re.sub('\s+(?=<)', '', body)

        response_hash = Response.hash(response.status_code, body, response_headers, response_cookies)
        resp = Response.get(response_hash)
        if not resp:
            resp = Response.insert(response.status_code, body, response_headers, response_cookies, processed_request)
        if resp:
            resp.link(processed_request)

        return resp

    # Check if requests can be crawled based on the scope, the type of document to be requested and if the request has been already made
    def __isCrawleable(self, url, method, content_type=None, data=None):
        domain = urlparse(url).netloc

        if Domain.checkScope(domain) and Path.checkExtension(url) and not Request.check(url, method, content_type, data, self.cookies):
            return True

        return False

    # Traverse the HTML looking for paths to crawl
    def __parseHTML(self, parent_url, response, headers):
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
                if path[-1] == '#':
                    path = path[:-1]

                url = urljoin(parent_url, path)

                if self.__isCrawleable(url, 'GET'):
                    self.__crawl(url, 'GET', headers)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method').upper() if element.get('method') else 'GET'
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)

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
                    
                req_headers = headers
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
                    
                    req_headers += [h]

                if self.__isCrawleable(url, method, content_type, data):
                    self.__crawl(url, method, data, req_headers)

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
                        content = requests.get(src, verify=False).text
                        if content:
                            s = Script.get(src, content)
                            if not s:
                                s = Script.insert(src, content)
                            if s:
                                s.link(response)
                    except:
                        lib.controller.Controller.send_error_msg(utils.getExceptionString(), "crawler")
                        continue

            elif element.name == 'iframe':
                path = element.get('src')
                if not path:
                    continue

                url = urljoin(parent_url, path)

                if self.__isCrawleable(url, 'GET'):
                    self.__crawl(url, 'GET', headers)   

            elif element.name == 'button':
                # If button belongs to a form                
                if element.get('form') or element.get('type') == 'submit' or element.get('type') == 'reset':
                    continue
                
                try:

                    # Generate XPATH selector
                    components = []
                    child = element if element.name else element.parent
                    for parent in child.parents:
                        siblings = parent.find_all(child.name, recursive=False)
                        components.append(child.name if siblings == [child] else '%s[%d]' % (child.name, 1 + siblings.index(child)))
                        child = parent
                    components.reverse()
                    xpath_selector = '/%s' % '/'.join(components)

                    # Click the button to check if requests have been made or URL has been changed
                    self.driver.get(parent_url)
                    del self.driver.requests
                    self.driver.execute_script("document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click();", xpath_selector)

                    # Wait until request is received by selenium
                    while len(self.driver.requests) == 0:
                        time.sleep(1)

                    #Check if requests have been made
                    if self.driver.requests[0]:
                        req = self.driver.requests[0]
                        data = req.body.decode('utf-8', errors='ignore')
                        
                        if self.__isCrawleable(req.url, req.method, req.headers.get_content_type(), data):
                            self.__crawl(req.url, req.method, data, headers)

                    #Else, check if at least the url has changed
                    elif self.driver.current_url != parent_url:
                        
                        if self.__isCrawleable(self.driver.current_url, 'GET'):
                            self.__crawl(self.driver.current_url, 'GET', headers)

                except:
                    continue
   
    def __sendScreenshot(self, path):
        filename = config.SCREENSHOT_FOLDER + "".join(str(path).split('?')[0]).replace('://', '_').replace('/', '_') + '-' + ''.join(random.choices(string.ascii_lowercase, k=10)) + '.png'
        if not self.driver.save_screenshot(filename):
            return False

        lib.controller.Controller.send_img(filename, "crawler")
        return True

    # Main method of crawler
    def __crawl(self, parent_url, method, data=None, headers=[]):
        # If execution is stopped
        if self.stop.is_set():
            return

        # Always inserts path into database since __crawl should only be called if the path hasn't been crawled yet
        path = Path.insert(parent_url)
        if not path:
            return
        domain = path.domain
        
        lib.controller.Controller.send_msg('[%s] %s' % (method,parent_url), "crawler")

        # Add local storage in case it has been deleted
        # https://stackoverflow.com/questions/46361494/how-to-get-the-localstorage-with-python-and-selenium-webdriver
        parsed = urlparse(parent_url)
        location = parsed.scheme + '://' + parsed.netloc + '/'
        if self.localStorage.get(location):
            # Apply delay
            if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
                time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

            self.driver.get(location)

            self.t = datetime.datetime.now()

            for k,v in self.localStorage.get(location).items():
                self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", k, v)

        # Request resource
        try:
            # Delete all previous requests so they don't pollute the results
            del self.driver.requests

            # Apply delay
            if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
                time.sleep(self.getDelay() - (datetime.datetime.now() - self.t).total_seconds())

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

                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data, headers)
        except Exception as e:
            if "timeout: Timed out receiving message from renderer" in e.msg:
                lib.controller.Controller.send_msg("Timeout exception requesting %s" % parent_url, "crawler")
            else:
                lib.controller.Controller.send_error_msg(utils.getExceptionString(), "crawler")
            return

        self.t = datetime.datetime.now()

        # Copy browser cookies to local copy
        n_cookies = 0
        self.cookies = []
        while n_cookies != len(self.driver.get_cookies()):
            n_cookies = len(self.driver.get_cookies())
            for cookie in self.driver.get_cookies():
                c = Cookie.get(cookie['name'])
                if not c or c.value != cookie.get('value'):
                    c = Cookie.insert(cookie)
                if c and c not in self.cookies:
                    self.cookies.append(c)
            time.sleep(0.5)

        # List of responses to analyze
        resp_to_analyze = []

        main_request = None
        main_response = None

        # Process all requests
        for request in self.driver.iter_requests():

            # Main request
            if request.url == parent_url and main_request is None and main_response is None:

                # Only cookies sent in requests are merged because cookies coming in set-cookie headers may not be accepted by the browser. 
                # It's easier to only take into account those which get directly accepted by only taking cookies from requests
                main_request = self.__processRequest(request)
                if not main_request:
                    return

                main_response = self.__processResponse(request, main_request, main=True)
                if not main_response:
                    return

                # Follow redirect if 3xx response is received
                code = main_response.code
                if code//100 == 3:
                    if code == 304:
                        lib.controller.Controller.send_msg("304 received: Chached response", "crawler")
                    else:
                        redirect_to = main_response.getHeader('location').value
                        if not redirect_to:
                            lib.controller.Controller.send_error_msg("Received %d but location header is not present" % code, "crawler")
                        else:
                            redirect_to = urljoin(parent_url, redirect_to)

                            if code != 307 and code != 308:
                                method = 'GET'
                                data = None


                            if Domain.checkScope(urlparse(redirect_to).netloc):
                                if self.__isCrawleable(redirect_to, method, data=data):
                                    lib.controller.Controller.send_msg("[%d] Redirect to %s" % (code, redirect_to), "crawler")
                                    self.__crawl(redirect_to, method, data, headers)
                            else:
                                lib.controller.Controller.send_msg("[%d] Redirect to %s [OUT OF SCOPE]" % (code, redirect_to), "crawler")

                    return

                # Send screenshot once we know if the request was redirected or not
                self.__sendScreenshot(main_request.path)

                resp_to_analyze.append({'url': parent_url, 'response':main_response})

            # Dynamic requests      
            else:
                domain = urlparse(request.url).netloc
                if Domain.checkScope(domain):

                    # If resource is a JS file
                    if pathlib.Path(request.url.split('?')[0]).suffix.lower() == '.js':
                        resp = request.response
                        if resp:
                            content = decode(resp.body, resp.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
                            s = Script.get(request.url, content)
                            if not s:
                                s = Script.insert(request.url, content)
                            if s:
                                s.link(main_response)
                            
                        continue

                    elif Path.checkExtension(request.url) and not Request.check(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore'), self.cookies):
                        lib.controller.Controller.send_msg('[%s][DYNAMIC] %s' % (request.method, request.url), "crawler")
                        
                        req = self.__processRequest(request)
                        resp = self.__processResponse(request, req)
                        if resp: 
                            # If dynamic request responded with HTML, send it to analize
                            if (resp.body is not None) and (resp.getHeader('content-type').value == "text/html"):
                                resp_to_analyze.append({'url': request.url, 'response':resp})
                        continue

        # Process all responses
        for r in resp_to_analyze:
            self.__parseHTML(r['url'], r['response'], headers)

    def run(self):
        # Generator for domains
        domains = Domain.yieldAll()
        while not self.stop.is_set():
            # Mark module as inactive
            self.setInactive()

            # Get url from queue. If queue is empty, get domain from database. If it's also
            # empty, sleeps for 5 seconds and starts again
            if len(self.queue) > 0:
                url = self.queue.pop(0)
                path = Path.insert(url)
                if not path:
                    continue
                domain = path.domain

                try:
                    requests.get(url, allow_redirects=False, verify=False)
                except:
                    lib.controller.Controller.send_error_msg(utils.getExceptionString(), "crawler")
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
                    http_request = requests.get('http://'+domain_name+'/',  allow_redirects=False, timeout=5, verify=False)
                    if http_request and http_request.is_permanent_redirect and urlparse(http_request.headers.get('Location')).scheme == 'https':
                        http_request = None
                except:
                    pass

                try:
                    https_request = requests.get('https://'+domain_name+'/',  allow_redirects=False, timeout=5, verify=False)
                except:
                    pass

                # If both http and https are up, start by http and add https to queue, else, start by the one that is up
                if http_request and https_request:
                    url = http_request.url
                    self.addToQueue(https_request.url)
                elif http_request is not None:
                    url = http_request.url
                elif https_request is not None:
                    url = https_request.url
                else:
                    lib.controller.Controller.send_msg('Cannot request %s' % domain_name, "crawler")
                    continue

                if http_request:
                    lib.controller.Controller.send_msg("HTTP protocol used by %s" % http_request.url, "crawler")

            # If url already in database, skip
            if Request.check(url, 'GET'):
                continue

            # Mark module as active
            self.setActive()

            lib.controller.Controller.send_msg("Started crawling %s" % url, "crawler")
            
            # Add domain headers
            if domain.headers:
                headers_string = "Headers used:\n"
                for header in domain.headers:
                    headers_string += str(header) + "\n"
                headers_string += "\n"
                lib.controller.Controller.send_msg(headers_string, "crawler")

            # Add cookie headers
            if domain.cookies:
                valid = []
                for cookie in domain.cookies:
                    try:
                        self.driver.get(url)
                        self.driver.add_cookie(cookie.getDict())
                        valid.append(cookie)
                        del self.driver.requests
                    except Exception as e:
                        lib.controller.Controller.send_error_msg(utils.getExceptionString(), "crawler")
                
                cookies_string = "Cookies used:\n"
                for cookie in valid:
                    cookies_string += str(cookie) + "\n"
                cookies_string += "\n"
                lib.controller.Controller.send_msg(cookies_string, "crawler")
            
            self.__crawl(url, 'GET', headers=domain.headers)

            lib.controller.Controller.send_msg('Finished crawling %s' % url, "crawler")
