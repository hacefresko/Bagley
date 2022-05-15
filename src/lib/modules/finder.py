import subprocess, json, shutil, time, socket, os, requests, traceback
from urllib.parse import urljoin

import config, lib.controller
from lib.modules.module import Module
from lib.entities import *

class Finder(Module):
    def __init__(self, controller, stop, rps, active_modules, lock, crawler):
        super().__init__(["gobuster", "subfinder", "gau"], controller, stop, rps, active_modules, lock, ["fuzz_subdomains", "find_subdomains", "fuzz_paths", "find_paths"])
        self.crawler = crawler

    def checkDependencies(self):
        for f in [config.DIR_FUZZING, config.DOMAIN_FUZZING]:
            if not os.path.exists(f):
                print('%s from config file not found' % f)
                return False
        return super().checkDependencies()

    def __fuzzSubDomains(self, domain, errcodes=[]):
        # Gobuster options:
        # dns: Bruteforce subdomains
        # -q: quiet
        # -t: threads -> only 1
        # -w: wordlist to use
        # -d: domain to bruteforce
        # --delay: delay between requests
        command = [shutil.which('gobuster'), 'dns', '-q', '-t', '1', '-w', config.DOMAIN_FUZZING, '-d', str(domain)[1:], '--delay', str(int(self.getDelay()*1000))+'ms']

        # Add errorcodes if specified
        if len(errcodes) != 0:
            command.append('-s')
            command.append(','.join(errcodes))

        self.send_msg("Fuzzing domain %s" % str(domain)[1:], "finder")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                discovered = line.split('Found: ')[1].rstrip()
                if Domain.checkScope(discovered) and not Domain.get(discovered):
                    self.send_msg("DOMAIN FOUND: Inserted %s to database" % discovered, "finder")
                    Domain.insert(discovered, check=True)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')
        
        # Collect errors if execution fails
        if process.poll() != 0:
            error = process.stderr.readline().decode('utf-8', errors='ignore')
            self.send_msg(error, "finder")
            # If errorcodes must be specified to gobuster
            if 'Error: the server returns a status code that matches the provided options for non existing urls' in error:
                try:
                    # Repeat the execution with errorcodes
                    errcode = error.split('=>')[1].split('(')[0].strip()
                    errcodes.append(errcode)
                    self.__fuzzSubDomains(str(domain), errcodes)
                except:
                    return

    def __findSubDomains(self,domain):

        # Subfinder options:
        # -oJ: output in JSON
        # -nc: don't use colors in output
        # -all: use all sources
        # -d: domain to find subdomains for
        # -rl: requests per second = 1 -> Else, it generates too much traffic and ISPs are very greedy and take down the Internet. It doesn't compromise performance
        command = [shutil.which('subfinder'), '-oJ', '-nc', '-all', '-d', str(domain)[1:], '-rl', '1']

        self.send_msg("Finding subdomains for %s" % str(domain)[1:], "finder")

        for line in subprocess.run(command, capture_output=True, encoding='utf-8', input=str(domain)).stdout.splitlines():
            discovered = json.loads(line).get('host')
            # Sometimes output from some sources is Domain\nDomain\nDomain...
            for d in discovered.split('\n'):
                try:
                    # Check if domain really exist, since subfinder does not check it
                    socket.gethostbyname(d)
                    if Domain.checkScope(d) and not Domain.get(discovered):
                        self.send_msg("DOMAIN FOUND: Inserted %s to database" % d, "finder")
                        Domain.insert(d, check=True)
                except:
                    continue
 
    def __fuzzPaths(self, path, errcodes=[]):
        url = str(path)

        # Gobuster options:
        # dir: Bruteforce URL paths
        # -q: quiet
        # -k: don't check SSL certs
        # -t: threads -> only 1
        # -w: wordlist to use
        # -u: URL to bruteforce
        # --delay: delay between requests
        # --random-agent: use random agents on each request
        # -r: follow redirects
        command = [shutil.which('gobuster'), 'dir', '-q', '-k', '-t', '1', '-w', config.DIR_FUZZING, '-u', url, '--delay', str(int(self.getDelay()*1000))+'ms', '--random-agent', '-r']

        # Add headers
        for header in path.domain.headers:
            command.append('-H')
            command.append("'" + str(header) + "'")

        # Add cookies
        if path.domain.cookies:
            command.append('-c')
            cookies = ''
            for cookie in path.domain.cookies:
                cookies += str(cookie) + ' '
            command.append(cookies)

        # Add errorcodes if specified
        if len(errcodes) != 0:
            command.append('-b')
            command.append(','.join(errcodes))

        # If function hasn't been called by itself
        if len(errcodes) == 0:
            self.send_msg("Fuzzing path %s" % url, "finder")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                code = int(line.split('(')[1].split(')')[0].split(':')[1].strip())
                discovered = urljoin(url, ''.join(line.split(' ')[0].split('/')[1:]))
                if (code != 404) and (code != 400) and (code != 500) and self.crawler.isQueueable(discovered):
                        self.send_msg("PATH FOUND: Queued %s to crawler" % discovered, "finder")
                        self.crawler.addToQueue(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')
        
        # If execution fails because errorcodes must be specified to gobuster, run again specifing error codes
        if process.poll() != 0:
            error = process.stderr.readline().decode('utf-8', errors='ignore')
            if 'Error: the server returns a status code that matches the provided options for non existing urls' in error:
                try:
                    errcode = error.split('=>')[1].split('(')[0].strip()
                    errcodes.append(errcode)
                    self.__fuzzPaths(url, errcodes)
                except:
                    return

    def __findPaths(self, domain):
        command = [shutil.which('gau')]

        self.send_msg("Finding paths for domain %s" % str(domain), "finder")
        
        for url in subprocess.run(command, capture_output=True, encoding='utf-8', input=str(domain)).stdout.splitlines():
            if self.crawler.isQueueable(url):
                self.applyDelay()
                
                try:
                    code = requests.get(url, verify=False, allow_redirects=False).status_code
                except requests.exceptions.ConnectionError:
                    # If site is not available
                    pass
                
                self.updateLastRequest()
                
                if (code != 404) and (code != 400) and (code != 500):
                    self.send_msg("PATH FOUND: Queued %s to crawler" % url, "finder")
                    self.crawler.addToQueue(url)
       
    def run(self):
        directories = Path.yieldDirectories()
        domains = Domain.yieldAll()
        while not self.stop.is_set():
            try:
                domain = next(domains)
                if domain:

                    # If domain is a group of subdomains
                    if domain.name[0] == '.':
                        if "find_subdomains" not in domain.excluded:
                            self.setActive()
                            self.__findSubDomains(domain)
                            self.setInactive()

                        if "fuzz_subdomains" not in domain.excluded:
                            self.setActive()
                            self.__fuzzSubDomains(domain)
                            self.setInactive()

                    elif "find_paths" not in domain.excluded:
                        self.setActive()
                        self.__findPaths(domain)
                        self.setInactive()

                directory = next(directories)
                if (directory is not None) and ("fuzz_paths" not in directory.domain.excluded):
                        self.setActive()
                        self.__fuzzPaths(directory)
                        self.setInactive()

                if (domain is None) and (directory is None):
                    time.sleep(5)
                    
            except:
                self.send_error_msg(traceback.format_exc(), "finder")