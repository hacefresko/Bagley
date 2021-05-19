import os, signal, datetime, getopt, sys, time, requests, threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from multiprocessing import set_start_method

set_start_method("spawn")

# List of domains in scope
SCOPE = []

# Map of urls for each domain
DISCOVERED_URLS = []
URLS_LOCK = threading.Lock()


# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n[x] SIGINT: Exiting...')
    scope_file.close()
    quit()
signal.signal(signal.SIGINT, sigint_handler)

class Crawler (threading.Thread):
    def __init__(self, scope_file):
        threading.Thread.__init__(self)
        self.scope_file = scope_file
        self.crawled = []
        self.protocol = 'http'

    def run(self):
        while True:
            line = self.scope_file.readline()
            if not line:
                time.sleep(5)
                continue

            domain = line.split(' ')[0]

            if domain not in SCOPE:
                SCOPE.append(domain)
            
            print("[+] Crawling %s" % domain)

            initial_request = requests.get(self.protocol + '://' + domain,  allow_redirects=False)
            if initial_request.status_code == 301 and urlparse(initial_request.headers.get('Location')).scheme == 'https':
                self.protocol = 'https'

            self.__crawl(self.protocol + "://" + domain)

            print("[+] Finished crawling %s" % domain)

    def __crawl(self, parent_url):
        self.crawled.append(parent_url)

        try:
            r = requests.get(parent_url)
        except Exception as e:
            print('[x] Exception ocurred when requesting %s: %s' % (url, e))
            return

        parser = BeautifulSoup(r.text, 'html.parser')
        for link in parser.find_all('a'):
            path = link.get('href') 

            if path == '#' or path is None:
                return

            path = urljoin(parent_url, path)
            domain = urlparse(path).netloc

            params = urlparse(path).query.split('&')
            if params[0]:
                new_params = ''
                for param in params:
                    value = param.split('=')[0]
                    new_params += value + "=1337&"
                new_params = new_params[:-1]
                path = urlparse(path)._replace(query=new_params).geturl()

            if domain in SCOPE and path not in self.crawled:

                URLS_LOCK.acquire()
                DISCOVERED_URLS.append(path)
                URLS_LOCK.release()

                self.__crawl(path)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'D:')

        for opt, arg in opts:
            if opt == '-D':
                scope_file_name = arg
                scope_found = True

        if not scope_found or scope_file_name == '':
            raise Exception
            
    except Exception:
        print(os.path.basename(__file__) + ' -D <scope file>')
        exit()

    print("[+] Starting time: %s" % datetime.datetime.now())
    print("[+] Scope file: %s" % scope_file_name)

    try:
        scope_file = open(scope_file_name, 'r')
    except FileNotFoundError:
        print('[x] Scope file not found')
        exit()

    # Build domains list for first time
    for line in scope_file.readlines():
        if line != '\n':
            SCOPE.append(line.split(' ')[0])
    scope_file.seek(0, 0)

    crawler = Crawler(scope_file)
    crawler.start()

    i=0
    while True:
        URLS_LOCK.acquire()
        try:
            url = DISCOVERED_URLS[i]
        except:
            continue
        finally:
            URLS_LOCK.release()
        i=i+1

        print(url)