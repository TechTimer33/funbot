# basic imports, setups and definitions for commands

import discord
from discord.ext import commands, tasks

import random
import os
import asyncio
import aiofiles
import math
import requests
import aiosqlite
import aiohttp
import time
import json
import re
from datetime import datetime
from replit import db
from webserver import keep_alive
from googlesearch import search
from discord.ext.commands.cooldowns import BucketType


@tasks.loop(minutes=60)
async def check_day(notice=7):
    if datetime.now().hour != 11:
        return
    (users, birthdays) = await get_birthdays_all()
    for i, bdayStr in enumerate(birthdays):
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not isinstance(bdayStr, str): continue
        birthday = convert_birthday(bdayStr).replace(year=now.year)
        birthdayDelta = (birthday - now).days
        if birthdayDelta == notice:
            await birthday_notice(users[i], notice)
        if birthdayDelta == 0:
            await birthday_notice(users[i], 0)


snipe_message_author = {}
snipe_message_content = {}
custom_prefixes = {}
default_prefixes = ['fb ', 'Fb ']

player1 = ""
player2 = ""
turn = ""
gameOver = True
board = []
winningConditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7],
                     [2, 5, 8], [0, 4, 8], [2, 4, 6]]


class Data:
    def __init__(self, wallet, bank):
        self.wallet = wallet
        self.bank = bank


# definitions and bot verifiers


async def ask_input(ctx, timeout=30):
    def check_author(msg):
        return msg.author == ctx.message.author

    try:
        response = await bot.wait_for('message',
                                      timeout=timeout,
                                      check=check_author)
    except asyncio.TimeoutError:
        await ctx.send('No reply received.')
        return False
    else:
        return response.content


async def ask_yes_no(ctx, timeout=15):
    return True if await ask_input(ctx, timeout) in ["Y", "y"] else False


def get_quote():
    response = requests.get(
        "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist&type=single"
    )
    json_data = json.loads(response.text)
    joke = json_data["joke"]
    return (joke)


def get_guilds_all():
    return db["guilds"] if "guilds" in db.keys() else False


def set_guild(guild):
    guildID = guild.id
    if "guilds" in db.keys():
        guilds = db["guilds"]
        if guildID not in guilds:
            guilds.append(guildID)
            db["guilds"] = guilds
    else:
        db["guilds"] = [guildID]
    print(f'Guild added.')


def get_channel(guild):
    idStr = str(guild.id)
    if idStr in db.keys():
        print(f'Channel retrieved.')
        return guild.get_channel(db[idStr])
    print(f'Channel not retrieved.')
    return False


def set_channel(channel):
    if "channels" in db.keys():
        channels = db["channels"]
        channels.append(channel.id)
        db["channels"] = channels
    else:
        db["channels"] = [channel.id]
    set_guild(channel.guild)
    print(f'Channel added.')


async def check_channel(ctx):
    channel = get_channel(ctx.guild)
    if channel: return channel
    await ctx.send(
        'There is no channel set to announce birthdays. Would you like to use this channel? (Y/N)'
    )
    if await ask_yes_no(ctx, 15):
        set_channel(ctx.channel)
        await ctx.send(
            f'The birthday channel has been set to {ctx.channel.name}')
    else:
        await ctx.send('No channel was assigned.')


def get_birthday(user):
    idStr = str(user.id)
    if idStr in db.keys():
        print(f'Birthday retrieved.')
        return db[idStr]
    print(f'Birthday not retrieved.')
    return False


async def get_birthdays_all():
    users = tuple(db.keys())
    birthdays = [db[user] for user in users]
    return (users, birthdays)


def convert_birthday(bday):
    try:
        bdayDate = datetime.strptime(bday, '%d/%m/%Y')
    except ValueError:
        return False
    else:
        return bdayDate


def set_birthday(user, bday):
    userID = str(user.id)
    db[userID] = bday


def delete_birthday(user):
    userID = str(user.id)
    del db[userID]


async def birthday_notice(userID, notice=0):
    guildIDs = get_guilds_all()
    for guildID in guildIDs:
        guild = bot.get_guild(guildID)
        user = guild.get_member(userID)
        if user:
            if notice == 0:
                embed = discord.Embed(
                    title=f'Happy Birthday {user.display_name}!',
                    description=f'Today is {user.display_name}\'s birthday',
                    color=0x00ff00)
            else:
                embed = discord.Embed(
                    title=f'It\'s almost {user.display_name}\'s birthday!',
                    description=
                    f'There are only {notice} days left until {user.display_name}\'s birthday.',
                    color=0x00ff00)
            embed.set_author(name=user.display_name, icon_url=user.avatar_url)
            channel = get_channel(guild)
            await channel.send(embed=embed)


def checkWinner(winningConditions, mark):
    global gameOver
    for condition in winningConditions:
        if board[condition[0]] == mark and board[
                condition[1]] == mark and board[condition[2]] == mark:
            gameOver = True


async def determine_prefix(bot, message):
    guild = message.guild
    if guild:
        return custom_prefixes.get(guild.id, default_prefixes)
    else:
        return default_prefixes


async def initialize():
    await bot.wait_until_ready()
    bot.db = await aiosqlite.connect("expData.db")
    await bot.db.execute(
        "CREATE TABLE IF NOT EXISTS guildData (guild_id int, user_id int, exp int, PRIMARY KEY (guild_id, user_id))"
    )


def msg_contains_word(msg, word):
    return re.search(fr'\b({word})\b', msg) is not None


with open("./config.json") as f:
    configData = json.load(f)

noPing = configData["noPing"]

if os.path.exists(os.getcwd() + "/config.json"):

    with open("./config.json") as f:
        configData = json.load(f)

else:
    configTemplate = {"Token": "", "Prefix": "fb ", "bannedWords": []}

    with open(os.getcwd() + "/config.json", "w+") as f:
        json.dump(configTemplate, f)

token = configData["Token"]
prefix = configData["Prefix"]
bannedWords = configData["bannedWords"]

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(intents=intents,
                   command_prefix=determine_prefix,
                   pm_help=True)

bot.warnings = {}
bot.multiplier = 1
bot.welcome_channels = {}
bot.goodbye_channels = {}
bot.reaction_roles = []
bot.users_dict = {}
cooldown = 5

# bot events, identifiers and data load


@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f"Heya, {member.name}! Welcome to {member.guild.name}! We hope you have a fun time here and enjoy our services!"
    )
    for guild_id in bot.welcome_channels:
        if guild_id == member.guild.id:
            channel_id, message = bot.welcome_channels[guild_id]
            await bot.get_guild(guild_id).get_channel(channel_id).send(
                f"{message} {member.mention}")
    role = discord.utils.get(member.guild.roles, name='Member')
    await member.add_roles(role)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"I need the permissions:")  
        return

    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title=
            "<:PensiveTrashCan:903474309803175938> Error 402: Command on Cooldown",
            description=
            "The command you tried to use is still on cooldown, try again in **{:.0f}** seconds."
            .format(error.retry_after),
            timestamp=ctx.message.created_at,
            color=0xe3cf57)
        await ctx.send(embed=embed)
        return

    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title=
            "<:plsunzipmeeee:921952277420449852> Error 400: Requirements Not Found",
            description="**Please pass in all required arguments!**",
            timestamp=ctx.message.created_at,
            color=0x7289da)
        await ctx.send(embed=embed)
        return

    if isinstance(error, commands.CheckFailure):
        pass

    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="<:okay:878113633408794675> Error 401: Permissions Missing",
            description="**You dont have permissions to use this command!!**",
            timestamp=ctx.message.created_at,
            color=0x76eec6)
        await ctx.send(embed=embed)
        return

    if isinstance(error, commands.CommandNotFound):
        choices = [
            "Slow down a bit, buddy", "Read the Helpline!",
            "Command error detected-", "Nope, not in my codes",
            "Wrong command there, pal", "Woah, not so fast!"
        ]
        embed = discord.Embed(
            title=
            f"<:Disgusted:854228408270979092> Error 403: {random.choice(choices)}",
            description=
            "The command you entered is not found in my databank! Use `fb help` for more information.",
            timestamp=ctx.message.created_at)
        embed.set_thumbnail(
            url=
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQokAWsoNNm9EeW9gA8DVBXfn7TtdQy1qaF6Q&usqp=CAU"
        )
        await ctx.send(embed=embed)
        return
    
    if isinstance(error, commands.MemberNotFound):
        embed = discord.Embed(
            title=
            f"<:sobglasses:903474801849544754> Error 406B: Member Not Found",
            description=
            "Invalid Member sent as argument! (Error 406 Variant)",
            timestamp=ctx.message.created_at)
        embed.set_thumbnail(
            url=
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQokAWsoNNm9EeW9gA8DVBXfn7TtdQy1qaF6Q&usqp=CAU"
        )
        await ctx.send(embed=embed)
        return
    
    if isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title=
            f"<:sobglasses:903474801849544754> Error 406: Bad Argument",
            description=
            "Bad argument for command you sent there, choose a valid choice!",
            timestamp=ctx.message.created_at)
        embed.set_thumbnail(
            url=
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQokAWsoNNm9EeW9gA8DVBXfn7TtdQy1qaF6Q&usqp=CAU"
        )
        await ctx.send(embed=embed)
        return    

    else:
      embed = discord.Embed(
            title=
            f"<:sobglasses:903474801849544754> Error 576: Unknown Code Error",
            description=
            "This error is an unknown error, if you see this error code when doing a command, you need to report this to the bot owner as soon as possible so that he could fix it. This error is mainly caused when there is an error in the code for the command. This is serious.",
            timestamp=ctx.message.created_at)
      embed.set_thumbnail(
            url=
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQokAWsoNNm9EeW9gA8DVBXfn7TtdQy1qaF6Q&usqp=CAU"
      )
      await ctx.send(embed=embed)
      return      


