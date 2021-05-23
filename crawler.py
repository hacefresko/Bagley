import threading, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import database

class Crawler (threading.Thread):
    def __init__(self, db):
        threading.Thread.__init__(self)
        self.db = db
        self.get_crawled = []
        self.post_crawled = []
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
        

        self.db.insertResponse(self.db.insertPath(parent_url), 'GET', r)

        parser = BeautifulSoup(r.text, 'html.parser')
        for link in parser.find_all('a'):
            path = link.get('href') 

            if path == '#' or path is None:
                return

            url = urljoin(parent_url, path)
            domain = urlparse(url).netloc

            if self.db.checkDomain(domain) and url not in self.get_crawled:
                self.__crawl('GET', url, None)

        for form in parser.find_all('form'):
            method = form.get('method')
            action = form.get('action') if form.get('action') is not None else ''

            url = urljoin(parent_url, action)
            domain = urlparse(url).netloc

            # Need to parse input, textarea and select

            