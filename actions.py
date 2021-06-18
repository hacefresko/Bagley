import threading, time, requests, subprocess, sqlite3, json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from database import DB
from entities import *
from seleniumwire import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

class Crawler (threading.Thread):
    def __init__(self, scope_file):
        threading.Thread.__init__(self)
        self.scope = scope_file

        # Init selenium driver
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
        opts = Options()
        opts.headless = True
        self.driver = webdriver.Chrome(desired_capabilities=capabilities, options = opts)

    def run(self):
        db = DB.getConnection()
        while True:
            line = self.scope.readline()
            if not line:
                time.sleep(5)
                continue
            
            domain = line.split(' ')[0]

            if not Domain.checkDomain(domain):
                Domain.insertDomain(domain)

            try:
                protocol = 'http'
                initial_request = requests.get(protocol + '://' + domain,  allow_redirects=False)
                if initial_request.is_permanent_redirect and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                    protocol = 'https'

                self.__crawl(protocol + '://' + domain, 'GET', None)
            except Exception as e:
                print('[x] Exception ocurred when crawling %s: %s' % (protocol + '://' + domain, e))
                continue
            finally:
                print("[+] Finished crawling %s" % domain)

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

    def __crawl(self, parent_url, method, data):
        print("[+] Crawling %s [%s]" % (parent_url, method))

        domain = urlparse(parent_url).netloc

        try:
            if method == 'GET':
                self.driver.get(parent_url)
            elif method == 'POST':
                self.__post(parent_url, data)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (parent_url, e))
            return

        request = self.driver.requests[0]
        response = request.response

        request_cookies = []
        if request.headers.get('cookie'):
            for cookie in request.headers.get('cookie').split('; '):
                c = Cookie.getCookie(cookie.split('=')[0], cookie.split('=')[1], parent_url)
                if c:
                    request_cookies.append()
            del request.headers['cookie']

        request_headers = []
        for k,v in request.headers.items():
            request_headers.append(Header.insertHeader(k, v))

        request = Request.insertRequest(parent_url, method, request_headers, request_cookies, data)

        response_cookies = []
        if response.headers.get_all('set-cookie'):
            for raw_cookie in response.headers.get_all('set-cookie'):
                # Default values for cookie attributes
                cookie = {'expires':'session', 'max-age':'session', 'domain': domain, 'path': '/', 'secure': False, 'httponly': False, 'samesite':'lax'}
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

        response = Response.insertResponse(response.status_code, response.body.decode('utf-8'), response_headers, response_cookies, request)


class Sqlmap (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        self.db = DB.VDT_DB()
        try:
            self.db.connect()
        except:
            print('[x] Couldn\'t connect to the database')


        requests_to_skip = []
        id = 1
        while True:
            try:
                if id in requests_to_skip:
                    id += 1
                    continue
                request = self.db.getRequest(id)
                if request is None:
                    time.sleep(2)
                    continue
                if len(request.get('url').split('?')) < 2 and request.get('data') is None:
                    id += 1
                    continue
                # Merge both lists
                requests_to_skip = [*self.db.getRequestWithSameKeys(id), *requests_to_skip]
            except sqlite3.OperationalError:
                continue

            id += 1

            if request.get('method') == 'POST':
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  request.get("url"), '--data', request.get("data")]
            else:
                command = ['sqlmap', '-v', '0', '--flush-session', '--batch', '-u',  request.get("url")]

            result = subprocess.run(command, capture_output=True, encoding='utf-8')

            if "---" in result.stdout:
                print("[+] SQL injection found in %s" % request.get('url'))
                print(result.stdout)