@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
      await message.channel.send(f"{message.author.mention} My default prefix is {prefix}")

    messageAuthor = message.author

    if bannedWords != None and (isinstance(
            message.channel, discord.channel.DMChannel) == False):
        for bannedWord in bannedWords:
            if msg_contains_word(message.content.lower(), bannedWord):
                await message.delete()
                await message.channel.send(
                    f"{messageAuthor.mention} your message was removed as it contained a banned word."
                )

    if not message.author.bot:
        cursor = await bot.db.execute(
            "INSERT OR IGNORE INTO guildData (guild_id, user_id, exp) VALUES (?,?,?)",
            (message.guild.id, message.author.id, 1))

        if cursor.rowcount == 0:
            await bot.db.execute(
                "UPDATE guildData SET exp = exp + 1 WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id))
            cur = await bot.db.execute(
                "SELECT exp FROM guildData WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id))
            data = await cur.fetchone()
            exp = data[0]
            lvl = math.sqrt(exp) / bot.multiplier

            if lvl.is_integer():
                await message.channel.send(
                    f"{message.author.mention} well done! You're now at level {int(lvl)}."
                )

        await bot.db.commit()

    await bot.process_commands(message)


@bot.event
async def on_member_remove(member):
    for guild_id in bot.goodbye_channels:
        if guild_id == member.guild.id:
            channel_id, message = bot.goodbye_channels[guild_id]
            await bot.get_guild(guild_id).get_channel(channel_id).send(
                f"{message} {member.mention}")
            return


@bot.event
async def on_message_delete(message):
    if len(message.mentions) == 0:
        return
    else:
      if message.author.bot:
        return
      else:
        ghostping = discord.Embed(title=f'GHOST PING DETECTED!', color=0xFF0000, timestamp=message.created_at)
        ghostping.add_field(name='**Name:**', value=message.author)
        ghostping.add_field(name='**ID:**', value=message.author.id, inline=True)
        ghostping.add_field(name='**Message Content:**', value=f'{message.content}', inline=False)
        ghostping.set_thumbnail(
            url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQiNtP86nKIDTLSCZpg78vFhiXxqlEbKdqweA&usqp=CAU')
        try:
            await message.channel.send(embed=ghostping)
        except discord.Forbidden:
            try:
                await message.author.send(embed=ghostping)
            except discord.Forbidden:
                return

    snipe_message_author[message.channel.id] = message.author
    snipe_message_content[message.channel.id] = message.content
    await asyncio.sleep(60)
    del snipe_message_author[message.channel.id]
    del snipe_message_content[message.channel.id]


@bot.event
async def on_raw_reaction_add(payload):
    for role_id, msg_id, emoji in bot.reaction_roles:
        if msg_id == payload.message_id and emoji == str(
                payload.emoji.name.encode("utf-8")):
            await payload.member.add_roles(
                bot.get_guild(payload.guild_id).get_role(role_id))
            return


@bot.event
async def on_raw_reaction_remove(payload):
    for role_id, msg_id, emoji in bot.reaction_roles:
        if msg_id == payload.message_id and emoji == str(
                payload.emoji.name.encode("utf-8")):
            guild = bot.get_guild(payload.guild_id)
            await guild.get_member(payload.user_id
                                   ).remove_roles(guild.get_role(role_id))
            return


@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            tips = [
                "Funbot.rgb is still in Beta development, so if any errors occur in one of Funbot's commands, feel free to DM its creator PX`Pixel#9297 or helper Decstarken#8613 for feedback. We would love to hear them!!",
                "Funbot's creator is PX`Pixel#9297, however Funbot contributor Decstarken#8613's codes for his bots has deeply inspired him.",
                "Funbot is not complete in development yet. Improvements and more commands will be soon added! But we would also love to hear your suggestions.",
                "Funbot's life is created by PX`Pixel#9297 when he met Decstarken#8613. His coding skills has seriously gave Pixel some jealousy.",
                "Funbot started as a program written in Node.js and by then, it is only a chat bot and can't do anything else. However, when creator PX`Pixel#9297 learnt a bit of Python, its programming language was switched from Node.js to Python instead and the code is much more easier to write.",
                "The first commands Funbot had is the kick and ban commands, followed by the dadjoke command as an entertainment feature.",
                "Funbot's best friend is Canost.rgb 2.0, which is a remaster of Cannon.rgb.",
                "Funbot's profile picture was pixelated by PX`Pixel#9297 on November 23rd of 2021 due to the concern of image copyright.",
                "As of December 2021, Funbot is now 2 months old!!!",
                "Some of Funbot's command code is found on the internet, especially on StackOverflow and YouTube. All credits are reserved for the codes I added to Funbot!",
                "Funbot is coded in repl.it"
            ]
            embed = discord.Embed(
                title="Thank you for inviting Funbot.rgb to your server",
                description=
                "Funbot is a future generation multigenre bot that will try its best to improve your server with its commands and features!! (Prefix = fb)"
            )
            embed.add_field(
                name="What does Funbot do exactly?",
                value=
                "Funbot's has a ton of commands. Literally, a ton of commands. These commands mostly include moderation, entertainment, music commands and general-purposed educational commands like the timer or the google search engine. You can find out more using `fb help`."
            )
            embed.set_thumbnail(url=bot.user.avatar_url)
            embed.set_footer(text=f"Fun fact/tip: {random.choice(tips)}")
            await channel.send(embed=embed)
        break


@bot.event
async def on_ready():
    for guild in bot.guilds:
        bot.warnings[guild.id] = {}

        async with aiofiles.open(f"{guild.id}.txt", mode="a") as temp:
            pass

        async with aiofiles.open(f"{guild.id}.txt", mode="r") as file:
            lines = await file.readlines()

            for line in lines:
                data = line.split(" ")
                member_id = int(data[0])
                admin_id = int(data[1])
                reason = " ".join(data[2:]).strip("\n")

                try:
                    bot.warnings[guild.id][member_id][0] += 1
                    bot.warnings[guild.id][member_id][1].append(
                        (admin_id, reason))

                except KeyError:
                    bot.warnings[guild.id][member_id] = [
                        1, [(admin_id, reason)]
                    ]

    for file in ["welcome_channels.txt", "goodbye_channels.txt"]:
        async with aiofiles.open(file, mode="a") as temp:
            pass

    async with aiofiles.open("welcome_channels.txt", mode="r") as file:
        lines = await file.readlines()
        for line in lines:
            data = line.split(" ")
            bot.welcome_channels[int(data[0])] = (int(data[1]), " ".join(
                data[2:]).strip("\n"))

    async with aiofiles.open("goodbye_channels.txt", mode="r") as file:
        lines = await file.readlines()
        for line in lines:
            data = line.split(" ")
            bot.goodbye_channels[int(data[0])] = (int(data[1]), " ".join(
                data[2:]).strip("\n"))

    async with aiofiles.open("reaction_roles.txt", mode="a") as temp:
        pass

    async with aiofiles.open("reaction_roles.txt", mode="r") as file:
        lines = await file.readlines()
        for line in lines:
            data = line.split(" ")
            bot.reaction_roles.append(
                (int(data[0]), int(data[1]), data[2].strip("\n")))

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.competing,
        name=f"{len(bot.guilds)} Guilds | fb help | Subscribe!"))
    bot.load_extension('dismusic')
    check_day.start()
    global startTime
    startTime = time.time()
    print("Bot is ready!")


bot.lava_nodes = [{
    'host': 'lava.link',
    'port': 80,
    'rest_uri': f"http://lava.link:80",
    'identifier': 'MAIN',
    'password': 'Brawlidays987',
    'region': 'singapore'
}]

# bot cmds (main)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def rolemembers(ctx, role: discord.Role):
    await ctx.send("\n".join(str(role) for role in role.members))


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.guild_only()
async def setprefix(ctx, *, prefix=""):
    custom_prefixes[ctx.guild.id] = prefix.split() or default_prefixes
    await ctx.send(f"Prefix in the server has been set to {prefix}")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def tictactoe(ctx, p1: discord.Member, p2: discord.Member):
    global count
    global player1
    global player2
    global turn
    global gameOver

    if gameOver:
        global board
        board = [
            ":white_large_square:", ":white_large_square:",
            ":white_large_square:", ":white_large_square:",
            ":white_large_square:", ":white_large_square:",
            ":white_large_square:", ":white_large_square:",
            ":white_large_square:"
        ]
        turn = ""
        gameOver = False
        count = 0

        player1 = p1
        player2 = p2

        line = ""
        for x in range(len(board)):
            if x == 2 or x == 5 or x == 8:
                line += " " + board[x]
                await ctx.send(line)
                line = ""
            else:
                line += " " + board[x]

        num = random.randint(1, 2)
        if num == 1:
            turn = player1
            myEmbed = discord.Embed(
                title="GAME IN PROGRESS",
                description="It is <@" + str(player1.id) +
                ">'s turn. Use -place <block-number> to do your move!",
                color=0xe74c3c)
            await ctx.send(embed=myEmbed)
        elif num == 2:
            turn = player2
            myEmbed = discord.Embed(
                title="GAME IN PROGRESS",
                description="It is <@" + str(player2.id) +
                ">'s turn. Use -place <block-number> to do your move!",
                color=0xe74c3c)
            await ctx.send(embed=myEmbed)
    else:
        myEmbed = discord.Embed(
            title="GAME IN PROGRESS",
            description=
            "A GAME IS STILL IN PROGRESS. FINISH IT BEFORE STARTING A NEW ONE",
            color=0xe74c3c)
        await ctx.send(embed=myEmbed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def place(ctx, pos: int):
    global turn
    global player1
    global player2
    global board
    global count
    global gameOver
    if not gameOver:
        mark = ""
        if turn == ctx.author:
            if turn == player1:
                mark = ":regional_indicator_x:"
            elif turn == player2:
                mark = ":o2:"
            if 0 < pos < 10 and board[pos - 1] == ":white_large_square:":
                board[pos - 1] = mark
                count += 1

                line = ""
                for x in range(len(board)):
                    if x == 2 or x == 5 or x == 8:
                        line += " " + board[x]
                        await ctx.send(line)
                        line = ""
                    else:
                        line += " " + board[x]

                checkWinner(winningConditions, mark)
                print(count)
                if gameOver == True:
                    myEmbed = discord.Embed(title="WINNER!",
                                            description=mark + " :crown: ",
                                            color=0xf1c40f)
                    await ctx.send(embed=myEmbed)
                elif count >= 9:
                    gameOver = True
                    myEmbed = discord.Embed(
                        title="TIE",
                        description="IT'S A TIE :handshake:",
                        color=0xf1c40f)
                    await ctx.send(embed=myEmbed)

                if turn == player1:
                    turn = player2
                elif turn == player2:
                    turn = player1
            else:
                myEmbed = discord.Embed(
                    title="PLACE ERROR!",
                    description=
                    "BE SURE TO CHOOSE AN INTEGER BETWEEN 1 AND 9 (INCLUSIVE) AND AN UNMARKED TILE. ",
                    color=0xe74c3c)
                await ctx.send(embed=myEmbed)
        else:
            myEmbed = discord.Embed(title="TURN ERROR!",
                                    description="IT'S NOT YOUR TURN",
                                    color=0xe74c3c)
            await ctx.send(embed=myEmbed)
    else:
        myEmbed = discord.Embed(
            title="START GAME",
            description="TO START A NEW GAME, USE -tictactoe COMMAND",
            color=0x2ecc71)
        await ctx.send(embed=myEmbed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def end_tictactoe(ctx):
    global count
    global player1
    global player2
    global turn
    global gameOver

    count = 0
    player1 = ""
    player2 = ""
    turn = ""
    gameOver = True

    myEmbed = discord.Embed(
        title="RESET GAME",
        description="TO START A NEW GAME, USE -tictactoe COMMAND",
        color=0x2ecc71)
    await ctx.send(embed=myEmbed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        await member.kick()
        await ctx.send(f"User {member.mention} has been kicked for no reason.")
        await member.create_dm()
        await member.dm_channel.send(
            f"{member.name} you have been kicked from {member.guild.name}. Do not break rules in the server ok"
        )
        return
    await member.kick(reason=reason)
    await ctx.send(f"User {member.mention} has been kicked for {reason}.")
    await member.create_dm()
    await member.dm_channel.send(
        f"{member.name} you have been kicked from {member.guild.name}. Do not break rules in the server ok"
    )
    return


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    guild = ctx.guild
    mutedRole = discord.utils.get(guild.roles, name="Muted")

    if not mutedRole:
        mutedRole = await guild.create_role(name="Muted")

        for channel in guild.channels:
            await channel.set_permissions(mutedRole,
                                          speak=False,
                                          send_messages=False,
                                          read_message_history=True,
                                          read_messages=False)
    embed = discord.Embed(title="Muted",
                          description=f"{member.mention} was muted ",
                          colour=discord.Colour.light_gray())
    embed.add_field(name="reason:", value=reason, inline=False)
    await ctx.send(embed=embed)
    await member.add_roles(mutedRole, reason=reason)
    await member.send(
        f" you have been muted from: {guild.name} reason: {reason}")


@bot.command()
@commands.has_permissions(ban_members=True)
@commands.cooldown(1, 5, BucketType.user)
async def ban(ctx, userID: int, *, reason):
    if reason is None:
        await ctx.guild.ban(discord.Object(id=userID))
        embed = discord.Embed(title=":white_check_mark:  " +
                              f"Successfully banned {userID} for no reason",
                              color=discord.Color.orange())
        await ctx.reply(embed=embed, mention_author=False)
    else:
        await ctx.guild.ban(discord.Object(id=userID))
        embed2 = discord.Embed(title=":white_check_mark:  " +
                               f"Successfully banned {userID} for {reason}",
                               color=discord.Color.orange())
        await ctx.reply(embed=embed2, mention_author=False)


@bot.command(brief="Unmutes a user")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_messages=True)
async def unmute(ctx, member: discord.Member):
    mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")

    await member.remove_roles(mutedRole)
    embed = discord.Embed(title="Unmuted",
                          description=f"Unmuted-{member.mention}",
                          colour=discord.Colour.light_gray())
    await ctx.send(embed=embed)


@bot.command(brief="Echoes back what you say")
@commands.cooldown(1, 5, commands.BucketType.user)
async def say(ctx, *, user_message):
    await ctx.send(f"{user_message}\n\n- **{ctx.author}**")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.guild_only()
async def softban(ctx, id: int):
    user = await bot.fetch_user(id)
    await ctx.guild.ban(user)
    await ctx.guild.unban(user)
    await ctx.send(f"Successfully softbanned {id}")


@bot.command(brief="Unbans user from guild")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.guild_only()
async def unban(ctx, id: int):
    user = await bot.fetch_user(id)
    await ctx.guild.unban(user)
    await ctx.send(f"Successfully unbanned {id}")


@bot.command(pass_context=True, brief="Gives role to a user")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await ctx.send(
        f"Hey {ctx.author.name}, {user.name} has been given a role called: {role.name}"
    )


@bot.command(pass_context=True, brief="Takes away role from user")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_roles=True)
async def takeawayrole(ctx, user: discord.Member, role: discord.Role):
    await user.remove_roles(role)
    await ctx.send(
        f"Hey {ctx.author.name}, {user.name} has been removed from role {role.name}"
    )


@bot.command(brief="Creates a role in server")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, *, name):
    guild = ctx.guild
    await guild.create_role(name=name)
    await ctx.send(f'Role `{name}` has been created')


@bot.command(pass_context=True, brief="Deletes a role from server")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_roles=True)
async def deleterole(ctx, role_name):
    role_object = discord.utils.get(ctx.message.guild.roles, name=role_name)
    await role_object.delete()
    await ctx.send(f'Role has been deleted!')


