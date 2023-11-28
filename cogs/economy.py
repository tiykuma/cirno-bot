#coding=utf-8
import asyncio
from datetime import datetime
import math
from numerize import numerize
import re
import discord
from motor.motor_asyncio import AsyncIOMotorClient
import humanfriendly
import certifi
import random
import typing as t
from discord.ext import commands
from discord.ui import Button, View
from pymongo import MongoClient

url = "MONGODB"
asyncdata = AsyncIOMotorClient(url, tlsCAFile=certifi.where())
# data = AsyncIOMotorClient(url)

db = asyncdata["cirnochan"]
database = db.user
shopCollection = MongoClient(url, tlsCAFile=certifi.where()).cirnochan.shop
fcash = "<:fumocoin:923881630567899177>"
fcashgif = "<a:fumo:922813445689180200>"
fcashass = "<:fumoass:923881668819972097>"


class AlreadyRegistered(commands.CommandError):
    pass

class NotRegistered(commands.CommandError):
    pass 

class NoMoney(commands.CommandError):
    pass

class UserBot(commands.CommandError):
    pass

class EconomyView(View):
    def __init__(self, timeout: t.Optional[float] = 20):
        super().__init__(timeout=timeout)
    
    async def on_timeout(self):
        for i in self.children:
            i.disabled = True
        await self.message.edit(content='This message is now frozen.', view=self)

