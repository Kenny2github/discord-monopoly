import time
from hashlib import sha256
import asyncio
import discord
from discord.ext import commands

background = asyncio.create_task

PERMS = discord.PermissionOverwrite(
    read_messages=True,
    add_reactions=True,
    send_messages=True,
    read_message_history=True,
)
HIDE = discord.PermissionOverwrite(read_messages=False)

class Monopoly(commands.Cog):

    def __init__(self, bot, guild_id, role_id):
        self.bot = bot
        self.guild = self.bot.get_guild(guild_id)
        self.role = self.guild.get_role(role_id)

    seeking = {} # user IDs seeking a game
    sought = {} # user IDs specifically whitelisted

    @commands.command(description='Play Monopoly!')
    async def seek(self, ctx, whitelist: commands.Greedy[discord.Member] = None):
        """Usage:

        `$seek`
        Looks for a game that anyone can join by sending "ok @you" or "yes @you"

        `$seek @person1 @person2 ...`
        Looks for a game that only @person1 and @person2 (and any others you
        care to specify) can join by just sending "ok" or "yes", or reject by
        sending "no"

        At any time until a game has been found, you can send "nvm" in chat
        to cancel your own seek.
        """
        seeker = ctx.author.mention
        if ctx.author.id in self.seeking:
            background(ctx.send(seeker, embed=discord.Embed(
                title='Error',
                description='You are [already seeking]({}) a game!'.format(
                    self.seeking[ctx.author.id].jump_url
                ),
                color=0xff0000
            )))
            return
        desc = f'{seeker} is looking for a game!\n'
        if whitelist:
            sought = set()
            for mention in whitelist:
                if mention.id in self.sought:
                    background(ctx.send(seeker, embed=discord.Embed(
                        title='Error',
                        description='{} is [already being sought]({}) for a game!'
                        .format(mention.mention, self.sought[mention.id].jump_url),
                        color=0xff0000
                    )))
                    return
                sought.add(mention.id)
            # only add to global sought all at once so there aren't partial seeks
            for mention in sought:
                self.sought[mention] = ctx.message
            desc += ', '.join(ment.mention for ment in whitelist)
            desc += ': Join by saying "ok" or "yes" in chat.'
        else:
            desc += f'Join by saying "ok {seeker}" or "yes {seeker}" in chat.'
        self.seeking[ctx.author.id] = ctx.message
        background(ctx.send(embed=discord.Embed(
            title='Looking For Game',
            description=desc,
            color=0x55acee
        )))
        fut = self.bot.loop.create_future()
        if whitelist:
            confirmed = {ment.id: False for ment in whitelist}
            @self.bot.listen()
            async def on_message(msg):
                content = msg.content.strip().casefold()
                if msg.author.id == ctx.author.id and content == 'nvm':
                    fut.cancel()
                    return
                if msg.author.id not in confirmed:
                    return
                if not content.startswith(('ok', 'yes', 'no')):
                    return
                if content.startswith(('ok', 'yes')):
                    confirmed[msg.author.id] = True
                if content.startswith('no'):
                    del confirmed[msg.author.id]
                if not confirmed:
                    fut.cancel()
                    return
                if all(confirmed.values()):
                    fut.set_result(True)
        else:
            players = set()
            @self.bot.listen()
            async def on_message(msg):
                content = msg.content.strip().casefold()
                if msg.author.id == ctx.author.id:
                    if content == 'nvm':
                        fut.cancel()
                        return
                    elif content in {'start', 'done'}:
                        fut.set_result(True)
                        return
                if not content.endswith((seeker, seeker.replace('@', '@!'))):
                    return
                if not content.startswith(('ok', 'yes')):
                    return
                players.add(msg.author)
        try:
            await asyncio.wait_for(fut, 60.0)
        except (asyncio.CancelledError, asyncio.TimeoutError) as exc:
            if isinstance(exc, asyncio.TimeoutError):
                desc = 'A minute passed before everyone had joined or declined.'
            elif whitelist and not confirmed:
                desc = 'Everyone you invited declined.'
            else:
                desc = 'You have quit seeking a game.'
            background(ctx.send(seeker, embed=discord.Embed(
                title='Game Cancelled',
                description=desc,
                color=0xff0000
            )))
            return
        else:
            if whitelist:
                players = {user for user in whitelist if user.id in confirmed}
        finally:
            self.bot.remove_listener(on_message)
            for user in players:
                self.seeking.pop(user.id, None)
                self.sought.pop(user.id, None)
        players.add(ctx.author)
        await self.setup(ctx, players)

    async def setup(self, ctx, players):
        """Set up the game and close off the seek."""
        hashstr = f"{' '.join(map(str, players))} {time.time()}"
        prefix = sha256(hashstr.encode()).hexdigest()[:7]
        del hashstr
        overwrites = {
            self.guild.default_role: HIDE
        }
        for user in players:
            overwrites[user] = PERMS
            background(user.add_roles(self.role))
        cat = await self.guild.create_category(prefix + '-gameplay',
                                               overwrites=overwrites)
        await self.guild.create_text_channel(prefix + '-game', category=cat)
