from abc import abstractmethod
import discord, logging, aiohttp, os, random, string, zipfile
import config, lib.utils

# Create bot object
bot = discord.Client()

# Function to send messages to a channel
async def send_msg(msg, channel):
    for c in bot.get_all_channels():
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

# Function to send files to a channel
async def send_file(filename, channel):
    for c in bot.get_all_channels():
        if c.name == channel:
            await c.send(file=discord.File(filename))
            break

# Define commands
class Command:
    def __init__(self, controller, name, help_msg, usage_msg):
        self.controller = controller
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
    def __init__(self, controller):
        super().__init__(controller, "start", "Start execution", "start does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        self.controller.start()
        await send_msg('Started', "terminal")

class StopCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "stop", "Stop execution", "stop does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await send_msg('Stopping', "terminal")
        self.controller.stop()
        await send_msg('Stopped', "terminal")

class RestartCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "restart", "Restart execution", "restart does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await send_msg('Restarting', "terminal")
        self.controller.stop()
        self.controller.start()
        await send_msg('Restarted', "terminal")

class AddCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "add", "Add a new domain (add help for more info)", "Usage: add <domain/group of subdomains> [options]")

    def parse(self, args):
        if len(args) < 2:
            return False

        return True

    async def run(self, args):
        if args[1] == 'help':
            s = self.usage_msg + "\n" + """Options (in JSON format):

excluded        List of domains which are out of scope.
                Only available if a group of subdomains was specified
                {"excluded": "example.com"}
headers         Headers that will be added to every request.
                {"headers": {"key": "value"}}
cookies         Cookies that will be added to the browser and other requests.
                Fields <name>, <value> and <domain> are mandatory.
                {"cookies": [{"name": "lel", "value": 1337, "domain": "example.com"}]}
localStorage    Key/value pairs to be added to the local storage of the specified location
                {"localStorage": {"items": {"lel":1337}, "url": "https://www.example.com/"}]}
queue           URLs to start crawling from. Domain must be in scope.
                {"queue": "http://example.com/example"}"""

        elif len(args) == 2:
            s = self.controller.addDomain(args[1])
        else:
            s = self.controller.addDomain(args[1], " ".join(args[2:]))
        
        await send_msg(s, "terminal")

class RmCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "rm", "Removes a domain", "Usage: rm <domain/group of subdomains> [options]")

    def parse(self, args):
        if len(args) != 2:
            return False

        return True

    async def run(self, args):
        await send_msg(self.controller.removeDomain(args[1]), "terminal")

class GetDomainsCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "getDomains", "Print all domains", "getDomains does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        domains = self.controller.getDomains()
        if len(domains) == 0:
            await send_msg("There are no domains yet", "terminal")
        else:
            s = "Domains:\n"
            for d in domains:
                s += str(d) + "\n"
            await send_msg(s, "terminal")

class GetPathsCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "getPaths", "Print all paths for a domain", "Usage: getpaths <domain>")

    def parse(self, args):
        if len(args) != 2:
            return False

        return True

    async def run(self, args):
        domain = args[1]
        paths = self.controller.getPaths(domain)
        if not paths:
            await send_msg("%s does not exists" % domain, "terminal")
        else:
            await send_msg("\n" + paths, "terminal")

class GetRPSCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "getRPS", "Print current requests per second", "getRPS does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        await send_msg("Requests per second: %d" % self.controller.getRPS(), "terminal")

class SetRPSCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "setRPS", "Set requests per second", "Usage: setrps <RPS>")

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
        await send_msg("Requests per second set to %d" % rps, "terminal")

class GetActiveCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "getActive", "Print active modules", "getActive does not accept arguments")

    def parse(self, args):
        if len(args) > 1:
            return False

        return True

    async def run(self, args):
        active = self.controller.get_active_modules()
        await send_msg("Active modules: %d\n%s" % (len(active), "\n".join(active)), "terminal")

class QueryCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "query", "Query directly to database", "Usage: query <query>")

    def parse(self, args):
        if len(args) < 2:
            return False

        return True

    async def run(self, args):
        try:
            await send_msg("\n" + self.controller.query(" ".join(args[1:])), "terminal")
        except:
            await send_msg(lib.utils.getExceptionString(), "terminal")

class GetScriptCommand(Command):
    def __init__(self, controller):
        super().__init__(controller, "getScript", "Get script information", "getScript <script id>")

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
            await send_msg("Specified script was not found", "terminal")
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

        await send_msg(msg, "terminal")
        await send_file(script.filename, "terminal")

        # Compress unpacked script if exists
        script_unpacked = config.SCRIPTS_FOLDER + str(script.id)
        if os.path.isdir(script_unpacked):
            zip_file_name = config.FILES_FOLDER + str(script.id) + '.zip'
            zip_file = zipfile.ZipFile(zip_file_name, 'w')
            for root, directories, files in os.walk(script_unpacked):
                for filename in files:
                    p = os.path.join(root, filename)
                    zip_file.write(p)

            await send_file(zip_file_name, "terminal")
            os.remove(zip_file_name)


class CommandParser():
    def __init__(self, controller):
        self.commands = [
            StartCommand(controller), 
            StopCommand(controller), 
            RestartCommand(controller), 
            AddCommand(controller),
            RmCommand(controller),
            GetDomainsCommand(controller), 
            GetPathsCommand(controller), 
            GetScriptCommand(controller),
            QueryCommand(controller),
            GetRPSCommand(controller), 
            SetRPSCommand(controller), 
            GetActiveCommand(controller)
        ]

    async def parse(self, line):
        args = line.lower().split()

        if args[0] == 'help':
            help_msg = "Available commands:\n\n"
            help_msg += "help        Print this message\n"
            for c in self.commands:
                help_msg += c.name.ljust(12) + c.help_msg + "\n"
            await send_msg(help_msg, "terminal")
        else:
            try:
                for c in self.commands:
                    if args[0] == c.name.lower():
                        if c.parse(args):
                            await c.run(args)
                        else:
                            await send_msg(c.usage_msg, "terminal")
                        return
                
                await send_msg('Cannot understand "%s"' % line, "terminal")
            except:
                await send_msg(lib.utils.getExceptionString(), "terminal")
                
# Define dispatchers for custom events
def dispatch_msg(message, channel):
    bot.dispatch("bagley_msg", message, channel)

def dispatch_img(filename, channel):
    bot.dispatch("bagley_img", filename, channel)

# Define event handlers and init bot
def initBot(controller):
    cp = CommandParser(controller)

    @bot.event
    async def on_ready():
        logging.info("Connected to Discord bot")
        for c in bot.get_all_channels():
            if c.name == "terminal":
                await c.send("`Hello`")

    @bot.event
    async def on_message(message):
        if message.author.id != bot.user.id:
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

    @bot.event
    async def on_bagley_msg(msg, channel):
        await send_msg(msg, channel)

    @bot.event
    async def on_bagley_img(filename, channel):
        await send_file(filename, channel)

    bot.run(config.DISCORD_TOKEN)