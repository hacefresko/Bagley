import discord, json, logging
import config, lib.controller as controller

from lib.entities import *

CHANNELS = {
    "terminal": config.DISCORD_TERMINAL,
    "errors": config.DISCORD_ERRORS,
    "crawler": config.DISCORD_CRAWLER,
    "dynamic analyzer": config.DISCORD_DYNAMIC_ANALYZER,
    "finder": config.DISCORD_FINDER,
    "injector": config.DISCORD_INJECTOR,
    "static analyzer": config.DISCORD_STATIC_ANALYZER,
    "vulnerabilities": config.DISCORD_VULNERABILITIES
}

help_msg = """
`This should be helpful. but there is no help message yet :D`
"""

# Init discord bot
bot = discord.Client()

def send_msg(msg, channel):
    logging.info("[%s] %s", channel, msg)
    bot.dispatch("bagley_msg", msg, channel)

def send_error_msg(msg, channel, exception=None):
    if exception:
        msg +="\n" + str(exception)
        logging.exception(msg)
    else:
        logging.error(msg)

    bot.dispatch("bagley_msg", msg, channel)
    bot.dispatch("bagley_msg", msg, "errors")

def send_vuln_msg(msg, channel):
    logging.critical(msg)
    bot.dispatch("bagley_msg", msg, channel)
    bot.dispatch("bagley_msg", msg, "vulnerabilities")

@bot.event
async def on_ready():
    logging.info("Connected to Discord bot")
    await  bot.get_channel(CHANNELS.get("terminal")).send("`Hello`")

@bot.event
async def on_message(message):
    try:
        terminal_channel = bot.get_channel(CHANNELS.get("terminal"))
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
                domain = message.content.split(" ")[1]
                if Domain.check(domain):
                    logging.error("Domain %s already in database", domain)
                    await terminal_channel.send("`Domain %s already in database`" % domain)
                else:
                    d = Domain.insert(domain)
                    if not d:
                        logging.error("Could't add domain %s", domain)
                        await terminal_channel.send("`Couldn't add domain %s`" % domain)
                    else:
                        if len(message.content.split(" ")) > 2:
                            opts = json.loads(message.content.split(" ")[2:])

                            # Get and insert headers
                            if opts.get('headers'):
                                for k,v in opts.get('headers').items():
                                    header = Header.insert(k,v, False)
                                    if header:
                                        d.add(header)
                                        logging.info("Added header %s", str(header))
                                        await terminal_channel.send("`Added header %s`" % str(header))

                            # Get and insert cookies
                            if opts.get('cookies'):
                                for c in opts.get('cookies'):
                                    cookie = Cookie.insert(c)
                                    if cookie:
                                        d.add(cookie)
                                        logging.info("Added cookie %s", str(cookie))
                                        await terminal_channel.send("`Added cookie %s`" % str(cookie))

                            # If group of subdomains specified, get out of scope domains
                            if domain[0] == '.':
                                excluded = opts.get('excluded')
                                if excluded:
                                    for e in excluded:
                                        if Domain.insertOutOfScope(e):
                                            logging.info("Added domain %s out of scope", str(e))
                                            await terminal_channel.send("`Added domain %s out of scope`" % str(e))

                            # Add to queue
                            if opts.get("queue"):
                                for q in opts.get("queue"):
                                    controller.addToQueue(q)
                                    logging.info("Added %s to queue", str(q))
                                    await terminal_channel.send("`Added %s to queue`" % str(q))
                        
                        logging.info("Added domain %s", str(d))
                        await terminal_channel.send("`Added domain %s`" % str(d))

            elif message.content.lower() == 'getdomains':
                s = '`'
                for d in controller.getDomains():
                    s += str(d) + "\n"
                s += '`'
                await terminal_channel.send(s)

            elif message.content.lower().startswith('getpaths'):
                domain = message.content.split(" ")[1]
                await terminal_channel.send('`' + controller.getPaths(domain) + '`')

            elif message.content.lower().startswith('set'):
                pass

            else:
                await terminal_channel.send('`Cannot understand "%s"`' % message.content)

    except:
        await terminal_channel.send("`Couldn't parse command`")

@bot.event
async def on_bagley_msg(msg, channel):
    if not CHANNELS.get(channel):
        logging.error("Tried sending message to inexistent channel %s", channel)
        return

    await bot.get_channel(CHANNELS.get(channel)).send("`"+msg+"`")