from abc import abstractmethod
import discord, logging, aiohttp
import config, lib.utils

# Create bot object
bot = discord.Client()

# Function to send messages to a channel
async def send_msg(msg, channel):
    for c in bot.get_all_channels():
        if c.name == channel:
            sent = 0
            while sent < len(msg):
                m = msg[sent:sent+1000]
                sent += len(m)
                await c.send("`" + m + "`")

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
        if len(args) < 2 or len(args) > 3:
            return False

        return True

    async def run(self, args):
        if args[1] == 'help':
            await send_msg(self.usage_msg + "\n" + """Options (in JSON format):
excluded        List of domains which are out of scope.
                Only available if a group of subdomains was specified
                {"excluded": "example.com"}
headers         Headers that will be added to every request.
                {"headers": {"key": "value"}}
cookies         Cookies that will be added to the browser and other requests.
                Fields <name>, <value> and <domain> are mandatory.
                {"cookies": [{"name": "lel", "value": 1337, "domain": "example.com"}]}
localStorage    Key/value pairs to be added to the local storage of the specified location
                {"localStorage": [{"key": "lel", "value": 1337, "url": "https://www.example.com/"}]}
queue           URLs to start crawling from. Domain must be in scope.
                {"queue": "http://example.com/example"}""", "terminal")

        elif len(args) == 2:
            s = self.controller.addDomain(args[1])
        else:
            s = self.controller.addDomain(args[1], " ".join(args[2:]))
        
        await send_msg(s, "terminal")

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

class CommandParser():
    def __init__(self, controller):
        self.commands = [
            StartCommand(controller), 
            StopCommand(controller), 
            RestartCommand(controller), 
            AddCommand(controller), 
            GetDomainsCommand(controller), 
            GetPathsCommand(controller), 
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
            for c in self.commands:
                if args[0] == c.name.lower():
                    if c.parse(args):
                        await c.run(args)
                    else:
                        await send_msg(c.usage_msg, "terminal")
                    return
            
            await send_msg('Cannot understand "%s"' % line, "terminal")
                
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
        for c in bot.get_all_channels():
            if c.name == channel:
                await c.send(file=discord.File(filename))

    bot.run(config.DISCORD_TOKEN)