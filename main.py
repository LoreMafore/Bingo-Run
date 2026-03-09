from sys import exception
import enum
from email.policy import default
import discord
from discord.ext import commands
from discord import ui
import logging
from dotenv import load_dotenv
import os
from dataclasses import dataclass, field
import random

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

print("Hello world")
bot = commands.Bot(command_prefix='!', intents=intents)

@dataclass
class Ids:
    server_id: int 
    channel_id: int

@dataclass
class BingoRunConfig_c:
    size: list = field(default_factory=list)
    challenge_list: list = field(default_factory=list)
    player_dic: dict[int, list] = field(default_factory=dict)


USER_CONFIGS : dict[int, BingoRunConfig_c] = {} #user_id, game_info
USER_IDS : dict[int, Ids] = {} #user_id, (server_id, channel_id)


def change_button_color(style, color: str):
    color = color.lower()

    if style != discord.ButtonStyle.secondary:
        style = discord.ButtonStyle.secondary

    else:
        match color:
            case "blurple":
                style = discord.ButtonStyle.primary
            case "green":
                style = discord.ButtonStyle.success
            case "red":
                style = discord.ButtonStyle.danger

    return style


def randomise(challenges: list, total: int):
    try:
        temp_list = challenges.copy()
        random_challenges: list = []
     
        for i in range(total):
            index = random.randint(0,len(temp_list) -1)
            challenge = temp_list.pop(index)
            random_challenges.append(challenge)
        return random_challenges
     
    except Exception as e:
        print(f"An error occured: {e}")
        return None


async def checkId(id: int) -> bool:
    try: 
        await bot.fetch_user(id)
        return True
    except discord.NotFound:
        return False
    except discord.HTTPException:
        return False


def checkColor(color: str) -> bool:
    try:
        color_list = ['blurple', 'green', 'red']
        
        if color in color_list:
            return True

        else: 
            return False

    except Exception as e:
        print(f"An error occured: {e}")
        return False

class BingoButton(ui.Button):

    def __init__(self, label: str, row: int, config: BingoRunConfig_c):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=row
        )
        self.config = config

        
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        for name, color in self.config.player_dic.values():
            if name == user_id:
                self.style = change_button_color(self.style, color)
                await interaction.response.edit_message(view=self.view)
                return
                
        await interaction.user.send(f"You do not have access to the game")


class BingoView(ui.View):
    def __init__(self, config: BingoRunConfig_c, id: Ids):
        super().__init__(timeout=43200) # 12hr timeout
        
        try: 
            total_buttons: int = config.size[0] * config.size[1]
            
            random_list = randomise(config.challenge_list, total_buttons)
            if len(random_list) == 0:
                print("Random list is empty")
                return
                
            for i in range(total_buttons):
                row = i // config.size[0]
                self.add_item(BingoButton(label=random_list[i], row=row, config=config))

        except Exception as e:
            print(f"An error occured: {e}")
            return


@bot.event 
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")


#Server Commands
@bot.command(name='new_game')
@commands.guild_only()
async def new_game(ctx):
    user_id = ctx.author.id 
    server_id = ctx.guild.id
    channel_id = ctx.channel.id

    if user_id in USER_CONFIGS:
        await ctx.author.send("You currently have a game in progress. Do end_game! to finish your game.")

    else:
        USER_IDS[user_id] = Ids(server_id, channel_id)
        USER_CONFIGS[user_id] = BingoRunConfig_c()

    await ctx.author.send(f"Send !info to learn how to start the game")


@bot.command(name='end_game')
@commands.guild_only()
async def end_game(ctx):
    user_id = ctx.author.id 

    if user_id in USER_CONFIGS:
        del USER_CONFIGS[user_id]
        del USER_IDS[user_id]
        await ctx.author.send("Your game finished!")

    else:
        await ctx.author.send("You do not have an active game")


@bot.command(name='info')
async def info(ctx):
    if ctx.guild is not None:
        await ctx.send(
            "In Bingo-Run you make a bingo challenge board. You will give "
            "me a list of challenges, size of board, and who is playing "
            "then I will make a board for you. To start a new game send: "
            "!new_game to the chat. From there I will dm you and you will "
            "send me your configurations and I will make you a bingo board. "
            "For more commands do !commands." 
        )

    else:
        await ctx.send(
                "In Bingo-Run you make a bingo challenge board. You will give "
                "me a list of challenges, size of board, and who is playing "
                "then I will make a board for you. We will need list of "
                "challenges, a board size, and list of players.\n\n"
                "To set a list do the following: \n"
                "!challenges challeneg1,challeneg2 \n"
                "or\n"
                "To set the size of the board do the following: \n"
                "!board_size 5 5\n"
                "This will give you a 5x5 board\n\n"
                "To set who can play the game and which color they will be assigned to do the following: \n"
                "!set_players 123456789 red, 987654321 green\n"
                "or\n"
                "To see all colors do !colors\n\n"
                "You can set a new game by using !load and uploading a csv file like\n"
                "board, 3, 5\n"
                "players, 566083012928733224 green, 699317005282705559 red\n"
                "challenges, challenege1s,challeneg2board, 3, 5\n"
                "To start the game enter !start.\n"
                "For any more commands do !commands"
            )


