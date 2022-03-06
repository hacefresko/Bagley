import discord, logging
import config, lib.utils

# Init discord bot
bot = discord.Client()

def getTerminal():
    # Get terminal channel
    for c in bot.get_all_channels():
        if c.name == "terminal":
            return c

def initBot(controller):
    @bot.event
    async def on_ready():
        logging.info("Connected to Discord bot")
        await getTerminal().send("`Hello`")

    @bot.event
    async def on_message(message):
        help_msg = """
        `This should be helpful. but there is no help message yet :D`
        """

        terminal_channel = getTerminal()

        for line in message.content.split('\n'):
            try:
                if message.author.id != bot.user.id:
                    logging.info("Received %s from Discord", line)
                    if line.lower() == 'help':
                        await terminal_channel.send(help_msg)

                    elif line.lower() == 'start':
                        controller.start()
                        await terminal_channel.send('`Started`')

                    elif line.lower() == 'stop':
                        await terminal_channel.send('`Stopping`')
                        controller.stop()
                        await terminal_channel.send('`Stopped`')

                    elif line.lower() == 'restart':
                        controller.stop()
                        controller.start()

                    elif line.lower().startswith('add'):
                        if len(line.split(" ")) == 2:
                            controller.addDomain(line.split(" ")[1])
                        elif len(line.split(" ")) > 2:
                            controller.addDomain(line.split(" ")[1], " ".join(line.split(" ")[2:]))
                        else:
                            await terminal_channel.send("`Usage: add <domain> [options]`")

                    elif line.lower() == 'getdomains':
                        domains = controller.getDomains()
                        if len(domains) == 0:
                            await terminal_channel.send("`There are no domains yet`")
                        else:
                            s = '`'
                            for d in domains:
                                s += str(d) + "\n"
                            s += '`'
                            await terminal_channel.send(s)

                    elif line.lower().startswith('getpaths'):
                        if len(line.split(" ")) <= 1:
                            await terminal_channel.send("`Usage: getpaths <domain>`")
                        else:
                            domain = line.split(" ")[1]
                            paths = controller.getPaths(domain)
                            if not paths:
                                await terminal_channel.send("`%s does not exists`" % domain)
                            else:
                                await terminal_channel.send("`%s`" % paths)

                    elif line.lower() == "getrps":
                        await terminal_channel.send("`Requests per second: %d`" % controller.getRPS())

                    elif line.lower().startswith('setrps'):
                        if len(line.split(" ")) <= 1:
                            await terminal_channel.send("`Usage: setrps <RPS>`")
                        else:
                            rps = int(line.split(" ")[1])
                            controller.setRPS(rps)
                            await terminal_channel.send("`Requests per second set to %d`" % rps)

                    else:
                        await terminal_channel.send('`Cannot understand "%s"`' % line)

            except Exception as e:
                await terminal_channel.send("`" + lib.utils.getExceptionString() + "`")

    @bot.event
    async def on_bagley_msg(msg, channel):
        for c in bot.get_all_channels():
            if c.name == channel:
                await c.send("`"+msg+"`")

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