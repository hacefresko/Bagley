import discord
import config, lib.controller as controller

# Init discord bot
bot = discord.Client()

@bot.event
async def on_ready():
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL_CHANNEL)
    print("[+] Connected to Discord server")
    await terminal_channel.send("`" + controller.title.replace('`', '\`') + "`")

@bot.event
async def on_message(message):
    terminal_channel = bot.get_channel(config.DISCORD_TERMINAL_CHANNEL)

    if message.content == 'help':
        pass

    elif message.content == 'start':
        print("[DISCORD] Starting")
        controller.start()
        await terminal_channel.send('`Started`')

    elif message.content == 'stop':
        print("[DISCORD] Stoping")
        await terminal_channel.send('`Stopping`')
        controller.stop()
        await terminal_channel.send('`Stopped`')

    elif message.content.startswith('add'):
        pass