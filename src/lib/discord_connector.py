from abc import abstractmethod
import discord, logging, aiohttp, os, random, string, shutil
import config, lib.utils, lib.controller

# Define commands
class Command:
    def __init__(self, controller, discord_connector, name, help_msg, usage_msg):
        self.controller = controller
        self.discord_connector = discord_connector
        self.name = name
        self.help_msg = help_msg
        self.usage_msg = usage_msg

    @abstractmethod
    def parse(self, args):
        pass

    @abstractmethod
    async def run(self, args):
        pass

class StartCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "start", "Start execution", "start does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        self.controller.start()
        await self.discord_connector.send_msg('Started', "terminal")

class StopCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "stop", "Stop execution", "stop does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await self.discord_connector.send_msg('Stopping', "terminal")
        self.controller.stop()
        await self.discord_connector.send_msg('Stopped', "terminal")

class RestartCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "restart", "Restart execution", "restart does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await self.discord_connector.send_msg('Restarting', "terminal")
        self.controller.stop()
        self.controller.start()
        await self.discord_connector.send_msg('Restarted', "terminal")

class AddCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "add", "Add a new domain (add help for more info)", "Usage: add <domain/group of subdomains> [options]")

    def parse(self, args):
        if len(args) < 2:
            return False

        return True

    async def run(self, args):
        if args[1] == 'help':
            s = self.usage_msg + "\n" + """Options (in JSON format):

excluded            List of domains which are out of scope.
                    Only available if a group of subdomains was specified
                    {"excluded": "example.com"}

headers             Headers that will be added to every request.
                    {"headers": {"key": "value"}}

cookies             Cookies that will be added to the browser and other requests.
                    Fields <name>, <value> and <domain> are mandatory.
                    {"cookies": [{"name": "lel", "value": 1337, "domain": "example.com"}]}

localStorage        Key/value pairs to be added to the local storage of the specified location
                    {"localStorage": {"items": {"lel":1337}, "url": "https://www.example.com/"}]}

queue               URLs to start crawling from. Domain must be in scope.
                    {"queue": "http://example.com/example"}

excluded_submodules Submodules that won't be executed with the added domains. Available
                    submodules: %s.
                    {"excluded_submodules": ["sqlmap", "pathFinder"]}""" % ", ".join(self.controller.getSubModules())

        elif len(args) == 2:
            s = self.controller.addDomain(args[1])
        else:
            s = self.controller.addDomain(args[1], " ".join(args[2:]))
        
        await self.discord_connector.send_msg(s, "terminal")

class RmCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "rm", "Removes a domain", "Usage: rm <domain/group of subdomains> [options]")

    def parse(self, args):
        if len(args) != 2:
            return False

        return True

    async def run(self, args):
        await self.discord_connector.send_msg(self.controller.removeDomain(args[1]), "terminal")

class GetDomainsCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "getDomains", "Print all domains", "getDomains does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        domains = self.controller.getDomains()
        if len(domains) == 0:
            await self.discord_connector.send_msg("There are no domains yet", "terminal")
        else:
            s = "Domains:\n"
            for d in domains:
                s += str(d) + "\n"
            await self.discord_connector.send_msg(s, "terminal")

class GetPathsCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "getPaths", "Print all paths for a domain", "Usage: getpaths <domain>")

    def parse(self, args):
        if len(args) != 2:
            return False

        return True

    async def run(self, args):
        domain = args[1]
        paths = self.controller.getPaths(domain)
        if not paths:
            await self.discord_connector.send_msg("%s does not exists" % domain, "terminal")
        else:
            await self.discord_connector.send_msg("\n" + paths, "terminal")

class GetRPSCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "getRPS", "Print current requests per second", "getRPS does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await self.discord_connector.send_msg("Requests per second: %d" % self.controller.getRPS(), "terminal")

class SetRPSCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "setRPS", "Set requests per second", "Usage: setrps <RPS>")

    def parse(self, args):
        if (len(args) != 2):
            return False

        try:
            args[1] = int(args[1])
            return True
        except:
            return False

    async def run(self, args):
        rps = int(args[1])
        self.controller.setRPS(rps)
        await self.discord_connector.send_msg("Requests per second set to %d" % rps, "terminal")

class GetActiveCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "getActive", "Print active modules", "getActive does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        active = self.controller.get_active_modules()
        await self.discord_connector.send_msg("Active modules: %d\n%s" % (len(active), "\n".join(active)), "terminal")

class QueryCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "query", "Query directly to database", "Usage: query <query>")

    def parse(self, args):
        if len(args) < 2:
            return False

        return True

    async def run(self, args):
        try:
            await self.discord_connector.send_msg("\n" + self.controller.query(" ".join(args[1:])), "terminal")
        except:
            await self.discord_connector.send_msg(lib.utils.getExceptionString(), "terminal")

