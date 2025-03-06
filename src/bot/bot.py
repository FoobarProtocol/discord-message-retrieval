import discord
from discord.ext import commands
from database.operations import store_message

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    try:
        await store_message(message.id, message.content, message.author.id, message.channel.id)
        await message.channel.send(f'Message stored: {message.content}')
    except Exception as e:
        await message.channel.send(f'Error storing message: {str(e)}')

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
