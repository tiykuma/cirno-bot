import discord
from discord.ext import commands


class Help(commands.Cog, commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, (self.context.message.content).split(' ', 1)[1], "[@someone]" if command.signature in ["[member]", "[user]"] else "<@someone>" if command.signature in ["<member>", "<user>"] else command.signature)

    async def send_command_help(self, command : commands.Command):
        if not (doc := command.help): doc = f"Not available\nUsage\n-----\n    {self.get_command_signature(command)}"
        options = None
        if "Options\n-------" in doc: 
            options = (doc.split("Options\n-------\n```\n")[1]).split("```\n")[0]
            doc = doc.split("\nOptions\n-------\n```")[0] + (doc.split("\nOptions\n-------\n```")[1]).split('```\n')[1]
        embed = discord.Embed(description=doc.split("\nUsage\n-----\n    ")[0], color=self.context.author.color)
        embed.set_author(name=f"Help: {(self.context.message.content).split(' ', 1)[1]}", icon_url=self.context.me.display_avatar.url)
        alias = command.aliases if command.cog_name != "Roleplay" else None
        if options: embed.add_field(name="Options", value=f"```yaml\n{options}\n```", inline=False)
        if alias: embed.add_field(name="Aliases", value="`" + "` `".join(alias) + "`", inline=True)
        cooldown = str(int(getattr(getattr(command, "cooldown", "None"), "per", "0"))) + 's'
        embed.add_field(name="Group", value=command.cog.qualified_name, inline=True)
        embed.add_field(name="Cooldown", value=cooldown, inline=True)
        channel = self.get_destination()
        embed.add_field(name="Usage", value="```%s```" % (doc.split('\nUsage\n-----\n    ')[1] if '\nUsage\n-----\n    ' in doc else self.get_command_signature(command)), inline=False)
        embed.set_footer(text="Syntax: <required> [optional]")
        await channel.send(embed=embed)
    
    def get_usage(self, command : commands.Command):
        if not (doc := command.help): doc = f"Not available\nUsage\n-----\n    {self.get_command_signature(command)}"
        return "```%s```" % (doc.split('\nUsage\n-----\n    ')[1] if '\nUsage\n-----\n    ' in doc else self.get_command_signature(command))
    
    async def send_bot_help(self, mapping):
        embed = discord.Embed(description=f"Use `{self.context.clean_prefix}help [command]` for more info on a command.\nYou can also use `{self.context.clean_prefix}help [category]` for more information on a category!\n⭐ - Premium command.", color=self.context.author.color)
        for cog, command_set in mapping.items():
            command_name = ""
            for i in command_set:
                if not i.hidden: 
                    if getattr(cog, "qualified_name", "No Category") == "Roleplay": 
                        command_name += "`" + i.name + "` `" +  "` `" .join(i.aliases) + '`'
                    # if i.checks != [] and i.checks[0].__name__ == "premium_check": command_name += f"{i.name} "
                    else: command_name += "`" + i.name + "` "
            if getattr(cog, "qualified_name", "No Category") not in ["Help", "No Category"]: embed.add_field(name=getattr(cog, "_emoji", "") + " " + getattr(cog, "qualified_name", "No Category"), value=command_name, inline=False)
        embed.set_author(name="Help section", icon_url=self.context.me.display_avatar.url)
        await self.get_destination().send(embed=embed)
    
    async def send_cog_help(self, cog : commands.Cog):
        commands = [i.name for i in cog.get_commands()]
        embed = discord.Embed(description=f"{cog.description}\nThere are {len(cog.get_commands()) if cog.qualified_name != 'Roleplay' else 1 + len(cog.get_commands()[0].aliases)} commands:\n **{'`' + '` `'.join(commands) + '`' if cog.qualified_name != 'Roleplay' else '`airkiss` `' + '` `'.join(cog.get_commands()[0].aliases) + '`'}**", color=self.context.author.color)
        embed.set_author(name=f"Help: {cog.qualified_name}", icon_url=self.context.me.display_avatar.url)
        await self.get_destination().send(embed=embed)
    
    async def send_group_help(self, group : commands.Group):
        commands = [f"**{i.name}** - {i.help[:15]}{'...' if len(i.help) > 15 else ''}\n" for i in group.commands]
        embed = discord.Embed(description=f"{group.short_doc}\n*There are {len(commands)} commands in this group:*\n{''.join(commands)}You can use {self.context.clean_prefix}help [command] for more info on a command.", color=self.context.author.color)
        embed.set_author(name=f"Help: {group.qualified_name}", icon_url=self.context.me.display_avatar.url)
        await self.get_destination().send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help())