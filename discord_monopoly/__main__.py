# low-level
import sys
import os
import time
import subprocess
# mid-level
import json
import traceback
# high-level
import asyncio
import argparse
# 3rd-party
import discord
from discord.ext import commands
# relative
from discord_monopoly.main import Monopoly

# constants
SRCDIR = os.path.dirname(os.path.abspath(__file__))
VERSION = subprocess.check_output(
    f"cd {SRCDIR} && git rev-parse --short HEAD", shell=True
).decode('ascii').strip()
CONFIG_FILE = 'discord-monopoly.json'
SOURCE_SUFFIXES = ('.py', '.json')

# command-line arguments
parser = argparse.ArgumentParser(description='Run the bot.')
parser.add_argument('--output', nargs='?', default='-',
                    help='File to redirect all output to, - for stdout')
parser.add_argument('--loop', action='store_true',
                    help='Whether to restart upon file modification')
cmdargs = parser.parse_args()
del parser

# output
if cmdargs.output != '-':
    try:
        sys.stdout = sys.stderr = open(cmdargs.output, 'a')
    except IOError:
        print(f"Couldn't open output file {cmdargs.output}, quitting")
        sys.exit(1)

client = commands.Bot(
    description='Play Monopoly on Discord!',
    command_prefix='$',
    help_command=commands.DefaultHelpCommand(dm_help=True),
    activity=discord.Game('Monopoly')
)

def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')

# logging

@client.event
async def on_command_error(ctx, exc):
    print(f'Exception in command {ctx.command}: {type(exc).__name__} {exc}')
    if hasattr(ctx.command, 'on_error'):
        return
    cog = ctx.cog
    if cog:
        if type(cog)._get_overridden_method(cog.cog_command_error) is not None:
            return
    if isinstance(exc, (
        commands.BotMissingPermissions,
        commands.MissingPermissions,
        commands.MissingRequiredArgument,
        commands.BadArgument,
        commands.CommandOnCooldown,
    )):
        await ctx.send(embed=discord.Embed(
            title='Error',
            description=str(exc),
            color=0xff0000
        ))
        return
    if isinstance(exc, (
        commands.CheckFailure,
        commands.CommandNotFound,
        commands.TooManyArguments,
    )):
        return
    print(''.join(traceback.format_exception(
        type(exc), exc, exc.__traceback__
    )))

@client.before_invoke
async def before_invoke(ctx):
    print(f"{now()}: {ctx.user} ran {ctx.command}")

@client.event
async def on_ready(*_, **__):
    print(f"{now()}: Ready!")

@client.check
def check_guild(ctx):
    return ctx.guild is not None and ctx.guild.id == GUILD_ID

# commands

@client.command(description='Git version of currently running bot instance')
async def version(ctx):
    await ctx.send(embed=discord.Embed(description=f'`{VERSION}`'))

@client.command(description='Pong!')
async def ping(ctx):
    await ctx.send(embed=discord.Embed(
        title='Pong!',
        description=f'{round(client.latency * 1000, 3)}',
        color=0x55acee,
    ))

@client.command(description='Stop the bot.')
@commands.is_owner()
async def stop(ctx):
    await client.close()

# keep-alive

def get_source_files(root, *parents, mtimes=None):
    if mtimes is None:
        mtimes = {}
    for name in os.listdir(os.path.join(*parents, root)):
        path = os.path.join(*parents, root, name)
        if os.path.isdir(path):
            return source_files(name, *parents, root, mtimes=mtimes)
        if not name.endswith(SOURCE_SUFFIXES):
            continue
        mtimes[path] = os.path.getmtime(path)
    return mtimes
source_files = get_source_files(os.path.abspath('.'))

async def restart_if_modified():
    await client.wait_until_ready()
    while True:
        for path, mtime in source_files.items():
            if os.path.getmtime(path) > mtime:
                if cmdargs.loop:
                    os.system(f'{COMMAND} restart')
                sys.exit(0)
        try:
            await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            return

# config

with open(CONFIG_FILE) as cfile:
    CONFIG = json.load(cfile)
COMMAND = CONFIG['command'] # command to restart the bot
TOKEN = CONFIG['token'] # discord API token
GUILD_ID = CONFIG['server'] # server ID this bot is in
ROLE_ID = CONFIG['role'] # ID for "In Game" role

# run

client.add_cog(Monopoly(client, GUILD_ID, ROLE_ID))

try:
    client.loop.create_task(client.start(TOKEN))
    client.loop.run_until_complete(restart_if_modified())
except KeyboardInterrupt:
    pass
finally:
    if sys.__stdout__ is not sys.stdout:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        sys.stderr.close()
        sys.stderr = sys.__stderr__
    client.loop.run_until_complete(client.close())
    client.loop.stop()
    client.loop.close()
