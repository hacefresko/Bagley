import threading, time, requests, subprocess, sqlite3
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from database import DB

class Crawler (threading.Thread):
    def __init__(self, scope_file):
        threading.Thread.__init__(self)
        self.scope = scope_file

    def run(self):
        self.db = DB.VDT_DB()
        try:
            self.db.connect()
        except:
            print('[x] Couldn\'t connect to the database')
            
        while True:
            line = self.scope.readline()
            if not line :
                time.sleep(5)
                continue

            domain = line.split(' ')[0]

            if not self.db.checkDomain(domain):
                self.db.insertDomain(domain)

            try:
                # Check for https
                protocol = 'http'
                initial_request = requests.get(protocol + '://' + domain,  allow_redirects=False)
                if initial_request.is_permanent_redirect and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                    protocol = 'https'

                self.__crawl(protocol + "://" + domain, 'GET', None)
            except Exception as e:
                print('[x] Exception ocurred when crawling %s: %s' % (protocol + '://' + domain, e))
                continue
            finally:
                print("[+] Finished crawling %s" % domain)

    def __crawl(self, parent_url, method, data):
        print("[+] Crawling %s [%s]" % (parent_url, method))
        request = self.db.insertRequest(parent_url, method, data)
        try:
            if (method == 'GET'):
                r = requests.get(parent_url)
            elif (method == 'POST'):
                r = requests.post(parent_url, data)
            else:
                return
            response = self.db.insertResponse(r, request)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (parent_url, e))
            return

        parser = BeautifulSoup(r.text, 'html.parser')
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

                if self.db.checkDomain(domain) and not self.db.checkRequest(url, 'GET', None):
                    self.__crawl(url, 'GET', None)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method').upper() if element.get('method') else 'GET'
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)
                domain = urlparse(url).netloc

                if self.db.checkDomain(domain):
                    # Parse input, select and textarea (textarea is outside forms, linked by form attribute)
                    data = ''
                    textareas = parser('textarea', form=form_id) if form_id is not None else []
                    for input in element(['input','select']) + textareas:
                        # Skip submit buttons
                        if input.get('type') != 'submit' and input.get('name') is not None:
                            # If input is a CSRF value, put CSRFvalue
                            if 'csrf' in input.get('name').lower():
                                data += input.get('name') + "=CSRFvalue&"
                            # If value is empty, put '1337'
                            elif input.get('value') is None or input.get('value') == '':
                                data += input.get('name') + "=1337&"
                            else:
                                data += input.get('name') + "=" + input.get('value') + "&"
                    data = data[:-1]
                        
                    # If form method is GET, append data to URL as params and set data to None
                    if method == 'GET' and len(data) != '':
                        url += '?' + data
                        data = None

                    if not self.db.checkRequest(url, method, data):
                        self.__crawl(url, method, data)

            elif element.name == 'script':
                src = element.get('src')
                if src is None:
                    if element.string is None:
                        continue

                    self.db.insertScript(None, element.string, response)
                else:
                    src = urljoin(parent_url, src)
                    domain = domain = urlparse(src).netloc
                    if not self.db.checkDomain(domain):
                        continue

                    script = requests.get(src)
                    self.db.insertScript(src, script.text, response)

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
           