@bot.command(brief="Rolls a dice")
@commands.cooldown(1, 5, commands.BucketType.user)
async def rolldice(ctx):
    message = await ctx.send(
        "Choose a number:\n**1**, **2**, **3**, **4**, **5**, **6** ")

    def check(m):
        return m.author == ctx.author

    try:
        message = await bot.wait_for("message", check=check, timeout=30.0)
        m = message.content

        if m != "1" and m != "2" and m != "3" and m != "4" and m != "5" and m != "6":
            await ctx.send("Sorry, invalid choice.")
            return

        coming = await ctx.send("Here it comes...")
        await asyncio.sleep(1)
        await coming.delete()
        await ctx.send(f"**{random.randint(1, int(m))}**")

    except asyncio.TimeoutError:
        await message.delete()
        await ctx.send(
            "Process has been cancelled because you didn't respond in **30** seconds."
        )


@bot.command(aliases=['8ball'], brief="Play with the magic 8ball")
@commands.cooldown(1, 5, commands.BucketType.user)
async def _8ball(ctx, *, question):
    responses = [
        'It is certain.', 'It is decidedly so.', 'Without a doubt.',
        'Yes - definitely.', 'You may rely on it.', 'As I see it, yes.',
        'Most likely.', 'Outlook good!', 'Yes.', 'Signs point to yes.',
        'Reply hazy, try again.', 'Ask again later...',
        'Better not tell you now.', 'Cannot predict now.',
        "Don't count on it.", 'My reply is no.', 'My source say no.',
        'Outlook not so good.', 'Very doubtful.'
    ]

    embed = discord.Embed(title="Funbot Magical 8Ball Result")
    embed.add_field(name="Question:", value=f"{question}")
    embed.add_field(name="Answer:", value=f"{random.choice(responses)}")
    embed.set_footer(text=f"Question asked by {ctx.author}")
    embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQGwIirLX700R3xEt55RgpsxjkUT9C-Epiw2g&usqp=CAU")

    await ctx.send(embed=embed)


