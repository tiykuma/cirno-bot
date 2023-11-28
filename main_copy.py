import asyncio
import discord
import os
import logging
from cogs.help import Help 
from dotenv import load_dotenv
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

load_dotenv(dotenv_path=".env")

client = commands.Bot(command_prefix='=', owner_id = 630981548258099210, case_insensitive=True, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name=f"=help"))
client.help_command = Help()

@client.command(hidden=True)
@commands.is_owner()
async def reload(ctx, extension):
    await client.reload_extension(f"cogs.{extension}")  
    embed = discord.Embed(title='Reload', description=f'{extension} successfully reloaded', color=ctx.author.color)
    embed.set_footer(text=f"Changes made by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = await ctx.send('⏱ | Please try again in {:.2f}s!'.format(error.retry_after))
        await asyncio.sleep(3)
        await msg.delete()
    elif isinstance(error, commands.MissingPermissions):
        msg = await ctx.send(":x: | You can't use this command!")
        await asyncio.sleep(3)
        await msg.delete()
        ctx.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    elif isinstance(error, commands.MemberNotFound):
        msg = await ctx.send(":x: | Wrong arguments! Tag someone, please!")
        await asyncio.sleep(3)
        await msg.delete()
        ctx.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    elif isinstance(error, discord.Forbidden):
        pass
    elif isinstance(error, commands.CommandNotFound):
        pass  
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        command = ctx.invoked_with      
        if cmd := ctx.bot.get_command(command): 
            await client.help_command.command_help_ctx(ctx, command=cmd)
        ctx.bot.get_command(command).reset_cooldown(ctx)
    else:
        logging.basicConfig(
            filename='cirno.log',
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.ERROR,
            datefmt='%Y-%m-%d %H:%M:%S')
        logging.error(f"Command: {ctx.invoked_with}: {error}")


@client.event
async def on_ready():
    print(f'Launcher has logged in as {client.user}')

async def main():
    async with client:
        for filename in os.listdir('./cogs'):
            if filename.endswith('py')  :
                await client.load_extension(f'cogs.{filename[:-3]}')
        await client.start(os.getenv('DISCORD_TOKEN_2'))

asyncio.run(main())

