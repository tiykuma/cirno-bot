from dis import disco
import io
import discord
import googletrans
from googletrans import Translator
import requests
import asyncio
import typing as t
from discord.ui import Button, View, Modal, TextInput
import json
import aiohttp
import asyncpraw
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient
import akinator
import certifi
import random
from discord.ext import commands

data = MotorClient("MONGODB", tlsCAFile=certifi.where())
db = data['cirno']
reddit = asyncpraw.Reddit(client_id='JGrBNto33ZGbNf08nGuCjw', client_secret="Ch_lE750kURXM67BGh6CtWM41cB7sA",username='amorgussussususus', password='Trongnguyen123',user_agent='python')

class FunView(View):
    def __init__(self, timeout: t.Optional[float] = 60):
        super().__init__(timeout=timeout)
    
    async def disable_buttons(self):
        for i in self.children:
            i.disabled = True

    async def on_timeout(self):
        await self.disable_buttons()
        self.stop()
        await self.message.edit(content="This message is now frozen.", view=self)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._emoji = "😁"


    @commands.Cog.listener()
    async def on_ready(self):
        print("Fun cog loaded successfully.")
    
    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel): return False
        return True
    
    @commands.command(name='dokidoki', aliases=['dokidokiwakuwaku'])
    async def ddww_command(self, ctx : commands.Context):
        """
        Basically it sends a full Doki Doki Waku Waku

        Usage
        -----
            =dokidoki
        """
        await ctx.send(file=discord.File(r"assets/8mb.video-aUP-yBUbItW9.mp4",filename="Doki Doki.mp4"))
        
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.command(name='copypasta', aliases=['cp', 'para' 'vanmau','vmau','vm'])
    async def copypasta(self, ctx, query : t.Optional[str]):
        """
        Give you some paragraphs which were stolen from the internet.

        Usage
        -----
            =copypasta [copypasta id]
        """
        self.currentPage = 0
        count = db['vanmau'].estimated_document_count()
        list = []
        async for i in db['vanmau'].find(): list += i
        if query is None:
            def help(da, page):
                em = discord.Embed(description="Give you some Vietnamese copypastas which were stolen from the internet.\nUsage: `=cp [id]`",colour=ctx.author.color)
                em.set_author(name="Copypastas", icon_url=self.bot.user.display_avatar.url)
                number = 25 * page
                for items in range(25*page, 25*(page+1)):
                    try:
                        number += 1
                        ho = list[items]
                        em.add_field(name=f"`#{number}`", value=ho['title'])
                    except: break
                em.set_footer(text=f"Requested by {ctx.author.name} | Page {page + 1} of {pages}", icon_url=ctx.author.display_avatar.url)
                return em
            if count % 25 == 0: 
                pages = count / 25
            else: pages = int(count / 25) + 1
            next = Button(emoji='▶')
            prev = Button(emoji='◀')
            cancel = Button(emoji='❌', label="End Interaction", style=discord.ButtonStyle.danger)
            # donate = Button(label="Donate A Copypasta", style=discord.ButtonStyle.blurple)
            view = FunView()
            for i in [prev, next, cancel]:
                view.add_item(i)
            async def nextCallback(interaction : discord.Interaction):
                if pages > self.currentPage +1:
                    await interaction.response.defer()
                    self.currentPage += 1
                    await interaction.edit_original_message(embed = help(list, self.currentPage))
            async def previousCallback(interaction : discord.Interaction):
                if self.currentPage > 0:
                    await interaction.response.defer()
                    self.currentPage -= 1
                    await interaction.edit_original_message(embed = help(list, self.currentPage))
            async def cancelCallback(interaction : discord.Interaction):
                await view.on_timeout()
                # await interaction.response.edit_message(view=view)
            # async def donateCallback(interaction : discord.Interaction):
            #     modal = Modal(title="Donate the bot A Copypasta!")
            #     modal.on_submit = self.on_submit()
            #     modal.add_item(TextInput(label="Name", required=False, max_length=100))
            #     modal.add_item(TextInput(label="Content", style=discord.TextStyle.long, max_length=3900))
            #     await interaction.response.send_modal(modal)
            #     async def on_submit(interaction : discord.Interaction):
            #         owner = self.bot.get_user(630981548258099210)
            #         embed = discord.Embed(title=modal.children[0].value, description=modal.children[1].value)
            #         embed.set_footer(text=f"Donated by {interaction.user}", icon_url=interaction.user.display_avatar.url)
            #         await owner.send(embed=embed)
            #         await interaction.response.send_message("Thank you for donating the bot!", ephemeral=True)
            next.callback = nextCallback
            prev.callback = previousCallback
            cancel.callback = cancelCallback
            # donate.callback = donateCallback
            view.message = await ctx.send(embed = help(list, self.currentPage), view = view)
            # await ctx.send(content='hello', view=view)
        else:
            try:
                num = int(query)
                text = list[num-1]
                em = discord.Embed(description=text['content'],colour=ctx.author.color)
                em.set_author(name=text['title'], icon_url=ctx.author.display_avatar.url)
                # em.set_footer(text=f"Requested by {ctx.author.name}")
            except:
            
                self.bot.get_command('vm').reset_cooldown(ctx)
                em = discord.Embed(title='Try `=copypasta` to find another!',colour=ctx.author.color)
                em.set_author(name='This copypasta does not exist.',icon_url=ctx.author.display_avatar.url)
            await ctx.channel.send(embed=em)


    @commands.cooldown(1,5, commands.BucketType.user)   
    @commands.command(name='redditmeme',aliases=['rmeme','redditmemes'])
    async def redditmemes_command(self, ctx):
        """Watch some funny Reddit memes.

        Usage
        -----
            =redditmemes
        """
        async def next(interaction : discord.Interaction):
            await interaction.response.defer()
            await interaction.edit_original_message(embed = await self.meme_get(ctx))
        async def cancel(interaction : discord.Interaction):
            await view.on_timeout()
        btn1 = Button(label='Next Meme',style=discord.ButtonStyle.success)
        btn2 = Button(label='End Interaction',style=discord.ButtonStyle.danger)
        view = FunView()
        btn1.callback = next
        btn2.callback = cancel
        view.add_item(btn1)
        view.add_item(btn2)
        view.message = await ctx.send(embed=(await self.meme_get(ctx)), view=view)

    
    async def meme_get(self, ctx):
        legend = requests.get(url='https://meme-api.herokuapp.com/gimme').text
        information = json.loads(legend)
        em = discord.Embed(color=ctx.author.color)
        em.set_author(name=information['title'], url=information['postLink'], icon_url=ctx.author.display_avatar.url)
        em.set_footer(text=f'✍️ {information["author"]} | 👍 {information["ups"]}')
        em.set_image(url=information['url'])
        return em
    
    @commands.cooldown(1,5, commands.BucketType.user)   
    @commands.command(name='fumomeme', aliases=['fumomemes', 'fumo'])
    async def fumomeme_command(self, ctx):
        """
        Get exclusive quality Fumo memes.

        Usage
        -----
            =fumomeme
        """
        async def next(interaction : discord.Interaction):
            await interaction.response.defer()
            await interaction.edit_original_message(embed = await self.memefumo_get(ctx))
        
        async def cancel(interaction : discord.Interaction):
            await view.on_timeout()
        btn1 = Button(label='Next Meme',style=discord.ButtonStyle.success)
        btn2 = Button(label='End Interaction',style=discord.ButtonStyle.danger)
        view = FunView()
        btn1.callback = next
        btn2.callback = cancel
        view.add_item(btn1)
        view.add_item(btn2)
        view.message = await ctx.send(embed=(await self.memefumo_get(ctx)), view=view)

    
    async def memefumo_get(self, ctx):
        subred = await reddit.subreddit("Fumofumo")
        legend = await subred.random()
        extension = legend.url[len(legend.url) - 3 :].lower()
        while True:
            if extension in ['jpg', 'png']: break
            subred = await reddit.subreddit("Fumofumo")
            legend = await subred.random()
            extension = legend.url[len(legend.url) - 3 :].lower()
        em = discord.Embed(color=ctx.author.color)
        em.set_author(name=legend.title, icon_url=ctx.author.display_avatar.url)
        # em.set_footer(text=f'Requested by {ctx.author.name}', icon_url=ctx.author.display_avatar.url)
        em.set_image(url=legend.url) 
        return em

    @commands.cooldown(1,5, commands.BucketType.user)   
    @commands.command(name='catfact',aliases=['cfact','catfacts'])
    async def catfact_cmd(self, ctx):
        """Give some useless (or not) cat facts.

        Usage
        -----
            =catfact
        """
        async def next(interaction):
            await interaction.response.edit_message(embed = await self.fact_get(ctx))
        async def cancel(interaction):
            await interaction.response.edit_message(view = None)
        btn1 = Button(label='Next Fact',style=discord.ButtonStyle.success)
        btn2 = Button(label='End Interaction',style=discord.ButtonStyle.danger)
        view = FunView()
        btn1.callback = next
        btn2.callback = cancel
        view.add_item(btn1)
        view.add_item(btn2)
        await ctx.send(embed=(await self.fact_get(ctx)), view=view)

    async def fact_get(self, ctx):
        legend = requests.get(url='https://catfact.ninja/fact').text
        information = json.loads(legend)
        em = discord.Embed(title=information['fact'],color=ctx.author.color)
        em.set_author(name="Fact of the day", icon_url=ctx.author.display_avatar.url)
        return em

    @commands.cooldown(1,5, commands.BucketType.user)   
    @commands.command(name='catmeme',aliases=['cat','catmemes','cmeme'])
    async def catmeme_command(self, ctx):
        """Cat memes. What can I say? This is... cat memememes.

        Usage
        -----
            =catmeme
        """
        async def next(interaction : discord.Interaction):
            await interaction.response.defer()
            await interaction.edit_original_message(embed = await self.catmeme_get(ctx))
        async def cancel(interaction):
            await view.on_timeout()
        btn1 = Button(label='Next Cat',style=discord.ButtonStyle.success, emoji='🐱')
        btn2 = Button(label='End Interaction',style=discord.ButtonStyle.danger)
        view = FunView()
        btn1.callback = next
        btn2.callback = cancel
        view.add_item(btn1)
        view.add_item(btn2)
        view.message = await ctx.send(embed=(await self.catmeme_get(ctx)), view=view)
    
    async def catmeme_get(self, ctx):
        legend = requests.get(url='http://aws.random.cat/meow').text
        information = json.loads(legend)
        em = discord.Embed(color=ctx.author.color)
        em.set_author(name="Cat meme", icon_url=ctx.author.display_avatar.url)
        em.set_image(url=information['file'])
        return em

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._emoji = "⛏"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Tools cog loaded sucessfully")

    @commands.cooldown(1,3, commands.BucketType.user)   
    @commands.command(name='translate',aliases=['trans'])
    async def trans_command(self, ctx, *, query):
        """Using Google Translate's API to translate everything!

        Usage
        -----
            =translate <query> [--language]
        """
        try: language = query.split("--")[1].lower()
        except IndexError: language = 'en'
        query = query.split("--")[0]
        translator = Translator()
        # query = ' '.join(args)
        source_lang = googletrans.LANGUAGES[(translator.detect(query).lang)]
        if language in googletrans.LANGUAGES:
            language = googletrans.LANGUAGES[language]
        final_result = translator.translate(query, dest=language).text
        embed = discord.Embed(color=ctx.author.color)
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=f'Translation')
        embed.add_field(name='Source text', value=f'```{query}```', inline=False)
        embed.add_field(name='Translated text', value=f'```{final_result}```',inline=False)
        embed.set_footer(text=f'From {source_lang.capitalize()} to {language.capitalize()}')
        await ctx.send(embed = embed)
        

    @commands.cooldown(1,3, commands.BucketType.user)   
    @commands.command(name='9ball',aliases=['8b','8ball'])
    async def nineball_command(self, ctx, *, query):
        """Ask ⑨ball and she will respond!

        Usage
        -----
            =9ball <question>
        """
        responses = ["As I see it, yes.", "Ask again later.", "Better not tell you now.", "Cannot predict now.","Concentrate and ask again.", "Don’t count on it.", "It is certain.", "It is decidedly so.", "Most likely.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Outlook good.", "Reply hazy, try again.", "Signs point to yes.", "Very doubtful.", "Without a doubt.", "Yes.", "Yes – definitely.", "You may rely on it."]
        embed = discord.Embed(title=f'Question: {query}', description=f'My answer is: **{random.choice(responses)}**')
        embed.set_author(name=f"Magic ball ⑨", icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

class Roleplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._emoji = '🤗'
    
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="airkiss", aliases=["angrystare","bite","bleh","blush","brofist","celebrate","cheers","clap","confused","cool","cry","cuddle","dance","drool","evillaugh","facepalm","handhold","happy","headbang","hug","kiss","laugh","lick","love","mad","nervous","no","nom","nosebleed","nuzzle","pat","peek","pinch","poke","pout","punch","roll","run","sad","scared","shrug","shy","sigh","sip","slap","sleep","slowclap","smack","smile","smug","sneeze","sorry","stare","surprised","sweat","thumbsup","tickle","tired","wave","wink","woah","yawn","yay","yes"])
    async def actions(self, ctx, member : t.Optional[discord.Member]):
        """To help you interact with someone by cute GIFs!
        """
        situations = {
            "airkiss": "name gave an airkiss to someone! So cute!",
            "angrystare": "name gave someone an angry stare 😓",
            "bite": "name had bitten someone!",
            "bleh": "name bleeeeee'd someone!",
            "blush": "name is blushing! So cute!",
            "cool": "name is acting cool rn 😎",
            "cry": "Oh no, name is crying! 😓",
            "cuddle": "name is cuddling someone!",
            "drool": "Look at name mouth! So gross 😝",
            "evillaugh": "What name gonna do 😨",
            "facepalm": "name can't believe this 🤦‍♂️",
            "handhold": "name is holding someone's hand!",
            "happy": "name is happy!!1 😁",
            "headband": "name headbangin because of Cirno's cuteness",
            "kiss": "name is kissing someone! Cute!",
            "laugh": "name think it's hilarious!",
            "lick": "name is licking someone!",
            "brofist": "name gave someone a bro fist! 🤜🤛",
            "celebrate": "name is celebrating someone! 🎉🎉",
            "clap": "👏👏 Good job, name!",
            "confused": "name is confusing, can someone help him?",
            "cheers": "Cheers!",
            "love": "name is all love! <33",
            "mad": "Oh no! name is full mad 💢",
            "nervous": "Hmm, why does name feeling nervous?",
            "no": "name said no.",
            "nom": "name is so hungry! 😋",
            "dance": "name is dancing!",
            "nosebleed": "name finds it super cute~!",
            "pat": "name is patting someone!",
            "peek": "name is peeking someone.",
            "nuzzle": "name is nuzzling someone!",
            "pinch": "name is pinching someone!",
            "poke": "name is poking someone!",
            "pout": "angy",
            "punch": "Oh no, name is giving someone a punch! 👊",
            "roll": "ROFL...~",
            "run": "Run run name!",
            "sad": "name is sad rn 😥 Don't worry ⑨ will make you happy!",
            "scared": "name is scared... 😨",
            "hug": "name is hugging someone <3",
            "shrug": "¯\_(ツ)_/¯",
            "shy": "name's face is all red >///<",
            "sigh": "u  g  h ",
            "sip": "name sippin some tee",
            "slap": "OUCH, name is slapping someone! 🤚😟",
            "sleep": "name is sleeping 💤",
            "slowclap": "👏 Good job!",
            "smack": "Bakaaa ⑨!",
            "smile": "name is smiling! So cute",
            "smug": "name smuggin",
            "sneeze": "Atchooo!!",
            "sorry": "name feels guilty for what they did to someone!",
            "stare": '"Why name starin at me?"\n-someone-',
            "stop": "STOP!",
            "surprised": "name is surprised.",
            "sweat": "name is sweating all their body.",
            "thumbsup": "👍",
            "tickle": "name's tickling someone!",
            "tired": "name is so tired rn",
            "wave": "Say hi to someone, name!",
            "wink": "name is giving a wink to someone.",
            "woah": "Sugoiii~!",
            "yawn": "name should take a nap rn",
            "yay" : '"Yay!!" said name',
            "yes" : "name said yes to someone."
        }
        async with ctx.typing():
            query = situations[ctx.invoked_with]
            if member is not None: query = query.replace("someone", f"**{member.display_name}**")
            query = query.replace("name", f"**{ctx.author.display_name}**")
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f"https://api.otakugifs.xyz/gif?reaction={ctx.invoked_with}") as r:
                    result = await r.json()
                    embed = discord.Embed(description=query, color=ctx.author.color)
                    embed.set_author(name=str(ctx.invoked_with).capitalize(), icon_url=ctx.author.display_avatar.url)
                    embed.set_image(url=result['url'])
                    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
    await bot.add_cog(Tools(bot))
    await bot.add_cog(Roleplay(bot))
    # await bot.add_cog(Emotes(bot))