import threading, subprocess, json, shutil
from urllib.parse import urljoin

from config import *
from lib.entities import *

class Discoverer(threading.Thread):
    def __init__(self, crawler):
        threading.Thread.__init__(self)
        self.crawler = crawler

    def __fuzzPath(self, url, headers, cookies, errcodes=[]):
        # Crawl all urls on the database that has not been crawled
        if not Request.checkRequest(url, 'GET', None, None):
            self.crawler.addToQueue(url)

        delay = str(int((1/REQ_PER_SEC) * 1000)) + 'ms'
        command = [shutil.which('gobuster'), 'dir', '-q', '-w', DIR_FUZZING, '-u', url, '--delay', delay]

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

        # Add errorcodes if specified
        if len(errcodes) != 0:
            command.append('-b')
            command.append(','.join(errcodes))

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                code = int(line.split('(')[1].split(')')[0].split(':')[1].strip())
                discovered = urljoin(url, ''.join(line.split(' ')[0].split('/')[1:]))
                if int(code / 100) != 4 and not Request.checkRequest(discovered, 'GET', None, None):
                    print("[*] Path found! Queued %s to crawler" % discovered)
                    Path.insertPath(discovered)
                    self.crawler.addToQueue(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')
        
        # Collect errors if execution fails
        if process.poll() != 0:
            error = process.stderr.readline().decode('utf-8', errors='ignore')
            # If errorcodes must be specified to gobuster
            if 'Error: the server returns a status code that matches the provided options for non existing urls' in error:
                try:
                    errcode = error.split('=>')[1].split('(')[0].strip()
                    errcodes.append(errcode)
                    self.__fuzzPath(url, headers, cookies, errcodes)
                except:
                    return

    def __fuzzSubDomain(self, domain, errcodes=[]):
        command = [shutil.which('gobuster'), 'dns', '-q', '-w', DOMAIN_FUZZING, '-d', domain]
        # Add errorcodes if specified
        if len(errcodes) != 0:
            command.append('-b')
            command.append(','.join(errcodes))

        print("[+] Fuzzing domain %s" % domain)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                discovered = line.split('Found: ')[1].rstrip()
                if Domain.checkScope(discovered):
                    print('[*] Domain found! Inserted %s to database' % discovered)
                    Domain.insertDomain(discovered)
                    self.__subdomainTakeover(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')
        
        # Collect errors if execution fails
        if process.poll() != 0:
            error = process.stderr.readline().decode('utf-8', errors='ignore')
            # If errorcodes must be specified to gobuster
            if 'Error: the server returns a status code that matches the provided options for non existing urls' in error:
                try:
                    # Repeat the execution with errorcodes
                    errcode = error.split('=>')[1].split('(')[0].strip()
                    errcodes.append(errcode)
                    self.__fuzzPath(domain, errcodes)
                except:
                    return

    def __findSubDomains(self,domain):
        command = [shutil.which('subfinder'), '-oJ', '-nC', '-silent', '-all', '-d', domain]

        print("[+] Finding subdomains for %s" % domain)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                discovered = json.loads(line).get('host')
                if Domain.checkScope(discovered):
                    print('[*] Domain found! Inserted %s to database' % discovered)
                    Domain.insertDomain(discovered)
                    self.__subdomainTakeover(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')

    def __subdomainTakeover(self, domain):
        command = [shutil.which('subjack'), '-a', '-m', '-d', domain]
        
        print("[+] Checking if subdomain %s is available for takeover" % domain)

        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.stdout != '':
            Vulnerability.insertVuln('Subdomain Takeover', result.stdout)
            print('[*] Subdomain Takeover found at %s!\n\n%s\n' % (domain, result.stdout))
        
    def run(self):
        directories = Path.getDirectories()
        domains = Domain.getDomains()
        while True:
            domain = next(domains)
            if domain and domain.name[0] == '.':
                self.__findSubDomains(domain.name[1:])
                self.__fuzzSubDomain(domain.name[1:])
            else:
                directory = next(directories)
                if not directory:
                    time.sleep(5)
                    continue
                
                print("[+] Fuzzing path %s" % directory)
                self.__fuzzPath(str(directory), directory.domain.headers, directory.domain.cookies)