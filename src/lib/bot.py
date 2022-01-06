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
    await terminal_channel.send("Hello there")

@bot.event
async def on_message(message):
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL_CHANNEL)

    if message.content.lower() == 'help':
        print("[DISCORD] Sent help")
        await terminal_channel.send(help_msg)

    elif message.content.lower() == 'start':
        print("[DISCORD] Starting")
        controller.start()
        await terminal_channel.send('Started')

    elif message.content.lower() == 'stop':
        print("[DISCORD] Stoping")
        await terminal_channel.send('Stopping')
        controller.stop()
        await terminal_channel.send('Stopped')

    elif message.content.lower().startswith('add'):
        pass

    elif message.content.lower() == 'getdomains':
        pass

    elif message.content.lower().startswith('getpaths'):
        pass