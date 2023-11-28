import asyncio
from dis import disco
from enum import Enum
import math
from motor.motor_asyncio import AsyncIOMotorClient
import random
import discord
import re
import time
from discord.ui import View, Button
import datetime
from wavelink.ext import spotify
from typing import Optional
from pymongo import MongoClient
from discord.ext import commands
import lyricsgenius
import wavelink
import certifi

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {
    "1️⃣" : 0,
    "2️⃣" : 1,
    "3️⃣" : 2,
    "4️⃣" : 3,
    "5️⃣" : 4
}
TIME_REGEX = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"
GENIUS = lyricsgenius.Genius(access_token="3k0pOlvaIrS1YB7tLMLrM-Ip6t94zNVuzyJGx9Pa56aORyh6kQfedebeOJ9ouyo9")

playlistDB = AsyncIOMotorClient("MONGDB", tlsCAFile=certifi.where()).cirnochan.guild
premiumDB = MongoClient("MONGDB", tlsCAFile=certifi.where()).cirnochan.premium

def time_converter(seconds):
    if seconds > 3600:
        return datetime.timedelta(seconds=seconds)
    return time.strftime("%M:%S", time.gmtime(seconds))
class Loop(Enum):
    OFF = 0
    ONE = 1
    ALL = 2

    def next(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        if index >= len(members):
            index = 0
        return members[index]

class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass

class NoTracksFound(commands.CommandError):
    pass

class PlaylistAlreadyCreated(commands.CommandError):
    pass

class TrackButton(discord.ui.Button):
    def __init__(self, emoji, value, ctx : commands.Context):
        super().__init__(emoji=emoji)
        self.value = value
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if self.ctx.author == interaction.user:
            view : TrackView = self.view
            view.value = self.value
            view.stop()
    
class TrackView(discord.ui.View):
    def __init__(self, ctx, timeout: Optional[float] = 30.0):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None
        for emoji in list(OPTIONS.keys()):
            self.add_item(TrackButton(emoji=emoji, value=OPTIONS[emoji], ctx=ctx))

class MusicView(View):
    def __init__(self, timeout):
        super().__init__(timeout=timeout)


    async def disable_button(self):
        for x in self.children:
            x.disabled = True
    
    async def on_timeout(self):
        await self.disable_button()
        await self.message.edit(content="This message is now frozen", view=self)


class Queue:
    def __init__(self):
        self._queue = []
        self.old_queue = []
        self.position = 0
        self.loop = Loop.OFF
        self.shuffleMode = False
    
    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty
        return self._queue[self.position+1:]

    def add(self, *args):
        self._queue.extend(args)
        self.old_queue.extend(args)

    def get_first_track(self):
        if not self._queue:
            raise QueueIsEmpty  
        
        return self._queue[0]

    def is_empty(self) -> bool:
        return not bool(self.count())
        

    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty
        try: position = self._queue[self.position]
        except IndexError:
            return None
        return self._queue[self.position]

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty
        
        self.position += 1
        if self.position > len(self._queue) - 1:
            if self.loop == Loop.ALL:
                self.position = 0
            else: return None
        return self._queue[self.position]

    def set_repeat_mode(self, mode):
        if mode is None:
            self.loop = self.loop.next()
        else:
            if mode.lower() in ['none', 'no', 'remove', '0', 'off']:
                self.loop = Loop.OFF
            elif mode.lower() in ['1', 'one', 'only']:
                self.loop = Loop.ONE
            elif mode.lower() in ['2', 'all', 'queue']:
                self.loop = Loop.ALL
        return self.loop.name
        
    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty
        if len(self._queue) < 2:
            return
        if not self.shuffleMode:
            upcoming = self.upcoming
            random.shuffle(upcoming)
            self._queue = self._queue[:self.position+1]
            self._queue.extend(upcoming)
            self.shuffleMode = True
        else:
            self._queue = self._queue[:self.position+1]
            self._queue += self.old_queue[self.position+1:]
            self.shuffleMode = False

    def count(self):
        return len(self._queue)


class Player(wavelink.Player):
    def __init__(self, ctx, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx : commands.Context = ctx
        self.queue = Queue()
        self.channelID = 0
    
    async def teardown(self):
        try:
            await self.stop()
            self.queue._queue.clear()
            await self.disconnect(force=True)
            del self
        except KeyError:
            pass
    
    async def add_tracks(self, ctx, query, message, gettoplay=True, shuffle=False):
        if not query:
            raise NoTracksFound
        playlist = False
        spotify_check = spotify.decode_url(query)
        if spotify_check: return await self.add_spotify_track(ctx, query, message, gettoplay, shuffle=shuffle)
        try: 
            tracks = await wavelink.NodePool.get_node().get_tracks(cls=wavelink.Track, query=query)
        except wavelink.LoadTrackError: 
            raise NoTracksFound
        except (wavelink.LavalinkException):
            playlist = True
            await self.add_playlist(ctx, await wavelink.NodePool.get_node().get_playlist(cls=wavelink.YouTubePlaylist, identifier=query), message, shuffle=shuffle)
        if playlist is False:
            if len(tracks) == 1:
                tracks = tracks[0]
            else:
                message, tracks = await self.choose_track(ctx, tracks, message)
            self.queue.add(tracks)
            if gettoplay is True:
                embed=discord.Embed(title=f"Added a track to queue.", color=ctx.author.color, timestamp=datetime.datetime.now())
                try:
                    embed.add_field(name="Duration", value=f"{time_converter(int(tracks.length))}", inline=True)
                except OverflowError:
                    embed.add_field(name="Duration", value=f"Indeterminable", inline=True)
                embed.add_field(name="Author", value=f"{tracks.author}", inline=True)
                embed.add_field(name="Position", value=self.queue._queue.index(tracks)+1, inline=True)
                embed.add_field(name=f"Track", value=f"[{tracks.title}]({tracks.uri})", inline=False)
                embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url=f"https://img.youtube.com/vi/{tracks.identifier}/hqdefault.jpg")
                await message.edit(embed=embed, view=None)
            if not self.is_playing() and gettoplay is True: return await self.start_playback()
            return tracks
            
    
    async def add_spotify_track(self, ctx, query, message, gettoplay=True, shuffle=False):
        playlist = False
        spotify_track = spotify.decode_url(query)
        if not spotify_track['type'].value == 0:
            playlist = True
            return await self.add_spotify_playlist(ctx, query, message, gettoplay, shuffle=shuffle)
        else:
            tracks = await spotify.SpotifyTrack.search(query=spotify_track['id'], type=spotify_track['type'], return_first=True)
        if playlist is False:
            if gettoplay is True: self.queue.add(tracks)
            embed=discord.Embed(title=f"Added a track to queue.", color=ctx.author.color, timestamp=datetime.datetime.now())
            embed.add_field(name="Duration", value=f"{time_converter(int(tracks.length))}", inline=True)
            embed.add_field(name="Author", value=f"{tracks.author}", inline=True)
            embed.add_field(name="Position", value=self.queue._queue.index(tracks)+1, inline=True)
            embed.add_field(name=f"Track", value=f"[{tracks.title}]({tracks.uri})", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{tracks.identifier}/hqdefault.jpg")
            await message.edit(embed=embed, view=None)
            if self.is_playing() is False and gettoplay is True: return await self.start_playback()
            return tracks
    
    async def add_spotify_playlist(self, ctx, query, message, addqueue=True, shuffle=False):
        countTracks = 0
        count = self.queue.count()
        desc = ""
        tracks = []
        async for i in spotify.SpotifyTrack.iterator(query=query, partial_tracks=True, type=spotify.decode_url(query)['type']):
            tracks.append(i)
        if shuffle is True:
            random.shuffle(tracks)
        for i in tracks:
            if countTracks < 8:
                desc += f"`#{count + 1}`. **{i.title}**\n"
                count += 1
            countTracks += 1
        if countTracks > 8:
            desc += f"...**and {countTracks - 8} more tracks**"
        self.queue.old_queue += tracks
        self.queue._queue += tracks
        embed=discord.Embed(
            title=f"Added a playlist of {countTracks} tracks to queue.",
            description=desc.strip('\n'),
            color=ctx.author.color,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="*Position in queue*", value=f"{self.queue.count() + 1 - countTracks} - {self.queue.count()}", inline=True)
        embed.add_field(name=f"*Added by*", value=f"<@{ctx.author.id}>", inline=True)
        embed.set_footer(icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url="https://i.imgur.com/8iID9Ps.png")
        await message.edit(embed=embed)
        if not self.is_playing():
            await self.start_playback()

    async def add_playlist(self, ctx, playlist : wavelink.YouTubePlaylist, message, shuffle=False):
        desc = ''
        count = self.queue.count()
        countTracks = 0
        track = []
        if shuffle is True: 
            random.shuffle(playlist.tracks)
        for i in playlist.tracks:
            track.append(i)
            if countTracks < 8:
                desc += f"`#{count + 1}`. **{i.title[:60]}**\n"
                count += 1
            countTracks += 1
        if len(playlist.tracks) > 8:
            desc += f"...**and {len(playlist.tracks) - 8} more tracks**"
        embed=discord.Embed(
            title=f"Added a playlist of {len(playlist.tracks)} tracks to queue.",
            description=desc.strip('\n'),
            color=ctx.author.color,
            timestamp=datetime.datetime.now()
        )
        self.queue.old_queue += track
        self.queue._queue += track
        embed.add_field(name="*Position in queue*", value=f"{self.queue.count() - len(playlist.tracks) + 1} - {self.queue.count()}", inline=True)
        embed.add_field(name=f"*Added by*", value=f"<@{ctx.author.id}>", inline=True)
        embed.set_footer(icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url="https://i.imgur.com/8iID9Ps.png")
        await message.edit(embed=embed)
        if not self.is_playing():
            await self.start_playback()
    
    async def multiplay_function(self, ctx, tracks, message):
        for i in range(0, len(tracks)-1):
            PartialTrack = wavelink.PartialTrack(query=tracks[i])
            PartialTrack.title = tracks[i]['name']
            self.queue.add(PartialTrack)
        description = ''
        count = 0
        for i in range(0, len(tracks)):
            if count < 8:
                description += f"`#{count+1}`. **{tracks[i]['name']}**\n"
            count += 1
        if len(tracks) > 8: description += f"*... and {len(tracks) - 8} more tracks*"
        embed = discord.Embed(title=f"Added a playlist of {len(tracks)} tracks", description=description, color=ctx.author.color)
        embed.set_thumbnail(url="https://i.imgur.com/8iID9Ps.png")
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await message.edit(embed=embed)
        if not self.is_playing():
            await self.start_playback()
    
    async def choose_track(self, ctx, tracks, message):
        if len(tracks) == 0: raise NoTracksFound
        embed = discord.Embed(title="Pick a track!", description="\n".join(f"`#{i+1}`. **{t.title}** ({time_converter(int(t.length))})" for i, t in enumerate(tracks[:5])), color=ctx.author.color) #!!!
        embed.set_thumbnail(url="https://i.imgur.com/8iID9Ps.png")
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        view = TrackView(ctx)
        await message.edit(embed=embed, view=view)
        try:
            task = await asyncio.wait_for(view.wait(), timeout=30)
            indicator = view.value
            view.children[indicator].emoji = "✔️"
            view.children[indicator].style = discord.ButtonStyle.success
            await message.edit(embed=embed, view=view)
            return message, tracks[indicator]
        except asyncio.TimeoutError:
            for i in view.children: i.disabled = True
            await message.edit(content="This message is now frozen.", view=view)

    async def start_playback(self):
        await self.play(self.queue.current_track())
        if self.ctx.me.voice.mute:
            await self.pause()
            await self.ctx.send(embed=discord.Embed(description="⚠ Failed to play! I'm currently being muted by the server admin. Please unmute me.", color=discord.Color.red()))

    
    async def playback_control(self):
        try:
            if self.queue.loop == Loop.ONE: track = self.queue.current_track()
            else: track = self.queue.get_next_track()
            if track is not None:
                trackPlay = await self.play(track)
                await self.ctx.send(embed=discord.Embed(description=f"Playing **[{trackPlay.title}]({trackPlay.uri})**", color=self.ctx.author.color))
                if self.ctx.me.voice.mute:
                    await self.pause()
                    return await self.ctx.send(embed=discord.Embed(description="⚠ Failed to play! I'm currently being muted by the server admin. Please unmute me.", color=discord.Color.red()))
            else:   
                await self.ctx.send(embed=discord.Embed(description="There is no upcoming track, please add one.", color=self.ctx.author.color))
                await self.voicestate_update()
        except QueueIsEmpty:
            pass
    
    async def voicestate_update(self):
        time = 60
        left = False
        while time > 0:
            if not self.is_playing() and not self.is_paused(): time -= 1
            else: left = True
            if self.is_connected() is False: left = True
            if left is True: return
            await asyncio.sleep(0.99)
        try: await self.teardown()
        except: pass
        await self.bot.get_channel(self.channelID).send(embed=discord.Embed(description=f"No activity in the voice channel for a minute, leaving...", color=discord.Color.red()))

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._emoji = '🎶'
        bot.loop.create_task(self.connect_nodes())
    
    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        try: await wavelink.NodePool.create_node(bot=self.bot,
                                            host='lavalink-repl.tiykuma.repl.co',
                                            port=443,  
                                            password='CIRNO-1',
                                            identifier="replit-crino-powreful-lavalink-sever",
                                            spotify_client=spotify.SpotifyClient(client_id="6c7d66f868b04aa181229d478b250ba9", client_secret="722c1adb8f304f809880464ae2051f9a"),
                                            https=True)
        except wavelink.errors.NodeOccupied: return

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f' Node {node.identifier} is ready!')
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Music cog loaded successfully.")

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return False
        return True
    
    def premium_check(ctx : commands.Context):
        if (premium := premiumDB.find_one({"_id" : ctx.author.id})) is not None:
            return premium
        else: return False
    
    def get_player(self, guild):
        return wavelink.NodePool.get_node().get_player(guild)
    
    async def get_track_playlist(self, ctx, query, playlistname, message):
        if not query: raise NoTracksFound
        if (check_spotify := spotify.decode_url(query)):
            # if check_spotify['type'].value == 0:
            #     track = spotify.SpotifyTrack.search(query=check_spotify['id'], type=check_spotify['type'], return_first=True)
            # else:
            #     track = []
            #     isplaylist = True
            #     count = 0
            #     desc = ''
            #     async for i in spotify.SpotifyTrack.iterator(query=query, partial_tracks=False, type=check_spotify['type']):
            #         track.append({"name":i.title, "uri":i.uri, "duration":i.duration})
            #         if count < 8:
            #             desc += f"`#{count+1}`. **{i.title[:60]}**\n"
            #         count += 1
            return await ctx.send(embed=discord.Embed(description="Spotify isn't supported yet. Try next time!"))
        isplaylist = False
        if not re.match(URL_REGEX, query): query = f"ytsearch:{query}"
        try: track = await wavelink.NodePool.get_node().get_tracks(cls=wavelink.Track, query=query)
        except (wavelink.LavalinkException):
            isplaylist = True
            track = []
            playlist = (await wavelink.NodePool.get_node().get_playlist(wavelink.YouTubePlaylist, query))
            count = 0
            desc = ''
            for i in playlist.tracks:
                track.append({"name":i.title, "uri":i.uri, "duration":i.duration})
                if count < 8:
                    desc += f"`#{count+1}`. **{i.title[:60]}**\n"
                    count += 1
            if len(playlist.tracks) > 8:
                desc += f"...**and {len(playlist.tracks) - 8} more tracks**"
            embed=discord.Embed(description=desc.strip('\n'),color=ctx.author.color,timestamp=datetime.datetime.now())
            embed.set_author(name=f"Added a playlist of {len(playlist.tracks)} tracks to queue.", icon_url=ctx.author.display_avatar.url)
        if isplaylist is False:
            if len(track) == 1: track = track[0]
            embed = discord.Embed(color=ctx.author.color, timestamp=datetime.datetime.now())
            embed.set_author(name=f"Added a track to playlist **{playlistname}**", icon_url=ctx.author.display_avatar.url)
            embed.add_field(name="Track", value=f"[{track.title}]({track.uri})", inline=True)
            embed.add_field(name="Duration", value=f"{time_converter(track.duration)}", inline=True)
            embed.set_footer()
            track = {"name":track.title, "uri":track.uri, "duration":track.duration}
        await message.edit(embed=embed)
        return track

    async def connect_voice(self, ctx : commands.Context):
        voice = ctx.author.voice
        if not voice: raise NoVoiceChannel 
        if (channel := getattr(voice, "channel")) is None: 
            raise NoVoiceChannel
        if ctx.voice_client:
            if ctx.voice_client.channel == voice.channel:
                raise AlreadyConnectedToChannel
            else:
                # await ctx.voice_client.move_to(channel)
                await ctx.guild.change_voice_state(channel=channel, self_deaf=True)    
        else:
            # self.bot.user.voice.
            await channel.connect(cls=Player(ctx))
            await ctx.guild.change_voice_state(channel=channel, self_deaf=True)    
        return channel      

    async def connecter(self, ctx : commands.Context, send=False):
        # player = self.get_player(ctx.guild)
        try: 
            channel = await self.connect_voice(ctx)
        except AlreadyConnectedToChannel:
            if send is True:
                await ctx.send(embed=discord.Embed(description="We are in the same voice channel!", color=ctx.author.color))
            return None, self.get_player(ctx.guild)
        except NoVoiceChannel:
            await ctx.send(embed=discord.Embed(description="You are not connected to any voice channel.", color=ctx.author.color))
            return None, None
        if (player := self.get_player(ctx.guild)).channelID == 0:
            player.channelID = ctx.channel.id
        player.bot = self.bot
        return channel, self.get_player(ctx.guild)

    @commands.command(name='connect', aliases=['join', 'j'])
    async def connect_command(self, ctx : commands.Context):
        """ 
        Connects to your voice channel.
        """
        channel, _ = await self.connecter(ctx, True)
        if channel:
            await ctx.send(embed=discord.Embed(description=f"Connected to {channel}.", color = ctx.author.color))

    @commands.command(name='disconnect',aliases=['leave', 'l'])
    async def disconnect_command(self, ctx):
        """ Leaves your voice channel."""
        player = self.get_player(ctx.guild)
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
        if player is not None:
            await player.teardown()
            # player._connected = False
            return await ctx.send(embed=discord.Embed(description="Disconnected.", color=ctx.author.color))
        else:
            return await ctx.send(embed=discord.Embed(description="I am not currently in a voice channel.", color=ctx.author.color))

    @commands.command(name='play', aliases=['p'])
    async def play_command(self, ctx, *, args : Optional[str]):
        """Play a track/playlist.
        Currently supports: YouTube, YouTube Music, SoundCloud, Spotify, Bandcamp, Twitch.

        Options
        -------
        ```
        shuffle    : shuffles the playlist.
        soundcloud : searches SoundCloud tracks.
        ```
        
        Usage
        -----
            =play <track url/title> [--option(s)]
        """
        if args is None:
            return await self.resume_command(ctx)
        channel, player = await self.connecter(ctx)
        if not player: return
        args = (args.split("--"))
        args = [i.strip() for i in args]
        shuffle = False
        soundcloud = False
        for i in args: 
            if i.lower() in ['shuffle']: shuffle = True
            if i.lower() in ['soundcloud', 'sc', 'scloud', 'scsearch']: soundcloud = True
        else:
            args[0] = args[0].strip('<>')
            name = args[0]
            if not re.match(URL_REGEX, args[0]):
                if soundcloud is True: args[0] = f"scsearch:{args[0]}"
                else: args[0] = f"ytsearch:{args[0]}"
            message = await ctx.send(embed=discord.Embed(description="Searching...", color=ctx.author.color))
            try: await player.add_tracks(ctx, args[0], message, shuffle=shuffle)
            except NoTracksFound: return await message.edit(embed=discord.Embed(description=f"Error: **No track named {name} is found**", color=ctx.author.color))

    @commands.command(name='pause',aliases=['pa'])
    async def pause_command(self, ctx : commands.Context):
        """
        Pause the current track.
        """
        try:
            player = self.get_player(ctx.guild)
            if ctx.author not in player.channel.members:
                return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
            if ctx.voice_client.is_playing() and ctx.voice_client.is_connected():
                await player.pause()
                await ctx.send(embed=discord.Embed(description=f"Track **[{player.track.title}]({player.track.uri})** paused.", color=ctx.author.color))
        except:
            await ctx.send(embed=discord.Embed(description="Currently I'm not playing any track.", color=ctx.author.color))

    @commands.command(name='resume', aliases=['re'])
    async def resume_command(self, ctx : commands.Context):
        """
        Resume the current track.

        Usage
        -----
            =resume
        """
        try:
            player = self.get_player(ctx.guild)
            if ctx.author not in player.channel.members:
                return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
            if ctx.voice_client.is_playing() and ctx.voice_client.is_connected():
                if ctx.me.voice.mute: return await ctx.send(embed=discord.Embed(description="⚠ Failed to play! I'm currently being muted by the server admin. Please unmute me.", color=discord.Color.red()))
                await player.resume()
                await ctx.send(embed=discord.Embed(description=f"Track **[{player.track.title}]({player.track.uri})** resumed.", color=ctx.author.color))
        except:
            await ctx.send(embed=discord.Embed(description="Currently I'm not pausing any track.", color=ctx.author.color))
    
    @commands.command(name='next', aliases=['skip', 'ne', 'sk'])
    async def next_command(self, ctx, track : Optional[int], send = True):
        """
        Plays the next track in the queue, or jump into a track provided in the queue.
        
        Usage
        -----
            =next [track index]
        """
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send("There's nothing in the queue.")
        try: 
            if ctx.author not in player.channel.members:
                return await ctx.send(f"You must be in <#{player.channel.id}> to do this command.")
            if track is not None:
                player.queue.position = track - 2
                if player.is_playing() or player.is_paused():
                    pass
                else:
                    await player.playback_control()
                    return
            if player.queue.loop.value == 1 and player.queue.count() != 1: player.queue.position += 1
            await player.stop()
        except IndexError:
            if send is True:
                await ctx.send("There's no more track in the queue.")
        except AttributeError:
            if send is True:
                return await ctx.send("There's nothing in the queue.")
    
    @commands.command(name='previous', aliases=['pre', 'prev', 'before'])
    async def previous_command(self, ctx, track : Optional[int]):
        """
        Plays the track before playing track in the queue, or jump into a track provided in the queue.
        
        Usage
        -----
            =previous [track index]
        """
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send("There's nothing in the queue.")
        try: 
            if ctx.author not in player.channel.members:
                return await ctx.send(f"You must be in <#{player.channel.id}> to do this command.")
            if track is not None: 
                if player.queue.loop == Loop.ONE: player.queue.position = track - 1
                else:             
                    player.queue.position = track - 2
                    if player.is_playing() or player.is_paused():
                        pass
                    else:
                        await player.playback_control()
                        return
            else:
                if player.queue.loop == Loop.ONE: player.queue.position -= 1
                else: 
                    player.queue.position -= 2
                    if not player.is_playing() and not player.is_paused():
                        await player.playback_control()
                        return
                if player.queue.position < -2: 
                    if player.queue.loop == Loop.ALL: player.queue.position = player.queue.count() - 1
                    else:
                        player.queue.position = 0
                        raise IndexError
            await player.stop()
        except IndexError:
            await ctx.send(embed=discord.Embed(description="There is no previous track in the queue.", color=ctx.author.color))
    
    @commands.command(name='queue', aliases=['q'])
    async def queue_command(self, ctx):
        """
        Shows the queue.

        Usage
        -----
            =queue
        """
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send("Currently you don't have any queue tracks.")
        view = View(timeout=120)
        btn1 = Button(style=discord.ButtonStyle.blurple, emoji='◀️')
        btn2 = Button(style=discord.ButtonStyle.blurple, emoji='▶️')
        for i in [btn1, btn2]:
            view.add_item(i)
            
        count = player.queue.count()
        self.pages = math.ceil(count/10) - 1
        now = player.queue.position + 1
        self.nowPage = math.ceil(now / 10) - 1
        async def btn1_callback(interaction : discord.Interaction):
            if interaction.user == ctx.author:
                self.nowPage -= 1
                if self.nowPage < 0:
                    self.nowPage = self.pages
                await interaction.response.edit_message(embed=self.queue_show(ctx, player, count, self.pages, self.nowPage))
        async def btn2_callback(interaction : discord.Interaction):
            if interaction.user == ctx.author:
                self.nowPage += 1
                if self.nowPage == self.pages + 1:
                    self.nowPage = 0
                await interaction.response.edit_message(embed=self.queue_show(ctx, player, count, self.pages, self.nowPage))
        btn1.callback = btn1_callback
        btn2.callback = btn2_callback
        if count >= 10: message = await ctx.send(embed=self.queue_show(ctx, player, count, self.pages, self.nowPage), view=view)
        else: message = await ctx.send(embed=self.queue_show(ctx, player, count, self.pages, self.nowPage))

    def queue_show(self, ctx, player, count, pages, nowpage):
        tracks = ""
        for i in range(nowpage * 10, (nowpage + 1) * 10):
            try:
                tracks += f"{'__' if player.queue._queue.index(player.queue._queue[i]) == player.queue.position else ''}`#{i+1}`: **{player.queue._queue[i].title}**{'__' if player.queue._queue.index(player.queue._queue[i]) == player.queue.position else ''}\n"
            except IndexError:
                break
        embed = discord.Embed(title="Queue", description=f"{tracks}", color=ctx.author.color)
        embed.add_field(name="Loop", value=player.queue.loop.name, inline=True)
        embed.add_field(name="Shuffle", value="ON" if player.queue.shuffleMode is True else "OFF", inline=True)
        embed.add_field(name="Total", value=f"{count} {'tracks' if count > 1 else 'track'}", inline=True)
        now = round(int(player.position) / math.ceil(int(player.track.duration) / 20))
        duration = ['▬' for i in range(0, 20)]
        duration[now] = '🔘'
        embed.add_field(name="Duration", value=f"{time_converter(int(player.position))} `{''.join(duration)}` {time_converter(int(player.track.duration))}", inline=False)
        # embed.add_field(name=f"Showing {count if count <= 10 else 10} out of {count} {'tracks' if count > 1 else 'track'}", value=tracks, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.name} | Page {nowpage + 1} of {pages + 1}", icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.name} | Page {nowpage + 1} of {pages + 1}", icon_url=self.bot.user.display_avatar.url)
        return embed

    @commands.command(name='volume', aliases=['vol'])
    async def volume_command(self, ctx, volume : int):
        """
        Controls the volume (from 0 to 150)
        
        Usage:
            =volume <amount>
        """
        if (player := self.get_player(ctx.guild)) is None or player.track is None:
            return await ctx.send(embed=discord.Embed(description="I'm not playing anything.", color=ctx.author.color))
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
        if volume < 0:
            return await ctx.send(embed=discord.Embed(description="You won't hear anything, so why?", color=ctx.author.color))
        if volume > 150:
            return await ctx.send(embed=discord.Embed(description="Too loud!", color=ctx.author.color))
        await player.set_volume(volume/100)
        await ctx.send(embed=discord.Embed(description=f"Set the volume to {volume}%.", color=ctx.author.color))
    
    @commands.command(name='stop', aliases=['clear', 'cl'])
    async def stop_command(self, ctx):
        """
        Stops playing, and clear the queue.

        Usage
        -----
            =stop
        """
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send(embed=discord.Embed(description="You aren't playing any track.", color=ctx.author.color))
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))   
        async def ButtonCallback(interaction : discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You didn't invoke this command, did you?", ephemeral=True)
            elif interaction.data['custom_id'] == "Confirm":
                await player.stop()
                player.queue._queue.clear()
                player.queue.position = 0
                await view.disable_button()
                await interaction.response.edit_message(content="Player stopped. It is now safe to turn off Discord, or start another player.", view=None)
                await player.voicestate_update()
            elif interaction.data['custom_id'] == "Cancel":
                await interaction.response.edit_message(content="Command canceled.", embed=None, view=None)
        view = MusicView(timeout=60)
        for i in [Button(style=discord.ButtonStyle.success, label="Confirm", custom_id="Confirm"), Button(style=discord.ButtonStyle.danger, label="Cancel", custom_id="Cancel")]:
            view.add_item(i)
            i.callback = ButtonCallback
        view.message = await ctx.send("Do you want me to stop playing?\n**CAUTION**: This will remove all the queue tracks.", view=view)
        
    
    @commands.command(name='loop', aliases=['repeat', 'r'])
    async def loop_command(self, ctx, mode : Optional[str]):
        """
        Choose a loop mode.

        Usage
        -----
            =loop [none | one | all]
        """
        if (player := self.get_player(ctx.guild)) is None:
            return await ctx.send(embed=discord.Embed(description="I'm not playing anything!",color=ctx.author.color))
        if mode is not None:
            if mode.lower() not in ['none', 'no', 'remove', 'off' , '0', '1', 'one', 'only', '2', 'all', 'queue']:
                return await ctx.send(embed=discord.Embed(description="Invalid loop mode. Try again with: `none`, `1`, `all`",color=ctx.author.color))
        else: mode = None
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=f"You must be in <#{player.channel.id}> to do this command.",color=ctx.author.color))
        mode = player.queue.set_repeat_mode(mode)
        await ctx.send(embed=discord.Embed(description=f"The loop mode has been set to {mode}.", color=ctx.author.color))
    
    @commands.command(name='lyrics', aliases=['lyr'])
    async def lyrics_command(self, ctx, *, query : Optional[str]):
        """
        Get the lyrics of the playing track or another one.

        Usage
        -----
            =lyrics [track title]
        """
        if not query: 
            if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
                return await ctx.send(embed=discord.Embed(description="I'm not playing anything!",color=ctx.author.color))
            query = player.track.title
        GENIUS.verbose = False
        count = 1
        song = GENIUS.search_song(query)
        if song is None:
            length = len(query.split(' '))
            while count < length:
                query = query.rsplit(' ', 1)[0]
                song = GENIUS.search_song(query)
                if (song is not None):
                    break
                count += 1
        if song is not None:
            song.lyrics = song.lyrics.replace("Embed", "")
            song.lyrics = song.lyrics[:-1]
            song.lyrics = song.lyrics.replace("Lyrics", "Lyrics\n", 1)
            embed = discord.Embed(description=song.lyrics[:3995], color=ctx.author.color)
            embed.set_author(name=f"Lyrics for track {query}", icon_url=ctx.author.display_avatar.url)
            view = MusicView()
            if len(song.lyrics) > 3995: 
                pages = math.ceil(len(song.lyrics) / 3995)
                if pages == 1: await ctx.send(embed=embed)
                else:
                    embed.set_footer(text=f"Page 1 of {pages}")
                    self.current = 1
                    view = MusicView(timeout=60)
                    async def ButtonCallback(interaction : discord.Interaction):
                        if interaction.data['custom_id'] == "▶":
                            if self.current + 1 == pages: self.current = 0
                            else: self.current += 1
                        if interaction.data['custom_id'] == "◀":
                            if self.current == 0: self.current = pages - 1
                            else: self.current -= 1
                        embed.description = song.lyrics[3995*self.current:][:3995]
                        # print(song.lyrics[3995*self.current:][:3995*(self.current+1)])
                        embed.set_footer(text=f"Page {self.current + 1} of {pages}")
                        await interaction.response.edit_message(embed=embed)
                    for i in ("◀", "▶"):
                        btn = Button(emoji=i, custom_id=i)
                        view.add_item(btn)
                        btn.callback = ButtonCallback
                view.message = await ctx.send(embed=embed, view=view)
            await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(description=f"No lyrics of the given track. Tried **{count}** times.", color=ctx.author.color)
            return await ctx.send(embed=embed)
            
        

    @commands.command(name='nowplaying', aliases=['np', 'playing'])
    async def nowplaying_command(self, ctx):
        """
        Show the playing track and many other things.

        Usage
        -----
            =nowplaying
        """
        if (player := self.get_player(ctx.guild)) is None or not player.is_playing():
            return await ctx.send(embed=discord.Embed(description=
"I'm not playing anything!",color=ctx.author.color))
        embed = discord.Embed(title="Now playing", description=f"Track: **[{player.track.title}]({player.track.uri})**", color=ctx.author.color, timestamp=datetime.datetime.now())
        embed.add_field(name="Shuffle", value="ON" if player.queue.shuffleMode is True else "OFF", inline=True)
        embed.add_field(name="Loop", value=player.queue.loop.name, inline=True)
        embed.add_field(name="Position in queue", value=player.queue.position + 1, inline=True)
        now = round(int(player.position) / math.ceil(int(player.track.duration) / 30))
        duration = ['▬' for i in range(0, 30)]
        duration[now] = '🔘'
        embed.add_field(name="Duration", value=f"{time_converter(int(player.position))} `{''.join(duration)}` {time_converter(int(player.track.duration))}", inline=False)
        embed.set_thumbnail(url=f"https://img.youtube.com/vi/{player.track.identifier}/hqdefault.jpg")
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="remove", aliases=['del', 'delete'])
    async def removetrack_command(self, ctx, track : Optional[int]):
        """ 
        Remove a track from the queue. If nothing is provided, remove the whole queue.

        Usage
        -----
            =remove [track index]
        
        """
        if track is None:
            return await self.stop_command(ctx)
        if (player := self.get_player(ctx.guild)) is None:
            return await ctx.send(embed=discord.Embed(description=
"Currently there is nothing in the queue",color=ctx.author.color))
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=
f"You must be in <#{player.channel.id}> to do this command.",color=ctx.author.color))
        await ctx.send(embed=discord.Embed(description=f"Successfully removed #{track}: **{player.queue._queue[track-1].title}**", color=ctx.author.color))
        player.queue._queue.pop(track-1)
        if track - 1 < player.queue.position: player.queue.position -= 1
        if track - 1 == player.queue.position:
            player.queue.position -= 1
            await self.next_command(ctx, None, False)
    
    @commands.command(name="seek")
    async def seek_command(self, ctx, position: str):
        """
        Seek the track to an amount of time.
        Example positions: `2:26`, `0m12s`, `25s`.

        Usage
        -----
            =seek <position>
        """
        if (player := self.get_player(ctx.guild)) is None or player.track is None:
            return await ctx.send(embed=discord.Embed(description=
"I'm not playing anything!", color=ctx.author.color))
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=
f"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
        if not (match := re.match(TIME_REGEX, position)):
            return await ctx.send(embed=discord.Embed(description=
"Invalid time format.\nCorrect time format: `2:26`, `0m12s`, `25s`", color=ctx.author.color))
        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await ctx.send(embed=discord.Embed(description=f"Sought the current track to **{time_converter(secs)}**.", color=ctx.author.color))

    @commands.command(name='shuffle', aliases=['sh'])
    async def shuffle_command(self, ctx):
        """Turn on shuffling the queue or off.

        Usage
        -----
            =shuffle        
        """
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send(embed=discord.Embed(description=
"Currently you don't have any queue tracks.", color=ctx.author.color))
        if ctx.author not in player.channel.members:
            return await ctx.send(embed=discord.Embed(description=
"You must be in <#{player.channel.id}> to do this command.", color=ctx.author.color))
        player.queue.shuffle()
        await ctx.send(embed = discord.Embed(description="The queue has been shuffled." if player.queue.shuffleMode is True else "The queue has been reverted.", color = ctx.author.color))
    
    @commands.is_owner()
    @commands.command(name='musinfo', hidden=True)
    async def musinfo_command(self, ctx):
        if (player := self.get_player(ctx.guild)) is None or player.queue.count() == 0:
            return await ctx.send("Currently you don't have any queue tracks.")
        await ctx.send(f"Position: {player.queue.position}\nLoop: {player.queue.loop}\nShuffle mode: {player.queue.shuffleMode}")
    
    # @commands.check(premium_check)
    # @commands.group(name='playlist', aliases=['pl'])
    # async def playlist_command(self, ctx):
    #     """
    #     A group command of playlist, **only available to premium users**.
    #     """
    #     if ctx.invoked_subcommand is None:
    #         await self.show_playlists(ctx, name=None)
            
    # @commands.check(premium_check)
    # @playlist_command.command(name="show", aliases=['list', 'l'])
    # async def show_playlists(self, ctx, *, name):
    #     """
    #     Show all playlists in this server.
    #     `name`: The playlist name.
    #     """
    #     try: find = (await playlistDB.find_one({"_id" : ctx.guild.id}))['playlists']
    #     except (TypeError, KeyError): return await ctx.send(embed=discord.Embed(description="No playlist was created in this server.", color=ctx.author.color))
    #     description = ['']
    #     count = 0
    #     if not name:
    #         for i in find:
    #             description.append(f'`#{count + 1}`. {i["name"]}')
    #             count += 1
    #         embed = discord.Embed(title=f"There are {count} playlists in {ctx.guild.name}", description='\n'.join(description), timestamp=datetime.datetime.now(), color=ctx.author.color)
    #     else:
    #         playlist = None
    #         for i in find:
    #             if i['name'] == name: 
    #                 playlist = i
    #                 break
    #         if not playlist: return await ctx.send(embed=discord.Embed(description=f"No playlist named {name} was created in this server.", color=ctx.author.color))
    #         for i in playlist['tracks']:
    #             description.append(f"`#{count+1}`. **{i['name']}**")
    #             count += 1
    #         embed = discord.Embed(title=f"Playlist: {name}", description='\n'.join(description[:10]), color=ctx.author.color)
    #     page = 1
    #     pages = math.ceil(len(description) / 10)
    #     if pages > 1:
    #         async def ButtonCallback(interaction : discord.Interaction):
    #             if interaction.user != ctx.author: return await interaction.response.send_message("You didn't invoke this command.", delete_after=5, ephemeral=True)
    #             if interaction.data['custom_id'] == '◀️':
    #                 page -= 1
    #                 embed.description = '\n'.join(description[page * 10 + 1:][:page*10+2])
    #                 await interaction.response.edit_message(embed=embed)
                    
    #         view = View()
    #         for i in ['◀️', '▶️']:
    #             btn = Button(emoji=i, style=discord.ButtonStyle.blurple, custom_id=i)
    #             view.add_item(btn)
    #             btn.callback = ButtonCallback
            
    #     if count > 3: embed.set_thumbnail(url="https://i.imgur.com/8iID9Ps.png")
    #     embed.set_footer(text=f"Requested by {ctx.author.name} • Page {page} of {pages}", icon_url=ctx.author.display_avatar.url)
    #     await ctx.send(embed=embed)
    
    # @commands.check(premium_check)
    # @playlist_command.command(name='play', aliases=['p'])
    # async def play_playlist(self, ctx, *, name):
    #     """
    #     Play the whole given playlist.
        
    #     Usage
    #     -----
    #         =playlist play <playlist name>
    #     """
    #     channel, player = await self.connecter(ctx)
    #     if not player: return
    #     try: find = (await playlistDB.find_one({"_id" : ctx.guild.id}))['playlists']
    #     except (TypeError, KeyError): return await ctx.send(embed=discord.Embed(description="No playlist was created in this server.", color=ctx.author.color))
    #     playlist = None
    #     for i in find:
    #         if i['name'] == name:
    #             playlist = i
    #             break
    #     if not playlist: return await ctx.send(embed=discord.Embed(description=f"No playlist named **{name}** was created in this server.", color=ctx.author.color))
    #     message = await ctx.send(embed=discord.Embed(description="Getting to play...", color=ctx.author.color))
    #     await player.multiplay_function(ctx, playlist['tracks'], message=message)
    
    # @commands.check(premium_check)
    # @playlist_command.command(name='remove', aliases=['delete, del'])
    # async def remove_playlist(self, ctx, *, query : str):
    #     """
    #    Delete a playlist or a track in a playlist.
        
    #     Usage
    #     -----
    #         =playlist remove <playlist name> [ | track index]
    #     """
    #     playlist = query.split('|')[0].strip()
    #     try: track = query.split('|')[1].strip()
    #     except IndexError: track = None
    #     try: find = (await playlistDB.find_one({"_id" : ctx.guild.id}))['playlists']
    #     except (TypeError, KeyError): return await ctx.send(embed=discord.Embed(description="No playlist was created in this server.", color=ctx.author.color))
    #     playlistProvided = None
    #     for i in find:
    #         if i['name'] == playlist: 
    #             playlistProvided = i
    #             break
    #     if not playlistProvided: return await ctx.send(embed=discord.Embed(description=f"No playlist {playlist} was created in this server.", color=ctx.author.color))
    #     if not track: pass
    #     else:
    #         try: track = int(track)
    #         except: return await ctx.send(embed=discord.Embed(description="Invalid track ID. Please provide the order of track you want to remove.", color=ctx.author.color))
    #         trackName = playlistProvided['tracks'][track-1]['name']
    #     view = View()
    #     async def buttonCallback(interaction : discord.Interaction):
    #         if interaction.user != ctx.author: return await interaction.response.send_message("You didn't invoke this command.", ephemeral=True, delete_after=5)
    #         if interaction.data['custom_id'] == "Confirm":
    #             if not track:
    #                 await playlistDB.update_one({"_id" : ctx.guild.id}, {"$pull" : {"playlists" : {"name" : playlist}}})
    #                 for i in view.children: i.disabled = True
    #                 await interaction.response.edit_message(content=f"Removed playlist {playlist}", view=view)
    #             else:
    #                 await playlistDB.update_one({
    #                     "_id": ctx.guild.id,
    #                     "playlists.name": playlist
    #                     },
    #                     {
    #                     "$set": {
    #                         f"playlists.$.tracks.{track - 1}": None
    #                     }
    #                     })
    #                 await playlistDB.update_one({
    #                     "_id": ctx.guild.id,
    #                     "playlists.name": playlist
    #                     },
    #                     {
    #                     "$pull": {
    #                         "playlists.$.tracks": None
    #                     }
    #                     })
    #                 for i in view.children: i.disabled = True
    #                 await interaction.response.edit_message(content=f"Removed successfully.", view=view)
    #     for i in [{"label" : "Confirm", "color" : discord.ButtonStyle.success}, {"label" : "Cancel", "color" : discord.ButtonStyle.danger}]:
    #         button = Button(label=i['label'], style=i['color'], custom_id=i['label'])
    #         view.add_item(button)
    #         button.callback = buttonCallback
    #     if not track: await ctx.send(embed=discord.Embed(description=f"Are you sure you want to delete playlist **{playlist}**?"), view=view)
    #     else: await ctx.send(embed=discord.Embed(description=f"Are you sure you want to delete track **[{playlistProvided['tracks'][track-1]['name']}]({playlistProvided['tracks'][track-1]['uri']})**?"), view=view)
         
    # @commands.check(premium_check)
    # @playlist_command.command(name='create', aliases=['new'])
    # async def create_playlist(self, ctx, *, name):
    #     """
    #     Create a new playlist.
        
    #     Usage
    #     -----
    #         =playlist create <playlist name>
    #     """
    #     try: 
    #         playlist = await self.creator(ctx, name, True)
    #     except PlaylistAlreadyCreated: return await ctx.send(embed=discord.Embed(description=f"The playlist **{name}** is already created on this server. Try choosing an another name.", color=ctx.author.color))
    #     # else:
    #     await ctx.send(embed=discord.Embed(description=f"Successfully created playlist **{name}**.", color=ctx.author.color))

    # async def creator(self, ctx, name, send=True):
    #     find = (await playlistDB.find_one({"_id" : ctx.guild.id}))
    #     try: 
    #         for i in find['playlists']:
    #             if i['name'] == name:
    #                 if send is True: raise PlaylistAlreadyCreated
    #                 return i
    #     except (TypeError, KeyError): pass
    #     info = {
    #         "name" : name,
    #         "author" : ctx.author.id,
    #         "tracks" : []
    #     }
    #     await playlistDB.update_one({"_id" : ctx.guild.id}, {"$push": {"playlists": info }}, upsert=True)
    #     for i in (await playlistDB.find_one({"_id" : ctx.guild.id}))['playlists']:
    #         if i['name'] == name: return i
    
    # @commands.check(premium_check)
    # @playlist_command.command(name='add', aliases=['insert'])
    # async def insert_playlist(self, ctx, *, args : str):
    #     """
    #     Add a track/playlist to playlist.

    #     Usage
    #     -----
    #         =playlist add <playlist name | track name/url>
    #     """
    #     dictQuery = args.split("|")
    #     player = Player(ctx)
    #     if len(dictQuery) != 2: return await ctx.send(embed=discord.Embed(description="Wrong argument! The correct is: `playlist name | track name/url`", color=ctx.author.color))
    #     message = await ctx.send(embed=discord.Embed(description="Searching...", color=ctx.author.color))
    #     playlistName = dictQuery[0].strip()
    #     playlist = await self.creator(ctx, playlistName, False)
    #     if playlist['author'] != ctx.author.id: return await ctx.send(embed=discord.Embed(title=f"You don't have permission to do this.", description=f"*Reason*: This playlist is created by **{(await self.bot.get_or_fetch_user(playlist['author']))}**.", color=ctx.author.color))
    #     query = dictQuery[1].strip()
    #     track = await self.get_track_playlist(ctx, query, playlistName, message)
    #     if type(track) is list:
    #         for i in track:
    #             await playlistDB.update_one({"_id" : ctx.guild.id, f"playlists.name" : playlistName}, {"$push" : {"playlists.$.tracks": i}})
    #     else: await playlistDB.update_one({"_id" : ctx.guild.id, f"playlists.name" : playlistName}, {"$push" : {"playlists.$.tracks": track}})
    
    # @playlist_command.error
    # async def on_command_error(self, ctx, err):
    #     if isinstance(err, commands.CheckFailure):
    #         await ctx.send(embed=discord.Embed(title="Premium users only!", description="This command is only available to those who donated to this bot!\nUse `=donate` command if you're intersted.", color=ctx.author.color))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member : discord.Member, before, after : discord.VoiceState):
        try: player = self.get_player(member.guild)
        except wavelink.errors.ZeroConnectedNodes: return
        try: 
            if before.channel is None: return
            if str(member) == str(self.bot.user) and after.channel is None:
                
                await player.teardown()
            if member == self.bot.user and member in after.channel.members:
                player = self.get_player(member.guild)
                await player.voicestate_update()
        except AttributeError: return
        if member == self.bot.user and after.mute == True:
            if player.is_playing() and not player.is_paused() and player.source is not None:
                await player.pause()
                try: await self.bot.get_channel(player.channelID).send(embed=discord.Embed(description=f"Pausing **[{player.track.title}]({player.track.uri})** until I am unmuted.", color=discord.Color.red()))
                except AttributeError: return
            return
        if member != self.bot.get_user and after.channel != before.channel:
            try:
                if not player.channel: return
                if before.channel != player.channel: return
            except AttributeError: return
            self.timer = 60
            while self.timer > 0:
                self.timer -= 1
                try:
                    for m in player.channel.members:
                        if m and not m.bot:
                            return
                except: pass
                await asyncio.sleep(1)
            player = self.get_player(member.guild)
            try: await player.teardown()
            except: pass
            await self.bot.get_channel(player.channelID).send(f"No activity in the voice channel for a minute, leaving...\n")
        if member == self.bot.user and after.mute == False:
            if before.mute == True:
                if player.is_playing() or player.is_paused():
                    await player.resume()
                    try: await self.bot.get_channel(player.channelID).send(embed=discord.Embed(description=f"Track **[{player.track.title}]({player.track.uri})** resumed.", color=discord.Color.red()))
                    except AttributeError: return
                return
    

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        await player.playback_control()


async def setup(bot):
    await bot.add_cog(Music(bot))
