import threading, subprocess, json, shutil, time, socket
from urllib.parse import urljoin

import config
from lib.entities import *

class Discoverer(threading.Thread):
    def __init__(self, stop, crawler):
        threading.Thread.__init__(self)
        self.crawler = crawler
        self.stop = stop

    def __fuzzPath(self, url, headers, cookies, errcodes=[]):
        # Crawl all urls on the database that has not been crawled
        if not Request.check(url, 'GET'):
            self.crawler.addToQueue(url)

        delay = str(int((1/config.REQ_PER_SEC) * 1000)) + 'ms'
        command = [shutil.which('gobuster'), 'dir', '-q', '-w', config.DIR_FUZZING, '-u', url, '--delay', delay]

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

        # If function hasn't been called by itself
        if len(errcodes) == 0:
            print("[+] Fuzzing path %s" % url)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                code = int(line.split('(')[1].split(')')[0].split(':')[1].strip())
                discovered = urljoin(url, ''.join(line.split(' ')[0].split('/')[1:]))
                if int(code / 100) != 4 and not Request.check(discovered, 'GET'):
                    print("[FOUND] Path found! Queued %s to crawler" % discovered)
                    Path.insert(discovered)
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
        command = [shutil.which('gobuster'), 'dns', '-q', '-w', config.DOMAIN_FUZZING, '-d', domain]
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
                    print('[FOUND] Domain found! Inserted %s to database' % discovered)
                    Domain.insert(discovered)
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
                # Sometimes output frome some sources is Domain\nDomain\nDomain...
                for d in discovered.split('\n'):
                    try:
                        # Check if domain really exist, since subfinder does not check it
                        socket.gethostbyname(d)
                        if Domain.checkScope(d):
                            print('[FOUND] Domain found! Inserted %s to database' % d)
                            Domain.insert(d)
                            self.__subdomainTakeover(d)
                    except:
                        continue
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')

    def __subdomainTakeover(self, domain):
        command = [shutil.which('subjack'), '-a', '-m', '-d', domain]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')

        if result.stdout != '':
            Vulnerability.insert('Subdomain Takeover', result.stdout)
            print('[TAKEOVER] Subdomain Takeover found at %s!\n\n%s\n' % (domain, result.stdout))
        
    def run(self):
        directories = Path.yieldDirectories()
        domains = Domain.yieldAll()
        while not self.stop.is_set():
            domain = next(domains)
            if domain and domain.name[0] == '.':
                self.__findSubDomains(domain.name[1:])
                self.__fuzzSubDomain(domain.name[1:])
            else:
                directory = next(directories)
                if not directory:
                    time.sleep(5)
                    continue
                self.__fuzzPath(str(directory), directory.domain.headers, directory.domain.cookies)