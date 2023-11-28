import asyncio
import datetime
from dis import disco
from pydoc import cli
import discord
import typing as t
import urllib.request
import humanfriendly
# from cogs.music import Music as lavalink
import wavelink
from humanfriendly import InvalidTimespan
from motor.motor_asyncio import AsyncIOMotorClient
from io import BytesIO
from discord.ext import commands
import certifi
from PIL import Image, ImageFont, ImageDraw, ImageChops
from discord.ui import View, Button
import requests

data = AsyncIOMotorClient("MONGDB", tlsCAFile=certifi.where())
db = data['cirnochan']

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levelling = db['user']
        self._emoji = '🏆'
        self._cd = commands.CooldownMapping.from_cooldown(1, 20, commands.BucketType.user)

    def get_ratelimit(self, message: discord.Message) -> t.Optional[int]:
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    def drawProgressBar(d, x, y, w, h, progress, bg="black", fg=(54, 57, 63)):
        # draw background
        # d.ellipse((x+w, y, x+h+w, y+h), fill=bg, width=215)
        # # d.ellipse((x, y, x+h, y+h), fill=bg, width=215)
        # d.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=bg)

        # # draw progress bar
        w *= progress
        d.ellipse((x+w, y, x+h+w, y+h),fill=fg, width=215)
        d.ellipse((x, y, x+h, y+h),fill=fg, width=215)
        d.rectangle((x+(h/2), y, x+w+(h/2), y+h),fill=fg)

    def circle(pfp ,size):
        pfp = pfp.resize(size, Image.ANTIALIAS).convert("RGBA")
        bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new('L', bigsize, 0)
        draw = ImageDraw.Draw(mask) 
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(pfp.size, Image.ANTIALIAS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)
        return pfp
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            ratelimit = self.get_ratelimit(message)
            if ratelimit is None:
                if await self.levelling.find_one({"id" : message.author.id}) is None:
                    newuser = {"id" : message.author.id, "name" : message.author.name, "guild" : [message.guild.id], "xp" : 0, "inventory" : {"things": [{'name': 'Landscape', 'type': 'background', 'index': 1, 'description': "Default Background", 'money': 0, 'link': 'https://i.imgur.com/ouX3DOH.png'}, {'name': 'Leather Armor', 'type': 'armor', 'index': 100, 'description': 'The default armor. It does nothing.', 'money': 0, 'link': 'https://i.imgur.com/3guC213.png', 'protect': 0, 'durability': 0}, {'name': 'Barehanded', 'type': 'weapon', 'index': 200, 'description': 'Your hand. You must have known what can your hand do, right?', 'money': 0, 'link': 'https://i.imgur.com/nZ9LhLn.png', 'damage': 0, 'durability': 0}],'background' : {'name': 'Landscape', 'type': 'background', 'index': 1, 'description': "Default background.", 'money': 0, 'link': 'https://i.imgur.com/ouX3DOH.png'}, 'armor': {'name': 'Leather Armor', 'type': 'armor', 'index': 100, 'description': 'The default armor. It does nothing.', 'money': 0, 'link': 'https://i.imgur.com/3guC213.png', 'protect': 0, 'durability': 0}, 'weapon': {'name': 'Barehanded', 'type': 'weapon', 'index': 200, 'description': 'Your hand. You must have known what can your hand do, right?', 'money': 0, 'link': 'https://i.imgur.com/nZ9LhLn.png', 'damage': 0, 'durability': 0}}}
                    await self.levelling.insert_one(newuser)
                if isinstance(message.guild, discord.DMChannel):
                    return
                if not str(message.guild.id) in str((await self.levelling.find_one({"id" : message.author.id}))['guild']):
                    await self.levelling.update_one({'id': message.author.id}, {'$push': {"guild": message.guild.id}}, upsert = True)
                else:
                    stats = await self.levelling.find_one({"id" : message.author.id})
                    xp = stats["xp"] + 5
                    await self.levelling.update_one({"id" : message.author.id}, {"$set":{"xp" : xp}})
                    level = 0
                    while True:
                        if xp < ((50*(level**2))+(50*level)):
                            break
                        level += 1
                    xp -= ((50*((level-1)**2))+(50*(level-1)))
                    if xp == 0:
                        try:
                            await message.channel.send(f"Nice try **{message.author.name}**! Level {level - 1}!!!")
                        except discord.Forbidden: pass
                        return
            else:
                return

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return False
        return True
        
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name='rank', aliases=['xp'])
    async def rank_cmd(self, ctx, member : t.Optional[discord.Member]):
        """ 
        Shows someone's rank (mostly you).
        Returns a picture which shows their name, profile picture, rankings, level and a very *cool* background that can be changed in shop.

        Usage
        -----
            =rank [@someone]
        """
        if (user := member) is None: user = ctx.author
        async with ctx.typing():
            if user.bot: return await ctx.send(embed = discord.Embed(description="Sorry, this member is a bot.", color=ctx.author.color))
            stats = await self.levelling.find_one({"id" : user.id})
            if stats is None: return await ctx.send(embed = discord.Embed(desrdescription="Try to send some messages first!", color=ctx.author.color))
            else:
                base = Image.open("assets/xp.png").convert("RGBA")
                background = (await self.levelling.find_one({"id" : user.id}))['inventory']['background']['link']
                with urllib.request.urlopen(background) as url:
                        url = BytesIO(url.read())
                bg = Image.open(url).convert("RGBA")
                bg = bg.resize(((1500, 842)))
                response = requests.get(user.display_avatar.url)
                pfp = Image.open(BytesIO(response.content)).convert("RGBA")
                d = ImageDraw.Draw(base)
                title = ImageFont.truetype("assets/GOTHAM-THIN.OTF", 33)
                subTitle = ImageFont.truetype("assets/GOTHAM-THIN.OTF", 30)
                body = ImageFont.truetype("assets/GOTHAM-MEDIUM.OTF", 65)
                width, height = d.textsize(user.name, font=body)
                xp = stats["xp"]
                level = 0
                rank = 0
                while True:
                    if xp < ((50*(level**2))+(50*level)):
                        break
                    level += 1
                xp -= ((50*((level-1)**2))+(50*(level-1)))
                rankings = self.levelling.find().sort("xp",-1)
                async for x in rankings:
                    rank += 1
                    if stats["id"] == x["id"]:
                        break
                pfp = Ranking.circle(pfp, (299, 299))
                d.text((514 + width, 259), f"#{user.discriminator}", font=title, fill=(255, 255, 255), stroke_fill="white", stroke_width=1)
                d.text((514, 232), f"{user.name}", font=body, fill=(255, 255, 255, 255), stroke_fill="white", stroke_width=1)
                d.text((1186, 514), f"#{rank}", font=body, fill=(98, 211, 245), anchor='rs')
                d.text((1191, 605), f"{level}", font=body, fill=(98, 211, 245), anchor='rs')
                d.text((183, 477), f"{xp}/{int(200*((1/2)*level))}", font=subTitle, fill=(255, 255, 255, 255), stroke_fill='white',stroke_width=1)
                Ranking.drawProgressBar(d, 154, 524, 779, 80, xp/int(200*((1/2)*level)), fg=(98, 211, 245))
                base.paste(pfp, (157, 93), pfp)
                bg.paste(base, (0,0), base)
            with BytesIO() as a:
                bg.save(a, "PNG")
                a.seek(0)
                await ctx.send(content='', file = discord.File(a, "xp.png"))
            # embed = discord.Embed(description=f"name{user.name}\nxp {xp}/{int(200*((1/2)*level))}\nrank {rank}")
            # await ctx.channel.send(embed = embed)
 
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name='leaderboard', aliases=['top'])
    async def leaderboard_command(self, ctx):
        """ 
        Shows the leaderboard of the following server.
        """
        rankings = self.levelling.find({"guild" : ctx.author.guild.id}).sort("xp",-1)
        i = 0
        info = ''
        embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
        # await ctx.send(ctx.author.guild_avatar)
        if ctx.author.guild_avatar is not None:
            embed.set_thumbnail(url=ctx.author.guild_avatar.url)    
        embed.set_author(name=f"Rankings in {ctx.author.guild.name}", icon_url=ctx.author.display_avatar.url)
        async for x in rankings:
            i += 1
            # temp = ctx.guild.get_member(x["id"])
            # print(temp)
            # if temp is None:    
                # continue
            tempxp = x["xp"]
            if x["id"] == ctx.author.id:
                info += "**#" + str(i) + ' | <@' +  str(x["id"]) + '> XP: `' + str(tempxp) + '`**\n'
            else: info += "#" + str(i) + ' | <@' +  str(x["id"]) + '> XP: `' + str(tempxp) + '`\n'
            if i == 10: break
        
        embed.add_field(name=f'Top {i} text', value=info, inline=True)
        await ctx.send(embed=embed)

    
