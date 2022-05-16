import time, requests, random, string, os, re, traceback
from bs4 import BeautifulSoup
from os.path import splitext
from urllib.parse import urljoin, urlparse
from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chrome.options import Options

import config
from lib.entities import *
from lib.modules.module import Module

class Crawler (Module):
    def __init__(self, controller, stop, rps, active_modules, lock):
        super().__init__(["chromedriver"], controller, stop, rps, active_modules, lock)

        # Init queue for other modules to send urls to crawler
        self.queue = []

        # Initial local storage to be maintained along the crawl
        self.localStorage = {}

        # Init selenium driver options
        self.opts = Options()

        # Enable headless mode
        self.opts.headless = True

        # Enable incognito mode
        self.opts.incognito = True

        # Options to increase performance (Chrome options: https://peter.sh/experiments/chromium-command-line-switches/)
        self.opts.add_argument("--no-proxy-server")                  
        self.opts.add_argument("--proxy-server='direct://'") 
        self.opts.add_argument("--proxy-bypass-list=*") 
        self.opts.add_argument("start-maximized"); 
        self.opts.add_argument("enable-automation");
        self.opts.add_argument("--no-sandbox");
        self.opts.add_argument("--disable-infobars")
        self.opts.add_argument("--disable-dev-shm-usage");
        self.opts.add_argument("--disable-browser-side-navigation");
        self.opts.add_argument("--disable-gpu");

        # Init driver
        self.driver = webdriver.Chrome(options=self.opts)

        # Set timeout
        self.driver.set_page_load_timeout(config.TIMEOUT)

    def checkDependencies(self):
        if not os.path.exists(config.SCREENSHOT_FOLDER):
            raise Exception('%s not found' % config.SCREENSHOT_FOLDER)
        
        super().checkDependencies()

    # Check if requests can be crawled based on the scope, the type of resource to be requested and 
    # if the request has been already made
    def isCrawlable(self, url, method='GET', content_type=None, data=None):
        domain = urlparse(url).netloc

        if Domain.checkScope(domain) and Path.checkExtension(url) and not Request.check(url, method, content_type, data):
            return True

        return False

    # If URL already exists in db or in queue, if it's not in scope or if file extension is blackilsted, it returns False
    def isQueueable(self, url):
        if Path.check(url) or (url in self.queue) or (not Domain.checkScope(urlparse(url).netloc)) or (not Path.checkExtension(url)):
            return False

        return True

    # Add URL to the queue 
    # If it already exists in db or in queue, if it's not in scope or if file extension is blackilsted, it won't be added
    def addToQueue(self, url):
        if self.isQueueable(url):
            self.queue.append(url)

    # Remove all URLs belonging to domain from the queue
    def removeDomainFromQueue(self, domain):
        newQueue = []

        for url in self.queue:
            d = urlparse(url).netloc
            if ((domain[0] == '.') and (not Domain.compare(domain, d))) or ((domain[0] != '.') and (d != domain)):
                newQueue.append(url)

        self.queue = newQueue

    # Update initial cookies so they remain although a logout button is pressed
    def __updateCookies(self, url):
        domain = Path.get(url).domain
        if domain.cookies:
            for cookie in domain.cookies:
                browser_cookie = self.driver.get_cookie(cookie.name)

                # If cookie is not in the browser, try adding it again
                if (browser_cookie is None) or (browser_cookie["value"] != cookie.value) or not Cookie.checkPath(browser_cookie, url):
                   
                    current_domain = urlparse(self.driver.current_url).netloc

                    # Check if current domain corresponds to the one in the cookie to get get it or not
                    if str(domain) != current_domain:
                        self.driver.get(url)
                    
                    try:
                        self.driver.add_cookie(cookie.getDict())
                    except:
                        self.send_msg("Cannot add cookie %s (cookie_domain: %s, current domain: %s)" % (str(cookie), cookie.domain, str(domain)), "crawler")

                     # Remove requests origined from getting domain
                    if str(domain) != current_domain:
                        del self.driver.requests

    # Add to local storage attribute to later update browser
    def addToLocalStorage(self, url, d):
        self.localStorage[url] = d

    # Updates localstorage for url with the key/values stored, so the localstorage remains although a logout button is pressed
    def __updateLocalStorage(self, url):
        parsed = urlparse(url)
        location = parsed.scheme + '://' + parsed.netloc + '/'
        if self.localStorage.get(location):
            
            self.applyDelay()

            # Location must be visited so the browser inserts the data in the local storage corresponding to that location
            self.driver.get(location)

            self.updateLastRequest()

            for k,v in self.localStorage.get(location).items():
                self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", k, v)

    # Function to send requests using any HTTP method by using JavaScript in the browser
    def __request(self, url, method, data, headers):
        current_requests = len(self.driver.requests)

        headers_dict = {}
        for header in headers:
            headers_dict[header.key] = header.value

        self.driver.execute_script("""
        function req(url, method, data, headers) {
            fetch(url, {
                method: method,
                headers: headers,
                body: data
            }).then((result)=>{return result;});
        }
        
        req(arguments[0], arguments[1], arguments[2], arguments[3]);
        """, url, method, data, headers_dict)

        # Wait until request is received by selenium or until it times out
        i = 0
        while (len(self.driver.requests) == current_requests) and (i < config.TIMEOUT):
            time.sleep(1)
            i += 1

    # Inserts in the database the request if url belongs to the scope
    # If an error occur, returns None
    # request is a request selenium-wire object
    def __processRequest(self, request):

        # Get cookies from cookies header to link them to the request
        # If is not already in the database, take all its parameters from the selenium driver
        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                cookie_name = cookie.split('=')[0]
                cookie_value = "=".join(cookie.split('=')[1:])
                c = Cookie.get(cookie_name, cookie_value, request.url)
                if c:
                    request_cookies.append(c)
                else:
                    browser_cookie = self.driver.get_cookie(cookie_name)
                    if (browser_cookie is not None) and (browser_cookie["value"] == cookie_value) and Cookie.checkPath(browser_cookie, request.url):
                        c = Cookie.insert(browser_cookie)
                        if c:
                            request_cookies.append(c)
                            break
                        
            del request.headers['cookie']

        request_headers = []
        for k,v in request.headers.items():
            h = Header.get(k,v) or Header.insert(k,v)
            if h:
                request_headers.append(h)

        return Request.insert(request.url, request.method, request_headers, request_cookies, request.body.decode('utf-8', errors='ignore'))

    # Inserts in the database the response if url belongs to the scope
    # request is a request selenium-wire object
    def __processResponse(self, request, processed_request):
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
                c = Cookie.insertRaw(raw_cookie, request.url)
                if c:
                    response_cookies.append(c)

            del response.headers['set-cookie']
        
        response_headers = []
        for k,v in response.headers.items():
            h = Header.get(k,v) or Header.insert(k,v)
            if h:
                response_headers.append(h)

        body = decode(response.body, response.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
        body = re.sub('\s+(?=<)', '', body)

        resp = Response.get(response.status_code, body) or Response.insert(response.status_code, body, response_headers, response_cookies, processed_request)
        if resp:
            resp.link(processed_request)

        return resp

    def __processScript(self, request, main_response):
        if not request.response:
            return False

        path = Path.insert(request.url)
        if not path:
            return False

        content = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode('utf-8', errors='ignore')
        s = Script.get(content) or Script.insert(content)
        if not s:
            return False
        
        s.link(path)
        
        if main_response is not None:
            s.link(main_response)

        return True

    # Traverse the HTML looking for paths to crawl
    def __parseHTML(self, parent_url, response):
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

                if self.isCrawlable(url, 'GET'):
                    self.__crawl(url, 'GET')
                
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
                    
                if method == 'POST':
                    content_type = "application/x-www-form-urlencoded"
               
                # If form method is not POST, append data to URL as params and set data and content type to None
                else:
                    content_type = None
                    if data:
                        if url.find('?'):
                            url = url.split('?')[0]
                        url += '?' + data
                        data = None

                if self.isCrawlable(url, method, content_type, data):
                    self.__crawl(url, method, data)

            elif element.name == 'script':
                if (element.get('type')) and (element.get('type') != "application/javascript") and (element.get('type') != "application/ecmascript"):
                    continue
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    s = Script.get(element.string) or Script.insert(element.string)
                    if s:
                        s.link(response)

                else:
                    src = urljoin(parent_url, src)
                    path = Path.insert(src)
                    if not path:
                        continue

                    try:
                        content = requests.get(src, verify=False).text
                    except requests.exceptions.ConnectionError:
                        # If site is not available
                        pass

                    if content:
                        s = Script.get(content) or Script.insert(content)
                        if s:
                            s.link(path)
                            s.link(response)

            elif element.name == 'iframe':
                path = element.get('src')
                if not path:
                    continue

                url = urljoin(parent_url, path)

                if self.isCrawlable(url, 'GET'):
                    self.__crawl(url, 'GET')   

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

                    # Wait until request is received by selenium or until it times out
                    i = 0
                    while (len(self.driver.requests) == 0) and (i < config.TIMEOUT):
                        time.sleep(1)
                        i += 1

                    #Check if requests have been made
                    if len(self.driver.requests) > 0:
                        req = self.driver.requests[0]
                        data = req.body.decode('utf-8', errors='ignore')
                        
                        if self.isCrawlable(req.url, req.method, req.headers.get_content_type(), data):
                            self.__crawl(req.url, req.method, data)

                    #Else, check if at least the url has changed
                    elif self.driver.current_url != parent_url:
                        
                        if self.isCrawlable(self.driver.current_url, 'GET'):
                            self.__crawl(self.driver.current_url, 'GET')

                except:
                    continue
   
    def __sendScreenshot(self, path):
        filename = config.SCREENSHOT_FOLDER + "".join(str(path).split('?')[0]).replace('://', '_').replace('/', '_') + '-' + ''.join(random.choices(string.ascii_lowercase, k=10)) + '.png'
        if not self.driver.save_screenshot(filename):
            return False

        self.send_file(filename, "crawler")
        return True

    # Main method of crawler
    def __crawl(self, parent_url, method, data=None):
        # If execution is stopped
        if self.stop.is_set():
            return

        path = Path.insert(parent_url)
        if not path:
            return

        self.send_msg('[%s] %s' % (method,parent_url), "crawler")

        self.__updateCookies(parent_url)
        self.__updateLocalStorage(parent_url)

        # Request resource
        try:
            # Delete all previous requests so they don't pollute the results
            del self.driver.requests

            self.applyDelay()

            if method == 'GET':
                if path.domain.headers:
                    # If we try to acces headers from interceptor by domain.headers, when another variable
                    # named domain is used, it will overwrite driver.headers so it will throw an exception.
                    # We need interceptor_headers to store the headers for the interceptor
                    interceptor_headers = path.domain.headers
                    def interceptor(request):
                        for header in interceptor_headers:
                            try:
                                del request.headers[header.key]
                            except:
                                pass
                            request.headers[header.key] = header.value
                    self.driver.request_interceptor = interceptor


                self.driver.get(parent_url)
            else:
                self.__request(parent_url, method, data, path.domain.headers)

        except selenium.common.exceptions.InvalidSessionIdException:
            # If InvalidSessionIdException is thrown, the driver needs to be restarted.
            # Also call __crawl again with same args so that execution continues
            self.driver.quit()
            self.driver = webdriver.Chrome(options=self.opts)
            self.driver.set_page_load_timeout(config.TIMEOUT)
            self.__crawl(parent_url, method, data)
            return

        except selenium.common.exceptions.TimeoutException:
            self.send_msg("Timeout exception requesting %s" % parent_url, "crawler")

        except:
            self.send_error_msg(traceback.format_exc(), "crawler")

        self.updateLastRequest()

        # List of responses to analyze
        responses2analyze = []

        main_request = None
        main_response = None

        # Process all requests
        for request in self.driver.iter_requests():
            extension = splitext(urlparse(request.url).path)[1].lower()

            # Scripts
            if (extension in config.SCRIPT_EXTENSIONS) and (request.response is not None) and (request.response.status_code == 200):
                if self.__processScript(request, main_response):
                    self.send_msg('[SCRIPT] %s' % (request.url), "crawler")

            # Main request
            # Main request doesn't have to be the first one that the iterator returns, since the order depends
            # on depends on when did they become available for the driver to get them. So in order to check which 
            # is the first one, it checks if request.url == parent_url
            elif request.url == parent_url and main_request is None and main_response is None:

                main_request = self.__processRequest(request)
                if not main_request:
                    self.send_msg("[ERROR] Couldn't process request for %s" % (request.url), "crawler")
                    return

                main_response = self.__processResponse(request, main_request)
                if not main_response:
                    self.send_msg("[ERROR] Didn't get response for %s" % (request.url), "crawler")
                    return

                # Follow redirect if 3xx response is received
                code = main_response.code
                if code//100 == 3:
                    if code == 304:
                        self.send_msg("[304]: Chached response", "crawler")
                    else:
                        redirect_to = main_response.getHeader('location').value
                        if not redirect_to:
                            self.send_msg("[%d][ERROR] location header is not present" % code, "crawler")
                        else:
                            redirect_to = urljoin(parent_url, redirect_to)

                            if code != 307 and code != 308:
                                method = 'GET'
                                data = None

                            if self.isCrawlable(redirect_to, method, data=data):
                                self.send_msg("[%d] Redirect to %s" % (code, redirect_to), "crawler")
                                self.__crawl(redirect_to, method, data)
                            elif not Domain.checkScope(urlparse(redirect_to).netloc):
                                self.send_msg("[%d] Redirect to %s [OUT OF SCOPE]" % (code, redirect_to), "crawler")

                        return

                self.send_msg("[%d] %s" % (code, request.url), "crawler")

                # Send screenshot once we know if the request was redirected or not
                self.__sendScreenshot(main_request.path)

                responses2analyze.append({'url': parent_url, 'response':main_response})

            # Dynamic requests
            elif self.isCrawlable(request.url, request.method, request.headers.get('content-type'), request.body.decode('utf-8', errors='ignore')):
                self.send_msg('[%s][DYNAMIC] %s' % (request.method, request.url), "crawler")
                
                req = self.__processRequest(request)
                resp = self.__processResponse(request, req)
                if resp:
                    self.send_msg("[%d][DYNAMIC] %s" % (resp.code, request.url), "crawler")
                    # If dynamic request responded with HTML, send it to analize
                    if (resp.body is not None) and (resp.getHeader('content-type') is not None) and (resp.getHeader('content-type').value == "text/html"):
                        responses2analyze.append({'url': request.url, 'response':resp})

        # Process all captured responses that are valid HTML
        for r in responses2analyze:
            self.__parseHTML(r['url'], r['response'])

    def run(self):
        # Generator for domains
        domains = Domain.yieldAll()
        while not self.stop.is_set():

            # Get url from queue. If queue is empty, get domain from database. If it's also
            # empty, sleep for 5 seconds and start again
            if len(self.queue) > 0:
                url = self.queue.pop(0)

                # Check if it's up before crawling it
                try:
                    requests.get(url, allow_redirects=False, verify=False)
                except requests.exceptions.ConnectionError:
                    self.send_error_msg(traceback.format_exc(), "crawler")
                    continue

                domain = Domain.get(urlparse(url).netloc)
                if (domain is None) and (Domain.checkScope(urlparse(url).netloc)):
                    domain = Domain.insert(urlparse(url).netloc)
                    if not domain:
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
                    self.send_msg('Cannot request %s' % domain_name, "crawler")
                    continue

            # If url already in database, skip
            if Request.check(url, 'GET'):
                continue

            # Set module as active
            self.setActive()

            self.send_msg("Started crawling %s" % url, "crawler")
            
            self.__crawl(url, 'GET')

            self.send_msg('Finished crawling %s' % url, "crawler")

            # Set module as active
            self.setInactive()