class GetScriptCommand(Command):
    def __init__(self, controller, discord_connector):
        super().__init__(controller, discord_connector, "getScript", "Get script information", "getScript <script id>")

    def parse(self, args):
        if (len(args) != 2):
            return False

        try:
            args[1] = int(args[1])
            return True
        except:
            return False

    async def run(self, args):
        script = self.controller.getScript(args[1])
        if script is None:
            await self.discord_connector.send_msg("Specified script was not found", "terminal")
            return

        msg = "SCRIPT %d\n" % script.id

        msg += "PATHS:\n"
        paths = script.getPaths()
        if len(paths) == 0:
            msg += "\t[No urls found for this script]\n"
        else:
            for path in paths:
                msg += "\t" + str(path) + "\n"
        msg += "\n"

        msg += "RESPONSES:\n"
        responses = script.getResponses()
        if len(responses) == 0:
            msg += "\t[No responses use this script]\n"
        else:
            for response in responses:
                for request in response.getRequests():
                    msg += "\t" + str(request.path) + "\n"
        msg += "\n"

        await self.discord_connector.send_msg(msg, "terminal")
        await self.discord_connector.send_file(script.file, "terminal")

        # Compress unpacked script if exists
        if script.folder is not None:

            dir_name = script.folder.split("/")[-1]
            parent_dir = "/".join(script.folder.split("/")[:-1]) + "/"

            # This function has very confusing params, http://www.seanbehan.com/how-to-use-python-shutil-make_archive-to-zip-up-a-directory-recursively-including-the-root-folder/ for more info
            shutil.make_archive(dir_name, "zip", parent_dir, dir_name)

            # Move zip file to temporary files directory
            zip_file_name = script.folder + '.zip'
            shutil.move(dir_name + '.zip', zip_file_name)
            
            # Send file
            await self.discord_connector.send_file(zip_file_name, "terminal")

            # Delete file
            os.remove(zip_file_name)


class CommandParser():
    def __init__(self, controller, discord_connector):
        self.discord_connector = discord_connector

        self.commands = [
            StartCommand(controller, discord_connector), 
            StopCommand(controller, discord_connector), 
            RestartCommand(controller, discord_connector), 
            AddCommand(controller, discord_connector),
            RmCommand(controller, discord_connector),
            GetDomainsCommand(controller, discord_connector), 
            GetPathsCommand(controller, discord_connector), 
            GetScriptCommand(controller, discord_connector),
            QueryCommand(controller, discord_connector),
            GetRPSCommand(controller, discord_connector), 
            SetRPSCommand(controller, discord_connector), 
            GetActiveCommand(controller, discord_connector)
        ]

    async def parse(self, line):
        args = line.lower().split()

        if args[0] == 'help':
            help_msg = "Available commands:\n\n"
            help_msg += "help        Print this message\n"
            for c in self.commands:
                help_msg += c.name.ljust(12) + c.help_msg + "\n"
            await self.discord_connector.send_msg(help_msg, "terminal")
        else:
            try:
                for c in self.commands:
                    if args[0] == c.name.lower():
                        if c.parse(args):
                            await c.run(args)
                        else:
                            await self.discord_connector.send_msg(c.usage_msg, "terminal")
                        return
                
                await self.discord_connector.send_msg('Cannot understand "%s"' % line, "terminal")
            except:
                await self.discord_connector.send_msg(lib.utils.getExceptionString(), "terminal")
    

# Define discord connector class
class Connector:
    def __init__(self, controller):
        # Create bot
        self.bot = discord.Client()

        # Create command parser
        cp = CommandParser(controller, self)

        @self.bot.event
        async def on_ready():
            logging.info("Connected to Discord bot")
            for c in self.bot.get_all_channels():
                if c.name == "terminal":
                    await c.send("`Hello`")

        @self.bot.event
        async def on_message(message):
            if message.author.id != self.bot.user.id:
                if len(message.attachments) == 0:
                    for line in message.content.split('\n'):
                        await cp.parse(line)
                else:
                    for attachment in message.attachments:
                        async with aiohttp.ClientSession().get(attachment.url) as r:
                            txt = await r.text()
                            if txt: 
                                for line in txt.split('\n'):
                                    await cp.parse(line)

        @self.bot.event
        async def on_bagley_msg(msg, channel):
            await self.send_msg(msg, channel)

        @self.bot.event
        async def on_bagley_file(filename, channel):
            await self.send_file(filename, channel)

    def init(self, token):
        self.bot.run(token)

    # Function for directly sending messages/files (only works for async functions)
    async def send_msg(self, msg, channel):
        for c in self.bot.get_all_channels():
            if c.name == channel:
                if len(msg) < 5000:
                    sent = 0
                    while sent < len(msg):
                        m = msg[sent:sent+1000]
                        sent += len(m)
                        await c.send("`" + m + "`")
                else:
                    # Create file, send it and remove it
                    filename = config.FILES_FOLDER + ''.join(random.choices(string.ascii_lowercase, k=20)) + '.txt'
                    while os.path.exists(filename):
                        filename = config.FILES_FOLDER + ''.join(random.choices(string.ascii_lowercase, k=20)) + '.txt'

                    temp_file = open(filename, 'w')
                    temp_file.write(msg)
                    temp_file.close()
                    
                    await c.send(file=discord.File(filename))

                    os.remove(filename)

                break

    async def send_file(self, filename, channel):
        for c in self.bot.get_all_channels():
            if c.name == channel:
                await c.send(file=discord.File(filename))
                break

    # Dispatchers for custom events (send_msg() and send_file() can only be used in async functions)
    def dispatch_msg(self, message, channel):
        self.bot.dispatch("bagley_msg", message, channel)

    def dispatch_file(self, filename, channel):
        self.bot.dispatch("bagley_file", filename, channel)