class Economy(commands.Cog):
    """Trade, buy, get more cirnoniums with me!
    """
    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self._emoji = '💵'

    async def info(self, user:discord.Member):
        try: in4 = await database.find_one({"id" : user.id})
        except: return None
        return in4
    
    async def user_cash(self, user : discord.Member, amount : t.Optional[int]=None):
        cash = (await self.info(user))['money']
        if not amount == None:
            if amount > cash: raise NoMoney
        return cash
    
    def human_format(num):
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

    
    def format_thousands(self, amount : int):
        return f"{amount:,}".replace(',','.')
    

    @commands.Cog.listener()
    async def on_ready(self):
        print("Economy cog loaded successfully.")

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return False
        return True

    @commands.command(name='cash', aliases=['balance','bal'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def balance_command(self, ctx, member : t.Optional[discord.Member]):
        """
        Check your (or someone's) balance.

        Usage
        -----
            =cash [@someone]
        """
        if (user := member) is None: user = ctx.author
        try: await self.open_acc(ctx, user)
        except AlreadyRegistered: 
            await ctx.channel.send(f"**{user.name}**, you are having {self.format_thousands(await self.user_cash(user))}{fcash}")
        except UserBot: return await ctx.send(f"Sorry, but **{user.name}** is a bot.")

    async def open_acc(self, ctx, mem:discord.Member):
        if mem.bot: raise UserBot
        try:
            get = (await database.find_one({"id" : mem.id}))['money']
            raise AlreadyRegistered
        except (TypeError, KeyError):
            # user = database.find_one({"id" : user.id})
            em = discord.Embed(description=f"You will be able to:\n - Send and receive coins.\n - Use many features, including gambling, shops, etc.\nRemember, this bot's currency is {fcash}.\nYou can't trade {fcash} outside Discord!\n*Thanks for using this bot!*", color=mem.color)
            em.set_author(name="Wanna to sign up a bank account?", icon_url=self.bot.user.display_avatar.url)
            view = EconomyView(timeout=180)
            em.set_footer(icon_url=mem.display_avatar.url,text=f"Register for: {mem.name}")
            btn = Button(label='Confirm', emoji='👍' ,style=discord.ButtonStyle.green)
            view.add_item(btn)
            async def btn_callback(interaction : discord.Interaction):
                if interaction.user == mem:
                    # await interaction.response.edit_message(embed=discord.Embed(title='Okey...', color=mem.color))
                    try:
                        get = (await database.find_one({"id" : mem.id}))['money']
                        await interaction.response.edit_message(embed=discord.Embed(title='Waaaaait', description=f"You've already registered!",color=mem.color), view=None)
                        raise AlreadyRegistered
                    except (TypeError, KeyError):
                        in4 = {
                            "id" : mem.id,
                            "name" : mem.name,
                            "money" : 1000,
                            'workcount' : 0,
                            'daily': '2019-01-01 00:00:00'
                        }
                        await database.update_one({"id" : mem.id}, {"$set": in4})
                        await interaction.response.edit_message(embed=discord.Embed(title='Successfully signed up.', description=f'You are given your first 1000{fcash}, hehe.',color=mem.color), view=None)
                        return
                else:
                    await interaction.response.send_message("Hey! Who are you???", ephemeral=True)
            view.message = await ctx.send(embed=em, view=view)
            btn.callback = btn_callback
    
    @commands.cooldown(1, 12, commands.BucketType.user)
    @commands.command(name='coinflip', aliases=['cf'])
    async def cf_command(self, ctx, num : str, th : t.Optional[str] = 'tails/heads'):
        """Do a coinflip (not gambling!)

        Usage
        -----
            =coinflip <amount of coins/all> [tails/heads]
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            if num.lower() in ['all', 'a']: 
                if await self.user_cash(ctx.author) > 50000: num = "50000"
                else: num = await self.user_cash(ctx.author)
            try: await self.user_cash(ctx.author, int(num))
            except NoMoney:
                self.bot.get_command('cf').reset_cooldown(ctx)
                return await ctx.channel.send(embed=discord.Embed(title=f"You don't have enough money.", color=ctx.author.color))
            except ValueError:
                self.bot.get_command('cf').reset_cooldown(ctx)
                return await ctx.channel.send(embed=discord.Embed(title=f"{ctx.author.name}, invalid arguments :c", color=ctx.author.color))
            else:
                if th == 'tails/heads': ha = 'heads'
                if th in ['t','T','TAILS','TAIL','tails', 'tail']: ha = "tails"
                else: ha = "heads"
                if int(num) < 1:
                    # self.bot.get_command('cf').reset_cooldown(ctx)
                    return await ctx.send(embed=discord.Embed(title=f"You need to flip more than **0{fcash}**.", color=ctx.author.color))
                msg = await ctx.channel.send(embed=discord.Embed(title=f"{ctx.author.name}'s trying to coinflip {self.format_thousands(int(num))}{fcashgif} and choose {ha} ...", description=f"The result is...",color=ctx.author.color))
                await asyncio.sleep(3)
                choice = random.choice(['heads', 'tails'])
                if choice == ha:
                    await msg.edit(embed=discord.Embed(title=f"{ctx.author.name}'s trying to coinflip {self.format_thousands(int(num))}{fcash if ha == 'heads' else fcashass} and choose {ha} ...", description=f"The result is... {choice}! You won **{self.format_thousands(int(num) * 2)}{fcash}** c:",color=ctx.author.color))
                    await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) + int(num))}})
                else:
                    await msg.edit(embed=discord.Embed(title=f"{ctx.author.name}'s trying to coinflip {self.format_thousands(int(num))}{fcashass if ha == 'heads' else fcash} and choose {ha} ...", description=f"The result is... {choice}! You lose **{self.format_thousands(int(num))}{fcash}** :c",color=ctx.author.color))
                    await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) - int(num))}})
    
    @commands.cooldown(1, 12, commands.BucketType.user)
    @commands.command(name='oddeven', aliases=['oe', 'chanle'])
    async def oddeven_command(self, ctx, amount : str):
        """Bet some money and chose, either odd or even.

        Usage
        -----
            =oddeven <amount>
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            if amount.lower() in ['all', 'a']: 
                if await self.user_cash(ctx.author) > 50000: amount = "50000"
                else: amount = await self.user_cash(ctx.author)
            try: await self.user_cash(ctx.author, int(amount))
            except NoMoney:
                self.bot.get_command('oddeven').reset_cooldown(ctx)
                return await ctx.channel.send(embed=discord.Embed(title=f"You don't have enough money.", color=ctx.author.color))
            except ValueError:
                self.bot.get_command('oddeven').reset_cooldown(ctx)
                return await ctx.send(embed=discord.Embed(title=f"{ctx.author.name}, invalid arguments :c", color=ctx.author.color))
            embed = discord.Embed(description=f"Chose a number from 1 to 10!\n*Currently betting:* __{self.format_thousands(int(amount))}{fcashgif}__", color=ctx.author.color, timestamp=datetime.utcnow())
            view = EconomyView(timeout=30)
            async def ButtonCallback(interaction : discord.Interaction):
                if interaction.user != ctx.author: return await interaction.response.send_message(random.choice(['Who are you?', "You aren't playing this game, so buzz off", "maybe you misclicked, right?"]), ephemeral=True)
                # await interaction.response.edit_message()
                await asyncio.sleep(2)
                if (number := random.randint(1, 1000)) % 2 == int(interaction.data['custom_id']) % 2:
                    view.children[int(interaction.data['custom_id'])-1].style = discord.ButtonStyle.success
                    for i in view.children: i.disabled = True
                    embed.description = f"You and I both choose an {'even' if number % 2 == 0 else 'odd'} number!\nYou got {self.format_thousands(int(int(amount) * 1.9))}{fcashgif}!\n*{random.choice(['That was lucky!', 'Nice move!'])}*"
                    # embed.set_author("🎉 Congratulations!")
                    await interaction.response.edit_message(embed=embed, view=view)
                    await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) + int(int(amount) * 1.9))}})
                else:
                    view.children[int(interaction.data['custom_id'])-1].style = discord.ButtonStyle.danger        
                    for i in view.children: i.disabled = True
                    embed.description = f"You chose an {'even' if int(interaction.data['custom_id']) % 2 == 0 else 'odd'} number, but I chose a {'even' if number % 2 == 0 else 'odd'} one!\nYou lose {self.format_thousands(int(amount))}{fcashgif}!\n*{random.choice(['So sad! You lose all the money.', 'Try better next time!'])}*"
                    await interaction.response.edit_message(embed=embed, view=view)
                    await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) - int(amount))}})
                view.stop()

            for i in range(1, 11):
                button = Button(label=str(i), custom_id=str(i))
                view.add_item(button)
                button.callback = ButtonCallback
            embed.set_author(name="Odd-Even game", icon_url=ctx.author.display_avatar.url)
            view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='daily')
    async def daily_command(self, ctx):
        """Get much money after 12 hours~!
        Usage
        -----
            =daily
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            view = EconomyView(timeout=180)
            view.add_item(Button(url="https://top.gg/bot/956419438159204362", label="Top.gg Link"))
            embed = discord.Embed(title="Daily", description="Vote for the bot to get the daily reward!", color=ctx.author.color)
            embed.set_image(url="https://images-ext-2.discordapp.net/external/7HEyOVXYjoYIADUOR19xaB6OPnU42Z0IcDgw0Q2j0Mw/https/i.imgur.com/NoK9MtD.png?width=1275&height=676")
            view.message = await ctx.send(embed=embed, view=view)

    @commands.cooldown(1, 35, commands.BucketType.user)
    @commands.command(name='baucua', aliases=['bctc', 'baucuatomca', 'thefeast', 'tf'])
    async def bctc_cmd(self, ctx, amount : str = None):
        """Play a fun gamblingn't game.

        Usage
        -----
            =baucua [amount]
        """
        
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            try:
                if amount is None: amount = 1000
                amount = int(amount) 
                await self.user_cash(ctx.author, int(amount))
            except NoMoney:
                self.bot.get_command('bctc').reset_cooldown(ctx)
                return await ctx.send(embed = discord.Embed(description="You don't have enough money.", colour=ctx.author.color))
            except ValueError:
                self.bot.get_command('bctc').reset_cooldown(ctx)
                return await ctx.send(embed=discord.Embed(title=f"{ctx.author.name}, invalid arguments :c", color=ctx.author.color))
            self.confirmed = False
            if amount < 500: 
                self.bot.get_command('bctc').reset_cooldown(ctx)
                return await ctx.send(f"Minimum amount of coin to bet: 500{fcash}", color=ctx.author.color)    
            if amount > 100000: 
                self.bot.get_command('bctc').reset_cooldown(ctx)
                return await ctx.send(f"Maximum amount of coin to bet: 100.000{fcash}", color=ctx.author.color)
            self_money = (await self.info(ctx.author))['money']
            button = {"<:nai:936652706389557288>" : "Deer", "<:bau:936652704254672916>" : "Gourd", "<:ga:936652706838347797>" : "Chicken",'<:ca:936652705487794207>' : 'Fish',"<:cua:936652706586718298>" : "Crab","<:tom:936652707144564767>":"Shrimp","✅":"Confirm","❎":"Cancel"}
            buttonMoney = {"<:nai:936652706389557288>":0, "<:bau:936652704254672916>":0, "<:ga:936652706838347797>":0,'<:ca:936652705487794207>':0,"<:cua:936652706586718298>":0,"<:tom:936652707144564767>":0}
            embed1 = discord.Embed(title="The Feast", description=f"1 interaction = __{self.format_thousands(amount)}{fcash}__", color=ctx.author.color)
            embed1.set_thumbnail(url="https://i.imgur.com/v98tzDN.png")
            embed1.set_footer(text=f"Player: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            for i in buttonMoney: embed1.add_field(name=f"{i} {button[i]}", value=f"{buttonMoney[i]} {fcash}", inline=True)
            view = EconomyView(timeout=180)
            async def callback(interaction : discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(content="Who are you? You aren't playing.", ephemeral=True)
                button_emoji = list(button.keys())[list(button.values()).index(interaction.data['custom_id'])]
                button_index = list(button.values()).index(interaction.data['custom_id'])
                await interaction.response.defer()
                try:
                    sum = 0
                    for i in range(0, 5): sum += buttonMoney[list(button.keys())[i]]
                    if sum > self_money - amount and interaction.data['custom_id'] not in ['Confirm', "Cancel"]: 
                        embed1.add_field(name="*Conclusion*", value=f"You betted {sum} {fcash}, your cash self.currently have {self_money} {fcash}.")
                        for i in view.children: 
                            if i.label not in ["Confirm", "Cancel"]: i.disabled = True
                    else:
                        buttonMoney[button_emoji] += amount
                    embed1.set_field_at(index=button_index, name=f"{button_emoji} {interaction.data['custom_id']}", value=f"{self.format_thousands(buttonMoney[button_emoji])} {fcash}", inline=True)
                    await interaction.edit_original_message(embed=embed1, view=view)
                except KeyError: 
                    if button_emoji == '✅': 
                        self.confirmed = True
                        for i in view.children: i.disabled = True
                        await interaction.edit_original_message(view=view)
                    else:
                        return await interaction.edit_original_message(content="Cancelled command.", embed=None, view=None)
                if self.confirmed is True:
                    resultMessage = await ctx.send(f"Rolling the dice... {fcashgif}")
                    await asyncio.sleep(3)
                    randomList = []
                    for i in range(0, 3): randomList.append(random.choice(list(buttonMoney.keys())))
                    await resultMessage.edit(content=''.join(randomList))
                    await ctx.send("Check the previous message for results.")
                    await asyncio.sleep(3)
                    sum = 0
                    for i in list(buttonMoney.keys()):
                        index = list(buttonMoney.keys()).index(i)
                        if i in randomList:
                            if buttonMoney[i] > 0:
                                buttonMoney[i] *= (randomList.count(i) - 0.1 + 1)
                                embed1.set_field_at(index=index, name=f"{i} {button[i]}", value=f"+{self.format_thousands(int(buttonMoney[i]))} {fcash}", inline=True)
                        else:
                            if buttonMoney[i] > 0:
                                buttonMoney[i] *= -2
                                embed1.set_field_at(index=index, name=f"{i} {button[i]}", value=f"{self.format_thousands(int(buttonMoney[i]))} {fcash}", inline=True)
                        sum += int(buttonMoney[i])
                    try:
                        embed1.set_field_at(index=6, name="*Total*", value=f"{f'You won {self.format_thousands(sum)} {fcash}, nice :ww' if sum > 0 else f'You lost {self.format_thousands(sum)} {fcash} , sorry ☹️.'}" if sum < 0 else 'You won nothing.', inline=False)
                    except IndexError:
                        embed1.add_field(name="*Total*", value='You won ' + self.format_thousands(sum) + fcash + ', nice :ww' if sum > 0 else 'You lost ' + self.format_thousands(sum)+ fcash + ', sorry ☹️.' if sum < 0 else 'You won nothing.', inline=False)
                    if (await self.info(ctx.author))['money'] + sum >= 0:
                        await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) + sum)}})
                    else:
                        await database.update_one({"id" : ctx.author.id}, {"$set": {"money": 0}})
                    return await interaction.edit_original_message(embed=embed1, view=None)
            for i in button:
                btn = Button(emoji=i, label=button[i], custom_id=button[i], style=discord.ButtonStyle.success if button[i] == "Confirm" else discord.ButtonStyle.danger if button[i] == "Cancel" else discord.ButtonStyle.grey)
                btn.callback = callback
                view.add_item(btn)
            view.message = await ctx.send(embed=embed1, view=view)
            

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name='shop', aliases=['store'])
    async def shop_command(self, ctx):
        """Let's buy something! ( *^-^)ρ(*╯^╰)

        Usage
        -----
            =shop
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            self.items = shopCollection.find().sort("index", 1)
            self.length = self.items.count()
            self.page = 0
            view = EconomyView(timeout=180)
            btn1 = Button(style=discord.ButtonStyle.green, emoji='⏮')
            btn2 = Button(emoji='◀')
            btn3 = Button(emoji='▶')
            btn4 = Button(style=discord.ButtonStyle.green, emoji='⏭')
            for i in [btn1, btn2, btn3, btn4]:
                view.add_item(i)
            async def btn1_callback(interaction : discord.Interaction):
                await interaction.response.edit_message(embed=self.page_show(ctx, 0))
            async def btn2_callback(interaction : discord.Interaction):
                if (self.page > 0):
                    self.page -= 1
                    await interaction.response.edit_message(embed=self.page_show(ctx, self.page))
            async def btn3_callback(interaction : discord.Interaction):
                if self.page < int(self.length / 10 + 1 if isinstance(self.length / 10, float) else self.length / 10) - 1:
                    self.page += 1
                    await interaction.response.edit_message(embed=self.page_show(ctx, self.page))
            async def btn4_callback(interaction : discord.Interaction):
                await interaction.response.edit_message(embed=self.page_show(ctx, int((self.length / 10 + 1 if isinstance(self.length / 10, float) else self.length / 10)) - 1))
            btn1.callback = btn1_callback
            btn2.callback = btn2_callback
            btn3.callback = btn3_callback
            btn4.callback = btn4_callback
            view.message = await ctx.channel.send(embed=self.page_show(ctx, 0), view=view)
    def page_show(self, ctx, page):
        em = discord.Embed(description="Available commands:\n `=buy [id]` to buy or get information of an item\nItem categories:\n 🖼️: Background, ⚔️: Weapon, 🛡️: Armor\n**Have a good day!**", color=ctx.author.color)
        em.set_author(name='Shop', icon_url=ctx.author.display_avatar.url)
        self.bg = ''
        for num in range(page*10, page*10+10):
            try:
                i = self.items[num]
                if i['type'] == 'background': icon = '🖼'
                elif i['type'] == 'armor': icon = '🛡'
                elif i['type'] == 'weapon': icon = '⚔'
                self.bg += f'`{i["index"]}` {icon} `{i["name"]}{" " * (35 - len(str(i["index"]) + icon + " " + i["name"] + numerize.numerize(float(i["money"])) + "f"))} {numerize.numerize(float(i["money"]))}`{fcash}\n'
            except: break
        self.bg.rstrip('\n')
        em.add_field(name="-"*55, value=self.bg, inline=False)
        em.set_footer(text=f"Page {page + 1} of {int(self.length / 10 + 1 if isinstance(self.length / 10, float) else self.length / 10)}")
        return em
        
    
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name='buy')
    async def buy_command(self, ctx, *, item):
        """Buy an item from the shop!

        -----
            =buy <item name / id>
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            thing = shopCollection.find_one({"name" : item.title()}, {"_id" : False})
            if not thing: thing = shopCollection.find_one({"index" : int(item)}, {"_id" : False})
            description = f" - Description: **{thing['description']}**\n"
            if thing['type'] in ['armor', 'weapon']:
                description += f"{' - Protection: **' + str(thing['protect']) + '**' if thing['type'] == 'armor' else ' - Damage: **' + str(thing['damage']) + '**'}\n - Durability: **{thing['durability']}**\n"
            description += f"- Money: **{numerize.numerize(thing['money'])}{fcash}**"
            em = discord.Embed(title=f"Do you want to buy {'🖼' if thing['type'] == 'background' else '🛡' if thing['type'] == 'armor' else '⚔' if thing['type'] == 'weapon' else ''} `{thing['name']}`?", description=description, color=ctx.author.color)
            em.set_image(url=thing["link"])
            em.set_author(name='Confirm', icon_url=ctx.author.display_avatar.url)
            # await ctx.send(embed = em)
            confirm = Button(label='Confirm', style=discord.ButtonStyle.green)
            cancel = Button(label='Cancel', style=discord.ButtonStyle.red)
            view = EconomyView()
            for i in [confirm, cancel]:
                view.add_item(i)
            async def confirmCallback(interaction : discord.Interaction):
                if interaction.user == ctx.message.author:
                    if thing in ((await database.find_one({"id" : ctx.author.id}))['inventory']['things']):
                        await interaction.response.edit_message(content=f"Yeeeyy! You've set {'🖼' if thing['type'] == 'background' else '🛡' if thing['type'] == 'armor' else '⚔' if thing['type'] == 'weapon' else ''} `{thing['name']}` successfully!", view=None)
                        await database.update_one({"id" : ctx.author.id}, {"$set":{f"inventory.{thing['type']}" : thing}})
                    else:
                        try: 
                            await self.user_cash(ctx.author, thing['money'])
                            await database.update_one({"id" : ctx.author.id}, {"$set": {"money": ((await self.user_cash(ctx.author)) - thing['money'])}})
                            await database.update_one({"id" : ctx.author.id}, {"$push":{"inventory.things": thing}})
                            await database.update_one({"id" : ctx.author.id}, {"$set":{f"inventory.{thing['type']}": thing}})
                            return await interaction.response.edit_message(content=f"🎉 Woo-hoo! You bought {'🖼' if thing['type'] == 'background' else '🛡' if thing['type'] == 'armor' else '⚔' if thing['type'] == 'weapon' else ''} `{thing['name']}`!", view=None)
                        except NoMoney:
                            await interaction.response.edit_message(content="Oopsie! You don't have enough money <(＿　＿)>", view=None)
                else:
                    await interaction.response.send_message("Hey! You can't use that!", ephemeral=True)
            async def cancelCallback(interaction : discord.Interaction):
                if interaction.user == ctx.message.author:
                    await interaction.response.edit_message(content='Cancelled command.', embed = None, view=None)
                else:
                    await interaction.response.send_message("Hey! You can't use that!", ephemeral=True)
            confirm.callback = confirmCallback
            cancel.callback = cancelCallback
            view.message = await ctx.channel.send(embed=em, view=view)
    
    @commands.command(name='item')
    async def item_command(self, ctx, *, query):
        """See your item's statistics.

        -----
            =item <item id/name>
        """
        thing = None
        for i in (userInventory := (await database.find_one({"id" : ctx.author.id}))['inventory']['things']):
            if query.lower() == i['name'].lower() or query == str(i['index']): thing = i
        if not thing: return await ctx.send(embed=discord.Embed(title=f"There's no item called {query} in your inventory.", color=ctx.author.color))
        embed = discord.Embed(title=f"About {thing['name']}", description=f"**{thing['description']}**", color=ctx.author.color)
        embed.add_field(name="Money", value=f"{numerize.numerize(thing['money'])} {fcash}", inline=True)
        embed.add_field(name="Index", value=thing['index'], inline=True)
        if thing['type'] in ['weapon', 'armor']:
            embed.add_field(name=f"{'Protection' if thing['type'] == 'armor' else 'Damage'}", value=thing['protect'] if thing['type'] == 'armor' else thing['damage'], inline=True)
            embed.add_field(name="Durability", value=thing['durability'], inline=True)
        embed.set_image(url=thing['link'])
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='sell')
    async def sell_command(self, ctx, item):
        """Sell an item and get 75% of its original price.

        -----
            =sell <item id/name>

        """
        userInventory = (await database.find_one({"id" : ctx.author.id}))['inventory']
        thing = None
        view = EconomyView(timeout=60)
        for i in userInventory['things']: 
            if str(i['index']) == item or i['name'] == item: 
                thing = i
                break
        async def callback(interaction : discord.Interaction):
            if interaction.user != ctx.author: return await interaction.response.send_message(content="You didn't invoked this command.", ephemeral=True, delete_after=3)
            if (cID := interaction.data['custom_id']) == '1':
                await database.update_one({"id" : ctx.author.id}, {"$pull" : {'inventory.things' : {"index" : item}}})
                await database.update_one({"id" : ctx.author.id}, {"$set": {"money": ((await self.user_cash(ctx.author)) + int(thing['money']/100*75))}})
                if userInventory[thing['type']] == thing: 
                    for i in [1, 100, 200]: 
                        if (default := shopCollection.find_one({'index' : i}))['type'] == thing['type']: 
                            await database.update_one({"id" : ctx.author.id}, {"$set" : {f"inventory.{thing['type']}" : default}})
                return await interaction.response.edit_message(content=f"You sold {'🖼' if thing['type'] == 'background' else '🛡' if thing['type'] == 'armor' else '⚔' if thing['type'] == 'weapon' else ''} `{thing['name']}`!", view=None)
            elif cID == '2':
                await interaction.response.edit_message(content="Cancelled command.", embed=None, view=None, delete_after=5)
        confirm = Button(style=discord.ButtonStyle.success, label="Confirm", custom_id='1')
        cancel = Button(style=discord.ButtonStyle.danger, label="Cancel", custom_id='2')
        for i in [confirm, cancel]:
            view.add_item(i)
            i.callback = callback
        if item in [1, 100, 200]: return await ctx.send(embed=discord.Embed(description="You can't sell default items!", color=ctx.author.color))
        if thing is None: return await ctx.send(embed=discord.Embed(description="The item isn't available.", color=ctx.author.color))
        embed = discord.Embed(title=f"Do you want to sell {'🖼' if thing['type'] == 'background' else '🛡' if thing['type'] == 'armor' else '⚔' if thing['type'] == 'weapon' else ''} `{thing['name']}`?", description=f"- Description: **{thing['description']}**\nYou will get: **{self.format_thousands(int(thing['money']/100*75))}{fcash}**", color=ctx.author.color)
        embed.set_image(url=thing['link'])
        embed.set_author(name=f"Confirm", icon_url=ctx.author.display_avatar.url)
        view.message = await ctx.send(embed=embed, view=view)
        

    @commands.command(name='inventory',aliases=['inv'])
    async def inventory_command(self, ctx):
        """Look at your inventory!
        
        Usage
        -----
            =inventory
        """
        things = (await database.find_one({"id":ctx.author.id}))["inventory"]["things"]
        things = sorted(things, key= lambda d: d['index'])
        pages = math.ceil(len(things) / 10)
        print(things)
        self.currently = 0
        inventory = []
        for count, i in enumerate(things, 1):
            inventory.append(f"{count}. {'🖼' if i['type'] == 'background' else '🛡' if i['type'] == 'armor' else '⚔' if i['type'] == 'weapon' else ''} **{i['name']}** `(ID: {i['index']})`")
        embed = discord.Embed(title=f"{ctx.author.name}'s inventory", description="\n".join(inventory[10 * self.currently:][:10]), color=ctx.author.color)
        view = None
        async def ButtonCallback(interaction : discord.Interaction):
            if interaction.user != ctx.author: return await interaction.response.send_message("Who are you?", ephemeral=True)
            if interaction.data['custom_id'] == "▶":
                if self.currently + 1 == pages: self.currently = 0
                else: self.currently += 1
            if interaction.data['custom_id'] == "◀":
                if self.currently == 0: self.currently = pages - 1
                else: self.currently -= 1
            embed.description = "\n".join(inventory[10 * self.currently:][:10])
            embed.set_footer(text=f"Page {self.currently + 1} of {pages}", icon_url=ctx.author.display_avatar.url)
            await interaction.response.edit_message(embed=embed)
        if pages > 1:
            embed.set_footer(text=f"Page {self.currently + 1} of {pages}", icon_url=ctx.author.display_avatar.url)
            view = EconomyView(timeout=60)
            for i in ['◀', '▶']:
                button = Button(emoji=i, custom_id=i)
                view.add_item(button)
                button.callback = ButtonCallback
            view.message = await ctx.send(embed=embed, view=view)
        else: await ctx.send(embed=embed, view=view)

    @commands.command(name='give', aliases=['giv','cho','send'])
    async def give_command(self, ctx, mem:discord.Member, amount : int):
        """Give someone an amount of cirnoniums

        
        Usage
        -----
            =give <@someone> <amount>
        """
        try: await self.open_acc(ctx, ctx.author)
        except AlreadyRegistered:
            tax = False
            try: await self.user_cash(ctx.author, amount)
            except NoMoney:
                await ctx.channel.send(embed=discord.Embed(title=f"You don't have enough money."))
                return
            try: await self.open_acc(ctx, mem)
            except AlreadyRegistered:
                if amount < 1:
                    await ctx.channel.send(embed=discord.Embed(title=f"Send a positive amount, please:)"))
                    return
                if amount > 50000: tax = True
                amount_without_fee = amount
                try: await self.open_acc(ctx, mem)
                except AlreadyRegistered:
                    if amount == None: await ctx.channel.send(embed=discord.Embed(title=f"Okey, {ctx.author.name} sent {mem.name} ... *how much?*",color=ctx.author.color))
                    else:
                        if tax == False:
                            await ctx.channel.send(embed=discord.Embed(title=f"{ctx.author.name} sent {mem.name} {self.format_thousands(amount)}{fcash}", description='*No extra fees required!*', color=ctx.author.color))
                        if tax == True:
                            embed=discord.Embed(title=f"{ctx.author.name} sent {mem.name} ~~{self.format_thousands(amount_without_fee)} {fcash}~~{self.format_thousands(round(amount - (amount / 100)))} {fcash}", description=f'*1% of fee is required because the amount is greater than 50.000*{fcash}', color=ctx.author.color)
                            await ctx.channel.send(embed=embed)
                            amount = round(amount - (amount / 100))
                        await database.update_one({"id" : ctx.author.id}, {"$set": {"money": (await self.user_cash(ctx.author) - amount_without_fee)}})
                        await database.update_one({"id" : mem.id}, {"$set": {"money": (await self.user_cash(mem) + amount)}})
        except:
            await ctx.channel.send(embed=discord.Embed(title=f"{ctx.author.name}, invalid arguments :c"))
    
    @commands.command(name='cheat', hidden=True)
    @commands.is_owner()
    async def cheat_mode(self, ctx, user : discord.Member, *, amount : int):
        try: await self.open_acc(ctx, user)
        except AlreadyRegistered:
            if amount == None: await ctx.channel.send(embed=discord.Embed(title=f"Okey, {ctx.author.name} cheated {user.name} ... *how much?*",color=ctx.author.color))
            else:
                await ctx.channel.send(embed=discord.Embed(title=f"{ctx.author.name} cheated {user.name} {self.format_thousands(amount)}{fcash}", description='*No extra fees required!*', color=ctx.author.color))
                await database.update_one({"id" : user.id}, {"$set": {"money": (await self.user_cash(user) + amount)}})
     
    async def daily_process(self, id):
        user = await self.bot.fetch_user(id)
        try:
            current_money = (await self.info(user))['money']
            reward = random.randint(1000, 5000)
            await database.update_one({"id" : user.id}, {"$set":{"money" : current_money + reward}})
            await user.send(embed=discord.Embed(title="Thank you!", description=f"You voted for the bot, and get {reward} coins!\nCome back in the next 12 hours to get more reward!"))
        except (TypeError, KeyError): pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == 949591469243650099:
            user = (message.content.split(" "))[0]
            user = re.sub("\D", "", user)
            await self.daily_process(user)

        

async def setup(bot):
    await bot.add_cog(Economy(bot))