import discord
import config, lib.controller as controller

help_msg = """

"""

# Init discord bot
bot = discord.Client()

@bot.event
async def on_ready():
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL_CHANNEL)
    print("[DISCORD] Connected to Discord server")
    await terminal_channel.send("```Hello hacker```" + "https://media1.tenor.com/images/3d190af70cfeea404f796f869f46a3c3/tenor.gif")

@bot.event
async def on_message(message):
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL_CHANNEL)

    if message.content == 'help':
        print("[DISCORD] Sent help")
        await terminal_channel.send('```%s```' % help_msg)

    elif message.content == 'start':
        print("[DISCORD] Starting")
        controller.start()
        await terminal_channel.send('```Started```')

    elif message.content == 'stop':
        print("[DISCORD] Stoping")
        await terminal_channel.send('```Stopping```')
        controller.stop()
        await terminal_channel.send('```Stopped```')

    elif message.content.startswith('add'):
        pass

    elif message.content == 'getdomains':
        pass

    elif message.content.startswith('getpaths'):
        pass