import discord, json, logging
import config, lib.controller as controller

from lib.entities import *

help_msg = """

"""

# Init discord bot
bot = discord.Client()

@bot.event
async def on_ready():
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL)
    logging.info("Connected to Discord bot")
    await terminal_channel.send("Hello")

@bot.event
async def on_message(message):
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL)
    if message.author.id != bot.user.id:
        logging.info("Received %s from Discord", message.content)
        if message.content.lower() == 'help':
            await terminal_channel.send(help_msg)

        elif message.content.lower() == 'start':
            controller.start()
            await terminal_channel.send('Started')

        elif message.content.lower() == 'stop':
            await terminal_channel.send('Stopping')
            controller.stop()
            await terminal_channel.send('Stopped')

        elif message.content.lower().startswith('add'):
            domain = message.content.split(" ")[1]
            if Domain.check(domain):
                logging.error("Domain %s already in database", domain)
                await terminal_channel.send("Domain %s already in database" % domain)
            else:
                d = Domain.insert(domain)
                if not d:
                    logging.error("Could't add domain %s", domain)
                    await terminal_channel.send("Couldn't add domain %s" % domain)
                else:
                    logging.info("Added domain %s", str(d))
                    await terminal_channel.send("Added domain %s" % str(d))

                    # Try parsing options if any
                    try:
                        if len(message.content.split(" ")) > 2:
                            opts = json.loads(message.content.split(" ")[2:])

                            # Get and insert headers
                            if opts.get('headers'):
                                for k,v in opts.get('headers').items():
                                    header = Header.insert(k,v, False)
                                    if header:
                                        d.add(header)
                                        logging.info("Added header %s", str(header))
                                        await terminal_channel.send("Added header %s" % str(header))

                            # Get and insert cookies
                            if opts.get('cookies'):
                                for c in opts.get('cookies'):
                                    cookie = Cookie.insert(c)
                                    if cookie:
                                        d.add(cookie)
                                        logging.info("Added cookie %s", str(cookie))
                                        await terminal_channel.send("Added cookie %s" % str(cookie))

                            # If group of subdomains specified, get out of scope domains
                            if domain[0] == '.':
                                excluded = opts.get('excluded')
                                if excluded:
                                    for e in excluded:
                                        if Domain.insertOutOfScope(e):
                                            logging.info("Added domain %s out of scope", str(e))
                                            await terminal_channel.send("Added domain %s out of scope" % str(e))

                            # Add to queue
                            if opts.get("queue"):
                                for q in opts.get("queue"):
                                    controller.addToQueue(q)
                                    logging.info("Added %s to queue", str(q))
                                    await terminal_channel.send("Added %s to queue" % str(q))
                    except:
                        await terminal_channel.send("Couldn't parse options")

        elif message.content.lower() == 'getdomains':
            pass

        elif message.content.lower().startswith('getpaths'):
            pass

        else:
            await terminal_channel.send('Cannot understand "%s"' % message.content)

@bot.event
async def on_bagley_msg(msg, channel):
    channels = {
        "crawler": config.DISCORD_CRAWLER,
        "dynamic analyzer": config.DISCORD_DYNAMIC_ANALYZER,
        "finder": config.DISCORD_FINDER,
        "injector": config.DISCORD_INJECTOR,
        "static analyzer": config.DISCORD_STATIC_ANALYZER,
        "vulnerabilities": config.DISCORD_VULNERABILITIES
    }

    c = channels.get(channel)
    if not c:
        logging.error("Tried sending message inexistent channel %s", channel)
        return

    await c.send(msg)    