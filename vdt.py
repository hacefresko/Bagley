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
    def run(self):
        while True:
            line = scope_file.readline()
            if not line:
                time.sleep(5)
                continue

            domain = line.split(' ')[0]

            if domain not in SCOPE:
                SCOPE.append(domain)
            
            for path in self.__crawl(domain):
                URLS_LOCK.acquire()
                print(path)
                DISCOVERED_URLS.append(path)
                URLS_LOCK.release()

    # Returns a generator object of paths to iterate over and it stores them
    def __crawl(self, parent_domain):
        to_crawl = ["http://" + parent_domain]
        crawled = []

        print("[+] Crawling %s" % parent_domain)

        while to_crawl:
            url = to_crawl.pop()
            crawled.append(url)
            try:
                r = requests.get(url)
            except Exception as e:
                print('[x] Exception ocurred when requesting %s: %s' % (url, e))
                continue

            parser = BeautifulSoup(r.text, 'html.parser')
            for link in parser.find_all('a'):
                path = link.get('href')

                if path == '#' or path is None:
                    continue
                
                if path[:2] == '//':
                    path = 'http:' + path

                domain = urlparse(path).netloc
                if domain in SCOPE and path not in crawled:
                    to_crawl.append(path)
                    yield path

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

    crawler = Crawler()
    crawler.start()