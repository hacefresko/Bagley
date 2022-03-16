import discord, logging, aiohttp
import config, lib.utils

# Init discord bot
bot = discord.Client()

async def send_msg(msg, channel):
    for c in bot.get_all_channels():
        if c.name == channel:
            sent = 0
            while sent < len(msg):
                m = msg[sent:sent+1000]
                sent += len(m)
                await c.send("`" + m + "`")

def getTerminal():
    # Get terminal channel
    for c in bot.get_all_channels():
        if c.name == "terminal":
            return c

async def parseLine(controller, line):
    help_msg = """
    `This should be helpful. but there is no help message yet :D`
    """

    terminal_channel = getTerminal()

    try:
        logging.info("Received %s from Discord", line)
        if line.lower() == 'help':
            await send_msg(help_msg, "terminal")

        elif line.lower() == 'start':
            controller.start()
            await send_msg('Started', "terminal")

        elif line.lower() == 'stop':
            await send_msg('Stopping', "terminal")
            controller.stop()
            await send_msg('Stopped', "terminal")

        elif line.lower() == 'restart':
            await send_msg('Restarting', "terminal")
            controller.stop()
            controller.start()
            await send_msg('Restarted', "terminal")

        elif line.lower().startswith('add'):
            if len(line.split(" ")) == 2:
                s = controller.addDomain(line.split(" ")[1])
                await send_msg(s, "terminal")
            elif len(line.split(" ")) > 2:
                s = controller.addDomain(line.split(" ")[1], " ".join(line.split(" ")[2:]))
                await send_msg(s, "terminal")
            else:
                await send_msg("Usage: add <domain> [options]", "terminal")

        elif line.lower() == 'getdomains':
            domains = controller.getDomains()
            if len(domains) == 0:
                await send_msg("There are no domains yet", "terminal")
            else:
                s = ""
                for d in domains:
                    s += str(d) + "\n"
                await send_msg(s, "terminal")

        elif line.lower().startswith('getpaths'):
            if len(line.split(" ")) <= 1:
                await send_msg("Usage: getpaths <domain>", "terminal")
            else:
                domain = line.split(" ")[1]
                paths = controller.getPaths(domain)
                if not paths:
                    await send_msg("%s does not exists" % domain, "terminal")
                else:
                    await send_msg(paths, "terminal")

        elif line.lower() == "getrps":
            await send_msg("Requests per second: %d" % controller.getRPS(), "terminal")

        elif line.lower().startswith('setrps'):
            if len(line.split(" ")) <= 1:
                await send_msg("Usage: setrps <RPS>", "terminal")
            else:
                rps = int(line.split(" ")[1])
                controller.setRPS(rps)
                await send_msg("Requests per second set to %d" % rps, "terminal")

        elif line.lower() == "getactive":
            active = controller.get_active_modules()
            await send_msg("Active modules: %d\n%s" % (len(active), "\n".join(active)), "terminal")

        else:
            await send_msg('Cannot understand "%s"' % line, "terminal")

    except Exception as e:
        await send_msg(lib.utils.getExceptionString(), "terminal")

def initBot(controller):
    @bot.event
    async def on_ready():
        logging.info("Connected to Discord bot")
        await getTerminal().send("`Hello`")

    @bot.event
    async def on_message(message):
        if message.author.id != bot.user.id:
            if len(message.attachments) == 0:
                for line in message.content.split('\n'):
                    await parseLine(controller, line)
            else:
                for attachment in message.attachments:
                    async with aiohttp.ClientSession().get(attachment.url) as r:
                        txt = await r.text()
                        if txt: 
                            for line in txt.split('\n'):
                                await parseLine(controller, line)

    @bot.event
    async def on_bagley_msg(msg, channel):
        await send_msg(msg, channel)

    @bot.event
    async def on_bagley_img(filename, channel):
        for c in bot.get_all_channels():
            if c.name == channel:
                await c.send(file=discord.File(filename))

    bot.run(config.DISCORD_TOKEN)

def dispatch_msg(message, channel):
    bot.dispatch("bagley_msg", message, channel)

def dispatch_img(filename, channel):
    bot.dispatch("bagley_img", filename, channel)