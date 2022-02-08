from os import terminal_size
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
        try:
            if message.author.id != bot.user.id:
                logging.info("Received %s from Discord", message.content)
                if message.content.lower() == 'help':
                    await terminal_channel.send(help_msg)

                elif message.content.lower() == 'start':
                    controller.start()
                    await terminal_channel.send('`Started`')

                elif message.content.lower() == 'stop':
                    await terminal_channel.send('`Stopping`')
                    controller.stop()
                    await terminal_channel.send('`Stopped`')

                elif message.content.lower() == 'restart':
                    controller.stop()
                    controller.start()

                elif message.content.lower().startswith('add'):
                    if len(message.content.split(" ")) == 2:
                        controller.addDomain(message.content.split(" ")[1])
                    elif len(message.content.split(" ")) == 3:
                        controller.addDomain(message.content.split(" ")[1], message.content.split(" ")[2])
                    else:
                        await terminal_channel.send("`Usage: add <domain> [options]`")

                elif message.content.lower() == 'getdomains':
                    domains = controller.getDomains()
                    if len(domains) == 0:
                        await terminal_channel.send("`There are no domains yet`")
                    else:
                        s = '`'
                        for d in domains:
                            s += str(d) + "\n"
                        s += '`'
                        await terminal_channel.send(s)

                elif message.content.lower().startswith('getpaths'):
                    if len(message.content.split(" ")) <= 1:
                        await terminal_channel.send("`Usage: getpaths <domain>`")
                    else:
                        domain = message.content.split(" ")[1]
                        paths = controller.getPaths(domain)
                        if not paths:
                            await terminal_channel.send("`%s does not exists`" % domain)
                        else:
                            await terminal_channel.send("`%s`" % paths)

                elif message.content.lower() == "getrps":
                    await terminal_channel.send("`Requests per second: %d`" % controller.getRPS())

                elif message.content.lower().startswith('setrps'):
                    if len(message.content.split(" ")) <= 1:
                        await terminal_channel.send("`Usage: setrps <RPS>`")
                    else:
                        rps = int(message.content.split(" ")[1])
                        controller.setRPS(rps)
                        await terminal_channel.send("`Requests per second set to %d`" % rps)

                else:
                    await terminal_channel.send('`Cannot understand "%s"`' % message.content)

        except Exception as e:
            await terminal_channel.send("`" + lib.utils.getExceptionString() + "`")

    @bot.event
    async def on_bagley_msg(msg, channel):
        for c in bot.get_all_channels():
            if c.name == channel:
                await c.send("`"+msg+"`")

    bot.run(config.DISCORD_TOKEN)

def dispatch(message, channel):
    bot.dispatch("bagley_msg", message, channel)