@bot.command(name='commands')
async def bot_commands(ctx):
    if ctx.guild is not None:
        await ctx.send(
            "!info - Sends a summary of how Bingo-Run works\n" 
            "!commands - Send a list of all commands and their descriptions \n"
            "!new_game - Starts a new game and sends a dm for configuration \n"
            "!end_game - To end game"
        )

    else:
        await ctx.send(
                "!info - Sends a summary of how Bingo-Run works\n" 
                "!start - Starts the game if you have entered players, box size and a list of challenges."
                "!commands - Send a list of all commands and their descriptions \n"
                "!challenges args - gives the bot a list of challenges"
                "!board_size args - sets the size of the board"
                "!players args - gives the bot a list of player_id's(121543210987654321) and their colors. Max three teams"
                "!colors - red, green, blurple"
                "!save - save a csv - not emplmented"
                "!load - load a csv"
                "!example - list an example of different commands - not implmented"
            )


#Dm Commands
# @bot.command(name='all_info')
# @commands.dm_only()
# async def display_info(ctx):
#     try:
#         user_id = ctx.author.id
#         print(USER_CONFIGS[user_id])
#
#     except Exception as e:
#         print(f"An error occured: {e}")
#         await ctx.send("Before seeing info you have to start a new game")
#         return None


@bot.command(name='board_size')
@commands.dm_only()
async def set_board_size(ctx, width: int, height: int):
    try:
        user_id = ctx.author.id
        int_w: int = int(width)
        int_h: int = int(height)

        if int_w > 5 or int_w < 0 :
            await ctx.send("Width must be between 0 and 5. Usage `!board_size 5 5`")

        elif int_h > 5 or int_h < 0 :
            await ctx.send("Height must be between 0 and 5. Usage `!board_size 5 5`")
            
        else:
            USER_CONFIGS[user_id].size = [int_w, int_h]
            await ctx.send(f"You set the board size to be: {USER_CONFIGS[user_id].size[0]}x{USER_CONFIGS[user_id].size[1]}")

    except Exception as e:
        print(f"An error occured: {e}")
        return None


@bot.command(name='challenges')
@commands.dm_only()
async def set_challenges(ctx, *, data: str):
    try: 
        user_id = ctx.author.id
        
        if user_id not in USER_CONFIGS:
            await ctx.send("You don't have an active game. Start one in a server with !new_game")
            return

        if len(USER_CONFIGS[user_id].size) == 0:
            await ctx.send("You need to have board size first before configuring the challenges. Set the size of the board with !board_size")
            return

        # Input format: " challenge1, challenge2"
        challenge_list: list = [p.strip() for p in data.split(',')]
        board_size: int = USER_CONFIGS[user_id].size[0] * USER_CONFIGS[user_id].size[1]

        if len(challenge_list) < board_size:
            await ctx.send(f'You challenge list has {len(challenge_list)} amount of challenges. It needs {board_size} challenges')
            return 
        
        altered_challenge_list: list = []
        altered_var: str = ''
        longest_word: int = 0

        longest_word = max(len(c) for c in challenge_list)
        altered_var = '-' * longest_word

        total_size: float = len(altered_var)/2

        for challenge in challenge_list:
            temp_altered: str = altered_var
            size:int = len(challenge)
            position: float = size/2

            start_pos: int = int(total_size) - int(position)
            temp_altered = temp_altered[:start_pos] + challenge + temp_altered[start_pos + size:]
            altered_challenge_list.append(temp_altered)

        USER_CONFIGS[user_id].challenge_list = altered_challenge_list
        await ctx.send(f"All players set: {USER_CONFIGS[user_id].challenge_list}")

    except Exception as e:
        print(f"An error occured: {e}")
        await ctx.send(f"An error occured: {e}")


@bot.command(name='players')
@commands.dm_only()
async def set_players(ctx, *, data: str):
    try: 
        user_id = ctx.author.id
        
        if user_id not in USER_CONFIGS:
            await ctx.send("You don't have an active game. Start one in a server with !new_game")
            return

        # Input format: "123456789 red, 987654321 green"
        players: list = [p.strip().split() for p in data.split(',')]

        # [[id, color ], [id, color]]
        for i, player_info in enumerate(players):
            if len(player_info) != 2:
                await ctx.send(f"Player {i+1}'s info is wrong. Format: `player1_id player1_color, player2_id, player2_color`")
                return

            player_id: int = int(player_info[0])
            color: str = player_info[1]

            is_id = await checkId(player_id)
            is_color = checkColor(color)

            if is_id and is_color:
                USER_CONFIGS[user_id].player_dic[i+1] = [player_id, color]

            elif is_id == False:
                await ctx.send(f"Player{i+1}'s id is not a real id")

            elif is_color == False:
                await ctx.send(f"Player{i+1}'s color is wrong")

            else:
                await ctx.send(f"Player{i+1}'s color and id are both wrong")
        await ctx.send(f"All players set: {USER_CONFIGS[user_id].player_dic}")

    except ValueError:
        await ctx.send("Player IDs must be numbers. Format: `!players 123456789 red, 987654321 green`")
    except Exception as e:
        print(f"An error occured: {e}")


