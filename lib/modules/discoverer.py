import threading, subprocess
from urllib.parse import urljoin

from config import *
from lib.entities import *

class Discoverer(threading.Thread):
    def __init__(self, crawler):
        threading.Thread.__init__(self)
        self.crawler = crawler

    def __fuzzPath(self, url, headers, cookies):
        # Crawl all urls on the database that has not been crawled
        if not Request.checkRequest(url, 'GET', None, None):
            self.crawler.addToQueue(url)

        delay = str(int((1/REQ_PER_SEC) * 1000)) + 'ms'

        command = ['gobuster', 'dir', '-q', '-w', DIR_FUZZING, '-u', url, '--delay', delay]

        # Add headers
        for header in headers:
            command.append('-H')
            command.append("'" + str(header) + "'")

        # Add cookies
        if cookies:
            command.append('-c')
            cookies = ''
            for cookie in cookies:
                cookies += str(cookie) + ' '
            command.append(cookies)

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            discovered = urljoin(url, line.split(' ')[0])
            if not Request.checkRequest(discovered, 'GET', None, None):
                print("[*] Path found! Queued %s to crawler" % discovered)
                Path.insertPath(discovered)
                self.crawler.addToQueue(discovered)

    def __fuzzDomain(self, domain):
        command = ['gobuster', 'dns', '-q', '-w', DOMAIN_FUZZING, '-d', domain]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            if line == '':
                continue
            discovered = line.split('Found: ')[1].strip()
            print('[*] Domain found! Inserted %s to database' % discovered)
            Domain.insertDomain(discovered)

    def __findSubDomains(self,domain):
        pass


    def run(self):
        directories = Path.getDirectories()
        domains = Domain.getDomains()
        while True:
            domain = next(domains)
            if domain and domain.name[0] == '.':
                print("[+] Finding subdomains for %s" % domain.name[1:])
                self.__findSubDomains(domain.name[1:])
                print("[+] Fuzzing domain %s" % domain.name[1:])
                self.__fuzzDomain(domain.name[1:])
            else:
                directory = next(directories)
                if not directory:
                    time.sleep(5)
                    continue
                
                print("[+] Fuzzing path %s" % directory)
                self.__fuzzPath('http://' + str(directory), directory.domain.headers, directory.domain.cookies)
                self.__fuzzPath('https://' + str(directory), directory.domain.headers, directory.domain.cookies)