@bot.command(pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def newnick(ctx, member: discord.Member, nick):
    await member.edit(nick=nick)
    await ctx.send(f'Nickname was changed to {member.mention} ')


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def userinfo(ctx, *, user: discord.Member = None):
    if user is None:
        user = ctx.author
    date_format = "%a, %d %b %Y %I:%M %p"
    embed = discord.Embed(title="User Information", color=0xdfa3ff)

    embed.set_author(name=str(user), icon_url=user.avatar_url)

    embed.set_thumbnail(url=user.avatar_url)

    embed.add_field(name="Name", value=user.name)
    embed.add_field(name="Tag", value=user.discriminator)
    embed.add_field(name="ID", value=str(user.id))
    embed.add_field(name="Nickname", value=user.nick)
    embed.add_field(name="Bot?", value=user.bot)
    embed.add_field(name="Joined", value=user.joined_at.strftime(date_format))
    members = sorted(ctx.guild.members, key=lambda m: m.joined_at)
    embed.add_field(name="Join Position", value=str(members.index(user) + 1))
    embed.add_field(name="Registered",
                    value=user.created_at.strftime(date_format))
    embed.add_field(name="Top Role", value=user.top_role.mention)
    embed.add_field(name="Status", value=str(user.status).title())
    embed.add_field(
        name="Activity",
        value=
        f"{str(user.activity.type).split('.')[-1].title()} - {user.activity.name}"
    )
    embed.add_field(name="Boosted?", value=bool(user.premium_since))

    if len(user.roles) > 1:
        role_string = ' '.join([r.mention for r in user.roles][1:])
        embed.add_field(name="Roles [{}]".format(len(user.roles) - 1),
                        value=role_string,
                        inline=False)
    perm_string = ', '.join([
        str(p[0]).replace("_", " ").title() for p in user.guild_permissions
        if p[1]
    ])

    embed.add_field(name="Guild permissions", value=perm_string, inline=False)

    return await ctx.send(embed=embed)


@bot.command(brief="Warns a user")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        await ctx.send("Please provide a reason for your warning!")
        return

    embed = discord.Embed(title="Warning issued: ", color=0xf40000)

    embed.add_field(name="Reason: ", value=f'{reason}', inline=False)
    embed.add_field(name="User warned: ",
                    value=f'{member.mention}',
                    inline=False)
    embed.add_field(name="Warned by: ", value=f'{ctx.author}', inline=False)

    try:
        first_warning = False
        bot.warnings[ctx.guild.id][member.id][0] += 1
        bot.warnings[ctx.guild.id][member.id][1].append(
            (ctx.author.id, reason))

    except KeyError:
        first_warning = True
        bot.warnings[ctx.guild.id][member.id] = [1, [(ctx.author.id, reason)]]

    count = bot.warnings[ctx.guild.id][member.id][0]

    async with aiofiles.open(f"{ctx.guild.id}.txt", mode="a") as file:
        await file.write(f"{member.id} {ctx.author.id} {reason}\n")

    await ctx.send(
        f"{member.mention} has been warned in {member.guild.name} for **{reason}** and now have {count} {'warning' if first_warning else 'warnings'} from Funbot."
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def warninglist(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(
            "You need to provide a user or user is not found.")

    embed = discord.Embed(
        title=f"Warnings executed by Admins for {member.name}",
        description="",
        colour=discord.Colour.dark_green())
    try:
        i = 1
        for admin_id, reason in bot.warnings[ctx.guild.id][member.id][1]:
            admin = ctx.guild.get_member(admin_id)
            embed.description += f"**Warning {i}** by: {admin.mention}, for reason *'{reason}'*.\n"
            i += 1

        await ctx.send(embed=embed)

    except KeyError:
        await ctx.send("This user has no warnings yet!")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def meme(ctx):
    r = requests.get("https://memes.blademaker.tv/api?lang=en")
    res = r.json()
    title = res["title"]
    m = discord.Embed(title=f"{title}",
                      description="Remember, keep on laughing")
    m.set_image(url=res["image"])
    m.set_footer(
        text=
        f"👍: {random.randint(0, 10000)} 👎: {random.randint(0, 3000)} 💬: {random.randint(1, 2000)}"
    )
    await ctx.send(embed=m)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_channels=True)
async def lockdown(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send('Channel locked.')


@bot.command()
@commands.has_permissions(manage_channels=True)
async def serverlockdown(ctx):
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role,
                                      send_messages=False,
                                      view_channel=True,
                                      read_message_history=True)
    await ctx.send('The server is now on lockdown!')


@bot.command(brief="Unlocks a channel from lockdown")
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role,
                                      send_messages=True)
    await ctx.send(ctx.channel.mention +
                   " has been unlocked. Sorry for lockdown!")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlockserver(ctx):
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role,
                                      send_messages=True,
                                      view_channel=True,
                                      read_message_history=True)
    await ctx.send('Server is now unlocked')


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def numberguess(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.message.channel

    number = random.randint(1, 100)
    await ctx.send('I picked a number from 1 to 100, guess which one it is!')

    for i in range(0, 8):
        guess = await bot.wait_for('message', check=check)

        if guess.content == str(number):
            await ctx.send('GGs, you got it right!')

            return

        elif guess.content < str(number):
            await ctx.send('Higher!')

        elif guess.content > str(number):
            await ctx.send('Lower!')

        else:
            return

    else:
        await ctx.send("Sad life, you lost")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def serverinfo(ctx):

    date_format = "%a, %d %b %Y %I:%M %p"

    embed = discord.Embed(title=str(ctx.guild.name) + " Server Information",
                          description=str(ctx.guild.description),
                          color=discord.Color.blue(),
                          timestamp=ctx.message.created_at)


    embed.set_thumbnail(url=str(ctx.guild.icon_url))

    statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

    embed.add_field(name="Owner", value=str(ctx.guild.owner))
    embed.add_field(name="Server ID", value=str(ctx.guild.id))
    embed.add_field(name="Region", value=str(ctx.guild.region))
    embed.add_field(name="Member Count", value=str(ctx.guild.member_count))
    embed.add_field(name="Created at",
                    value=ctx.guild.created_at.strftime(date_format))
    embed.add_field(name="Human Beings",
                    value=len(
                        list(filter(lambda m: not m.bot, ctx.guild.members))))
    embed.add_field(name="Bots",
                    value=len(list(filter(lambda m: m.bot,
                                          ctx.guild.members))))
    embed.add_field(name="Statuses", value=f"🟢 {statuses[0]} 🟡 {statuses[1]} 🔴 {statuses[2]} ⚪ {statuses[3]}")
    embed.add_field(name="Banned Members", value=len(await ctx.guild.bans()))
    embed.add_field(name="Text Channels", value=len(ctx.guild.text_channels))
    embed.add_field(name="Voice Channels", value=len(ctx.guild.voice_channels))
    embed.add_field(name="Categories", value=len(ctx.guild.categories))
    embed.add_field(name="Roles", value=len(ctx.guild.roles))
    embed.add_field(name="Invites", value=len(await ctx.guild.invites()))

    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def setdelay(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(
        f"Set the slowmode delay in this channel to {seconds} seconds!")


@bot.command(brief="Edits a channel's name")
@commands.cooldown(1, 5, commands.BucketType.user)
async def channelname(ctx, channel: discord.TextChannel, *, new_name):
    await channel.edit(name=new_name)


@bot.command(brief="Creates a channel")
@commands.cooldown(1, 5, commands.BucketType.user)
async def createchannel(ctx, *, name=None):
    guild = ctx.message.guild
    if name == None:
        await ctx.send(
            'Sorry, but you have to insert a name. Try again, but do it like this: `fb/create [channel name]`'
        )
    else:
        await guild.create_text_channel(name)
        await ctx.send(f"Created a channel named {name}")


@bot.command(brief="Creates a category")
@commands.cooldown(1, 5, commands.BucketType.user)
async def createcategory(ctx, *, name):
    await ctx.guild.create_category(name)
    await ctx.send("Boom! Category created!")


@bot.command(pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def delcategory(ctx, category: discord.CategoryChannel):
    delcategory = category
    channels = delcategory.channels

    for channel in channels:
        try:
            await channel.delete()
        except AttributeError:
            pass
    await delcategory.delete()


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=100):
    await ctx.channel.purge(limit=amount)


@bot.command(brief="Clones a channel")
@commands.cooldown(1, 5, commands.BucketType.user)
async def clone(ctx, channel_name):
    channel_id = int(''.join(i for i in channel_name if i.isdigit()))
    existing_channel = bot.get_channel(channel_id)
    if existing_channel:
        await existing_channel.clone(reason="Has been nuked")
        await ctx.send("Channel has been cloned.")


@bot.command(help='Delete a channel with the specified name')
@commands.cooldown(1, 5, commands.BucketType.user)
async def delchannel(ctx, channel_name):
    guild = ctx.guild
    existing_channel = discord.utils.get(guild.channels, name=channel_name)

    if existing_channel is not None:
        await existing_channel.delete()
    else:
        await ctx.send(f'No channel named, "{channel_name}", was found')


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ship(ctx,
               user1 = None,
               user2 = None):
    if user2 == None and user1 == ctx.author.mention:
        await ctx.send("bruh")
        return

    if user1 == None:
        user1 = random.choice(ctx.guild.members).mention
        arg = random.randint(0, 100)

        if arg == 0:
            str = "In Your Dreams"
        if arg >=1 <= 15:
            str = "Very Bad 😞"
        if arg > 15 < 35:
            str = "Bad 🙁"
        if arg >= 35 < 50:
            str = "Below Average 😐"
        if arg >= 50 < 60:
            str = "Average 😎"
        if arg >= 60 < 75:
            str = "Good 😎"
        if arg >= 75 < 90:
            str = "Extremely Good 😎"
        if arg >= 90 <= 99:
            str = "OP!"
        if arg == 100:
            str = "PERFECT!"

        await ctx.send("**MATCHMAKING---**", delete_after=3.0)
        await asyncio.sleep(3.5)

        embed = discord.Embed(title="♥ Shipping Test Results ♥", description=f"🚹 User 1: {ctx.author.mention}\n🚺 User 2: {user1}", color=0xffc0cb)
        embed.add_field(name="Score", value=f"{arg}%")
        embed.add_field(name="General", value=str, inline=True)

        await ctx.send(embed=embed)
        return
      
    if user2 == None:
        arg = random.randint(0, 100)

        if arg == 0:
            str = "In Your Dreams"
        if arg >=1 <= 15:
            str = "Very Bad 😞"
        if arg > 15 < 35:
            str = "Bad 🙁"
        if arg >= 35 < 50:
            str = "Below Average 😐"
        if arg >= 50 < 60:
            str = "Average 😎"
        if arg >= 60 < 75:
            str = "Good 😎"
        if arg >= 75 < 90:
            str = "Extremely Good 😎"
        if arg >= 90 <= 99:
            str = "OP!"
        if arg == 100:
            str = "PERFECT!"

        await ctx.send("**MATCHMAKING---**", delete_after=3.0)
        await asyncio.sleep(3.5)

        embed = discord.Embed(title="♥ Shipping Test Results ♥", description=f"🚹 User 1: {ctx.author.mention}\n🚺 User 2: {user1}", color=0xffc0cb)
        embed.add_field(name="Score", value=f"{arg}%")
        embed.add_field(name="General", value=str, inline=True)

        await ctx.send(embed=embed)
        return

    arg = random.randint(0, 100)

    if arg == 0:
        str = "In Your Dreams"
    if arg >=1 <= 15:
        str = "Very Bad 😞"
    if arg > 15 < 35:
        str = "Bad 🙁"
    if arg >= 35 < 50:
        str = "Below Average 😐"
    if arg >= 50 < 60:
        str = "Average 😎"
    if arg >= 60 < 75:
        str = "Good 😎"
    if arg >= 75 < 90:
        str = "Extremely Good 😎"
    if arg >= 90 <= 99:
        str = "OP!"
    if arg == 100:
        str = "PERFECT!"

    await ctx.send("**MATCHMAKING---**", delete_after=3.0)
    await asyncio.sleep(3.5)

    embed = discord.Embed(title="♥ Shipping Test Results ♥", description=f"🚹 User 1: {user1}\n🚺 User 2: {user2}", color=0xffc0cb)
    embed.add_field(name="Score", value=f"{arg}%")
    embed.add_field(name="General", value=str, inline=True)

    await ctx.send(embed=embed)
    return


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def timer(ctx, timeInput):
    try:
        try:
            time = int(timeInput)
        except:
            convertTimeList = {'s': 1, 'm': 60, 'h': 3600}
            time = int(timeInput[:-1]) * convertTimeList[timeInput[-1]]
        if time > 3600:
            await ctx.send(
                "We are not currently supporting timer over an hour long right now, sorry about that!"
            )
            return
        if time <= 0:
            await ctx.send("Timers don't go into negatives you genius :/")
            return
        if time >= 60:
            message = await ctx.send(
                f"Timer: {time//60} minutes {time%60} seconds")
        elif time < 60:
            message = await ctx.send(f"Timer: {time} seconds")
        while True:
            try:
                await asyncio.sleep(1)
                time -= 1
                if time == 3600:
                    await message.edit(content=f"Timer: {time//3600} hours")
                elif time >= 60:
                    await message.edit(
                        content=f"Timer: {time//60} minutes {time%60} seconds")
                elif time < 60:
                    await message.edit(content=f"Timer: {time} seconds")
                if time <= 0:
                    await message.edit(content="Ended!")
                    await ctx.send(
                        f"{ctx.author.mention} Your countdown has ended!!")
                    break
            except:
                break
    except:
        await ctx.send(f"Bruh how do you expect me to time **{timeInput}**??")
        return


page1 = discord.Embed(title="Funbot Helpline",
                      colour=discord.Colour.green())
page1.add_field(name="**__# Moderation Commands__**",
                value="*Funbot Commands for Moderation*",
                inline=False)
page1.add_field(name="\u200b",
                value="**fb ban <ID> <reason>** Bans user from guild. (Features Hackban!)",
                inline=False)
page1.add_field(name="fb/channelname <channel> <newname>",
                value="Changes the name of a channel",
                inline=False)
page1.add_field(name="fb/clear <amount>",
                value="Clears messages in a channel",
                inline=False)
page1.add_field(name="fb/clone <channelname>",
                value="Clones a channel",
                inline=False)
page1.add_field(name="fb/createcategory <name>",
                value="Creates a category",
                inline=False)
page1.add_field(name="fb/createchannel <name>",
                value="Creates a channel",
                inline=False)
page1.add_field(name="fb/createrole <name>",
                value="Creates a role",
                inline=False)
page1.add_field(name="fb/delcategory <category>",
                value="Deletes a category",
                inline=False)
page1.add_field(name="fb/deleterole <role>",
                value="Deletes a role",
                inline=False)
page1.add_field(name="fb/deletechannel <channel>",
                value="Deletes a channel",
                inline=False)
page1.add_field(name="fb/giverole <user> <role>",
                value="Gives a user a role",
                inline=False)
page1.add_field(name="fb/kick <member> <reason>",
                value="Kicks a member",
                inline=False)
page1.add_field(name="fb/lockdown <channel>",
                value="Lockdowns (mutes) a channel",
                inline=False)
page1.add_field(
    name="fb/mute <user> <reason>",
    value=
    "Mutes a user. They won't be unmuted until you use the unmute command",
    inline=False)
page1.add_field(name="\u200b",
                value="fb/newnick <member> <nickname> - Give a person a new nickname",
                inline=False)
page1.add_field(
    name="fb/setdelay <seconds>",
    value="Sets the slowmode in the channel you typed the command in",
    inline=False)
page1.add_field(
    name="fb/snipe",
    value=
    "Shows you the last deleted message inside the channel you typed the command in",
    inline=False)
page1.add_field(name="fb/takeawayrole <user> <role>",
                value="Takes away a user's role",
                inline=False)
page1.add_field(
    name="fb/tempmute <member> <time> <d> <reason>",
    value=
    "Temporarily mutes a user. Note d means time values, eg. s, m, h or d.",
    inline=False)
page1.add_field(name="fb/unban <user ID>", value="Unbans a user", inline=False)
page1.add_field(
    name="fb/unlock",
    value=
    "Unlocks a channel from lockdown (this must be executed inside the locked channel)",
    inline=False)
page1.add_field(name="fb/unmute <member>",
                value="Unmutes a member",
                inline=False)
page1.add_field(name="fb/warn <member> <reason>",
                value="Warns a member",
                inline=False)
page1.add_field(name="fb/warninglist <member>",
                value="Lists all warnings from a member",
                inline=False)
page1.set_footer(
    text=
    "Funbot Helpline Page 1 - Moderation Commands. Click the right pointed arrow to view the second page for Entertainment commands"
)
page2 = discord.Embed(title="Funbot Helpline",
                      description="List of all Funbot commands to use",
                      colour=discord.Colour.green())
page2.add_field(name="**__# Entertainment Commands__**",
                value="*Funbot Commands for Entertainment*",
                inline=False)
page2.add_field(name="fb/8ball <question/statement>",
                value="Play with the magical 8ball...",
                inline=False)
page2.add_field(name="fb/coinflip",
                value="Flips a coin and see the results",
                inline=False)
page2.add_field(name="fb/dadjoke",
                value="Tells you some random sick dadjokes",
                inline=False)
page2.add_field(
    name="fb/dial <phone number>",
    value=
    "Dial a phone number of your choice and see what happens!\nNote: Don't use your real phone number or someone else's phone number that you know of.",
    inline=False)
page2.add_field(name="fb/echo <sentence>",
                value="Echoes back what you says",
                inline=False)
page2.add_field(
    name="fb/emojify <sentence>",
    value=
    ":regional_indicator_t::regional_indicator_u::regional_indicator_r::regional_indicator_n::regional_indicator_s:   :regional_indicator_y::regional_indicator_o::regional_indicator_u::regional_indicator_r:   :regional_indicator_s::regional_indicator_e::regional_indicator_n::regional_indicator_t::regional_indicator_e::regional_indicator_n::regional_indicator_c::regional_indicator_e:   :regional_indicator_i::regional_indicator_n::regional_indicator_t::regional_indicator_o:  :regional_indicator_v::regional_indicator_e::regional_indicator_r::regional_indicator_b::regional_indicator_a::regional_indicator_l:  :regional_indicator_e::regional_indicator_m::regional_indicator_o::regional_indicator_j::regional_indicator_i::regional_indicator_s:\nNote: Does not yet work with capital letters or punctuations.",
    inline=False)
page2.add_field(name="fb/leetify <sentence>",
                value="7URn5 y0UR 53n73nc3 1n70 13375p34k 5ym6015",
                inline=False)
page2.add_field(name="fb/mcseedpicker",
                value="Picks you a random Minecraft seed to use",
                inline=False)
page2.add_field(name="fb/meme",
                value="Shows you some random sick memes",
                inline=False)
page2.add_field(
    name="fb/numberguess",
    value="Guess a number between 1 - 100, clues will be given as you go.",
    inline=False)
page2.add_field(name="fb/dadjoke",
                value="Tells you a random sick dadjoke",
                inline=False)

page2.add_field(name="fb/dadjoke",
                value="Tells you a random sick dadjoke",
                inline=False)

bot.help_pages = [page1, page2]


@bot.command()
async def help2(ctx):
    buttons = [u"\u23EA", u"\u2B05", u"\u27A1", u"\u23E9"]
    current = 0
    msg = await ctx.send(embed=bot.help_pages[current])

    for button in buttons:
        await msg.add_reaction(button)

    while True:
        try:
            reaction, user = await bot.wait_for(
                "reaction_add",
                check=lambda reaction, user: user == ctx.author and reaction.
                emoji in buttons,
                timeout=60.0)

        except asyncio.TimeoutError:
            return await ctx.send("Help command has timed out.")

        else:
            previous_page = current
            if reaction.emoji == u"\u23EA":
                current = 0

            elif reaction.emoji == u"\u2B05":
                if current > 0:
                    current -= 1

            elif reaction.emoji == u"\u27A1":
                if current < len(bot.help_pages) - 1:
                    current += 1

            elif reaction.emoji == u"\u23E9":
                current = len(bot.help_pages) - 1

            for button in buttons:
                await msg.remove_reaction(button, ctx.author)

            if current != previous_page:
                await msg.edit(embed=bot.help_pages[current])


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def tempmute(ctx, member: discord.Member, time: int, d, *, reason=None):
    guild = ctx.guild

    for role in guild.roles:
        if role.name == "Muted":
            await member.add_roles(role)

            embed = discord.Embed(
                title="Muted!",
                description=f"{member.mention} has been tempmuted ",
                colour=discord.Colour.light_gray())
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.add_field(name="Time left for unmute:",
                            value=f"{time}{d}",
                            inline=False)
            await ctx.send(embed=embed)

            if d == "s":
                await asyncio.sleep(time)

            if d == "m":
                await asyncio.sleep(time * 60)

            if d == "h":
                await asyncio.sleep(time * 60 * 60)

            if d == "d":
                await asyncio.sleep(time * 60 * 60 * 24)

            await member.remove_roles(role)

            embed = discord.Embed(title="Unmute (temp) ",
                                  description=f"Unmuted -{member.mention} ",
                                  colour=discord.Colour.light_gray())
            await ctx.send(embed=embed)

            return


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def emojify(ctx, *, text):
    emojis = []
    for s in text:
        if s.isdecimal():
            num2emo = {
                '0': 'zero',
                '1': 'one',
                '2': 'two',
                '3': 'three',
                '4': 'four',
                '5': 'five',
                '6': 'six',
                '7': 'seven',
                '8': 'eight',
                '9': 'nine'
            }
            emojis.append(f':{num2emo.get(s)}:')
        elif s.isalpha():
            emojis.append(f':regional_indicator_{s}:')
        else:
            emojis.append(s)
    await ctx.send(' '.join(emojis))


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def leetify(ctx, *, text):
    leets = []
    for s in text:
        if s.isalpha():
            num2emo = {
                'A': '4',
                'a': '4',
                'B': '8',
                'b': '6',
                'D': 'd',
                'E': '3',
                'e': '3',
                'C': 'C',
                'c': 'c',
                'd': 'd',
                'F': 'f',
                'f': 'f',
                'g': '9',
                'G': '9',
                'H': 'h',
                'h': 'h',
                'I': '1',
                'i': '1',
                'J': 'J',
                'j': 'j',
                'K': 'k',
                'k': 'k',
                'L': '1',
                'l': '1',
                'M': 'm',
                'm': 'm',
                'N': 'N',
                'n': 'n',
                'O': '0',
                'o': '0',
                'P': 'p',
                'p': 'p',
                'Q': 'Q',
                'q': 'Q',
                'R': 'r',
                'r': 'R',
                'S': '5',
                's': '5',
                'T': '7',
                't': '7',
                'U': 'u',
                'u': 'U',
                'V': 'v',
                'v': 'V',
                'W': 'w',
                'w': 'W',
                'X': 'x',
                'x': 'x',
                'Y': 'Y',
                'y': 'y',
                'Z': '2',
                'z': '2'
            }
            leets.append(f'{num2emo.get(s)}')
        else:
            leets.append(s)
    await ctx.send(''.join(leets))


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def createdm(ctx, user_id=None, *, args=None):
    if user_id != None and args != None:
        try:
            target = await bot.fetch_user(user_id)
            await target.send(args)

            await ctx.channel.send("'" + args + "' sent to: " + target.name)

        except:
            await ctx.channel.send("Couldn't dm the given user.")

    else:
        await ctx.channel.send(
            "You didn't provide a user's id and/or a message.")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def funfact(ctx):
    funfacts = [
        "Octopuses have three hearts.",
        "Cows don’t actually have four stomachs; they have one stomach with four compartments.",
        "The platypus doesn’t have a stomach at all: Their esophagus goes straight to their intestines.",
        "Eating parts of a pufferfish can kill you because in a defense mechanism to ward off predators, it contains a deadly chemical called tetrodotoxin. There’s enough in one pufferfish to kill 30 people and there’s no antidote. Still, pufferfish, called fugu, is a highly-prized delicacy in Japan, but can only be prepared by well-trained chefs.",
        "Polar bears have black skin. And actually, their fur isn’t white—it’s see-through, so it appears white as it reflects light.",
        "Tigers’ skin is actually striped, just like their fur. Also, no two fur patterns are alike.",
        "Flamingoes are only pink because of chemicals called carotenoids in the algae and fish (which also eat the algae) they eat; their feathers are grayish white when they’re born.",
        "Mosquitoes are the deadliest animal in the world: They kill more people than any other creature, due to the diseases they carry.",
        "What do Miss Piggy and Yoda have in common? They were both voiced by the same person, puppeteer Frank Oz.",
        "Psycho was the first movie to show a toilet flushing."
    ]

    await ctx.send(random.choice(funfacts))


@bot.command(brief="Dial somebody's number and troll them ecks dee")
@commands.cooldown(1, 5, commands.BucketType.user)
async def dial(ctx, number: int):
    replies = [
        "What's up? Wait who are you?! -PixelGames#9297",
        "Hey stranger! You like frence?! No? You are weird. -amobg us#0911",
        "BRO! YOU MADE ME WRITE THE WRONG CODE! WHY!! NOW I HAVE TO RESET IT ALL AGAIN! -ItzMe_Dec#8613",
        "BRO! WHY ARE YOU DIALING ME WHEN IM IN MY EXAM! -robopoke1345#1654",
        "Hey what's up, I'm toxic and dumb, you just dialed the noob guy -ITS ProDuncan_YT Gamer#0499",
        "i forgor -i forgor 💀", "It's a me, Mario! -Mario Fanboy#4541",
        "Sorry, the number you have dialed is empty. Please try again later. -Trollface#6969",
        "*silence* -Deleted User#0000",
        "🚽 rest rom -universal shape gaming#9586",
        "AHH PERVERT! IM STILL TAKING A SHOWER!! -ODer#5573",
        "pixel da best, and so is dec -🐍💥 ρ𝕣𝐎ƒεⓢᔕ𝐎я 𝓬𝐀ℓⒸ𝓊𝓵υＳ ♡🍟#5965",
        "you suzy baka, get out of my lab!!1!11!1! -dr nefardio#6942",
        "would u like to make gaem with me? no? ur weird man -kyoko#1837",
        "hi this is kenneth, but im kinda busy rn so u can call me later ok -Kenneth"
    ]
    await ctx.send(f"Dialing and connecting to **{number}**, please wait---",
                   delete_after=3.6)
    await asyncio.sleep(4)
    await ctx.send(f"**Successfully connected to {number}!**")
    await asyncio.sleep(1.5)
    await ctx.send(random.choice(replies))
    await asyncio.sleep(1)
    await ctx.send("**The other user hung up the phone**")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def snipe(ctx):
    channel = ctx.channel
    try:
        em = discord.Embed(name=f"Last deleted message in #{channel.name}",
                           description=snipe_message_content[channel.id])
        em.set_footer(
            text=f"This message was sent by {snipe_message_author[channel.id]}"
        )
        await ctx.send(embed=em)
        return

    except:
        await ctx.send(
            f"There are no recently deleted messages in #{channel.name}")
        return


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_welcome_channel(ctx,
                              new_channel: discord.TextChannel = None,
                              *,
                              message=None):
    if new_channel != None and message != None:
        for channel in ctx.guild.channels:
            if channel == new_channel:
                bot.welcome_channels[ctx.guild.id] = (channel.id, message)
                await ctx.channel.send(
                    f"Welcome channel has been set to: {channel.name} with the message {message}"
                )
                await channel.send("This is the new welcome channel!")

                async with aiofiles.open("welcome_channels.txt",
                                         mode="a") as file:
                    await file.write(
                        f"{ctx.guild.id} {new_channel.id} {message}\n")

                return

        await ctx.channel.send("Couldn't find the given channel.")

    else:
        await ctx.channel.send(
            "You didn't include the name of a welcome channel or a welcome message."
        )


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_goodbye_channel(ctx,
                              new_channel: discord.TextChannel = None,
                              *,
                              message=None):
    if new_channel != None and message != None:
        for channel in ctx.guild.channels:
            if channel == new_channel:
                bot.goodbye_channels[ctx.guild.id] = (channel.id, message)
                await ctx.channel.send(
                    f"Goodbye channel has been set to: {channel.name} with the message {message}"
                )
                await channel.send("This is the new goodbye channel!")

                async with aiofiles.open("goodbye_channels.txt",
                                         mode="a") as file:
                    await file.write(
                        f"{ctx.guild.id} {new_channel.id} {message}\n")

                return

        await ctx.channel.send("Couldn't find the given channel.")

    else:
        await ctx.channel.send(
            "You didn't include the name of a goodbye channel or a goodbye message."
        )


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def find(ctx, *, query):
    author = ctx.author.mention
    await ctx.channel.send(
        f"Here are the links that are most related to your query {author} !")
    async with ctx.typing():
        for j in search(query, tld="co.in", num=3, stop=3, pause=2):
            await ctx.send(f"\n:point_right: {j}")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_reaction(ctx,
                       role: discord.Role = None,
                       msg: discord.Message = None,
                       emoji=None):
    if role != None and msg != None and emoji != None:
        await msg.add_reaction(emoji)
        bot.reaction_roles.append(
            (role.id, msg.id, str(emoji.encode("utf-8"))))

        async with aiofiles.open("reaction_roles.txt", mode="a") as file:
            emoji_utf = emoji.encode("utf-8")
            await file.write(f"{role.id} {msg.id} {emoji_utf}\n")

        await ctx.channel.send("Reaction has been set.")

    else:
        await ctx.send("Invalid arguments.")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def stats(ctx, member: discord.Member = None):
    if member is None: member = ctx.author

    async with bot.db.execute(
            "SELECT exp FROM guildData WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)) as cursor:
        data = await cursor.fetchone()
        exp = data[0]

    async with bot.db.execute("SELECT exp FROM guildData WHERE guild_id = ?",
                              (ctx.guild.id, )) as cursor:
        rank = 1
        async for value in cursor:
            if exp < value[0]:
                rank += 1

    lvl = int(math.sqrt(exp) // bot.multiplier)

    current_lvl_exp = (bot.multiplier * (lvl))**2
    next_lvl_exp = (bot.multiplier * ((lvl + 1)))**2

    lvl_percentage = ((exp - current_lvl_exp) /
                      (next_lvl_exp - current_lvl_exp)) * 100

    embed = discord.Embed(title=f"Stats for {member.name}",
                          colour=discord.Colour.gold())
    embed.add_field(name="Level", value=str(lvl))
    embed.add_field(name="Exp", value=f"{exp}/{next_lvl_exp}")
    embed.add_field(name="Rank", value=f"{rank}/{ctx.guild.member_count}")
    embed.add_field(name="Level Progress",
                    value=f"{round(lvl_percentage, 2)}%")

    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def announce(ctx, channel: discord.TextChannel, role: discord.Role, *,
                   announcement):
    await channel.send(
        f"{role.mention}\n{announcement}\n\n      **--{ctx.author}**")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def covidreport(ctx, *, countryName=None):
    try:
        if countryName is None:
            embed = discord.Embed(
                title=
                "This command is used like this: ```fb/covidreport [country]```",
                colour=0xff0000,
                timestamp=ctx.message.created_at)
            await ctx.send(embed=embed)

        else:
            url = f"https://coronavirus-19-api.herokuapp.com/countries/{countryName}"
            stats = requests.get(url)
            json_stats = stats.json()
            country = json_stats["country"]
            totalCases = json_stats["cases"]
            todayCases = json_stats["todayCases"]
            totalDeaths = json_stats["deaths"]
            todayDeaths = json_stats["todayDeaths"]
            recovered = json_stats["recovered"]
            active = json_stats["active"]
            critical = json_stats["critical"]
            casesPerOneMillion = json_stats["casesPerOneMillion"]
            deathsPerOneMillion = json_stats["deathsPerOneMillion"]
            totalTests = json_stats["totalTests"]
            testsPerOneMillion = json_stats["testsPerOneMillion"]

            embed2 = discord.Embed(
                title=f"**Current COVID-19 Status Of {country}!**",
                description=
                "This Information Isn't Live Always, Hence It May Not Be Accurate!",
                colour=0x0000ff,
                timestamp=ctx.message.created_at)
            embed2.add_field(name="**Total Cases**",
                             value=totalCases,
                             inline=True)
            embed2.add_field(name="**Today Cases**",
                             value=todayCases,
                             inline=True)
            embed2.add_field(name="**Total Deaths**",
                             value=totalDeaths,
                             inline=True)
            embed2.add_field(name="**Today Deaths**",
                             value=todayDeaths,
                             inline=True)
            embed2.add_field(name="**Recovered**",
                             value=recovered,
                             inline=True)
            embed2.add_field(name="**Active**", value=active, inline=True)
            embed2.add_field(name="**Critical**", value=critical, inline=True)
            embed2.add_field(name="**Cases Per One Million**",
                             value=casesPerOneMillion,
                             inline=True)
            embed2.add_field(name="**Deaths Per One Million**",
                             value=deathsPerOneMillion,
                             inline=True)
            embed2.add_field(name="**Total Tests**",
                             value=totalTests,
                             inline=True)
            embed2.add_field(name="**Tests Per One Million**",
                             value=testsPerOneMillion,
                             inline=True)

            embed2.set_thumbnail(
                url=
                "https://cdn.discordapp.com/attachments/564520348821749766/701422183217365052/2Q.png"
            )
            await ctx.send(embed=embed2)

    except:
        embed3 = discord.Embed(
            title="Invalid Country Name Or API Error! Try Again..!",
            colour=0xff0000,
            timestamp=ctx.message.created_at)
        embed3.set_author(name="Error!")
        await ctx.send(embed=embed3)


@bot.command(pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def poll(ctx, channel: discord.TextChannel, question, *options: str):
    if len(options) <= 1:
        await ctx.send('You need more than one option to make a poll!')
        return
    if len(options) > 5:
        await ctx.send('You cannot make a poll for more than 5 things!')
        return

    if len(options) == 2 and options[0] == 'Yes' or 'yes' and options[
            1] == 'No' or 'no':
        reactions = ['✅', '❌']
    else:
        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

    description = []
    for x, option in enumerate(options):
        description += '\n {} {}'.format(reactions[x], option)
    embed = discord.Embed(title=question, description=''.join(description))
    embed.set_author(name=f"Poll by {ctx.author}")
    react_message = await channel.send(embed=embed)
    for reaction in reactions[:len(options)]:
        await react_message.add_reaction(reaction)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def friendscore(ctx, user1: discord.Member, user2: discord.Member):
    await ctx.send(
        f"**{user1}** is **{random.randint(0, 100)}%** likely to become friends with **{user2}**."
    )


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def makedecision(ctx, *choices):
    if len(choices) <= 1:
        await ctx.send('You need more than 1 choice to make a decision!')
        return
    if len(choices) > 5:
        await ctx.send('You cannot make a decision for more than 5 things!')
        return
    await ctx.send(f"I choose: **{random.choice(choices)}**")


@bot.command(pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def trivia(ctx, question=None, *options: str):
    if question is None:
        await ctx.send("Make a question for your trivia!")
        return
    if len(options) <= 1:
        await ctx.send('You need more than one option to make a trivia!')
        return
    if len(options) > 5:
        await ctx.send('You cannot make a trivia for more than 5 things!')
        return

    reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']

    description = []
    for x, option in enumerate(options):
        description += '\n {} {}'.format(reactions[x], option)
    embed = discord.Embed(title=question, description=''.join(description))
    react_message = await ctx.send(embed=embed)
    for reaction in reactions[:len(options)]:
        await react_message.add_reaction(reaction)
    embed.set_author(name=f"Trivia by {ctx.author}")
    await react_message.edit(embed=embed)


bot.loop.create_task(initialize())


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def addbannedword(ctx, word):
    if word.lower() in bannedWords:
        await ctx.send("Already banned")
    else:
        bannedWords.append(word.lower())

        with open("./config.json", "r+") as f:
            data = json.load(f)
            data["bannedWords"] = bannedWords
            f.seek(0)
            f.write(json.dumps(data))
            f.truncate()

        await ctx.message.delete()
        await ctx.send("Word added to banned words.")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def removebannedword(ctx, word):
    if word.lower() in bannedWords:
        bannedWords.remove(word.lower())

        with open("./config.json", "r+") as f:
            data = json.load(f)
            data["bannedWords"] = bannedWords
            f.seek(0)
            f.write(json.dumps(data))
            f.truncate()

        await ctx.message.delete()
        await ctx.send("Word removed from banned words.")
    else:
        await ctx.send("Word isn't banned.")


@bot.command()
async def setbdaychannel(ctx, channel: discord.TextChannel = None):
    if channel is None: channel = ctx.message.channel
    storedChannel = get_channel(ctx.guild)
    if storedChannel:
        await ctx.send(
            f'This server\'s birthday channel is already set as {storedChannel.name}. Would you like to change it? (Y/N)'
        )
        if await ask_yes_no(ctx, 15) == False:
            await ctx.send(f'The birthday channel was left as {storedChannel}.'
                           )
            return
    set_channel(channel)
    await ctx.send(f'The birthday channel has been set as {storedChannel}.')


@bot.command()
async def addbirthday(ctx, user: discord.Member = None):
    if user is None: user = ctx.message.author
    storedBday = get_birthday(user)
    if storedBday:
        await ctx.send(
            f'{user.name}\'s birthday is already set as {storedBday}. Would you like to change it? (Y/N)'
        )
        if await ask_yes_no(ctx, 15) == False:
            await ctx.send(f'{user.name}\'s birthday was left as {storedBday}.'
                           )
            return

    await ctx.send(
        'Cool! You are almost done. Now, enter your birthday in the format dd/mm/yyyy. For example, 24/08/2004.'
    )
    bday = await ask_input(ctx, 30)
    if bday == False: return
    print(f'Date received.')
    bdayDate = convert_birthday(bday)
    if bdayDate == False:
        await ctx.send(f'Invalid date format.')
        return

    set_birthday(user, bday)
    await ctx.send(f'{user.name}\'s birthday has been set as {bday}')
    await check_channel(ctx)


@bot.command()
async def deletebirthday(ctx, user: discord.Member = None):
    if user is None: user = ctx.message.author
    storedBday = get_birthday(user)
    if storedBday == False:
        await ctx.send(f'{user.name}\'s birthday was not set.')
    else:
        await ctx.send(
            f'{user.name}\'s birthday is set as {storedBday}. Would you like to delete it? (Y/N)'
        )
        if await ask_yes_no(ctx, 15) == False:
            await ctx.send(f'{user.name}\'s birthday was left as {storedBday}.'
                           )
            return

        delete_birthday(user)
        await ctx.send(f'{user.name}\'s birthday has been deleted.')


@bot.command()
async def scissorspaperrock(ctx, choice=None):
    choices = ["rock", "paper", "scissors"]
    if choice not in choices or choice is None:
        await ctx.send(
            "Error: please put rock, paper or scissors for your choice.")
    else:
        await ctx.send(random.choice(choices))


@bot.command()
async def joketime(ctx):
    embed = discord.Embed(title="**Which joke type do you prefer?**")
    embed.add_field(
        name="Choices:",
        value="1: Cold joke\n2: Dadjoke\n3: One-Line Statement Dadjoke")
    msg = await ctx.channel.send(embed=embed)
    await msg.add_reaction("1⃣")
    await msg.add_reaction("2⃣")
    await msg.add_reaction("3⃣")

    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            check=lambda reaction, user: user == ctx.author and reaction.emoji
            in ["1⃣", "2⃣", "3⃣"],
            timeout=30.0)

    except asyncio.TimeoutError:
        await ctx.send("Timed out")
        return

    else:
        if reaction.emoji == "1⃣":
            quote = get_quote()
            await ctx.send(quote)
            return

        if reaction.emoji == "2⃣":
            djoke = [
                'Which bear is the most condescending? A pan-duh!',
                "What kind of shoes do ninjas wear? Sneakers!",
                "How does a penguin build its house? Igloos it together.",
                "How did Harry Potter get down the hill? Walking. JK! Rowling.",
                'What kind of noise does a witch vehicle make? Brrrroooom, brrrroooom--',
                'What’s brown and sticky? A stick.',
                'How do you get a country girl’s attention? A tractor.',
                "Why are elevator jokes so classic and good? They work on many levels.",
                "What do you call a pudgy psychic? A four-chin teller.",
                'What did the police officer say to his belly-button? You’re under a vest.',
                "What do you call it when a group of apes starts a company? Monkey business.",
                'What do you call a naughty lamb dressed up like a skeleton for Halloween? Baaad to the bone.',
                'What kind of drink can be bitter and sweet? Reali-tea.',
                'Want to know why nurses like red crayons? Sometimes they have to draw blood.',
                'What would the Terminator be called in his retirement? The Exterminator.',
                'Why do bees have sticky hair? Because they use a honeycomb.',
                "What’s the most detail-oriented ocean? The Pacific.",
                "Why do some couples go to the gym? Because they want their relationship to work out.",
                "What country's capital is growing the fastest? Ireland. Every day it's Dublin."
            ]
            embed = discord.Embed(title="Here is your random funny Dadjoke!")
            embed.add_field(name="Dadjoke:", value=f"{random.choice(djoke)}")
            embed.set_footer(
                text=
                "Source: https://parade.com/940979/kelseypelzer/best-dad-jokes/"
            )
            await ctx.channel.send(embed=embed)
            return

        else:
            loljokes = [
                "I used to be addicted to soap, but I'm clean now.",
                "A guy walks into a bar... and he was disqualified from the limbo contest.",
                "You think swimming with sharks is expensive? Swimming with sharks cost me an arm and a leg.",
                "When two vegans get in an argument, is it still called a beef?",
                "I ordered a chicken and an egg from Amazon. I'll let you know...",
                "Do you wanna box for your leftovers? No, but I'll wrestle you for them.",
                "That car looks nice but the muffler seems exhausted.",
                "Shoutout to my fingers. I can count on all of them.",
                "Two guys walked into a bar, the third guy ducked.",
                "If a child refuses to nap, are they guilty of resisting a rest?",
                "A cheeseburger walks into a bar. The bartender says: 'Sorry, we do not serve food here.'"
            ]
            embed = discord.Embed(
                title="Here is your random funny One-Line Statement Dadjoke!")
            embed.add_field(name="Dadjoke:",
                            value=f"{random.choice(loljokes)}")
            embed.set_footer(
                text=
                "Source: https://www.countryliving.com/life/a27452412/best-dad-jokes/"
            )
            await ctx.channel.send(embed=embed)
            return


@bot.command()
async def animalpicture(ctx):
    embed = discord.Embed(title="**What animal would you like to see?**")
    embed.add_field(name="Choices:", value="1: Dog\n2: Cat\n3: Bird")
    msg = await ctx.channel.send(embed=embed)
    await msg.add_reaction("1⃣")
    await msg.add_reaction("2⃣")
    await msg.add_reaction("3⃣")

    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            check=lambda reaction, user: user == ctx.author and reaction.emoji
            in ["1⃣", "2⃣", "3⃣"],
            timeout=30.0)

    except asyncio.TimeoutError:
        await ctx.send("Timed out")
        return

    else:
        if reaction.emoji == "1⃣":
            async with aiohttp.ClientSession() as session:
                request = await session.get(
                    'https://some-random-api.ml/img/dog')
                dogjson = await request.json()
                embed = discord.Embed(
                    title="Doggo!",
                    description=
                    "A random cute doggy to make your day, how adorable <3")
                embed.set_image(url=dogjson['link'])
                await ctx.send(embed=embed)
                return

        if reaction.emoji == "2⃣":
            async with aiohttp.ClientSession() as session:
                request = await session.get(
                    'https://some-random-api.ml/img/cat')
                dogjson = await request.json()
                embed = discord.Embed(
                    title="Kitty!",
                    description=
                    "A random cute kitty to make your day, how adorable <3")
                embed.set_image(url=dogjson['link'])
                await ctx.send(embed=embed)
                return

        else:
            async with aiohttp.ClientSession() as session:
                request = await session.get(
                    'https://some-random-api.ml/img/bird')
                dogjson = await request.json()
                embed = discord.Embed(
                    title="Birdy!",
                    description=
                    "A random cute bird to make your day, how adorable <3")
                embed.set_image(url=dogjson['link'])
                await ctx.send(embed=embed)
                return


@bot.command()
async def personalityrate(ctx):
    embed = discord.Embed(
        title="**What personality would you like to know most about yourself?**"
    )
    embed.add_field(
        name="Choices:",
        value="1: Simp\n2: Epicness\n3: Noob\n4: Karen\n5: 🍆 Length\n6: Gay")
    embed.set_footer(
        text="Note: Don't use this command if you are easily offended.")
    msg = await ctx.channel.send(embed=embed)
    await msg.add_reaction("1⃣")
    await msg.add_reaction("2⃣")
    await msg.add_reaction("3⃣")
    await msg.add_reaction("4️⃣")
    await msg.add_reaction("5️⃣")
    await msg.add_reaction("6️⃣")

    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            check=lambda reaction, user: user == ctx.author and reaction.emoji
            in ["1⃣", "2⃣", "3⃣", "4️⃣", "5️⃣", "6️⃣"],
            timeout=30.0)

    except asyncio.TimeoutError:
        await ctx.send("Timed out")
        return

    else:
        if reaction.emoji == "1⃣":
            embed = discord.Embed(
                title="Simpness measurer by Funbot (100% accurate!!1!11!)",
                description=
                f"{ctx.author}'s simpness rate is **{random.randint(1, 100)}%**."
            )
            embed.set_footer(
                text="Command inspired by Glitcher's Little Penguin V2, by Dec"
            )
            await ctx.send(embed=embed)
            return

        if reaction.emoji == "2⃣":
            embed = discord.Embed(
                title="Funboot epicness measurer 1001010010% real xd",
                description=
                f"{ctx.author}'s epicness is **{random.randint(0, 100)}%**")
            embed.set_footer(
                text="Command inspired by Glitcher's Little Penguin")
            await ctx.send(embed=embed)
            return

        if reaction.emoji == "3⃣":
            embed = discord.Embed(
                title="Funboot noobness measurer 1001010010% real",
                description=
                f"{ctx.author}'s noobness is **{random.randint(0, 100)}%**")
            await ctx.send(embed=embed)
            return

        if reaction.emoji == "4️⃣":
            embed = discord.Embed(
                title="Funboot karen measurer 1001010010% real",
                description=
                f"{ctx.author} is **{random.randint(0, 100)}%** Karen")
            await ctx.send(embed=embed)
            return

        lengths = [
            "8=D", "8==D", "8===D", "8====D", "8=====D", "8======D",
            "8=======D", "8========D", "8=========D"
        ]

        if reaction.emoji == "5️⃣":
            embed = discord.Embed(
                title="Funboot pp measurer 1001010010% real",
                description=
                f"{ctx.author}'s' pp length is {random.choice(lengths)}")
            await ctx.send(embed=embed)
            return

        if reaction.emoji == "6️⃣":
            embed = discord.Embed(
                title="Funboot gay measurer 1001010010% real",
                description=
                f"{ctx.author}'s gayness is **{random.randint(0, 100)}%**")
            await ctx.send(embed=embed)
            return


@bot.command()
async def reminder(ctx, time: int, *, msg):
    while True:
        await asyncio.sleep(time)
        await ctx.send(f"{ctx.author.mention} it's time to {msg}")
        return


@bot.command(pass_context=True)
async def setafk(ctx, mins, *, reason):
    current_nick = ctx.author.nick
    guild = ctx.guild
    mutedRole = discord.utils.get(guild.roles, name="AFK")

    if not mutedRole:
        mutedRole = await guild.create_role(name="AFK")

    await ctx.author.add_roles(mutedRole, reason=reason)
    await ctx.send(
        f"{ctx.author.mention} has gone afk for {mins} minutes for {reason}.")
    await ctx.author.edit(nick=f"{ctx.author.name} [AFK]")

    counter = 0
    while counter <= int(mins):
        counter += 1
        await asyncio.sleep(60)

        if counter == int(mins):
            mutedRole = discord.utils.get(ctx.guild.roles, name="AFK")

            await ctx.author.remove_roles(mutedRole)
            await ctx.author.edit(nick=current_nick)
            await ctx.send(f"{ctx.author.mention} is no longer AFK")
            break


# errors


@tictactoe.error
async def tictactoe_error(ctx, error):
    print(error)
    if isinstance(error, commands.MissingRequiredArgument):
        myEmbed = discord.Embed(title="MENTION ERROR!",
                                description="PLEASE MENTION 2 USERS",
                                color=0xe74c3c)
        await ctx.send(embed=myEmbed)
    elif isinstance(error, commands.BadArgument):
        myEmbed = discord.Embed(
            title="ERROR!",
            description=
            "PLEASE MAKE SURE TO MENTION/PING PLAYERS (ie. <@688534433879556134>)",
            color=0xe74c3c)
        await ctx.send(embed=myEmbed)


@place.error
async def place_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        myEmbed = discord.Embed(title="NO POSITION",
                                description="PLEASE ENTER A POSITION TO MARK",
                                color=0xe74c3c)
        await ctx.send(embed=myEmbed)
    elif isinstance(error, commands.BadArgument):
        myEmbed = discord.Embed(title="INTEGER ERROR!",
                                description="PLEASE MAKE SURE IT'S AN INTEGER",
                                color=0xe74c3c)
        await ctx.send(embed=myEmbed)


@removebannedword.error
async def removebannedword_error(ctx, error):
    await ctx.send("Success!")


# secure port

keep_alive()

bot.run("ODkyMjI1MDAxNDkzNzY2MTg1.YVJzSQ.saybXcCWELG6C-73ktF_ZxUhI0o")
asyncio.run(bot.db.close())

# the end of my discord.py bot program :(
