import threading, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import database

class Crawler (threading.Thread):
    def __init__(self, db):
        threading.Thread.__init__(self)
        self.db = db
        self.get_crawled = []   # List to store crawled urls by GET
        self.post_crawled = {}  # Dict to store crawled urls with data keys by POST
        self.protocol = 'http'

    def run(self, domain):
        self.domain = domain
        print("[+] Crawling %s" % self.domain)

        try:
            # Check for https
            initial_request = requests.get(self.protocol + '://' + self.domain,  allow_redirects=False)
            if initial_request.is_permanent_redirect and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                self.protocol = 'https'
        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (self.protocol + '://' + self.domain, e))
            return

        self.__crawl('GET', self.protocol + "://" + self.domain, None)

        print("[+] Finished crawling %s" % self.domain)

    def __crawl(self, method, parent_url, data):
        self.get_crawled.append(parent_url)

        try:
            if (method == 'GET'):
                r = requests.get(parent_url)
            elif (method == 'POST'):
                r = requests.post(parent_url, data)

        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (parent_url, e))
            return

        response = self.db.insertResponse(self.db.insertPath(parent_url), method, r, data)

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

                if self.db.checkDomain(domain) and url not in self.get_crawled:
                    self.__crawl('GET', url, None)
                
            elif element.name == 'form':
                form_id = element.get('id')
                method = element.get('method')
                action = element.get('action') if element.get('action') is not None else ''

                url = urljoin(parent_url, action)
                domain = urlparse(url).netloc

                if self.db.checkDomain(domain):
                    # Parse input, select and textarea (textarea is outside forms, linked by form attribute)
                    data = {}
                    textareas = parser('textarea', form=form_id) if form_id is not None else []
                    for input in element(['input','select']) + textareas:
                        # Skip submit buttons
                        if input.get('type') != 'submit':
                            # If value is empty, put '1337'
                            data[input.get('name')] = input.get('value') if input.get('value') is not None and input.get('value') != '' else '1337'

                    # If form method is GET, append data to URL as params and set data to None
                    if method == 'GET' and len(data) > 0:
                        url += '?'
                        for key, value in data.items():
                            if key not in url:
                                url += key + '=' + value
                                url += '&'
                        url = url[:-1]

                        data = None

                    if method == 'GET' and url not in self.get_crawled:
                        self.get_crawled.append(url)
                    elif method == 'POST' and (self.post_crawled.get(url) is None or data.keys() not in self.post_crawled.get(url)):
                        if self.post_crawled.get(url) is None:
                            self.post_crawled[url] = [data.keys()]
                        elif data.keys() not in self.post_crawled.get(url):
                            self.post_crawled.get(url).append(data.keys())
                    else:
                        continue

                    self.__crawl(method, url, data)

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

                    # get script