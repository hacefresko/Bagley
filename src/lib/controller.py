import threading, logging, json
import lib.modules, lib.bot, config

from lib.entities import *
from lib.traffic_controller import TrafficController

class Controller:
    def __init__(self): 
        self.traffic_controller = TrafficController(config.REQ_PER_SEC)
        if not self.traffic_controller:
            return None

        self.stopThread = threading.Event()

        crawler = lib.modules.Crawler(self.stopThread)
        finder = lib.modules.Finder(self.stopThread, crawler)
        injector = lib.modules.Injector(self.stopThread)
        dynamic_analyzer = lib.modules.Dynamic_Analyzer(self.stopThread)
        static_analyzer = lib.modules.Static_Analyzer(self.stopThread)

        self.modules = {
            "crawler": crawler,
            "finder": finder,
            "injector": injector,
            "dynamic_analyzer": dynamic_analyzer,
            "static_analyzer": static_analyzer
        }

        # Check dependences for the modules
        for m in self.modules.values():
            if not m.checkDependeces():
                return None

    # Methods to communicate with traffic controller

    def getRPS(self):
        return self.traffic_controller.get_rps()

    def setRPS(self, rps):
        return self.traffic_controller.set(rps)

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
            self.send_error_msg("Domain %s already in database" % domain, "terminal")
            return -1

        d = Domain.insert(domain)
        if not d:
            self.send_error_msg("Couldn't add domain %s" % domain, "terminal")
            return -1

        if options:
            opts = json.loads(options)

            # Get and insert headers
            if opts.get('headers'):
                for k,v in opts.get('headers').items():
                    header = Header.insert(k,v, False)
                    if header:
                        d.add(header)
                        self.send_msg("Added header %s" % str(header), "terminal")

            # Get and insert cookies
            if opts.get('cookies'):
                for c in opts.get('cookies'):
                    cookie = Cookie.insert(c)
                    if cookie:
                        d.add(cookie)
                        self.send_msg("Added cookie %s" % str(cookie), "terminal")

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
        lib.bot.dispatch("bagley_msg", msg, channel)

    @staticmethod
    def send_error_msg(msg, channel, exception=None):
        if exception:
            msg +="\n" + str(exception)
            logging.exception(msg)
        else:
            logging.error(msg)

        lib.bot.dispatch("bagley_msg", msg, channel)
        lib.bot.dispatch("bagley_msg", msg, "errors")

    @staticmethod
    def send_vuln_msg(msg, channel):
        logging.critical(msg)
        lib.bot.dispatch("bagley_msg", msg, channel)
        lib.bot.dispatch("bagley_msg", msg, "vulnerabilities")