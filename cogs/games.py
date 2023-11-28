import asyncio
import random
import discord
import akinator
from discord.ext import commands
import certifi
from html import unescape
from motor.motor_asyncio import AsyncIOMotorClient
from discord.ui import Button, View
from typing import Optional
import urllib.request, json 

database = AsyncIOMotorClient("MONGODB", tlsCAFile=certifi.where())
collectionUser = database.cirnochan.user


class GamesView(View):
    def __init__(self, timeout):
        super().__init__(timeout=timeout)


    def disable_button(self):
        for x in self.children:
            x.disabled = True
    
    async def on_timeout(self):
        self.disable_button()
        await self.message.edit(content="This message is now frozen", view=self)
    
class Games(commands.Cog):
    def __init__(self, client):
        self.client = client
        self._emoji = "🎮"
 
    @commands.Cog.listener()
    async def on_ready(self):
        print("Games cog loaded successfully.")
    
    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return False
        return True
    
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name='trivia', aliases=['quiz'])
    async def quiz_command(self, ctx):
        """Do some quiz to widen your brain!

        Usage
        -----
            =trivia
        """
        url = "https://opentdb.com/api.php?amount=1"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        question = unescape(data['results'][0]['question'])
        view = GamesView(timeout=15)
        answers : list = data['results'][0]['incorrect_answers']
        answers.append(data['results'][0]['correct_answer'])
        embed = discord.Embed(description=f"You have 15 seconds to give an answer.\nQuestion: **{question}**", color=ctx.author.color)
        embed.add_field(name="Difficulty", value=f"`{data['results'][0]['difficulty'].capitalize()}`")
        embed.add_field(name="Category", value=f"`{data['results'][0]['category']}`", inline=True)
        embed.set_author(name="Trivia", icon_url=ctx.author.display_avatar.url)
        view.on_timeout = None
        async def timeout():
            view.disable_button()
            await view.message.edit(random.choice(['OK you didnt answer.', 'Why didnt you answer?', 'Gave up already? You can do it better bud!!~']), view=view)
        view.on_timeout = timeout
        async def ButtonCallback(interaction : discord.Interaction):
            if interaction.user != ctx.author: return await interaction.response.send_message(content=random.choice(["You arent playing lol", "who are you?", "Im playing with someone but you"]), ephemeral=True)
            if interaction.data['custom_id'] == data['results'][0]['correct_answer']:
                for i in view.children:
                    if i.label == data['results'][0]['correct_answer']: i.style = discord.ButtonStyle.success
                view.disable_button()
                view.stop
                await interaction.response.edit_message(content=random.choice(["Congratulations you gave the right answer", "amazing you answered correctly", "Yep thats the right answer congratulatIONs!"]), view=view)
            else:
                for i in view.children:
                    if i.label == data['results'][0]['correct_answer']: i.style = discord.ButtonStyle.success
                    elif i.label == interaction.data['custom_id']: i.style = discord.ButtonStyle.danger
                view.disable_button()
                view.stop
                await interaction.response.edit_message(content=random.choice(["Sorry thats the wrong answer", "come on u can do it", "Wrong."]), view=view)
        for i in answers:
            button = Button(label=i, custom_id=i, style=discord.ButtonStyle.blurple)
            view.add_item(button)
            button.callback = ButtonCallback
        random.shuffle(view.children)
        view.message = await ctx.send(embed=embed, view=view)
    
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name="fight", aliases=["1v1"])
    async def fight_command(self, ctx, member : discord.Member):
        '''
        Fight someone and say "ur the best heh"

        Usage
        -----
            =fight <@someone>
        '''
        if member.bot:
            await ctx.send("You can't fight a bot lmao")
        elif member == ctx.author:
            await ctx.send("Are you dumb or sth? You can't fight yourself!")
        else:
            # self.turns = 1
            player1 = {"player" : ctx.author, 
                        "hp" : 100, 
                        "armor" : (await collectionUser.find_one({"id" : ctx.author.id}))["inventory"]["armor"]["protect"], 
                        "weapon" : (await collectionUser.find_one({"id" : ctx.author.id}))["inventory"]["weapon"]["damage"]
                        }
            player2 = {"player" : member, 
                        "hp" : 100, 
                        "armor" : (await collectionUser.find_one({"id" : member.id}))["inventory"]["armor"]["protect"], 
                        "weapon" : (await collectionUser.find_one({"id" : member.id}))["inventory"]["weapon"]["damage"]
                        }
            self.playerOnTurn = 1
            self.anotherPlayer = 0
            self.is_playing = True
            # playersOnTurn = 0 => turn = Tiy
            # playersOnTurn = 1 => turn = Lan Anh
            players = [player1, player2] # cho tiện hơn thôi xD
            embed = discord.Embed(color=ctx.author.color)
            embed.add_field(name=player1['player'].name, value=f":heart: {player1['hp']}%\n:shield: {player1['armor']}%")
            embed.add_field(name=player2['player'].name, value=f":heart: {player2['hp']}%\n:shield: {player2['armor']}%")
            embed.add_field(name="Last action", value="`No actions were made, yet.`", inline=False)
            embed.set_thumbnail(url="https://i.imgur.com/ybuUIQK.png")
            view = GamesView(timeout=60)   
            btn1 = Button(label="Punch", emoji="<:punch:938641580523413504>", custom_id="Punch")
            btn2 = Button(label="Kick", emoji="<:kick:938641607555711006>", custom_id="Kick")
            btn3 = Button(label="Equippings", emoji="<:shoot:939530880744042547>", custom_id="Equippings")
            btn4 = Button(label="Surrender", emoji="<:surrender:938642015850225715>", custom_id="Surrender")
            for buttons in [btn1, btn2, btn3, btn4]:
                view.add_item(buttons)
            view.on_timeout = None
            async def Surrender():
                view.stop()
                view.disable_button()
                self.anotherPlayer = 1 if self.playerOnTurn == 0 else 0
                embed.set_field_at(index=2, name="Last action", value=f"`{players[self.anotherPlayer]['player'].name} {random.choice(['ran away', 'ended the fight', 'surrendered', 'dead'])}, so raffish!`", inline=False)
                await view.message.edit(content=f"{players[self.playerOnTurn]['player'].mention} won!", embed=embed, view=view)
            view.on_timeout = Surrender

            async def buttonCallback(interaction : discord.Interaction):
                if interaction.data['custom_id'] == "Equippings":
                    if str(interaction.user) not in [str(player1['player']), str(player2['player'])]:
                        return await interaction.response.send_message(content="Who are you lol", ephemeral=True)
                    else:
                        for i in players:
                            if i['player'] == interaction.user:
                                armor = (await collectionUser.find_one({"id" : interaction.user.id}))["inventory"]["armor"]
                                weapon = (await collectionUser.find_one({"id" : interaction.user.id}))["inventory"]["weapon"]
                        embedEquippings = discord.Embed(color=interaction.user.color)
                        embedEquippings.set_author(name=f"{interaction.user.name}'s equippings", icon_url=interaction.user.display_avatar.url)
                        embedEquippings.add_field(name="⚔ Weapon", value=f"> Name: *{weapon['name']}*\n> Damage: __{weapon['damage']}%__\n> Durability: __{weapon['durability']}__", inline=True)
                        embedEquippings.add_field(name="🛡 Armor", value=f"> Name: *{armor['name']}*\n> Protection: __{armor['protect']}%__\n> Durability: __{armor['durability']}__", inline=True)
                        embedEquippings.set_footer(text=f"Currently in a fight with {player1['player'].name if str(interaction.user) == str(player2['player']) else player2['player'].name}", icon_url=self.client.user.display_avatar.url)
                        await interaction.response.send_message(embed=embedEquippings, ephemeral=True)
                elif interaction.data['custom_id'] == "Surrender":
                    if str(interaction.user) not in [str(player1['player']), str(player2['player'])]:
                        return await interaction.response.send_message(content="Who are you lol", ephemeral=True)
                    self.playerOnTurn = 0 if str(interaction.user) == str(player2['player']) else 1
                    await Surrender()
                    return
                else:
                    if interaction.user != players[self.playerOnTurn]['player']:
                        return await interaction.response.send_message(content="It's not your turn.", ephemeral=True)
                    await interaction.response.defer()
                    if interaction.data['custom_id'] == "Punch":
                        damage = int(random.randint(5, 20) / 100 * (100 + players[self.playerOnTurn]['weapon']))
                        responses = f"{players[self.playerOnTurn]['player'].name} made a {random.choice(['hard punch', 'real punch', 'hurtful punch', 'BEEEG punch'])} to {players[self.anotherPlayer]['player'].name} dealing {damage} damage!"
                        players[self.anotherPlayer]['hp'], players[self.anotherPlayer]['armor'] = self.damage_count(players[self.anotherPlayer]['hp'], players[self.anotherPlayer]['armor'], damage)

                    if interaction.data['custom_id'] == "Kick":
                        if (fell := bool(random.getrandbits(1))) is True:
                            damage = int(random.randint(5, 20))
                            responses = f"{players[self.playerOnTurn]['player'].name} tried to make a {random.choice(['hard kick', 'kick', 'painful kick'])} to {players[self.anotherPlayer]['player'].name} but FELL DOWN! {players[self.playerOnTurn]['player'].name} lost {damage} damage!"
                            players[self.playerOnTurn]['hp'], players[self.playerOnTurn]['armor'] = self.damage_count(players[self.playerOnTurn]['hp'], players[self.playerOnTurn]['armor'], damage)
                            for i in players:
                                if i['hp'] <= 0: 
                                    i['hp'] = 0
                                    index = players.index(i)
                                    embed.set_field_at(index=index, name=i['player'].name, value=f":heart: {i['hp']}%\n:shield: {i['armor']}%")
                                    view.disable_button()
                                    await interaction.edit_original_message(content=f"You win, {i[1 if index == 0 else 0]['player'].mention}", embed=embed, view=view)
                                    view.stop()
                                    return
                            embed.set_field_at(index=self.playerOnTurn, name=players[self.playerOnTurn]['player'].name, value=f":heart: {players[self.playerOnTurn]['hp']}%\n:shield: {players[self.playerOnTurn]['armor']}%")
                            embed.set_field_at(index=2, name="Last action", value=f"`{responses}`", inline=False)
                            await interaction.edit_original_message(content=f"Your turn, {players[self.anotherPlayer]['player'].mention}", embed=embed)
                            self.playerOnTurn = 0 if self.playerOnTurn == 1 else 1
                            self.anotherPlayer = 0 if self.playerOnTurn == 1 else 1
                            return

                        else:
                            damage = int(random.randint(10, 25) / 100 * (100 + players[self.playerOnTurn]['weapon']))
                            players[self.anotherPlayer]['hp'], players[self.anotherPlayer]['armor'] = self.damage_count(players[self.anotherPlayer]['hp'], players[self.anotherPlayer]['armor'], damage)
                            responses = f"{players[self.playerOnTurn]['player'].name} made a {random.choice(['hard kick', 'kick', 'painful pick'])} to {players[self.anotherPlayer]['player'].name}. {players[self.anotherPlayer]['player'].name} lost {damage} damage!"
                    for i in players:
                        if i['hp'] <= 0: 
                            i['hp'] = 0
                            index = players.index(i)
                            embed.set_field_at(index=index, name=i['player'].name, value=f":heart: {i['hp']}%\n:shield: {i['armor']}%")
                            view.disable_button()
                            await interaction.edit_original_message(content=f"You win, {players[1 if index == 0 else 0]['player'].mention}", embed=embed, view=view)
                            view.stop()
                            return
                    embed.set_field_at(index=self.anotherPlayer, name=players[self.anotherPlayer]['player'].name, value=f":heart: {players[self.anotherPlayer]['hp']}%\n:shield: {players[self.anotherPlayer]['armor']}%")
                    embed.set_field_at(index=2, name="Last action", value=f"`{responses}`", inline=False)
                    await interaction.edit_original_message(content=f"Your turn, {players[self.anotherPlayer]['player'].mention}", embed=embed)
                    self.playerOnTurn = 0 if self.playerOnTurn == 1 else 1
                    self.anotherPlayer = 0 if self.playerOnTurn == 1 else 1
            for i in [btn1, btn2, btn3, btn4]:
                i.callback = buttonCallback
            view.message = await ctx.send(content=f"Your turn, {players[self.playerOnTurn]['player'].mention}",embed=embed, view=view)

    def damage_count(self, hp, armor, damage):
        if armor <= 0: hp -= damage
        else:
            oldHp = hp
            oldArmor = armor
            armor -= int(damage)
            hp -= damage / 3
            if armor < 0:
                armor = 0
                hp = oldHp - (damage - oldArmor)
        return int(hp), int(armor)
    
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name='akinator', aliases=['aki'])
    async def akinator_command(self, ctx, type : Optional[str] = 'en'):
        """Akinator, but got the power of Cirno.

        Usage
        -----
            =akinator [type]
        """
        if type.lower() in ['animals', 'objects']: type=f'en_{type.lower()}'
        view = GamesView(timeout=60)
        view.message = await ctx.send(embed=discord.Embed(description="Loading the game...", color=ctx.author.color))
        yes = Button(label='Yes', custom_id='y')
        no = Button(label='No', custom_id='n')
        idk = Button(label="I don't know", custom_id='idk')
        prob = Button(label='Probably', custom_id='probably')
        probnot = Button(label='Probably not', custom_id='probably not')
        back = Button(label='Back', custom_id='back', style=discord.ButtonStyle.blurple)
        cancel = Button(label='Stop interaction', custom_id='stop', style=discord.ButtonStyle.danger)
        aki = akinator.Akinator()
        aki.start_game(language=type)
        embed = discord.Embed(description=f"{aki.question}", color=ctx.author.color)
        embed.set_author(name=f"Question #{int(aki.step+1)}", icon_url=self.client.user.display_avatar.url)
        embed.set_thumbnail(url="https://i.imgur.com/jAh95rS.png")
        async def button_callback(interaction : discord.Interaction):
            try:
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(content="This is not your game luul", ephemeral=True)
                await interaction.response.defer()
                if (answer := interaction.data['custom_id']) in ['y', 'n', 'idk', 'probably', 'probably not']:
                    if aki.progression > 80:
                        aki.win()
                        embedWin = discord.Embed(title=f"It's {aki.first_guess['name']}!", description=aki.first_guess['description'], color=ctx.author.color)
                        embedWin.set_image(url=aki.first_guess['absolute_picture_path'])
                        embedWin.set_thumbnail(url="https://i.imgur.com/jAh95rS.png")
                        embedWin.set_footer(text="Don't get surprised! That's the power of ⑨", icon_url=ctx.author.display_avatar.url)
                        # for i in view.children: i.disabled = True
                        view.stop()
                        return await interaction.edit_original_message(embed=embedWin, view=None)
                    else: aki.answer(answer)
                elif answer == 'back':
                    try: aki.back()
                    except akinator.CantGoBackAnyFurther:
                        return await interaction.response.send_message(content="You can't go back!", ephemeral=True)
                elif answer == 'stop':
                    await view.on_timeout()
                    view.stop()
                embed.description = aki.question
                embed.set_author(name=f"Question #{int(aki.step+1)}", icon_url=self.client.user.display_avatar.url)
                embed.remove_footer()
                embed.set_footer(text="Trying to get your character!" if aki.progression < 30 else "Getting closer!" if aki.progression < 50 else "Almost get it!", icon_url=ctx.author.display_avatar.url)
                # await asyncio.sleep(6)
                await interaction.edit_original_message(embed=embed)
            except akinator.AkiTimedOut:
                await view.on_error()
                return await interaction.edit_original_message(content="Timed out.", embed=embed, view=view)
        for i in [yes, no, idk, prob, probnot, back, cancel]:
            view.add_item(i)
            i.callback = button_callback
        await view.message.edit(embed=embed, view=view)
        await asyncio.wait_for(await view.wait())

    @akinator_command.error
    async def akinator_error(self, ctx, err):
        if isinstance(err, commands.MaxConcurrencyReached):
            await ctx.send(embed=discord.Embed(description=f"❎ | You're already playing.", color=ctx.author.color))

    @commands.command(name='guessnum',aliases=['numguess', 'gtn'])
    async def guessnum_cmd(self, ctx, query : int = None):
        """Guess the number game...?

        Usage
        -----
            =guessnum [from 1 to ?]
        """
        if query is None: query = 100
        timer = 30
        number = random.randint(1, query)
        attempt = 1
        em = discord.Embed(title=f'Guess a number between 1 to {query}', description='You can type `end` to stop the game\nYou have **30 seconds** to guess', color=ctx.author.color)
        em.set_footer(icon_url=ctx.author.display_avatar.url,text=f"Requested by {ctx.author.name}")
        mess = await ctx.send(embed = em)
        def check(m):
            return m.author == ctx.author
        while True:
            try:
                msg = await self.client.wait_for('message', timeout=30, check=check)
                em = discord.Embed(color=ctx.author.color)
                if msg.content in ['end', '=end', 'endgame']:
                    em = discord.Embed(title=f"Game ended", description=f"You ended the game with {attempt} attempt(s)", color=ctx.author.color)
                    em.set_footer(icon_url=ctx.author.display_avatar.url,text=f"Requested by {ctx.author.name} | Guess a number between 1 to {query}")
                    await ctx.send(embed = em)
                    break
                val = msg.content
                if val in [str(number), f'={number}']: 
                    em = discord.Embed(title=f"That is a true answer!", description=f"You've tried {attempt} attempt(s) before giving a true answer.", color=ctx.author.color)
                    em.set_footer(icon_url=ctx.author.display_avatar.url,text=f"Requested by {ctx.author.name} | Guess a number between 1 to {query}")
                    await ctx.send(embed = em)
                    break
                else:
                    await msg.add_reaction('❎')
                    # await msg.add_reaction('')
                attempt += 1
            except asyncio.TimeoutError:
                em = discord.Embed(title=f'Guess a number between 1 to {query}', description=f"You can't get the answer after 30 seconds with **{attempt}** attempt(s)\nThe correct answer is: **{number}**!", color=ctx.author.color)
                await ctx.send(embed = em)
                return
    
    # @commands.command(name='tictactoe', aliases=['ttt'])
    # async def tictactoe_command(self, ctx, member : discord.Member):
    #     players = [ctx.author, member]
    #     turns = 0
        

async def setup(client):
    await client.add_cog(Games(client))