@bot.command(name='load')
@commands.dm_only()
async def load_config(ctx):
    try:
        user_id = ctx.author.id

        if user_id not in USER_CONFIGS:
            await ctx.send("You don't have an active game. Start one in a server with !new_game")
            return

        if not ctx.message.attachments:
            await ctx.send("Please attach a CSV file. Usage: `!load` with a .csv file attached")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.csv'):
            await ctx.send("File must be a .csv file")
            return

        content = await attachment.read()
        lines = content.decode('utf-8').splitlines()

        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            keyword = parts[0].lower()

            if keyword == 'board':
                width = int(parts[1])
                height = int(parts[2])

                if width > 5 or width < 0:
                    await ctx.send("Width must be between 0 and 5")
                    return
                if height > 5 or height < 0:
                    await ctx.send("Height must be between 0 and 5")
                    return

                USER_CONFIGS[user_id].size = [width, height]
                await ctx.send(f"Board size set to: {width}x{height}")

            elif keyword == 'players':
                player_entries = parts[1:]
                for i, entry in enumerate(player_entries):
                    player_info = entry.strip().split()
                    
                    if len(player_info) == 0:
                        continue  # Skip empty entries from extra delimiters
                    
                    if len(player_info) != 2:
                        await ctx.send(f"Player {i+1} format is wrong. Expected: `id color`")
                        return
                    
                    player_id_str, color = player_info[0], player_info[1]
                    
                    if not player_id_str.isdigit():
                        await ctx.send(f"Player {i+1}'s ID must be a number")
                        return
                    
                    player_id = int(player_id_str)
                    is_id = await checkId(player_id)
                    is_color = checkColor(color)
                    
                    if is_id and is_color:
                        USER_CONFIGS[user_id].player_dic[i+1] = [player_id, color]
                    elif not is_id:
                        await ctx.send(f"Player {i+1}'s ID is not valid")
                    elif not is_color:
                        await ctx.send(f"Player {i+1}'s color is not valid")
                
                await ctx.send(f"Players set: {USER_CONFIGS[user_id].player_dic}")
            elif keyword == 'challenges':
                if len(USER_CONFIGS[user_id].size) == 0:
                    await ctx.send("Board size must be set before challenges. Make sure your CSV has a `board` line before `challenges`")
                    return

                challenge_list = parts[1:]
                board_size = USER_CONFIGS[user_id].size[0] * USER_CONFIGS[user_id].size[1]

                if len(challenge_list) < board_size:
                    await ctx.send(f"Not enough challenges. Need {board_size}, got {len(challenge_list)}")
                    return

                longest_word = max(len(c) for c in challenge_list)
                altered_var = '-' * longest_word
                total_size = len(altered_var) / 2
                altered_challenge_list = []

                for challenge in challenge_list:
                    temp = altered_var
                    size = len(challenge)
                    start_pos = int(total_size) - int(size / 2)
                    temp = temp[:start_pos] + challenge + temp[start_pos + size:]
                    altered_challenge_list.append(temp)

                USER_CONFIGS[user_id].challenge_list = altered_challenge_list
                await ctx.send(f"Challenges set!")

            # Any other line (comments, blanks, headers) is just ignored

        await ctx.send("Config loaded! Use `!all_info` to review, then `!start` when ready.")

    except ValueError as e:
        await ctx.send(f"Invalid number format in CSV: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        await ctx.send(f"An error occurred: {e}")


# @bot.command(name='save')
# @commands.dm_only()
# async def start_game(ctx):
#     user_id = ctx.author.id


@bot.command(name='start')
@commands.dm_only()
async def start_game(ctx):
    user_id = ctx.author.id
    try:
        if len(USER_CONFIGS[user_id].size) == 0:
            await ctx.send("Board size is 0. Please set board size with !board_size")

        elif len(USER_CONFIGS[user_id].player_dic) == 0:
            await ctx.send("There are no players. Please set players with !players")

        elif len(USER_CONFIGS[user_id].challenge_list) == 0:
            await ctx.send("There are no challenges. Please set challenges with !challenges")

        channel_id = USER_IDS[user_id].channel_id
        channel = bot.get_channel(channel_id)
        BingoView(USER_CONFIGS[user_id], USER_IDS[user_id])

        view = BingoView(USER_CONFIGS[user_id], USER_IDS[user_id])

        if not isinstance(channel, discord.abc.Messageable):
            await ctx.send("The saved channel is not messageable!")
            return

        await channel.send("Bingo board is ready!", view=view)
        await ctx.send("Game started! Check the server channel.")

    except Exception as e:
        print(f"An error occured: {e}")


@new_game.error 
async def new_game_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command is only used in servers") 


@set_challenges.error
@set_players.error
@set_board_size.error
async def set_board_size_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide both width and height! Usage: `!board_size <width> <height>`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Args must be numbers. Usage `!board_size 5 5`")
    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command is only used in dms") 


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
