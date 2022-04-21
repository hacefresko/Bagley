import threading, logging, json
import lib.modules, lib.bot, config

from lib.entities import *
from .database import DB

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

    def get_active_modules(self):
        result = []
        for k,v in self.modules.items():
            if v.active:
                result.append(k)
        return result

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
            return "Domain %s already in database" % domain

        d = Domain.insert(domain)
        if not d:
            return "Couldn't add domain %s" % domain

        return_str = "Added domain %s" % str(d)

        try:
            if options:
                opts = json.loads(options)

                # Get and insert headers
                if opts.get('headers'):
                    for k,v in opts.get('headers').items():
                        header = Header.insert(k,v, False)
                        if header:
                            header.link(d)
                            return_str += "\nAdded header %s" % str(header)

                # Get and insert cookies
                if opts.get('cookies'):
                    for c in opts.get('cookies'):
                        cookie = Cookie.insert(c)
                        if cookie:
                            if cookie.link(d):
                                return_str += "\nAdded cookie %s" % str(cookie)
                            else:
                                return_str += "\nCouldn't add cookie %s" % str(cookie)

                if opts.get('localstorage'):
                    ls = opts.get('localstorage')
                    if ls.get('url') is not None and ls.get('items') is not None:
                        self.modules.get('crawler').addToLocalStorage(ls.get('url'), ls.get('items'))
                        return_str += "\nSuccesfully added local storage"
                    else:
                        return_str += "\nCouldn't add local storage"

                # If group of subdomains specified, get out of scope domains
                if (domain[0] == '.') and (opts.get('excluded')):
                    for e in opts.get('excluded'):
                        if Domain.insertOutOfScope(e):
                            return_str += "\nAdded domain %s out of scope" % str(e)

                # Add to queue
                if opts.get("queue"):
                    for q in opts.get("queue"):
                        self.addToQueue(q)
                        return_str += "\nAdded %s to queue" % str(q)

        except Exception as e:
            return_str += "\nCouldn't parse options"
        finally:
            return return_str

    def removeDomain(self, domain):
        if Domain.remove(domain):
            self.modules.get("crawler").removeDomainFromQueue(domain)
            return "Removed %s" % domain
        else:
            return "%s couldn't be removed" % domain        

    def getDomains(self):
        return Domain.getAll()

    def getPaths(self, domain):
        d = Domain.get(domain)
        if not d:
            return None
        
        return d.getStructure()

    def getScript(self, id):
        return Script.getById(id)

    # Method to communicate directly with db

    def query(self, query):
        return DB().query_string_like(query)

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
        lib.bot.dispatch_msg(msg, channel)
        lib.bot.dispatch_msg(msg, "vulnerabilities")
 
    @staticmethod
    def send_img(filename, channel):
        logging.info("[%s] Sent image %s", channel, filename)
        lib.bot.dispatch_img(filename, channel)