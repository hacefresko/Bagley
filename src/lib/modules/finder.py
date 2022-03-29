import subprocess, json, shutil, time, socket, os, datetime, requests
from urllib.parse import urljoin, urlparse

import config
from lib.modules.module import Module
from lib.entities import *
import lib.controller

class Finder(Module):
    def __init__(self, stop, rps, active_modules, lock, crawler):
        super().__init__(["gobuster", "subfinder", "gau"], stop, rps, active_modules, lock)
        self.crawler = crawler
        self.analyzed = []
        self.updateDelay()

    def checkDependences(self):
        for f in [config.DIR_FUZZING, config.DOMAIN_FUZZING]:
            if not os.path.exists(f):
                print('%s from config file not found' % f)
                return False
        return super().checkDependences()

    def __fuzzPaths(self, path, headers, cookies, errcodes=[]):
        url = str(path)
        # Crawl all urls on the database that has not been crawled
        if self.crawler.isCrawlable(url):
            self.crawler.addToQueue(url)

        command = [shutil.which('gobuster'), 'dir', '-q', '-k', '-t', '1', '-w', config.DIR_FUZZING, '-u', url, '--delay', str(int(self.getDelay()*1000))+'ms', '--random-agent', '-r']

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
            lib.controller.Controller.send_msg("Fuzzing path %s" % url, "finder")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                code = int(line.split('(')[1].split(')')[0].split(':')[1].strip())
                discovered = urljoin(url, ''.join(line.split(' ')[0].split('/')[1:]))
                if (code != 404) and (code != 400) and self.crawler.isCrawlable(discovered):
                        lib.controller.Controller.send_msg("PATH FOUND: Queued %s to crawler" % discovered, "finder")
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
                    self.__fuzzPaths(url, headers, cookies, errcodes)
                except:
                    return

    def __findPaths(self, domain):
        command = [shutil.which('gau')]

        lib.controller.Controller.send_msg("Finding paths for domain %s" % str(domain), "finder")
        
        for url in subprocess.run(command, capture_output=True, encoding='utf-8', input=str(domain)).stdout.splitlines():
            if self.crawler.isCrawlable(url):
                self.applyDelay()

                ok = requests.get(url).ok

                self.updateDelay()
                
                if ok:
                    lib.controller.Controller.send_msg("PATH FOUND: Queued %s to crawler" % url, "finder")
                    self.crawler.addToQueue(url)

    def __fuzzSubDomain(self, domain, errcodes=[]):
        command = [shutil.which('gobuster'), 'dns', '-q', '-t', '1', '-w', config.DOMAIN_FUZZING, '-d', str(domain)[1:], '--delay', str(int(self.getDelay()*1000))+'ms']
        # Add errorcodes if specified
        if len(errcodes) != 0:
            command.append('-s')
            command.append(','.join(errcodes))

        lib.controller.Controller.send_msg("Fuzzing domain %s" % str(domain)[1:], "finder")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                discovered = line.split('Found: ')[1].rstrip()
                if Domain.checkScope(discovered) and not Domain.get(discovered):
                    lib.controller.Controller.send_msg("DOMAIN FOUND: Inserted %s to database" % discovered, "finder")
                    Domain.insert(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')
        
        # Collect errors if execution fails
        if process.poll() != 0:
            error = process.stderr.readline().decode('utf-8', errors='ignore')
            lib.controller.Controller.send_msg(error, "finder")
            # If errorcodes must be specified to gobuster
            if 'Error: the server returns a status code that matches the provided options for non existing urls' in error:
                try:
                    # Repeat the execution with errorcodes
                    errcode = error.split('=>')[1].split('(')[0].strip()
                    errcodes.append(errcode)
                    self.__fuzzSubDomain(str(domain), errcodes)
                except:
                    return

    def __findSubDomains(self,domain):
        # Rate is limited to 1 always because if doesn't, it adds too much traffic and ISPs are very greedy
        command = [shutil.which('subfinder'), '-oJ', '-nc', '-all', '-d', str(domain)[1:], '-rl', '1']

        lib.controller.Controller.send_msg("Finding subdomains for %s" % str(domain)[1:], "finder")

        for line in subprocess.run(command, capture_output=True, encoding='utf-8', input=str(domain)).stdout.splitlines():
            discovered = json.loads(line).get('host')
            # Sometimes output from some sources is Domain\nDomain\nDomain...
            for d in discovered.split('\n'):
                try:
                    # Check if domain really exist, since subfinder does not check it
                    socket.gethostbyname(d)
                    if Domain.checkScope(d) and not Domain.get(discovered):
                        lib.controller.Controller.send_msg("DOMAIN FOUND: Inserted %s to database" % d, "finder")
                        Domain.insert(d)
                except:
                    continue
        
    def run(self):
        directories = Path.yieldDirectories()
        domains = Domain.yieldAll()
        while not self.stop.is_set():
            try:
                domain = next(domains)
                if domain:
                    self.setActive()
                    if domain.name[0] == '.':
                        self.__findSubDomains(domain)
                        self.__fuzzSubDomain(domain)
                    else:
                        self.__findPaths(domain)

                directory = next(directories)
                if directory:
                    self.setActive()
                    self.__fuzzPaths(directory, directory.domain.headers, directory.domain.cookies)

                if not domain and not directory:
                    self.setInactive()
                    time.sleep(5)
            except:
                lib.controller.Controller.send_error_msg(utils.getExceptionString(), "finder")