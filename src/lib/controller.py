from concurrent.futures import thread
import threading, logging, json
import lib.modules, lib.bot, config

from lib.entities import *

class Controller:
    def __init__(self):
        self.stopThread = threading.Event()

        self.rps = config.REQ_PER_SEC
        self.active_modules = 0
        self.lock = threading.Lock()

        crawler = lib.modules.Crawler(self.stopThread, self.rps, self.active_modules, self.lock)
        finder = lib.modules.Finder(self.stopThread, self.rps, self.active_modules, self.lock, crawler)
        injector = lib.modules.Injector(self.stopThread, self.rps, self.active_modules, self.lock)
        dynamic_analyzer = lib.modules.Dynamic_Analyzer(self.stopThread, self.rps, self.active_modules, self.lock)
        static_analyzer = lib.modules.Static_Analyzer(self.stopThread, crawler)

        self.modules = {
            "crawler": crawler,
            "finder": finder,
            "injector": injector,
            "dynamic_analyzer": dynamic_analyzer,
            "static_analyzer": static_analyzer
        }

        # Check dependences for the modules
        for m in self.modules.values():
            m.checkDependences()           

    # Methods to communicate with traffic controller

    def getRPS(self):
        return self.rps

    def setRPS(self, rps):
        if type(rps) != int:
            return False
        
        self.rps = rps
        for m in self.modules.values():
            m.rps = rps

        return True

    # Methods to communicate with modules

    def start(self):
        for m in self.modules.values():
            m.start()

    def stop(self):
        self.stopThread.set()
        for m in self.modules.values():
            m.join()

    def addToQueue(self, url):
        self.modules.get("crawler").addToQueue(url)

    # Methods to communicate with entities

    def addDomain(self, domain, options=None):
        if Domain.check(domain):
            self.send_msg("Domain %s already in database" % domain, "terminal")
            return -1

        if options:
            try:
                opts = json.loads(options)
            except:
                self.send_msg("Couldn't parse options:\n %s" % options, "terminal")

        d = Domain.insert(domain)
        if not d:
            self.send_msg("Couldn't add domain %s" % domain, "terminal")
            return -1

        if options:
            # Get and insert headers
            if opts.get('headers'):
                for k,v in opts.get('headers').items():
                    header = Header.insert(k,v, False)
                    if header:
                        d.addHeader(header)
                        self.send_msg("Added header %s" % str(header), "terminal")

            # Get and insert cookies
            if opts.get('cookies'):
                for c in opts.get('cookies'):
                    cookie = Cookie.insert(c)
                    if cookie:
                        self.modules.get("crawler").addCookie(cookie)

            # If group of subdomains specified, get out of scope domains
            if domain[0] == '.':
                excluded = opts.get('excluded')
                if excluded:
                    for e in excluded:
                        if Domain.insertOutOfScope(e):
                            self.send_msg("Added domain %s out of scope" % str(e), "terminal")

            # Add to queue
            if opts.get("queue"):
                for q in opts.get("queue"):
                    self.addToQueue(q)
                    self.send_msg("Added %s to queue" % str(q), "terminal")
            

        self.send_msg("Added domain %s" % str(d), "terminal")

    def getDomains(self):
        return Domain.getAll()

    def getPaths(self, domain):
        d = Domain.get(domain)
        if not d:
            return None
        
        return d.getStructure()

    # Methods to communicate with bot

    @staticmethod
    def send_msg(msg, channel):
        logging.info("[%s] %s", channel, msg)
        lib.bot.dispatch_msg(msg, channel)

    @staticmethod
    def send_error_msg(msg, channel):
        logging.error(msg)
        lib.bot.dispatch_msg(msg, channel)
        lib.bot.dispatch_msg(msg, "errors")

    @staticmethod
    def send_vuln_msg(msg, channel):
        logging.critical(msg)
        sent = 0
        while sent < len(msg):
            m = msg[sent:sent+1000]
            sent += len(m)
            lib.bot.dispatch_msg(m, channel)
            lib.bot.dispatch_msg(m, "vulnerabilities")
        
    @staticmethod
    def send_img(filename, channel):
        logging.info("[%s] Sent image %s", channel, filename)
        lib.bot.dispatch_img(filename, channel)