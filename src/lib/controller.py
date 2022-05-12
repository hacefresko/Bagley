import threading, json
import lib.modules, lib.discord_connector, config
from lib.entities import *
from .database import DB

class Controller:
    def __init__(self, logger):
        self.stopThread = threading.Event()

        self.rps = config.REQ_PER_SEC
        self.active_modules = 0
        self.lock = threading.Lock()
        self.logger = logger

        self.initModules()

        # Check dependencies for the modules
        for m in self.modules.values():
            m.checkDependencies()

        self.discord_connector = lib.discord_connector.Connector(self)
        self.discord_connector.init(config.DISCORD_TOKEN)

    def initModules(self):
        crawler = lib.modules.Crawler(self, self.stopThread, self.rps, self.active_modules, self.lock)
        finder = lib.modules.Finder(self, self.stopThread, self.rps, self.active_modules, self.lock, crawler)
        injector = lib.modules.Injector(self, self.stopThread, self.rps, self.active_modules, self.lock)
        dynamic_analyzer = lib.modules.Dynamic_Analyzer(self, self.stopThread, self.rps, self.active_modules, self.lock)
        static_analyzer = lib.modules.Static_Analyzer(self, self.stopThread, crawler)

        self.modules = {
            "crawler": crawler,
            "finder": finder,
            "injector": injector,
            "dynamic_analyzer": dynamic_analyzer,
            "static_analyzer": static_analyzer
        }

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

        # Init modules again so start() can be called after stop() (Threads can only be started once so we need to create the objects again)
        self.initModules()

    def addToQueue(self, url):
        self.modules.get("crawler").addToQueue(url)

    def getSubModules(self):
        submodules = []
        for m in self.modules.values():
            for subm in m.submodules:
                submodules.append(subm)
        return submodules

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
                        header = Header.get(k,v) or Header.insert(k,v, False)
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

                # Add excluded submodules
                if opts.get("excluded_submodules"):
                    submodules = self.getSubModules()
                    valid = True
                    for m in opts.get("excluded_submodules"):
                        if m not in submodules:
                            return_str += "\nSubmodule %s does not exist" % m
                            valid = False

                    if valid:
                        d.addExcludedSubmodules(opts.get("excluded_submodules"))


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

    def send_msg(self, msg, channel):
        self.logger.info("[%s] %s", channel, msg)
        self.discord_connector.dispatch_msg(msg, channel)

    def send_error_msg(self, msg, channel):
        self.logger.error(msg)
        self.discord_connector.dispatch_msg(msg, channel)
        self.discord_connector.dispatch_msg(msg, "errors")

    def send_vuln_msg(self, msg, channel):
        self.logger.critical(msg)
        self.discord_connector.dispatch_msg(msg, channel)
        self.discord_connector.dispatch_msg(msg, "vulnerabilities")
 
    def send_file(self, filename, channel):
        self.logger.info("[%s] Sent image %s", channel, filename)
        self.discord_connector.dispatch_file(filename, channel)