class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot : commands.Bot = bot
        self.currentPage = 0
        self._emoji = '⚙'

    @property
    def get_ping(self):
        ping = []
        for i in wavelink.NodePool._nodes: ping.append(wavelink.NodePool._nodes[i].penalty)
        return ping
    
    @property
    def get_number_players(self):
        players = 0
        for i in wavelink.NodePool._nodes: players += len(wavelink.NodePool._nodes[i].players)
        return players

    @commands.Cog.listener()
    async def on_ready(self):
        print("Miscellaneous cog loaded successfully.")
    
    @commands.command()
    async def ping(self, ctx):
        """Ping to the bot.

        Usage
        -----
            =ping
        """
        shard = ""
        for count, i in enumerate(self.get_ping, 1):
            shard += f'🎵 Shard #{count}: {round(i)}ms.\n'
        await ctx.send(f"🌎 API: {round(self.bot.latency * 1000)} ms.\n{shard.rstrip()}\n🎧 Players: {self.get_number_players} playing.")
    
    @commands.has_permissions(kick_members=True)
    @commands.command(name='kick')
    async def kick_command(self, ctx, member : discord.Member, *, reason: t.Optional[str] = None):
        """Kick someone outta the server.

        Usage
        -----
            =kick <@someone> [reason]
        """
        await member.send(embed=discord.Embed(description=f"You have been banned from server **{ctx.guild.name}**.\n{f'Reason: **{reason}**' if reason is not None else ''}\nWanna give a complaint? Direct message the server admin/mod {ctx.author.mention}."))
        await member.kick(reason=reason if reason is not None else None)
        await ctx.send(embed=discord.Embed(description=f"**✅ | {member.name} was kicked by {ctx.author.name}**\n{f'Reason: **{reason}**' if reason is not None else ''}", color=0x2ecc71))

    @kick_command.error
    async def kick_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=f"❎ | I can't kick this member.", color=0xe74c3c))

    @commands.has_permissions(ban_members=True)
    @commands.command(name='ban')
    async def ban_command(self, ctx, member : discord.Member, *, reason: t.Optional[str] = None):
        """Ban someone outta the server.

        Usage
        -----
            =ban <@someone> [reason]
        """
        await member.send(embed=discord.Embed(description=f"You have been banned from server **{ctx.guild.name}**.\n{f'Reason: **{reason}**' if reason is not None else ''}\nWanna give a complaint? Direct message the server admin/mod {ctx.author.mention}."))
        await member.ban(reason=reason if reason is not None else None)
        await ctx.send(embed=discord.Embed(description=f"**✅ | {member.name} was banned by {ctx.author.name}**.\n{f'Reason: **{reason}**' if reason is not None else ''}", color=0x2ecc71))
    
    @ban_command.error
    async def ban_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=f"❎ | I can't ban this member.", color=0xe74c3c))
    
    @commands.has_permissions(ban_members=True)
    @commands.command(name='unban')
    async def unban_command(self, ctx, member : discord.Member, *, reason: t.Optional[str] = None):
        """Unban someone, and notify them.

        Usage
        -----
            =unban <@someone> [reason]
        """
        await member.send(embed=discord.Embed(description=f"You have been unbanned from server **{ctx.guild.name}**.\n{f'Reason: **{reason}**' if reason is not None else ''}"))
        await member.unban(reason=reason if reason is not None else None)
        await ctx.send(embed=discord.Embed(description=f"**✅ | {member.name} was unbanned by {ctx.author.name}**.\n{f'Reason: **{reason}**' if reason is not None else ''}", color=0x2ecc71))
    
    @unban_command.error
    async def unban_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=f"❎ | I can't unban this member.", color=0xe74c3c))
    
    @commands.has_permissions(moderate_members=True)
    @commands.command(name='timeout')
    async def timeout_command(self, ctx, member : discord.Member, duration, *, reason: t.Optional[str] = None):
        """Timeout someone in the server.

        Usage
        -----
            =timeout <@someone> <duration> [why?]
        """
        try: 
            duration = humanfriendly.parse_timespan(duration)
            if duration > 60*60*24*28: raise InvalidTimespan
            duration = datetime.timedelta(seconds=duration)
        except InvalidTimespan: return await ctx.send(embed=discord.Embed(description="Invalid duration.", color=ctx.author.color))
        else:
            await member.timeout(duration, reason=reason if reason is not None else None)
            await ctx.send(embed=discord.Embed(description=f"**✅ | {member.mention} was timed out by {ctx.author.name} for {humanfriendly.format_timespan(duration)}.**\n{f'Reason: **{reason}**' if reason is not None else ''}", color=0x2ecc71))
    
    @timeout_command.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=f"❎ | I can't timeout this member.", color=0xe74c3c))
    
    @commands.has_permissions(moderate_members=True)
    @commands.command(name='untimeout', aliases=['removetimeout'])
    async def untimeout_command(self, ctx, member : discord.Member):
        """
        Untimeout a member.

        Usage
        -----
            =untimeout <@someone>
        """
        await member.edit(timed_out_until=None)
        await ctx.send(embed=discord.Embed(description=f"✅ | {member.mention} was no longer timed out.", color=0x2ecc71))
    
    # @untimeout_command.error
    # async def untimeout_error(self, ctx, error):
    #     if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
    #         await ctx.send(embed=discord.Embed(description=f"❎ | I can't untimeout this member.", color=0xe74c3c))
    
    @commands.command(name='avatar', aliases=['pfp', 'avt', 'ava'])
    async def avatar_command(self, ctx, member : t.Optional[discord.Member]):
        """
        Sends the lovely avatar of yourself or someone.
        
        Usage
        -----
            =avatar [@someone]
        """
        if member is None:
            embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
            embed.set_author(name=f"{ctx.author.name}'s avatar", icon_url=self.bot.user.display_avatar.url)
            embed.set_image(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
            embed.set_author(name=f"{member.name}'s avatar", icon_url=self.bot.user.display_avatar.url)
            embed.set_image(url=member.display_avatar.url)
            await ctx.send(embed=embed)

    @ban_command.error
    async def ban_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(embed=discord.Embed(description=f"❎ | You can't ban people!", color=0xe74c3c))
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=f"❎ | I can't ban bots/mods/admins.", color=0xe74c3c))
    
    @commands.command(name='donate', aliases=['support'])
    async def donate_command(self, ctx):
        """Donate for the bot to get perks, and to keep the bot from working perfectly.

        Usage
        -----
            =donate
        """
        embed = discord.Embed(title="Donate me!", description="Hello! To keep Cirno working and performing fine, consider donating!\nRemember to DM **Tiy#6324** to use your premium perks!", color=ctx.author.color)
        view = View(timeout=180)
        view.add_item(Button(url="https://www.patreon.com/cirnobot", label="Patreon"))
        await ctx.send(embed=embed, view=view)
    
async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
    await bot.add_cog(Ranking(bot))
