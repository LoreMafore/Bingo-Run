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
        temp_list = challenges
        random_challenges: list = []
    
        for i in range(total):
            index = random.randint(0,len(temp_list))
            challenge = temp_list.pop(index)
            random_challenges.append(challenge)

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
        self.channel = Ids.channel_id
        
        try: 
            total_buttons: int = config.size[0] * config.size[1]
            
            random_list = randomise(config.challenge_list, total_buttons)
            if len(random_list) == 0:
                print("Random list is empty")
                return

            for i, current_button in enumerate(total_buttons):
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

    print(user_id)
    USER_IDS[user_id] = Ids(server_id, channel_id)
    USER_CONFIGS[user_id] = BingoRunConfig_c()
    print(USER_IDS[user_id])

    await ctx.author.send(f"Send !info to learn how to start the game")

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
                "!set_list [\"challange1\", \"challenge2\"]\n"
                "or\n"
                "!set_list challenge.csv (where you uploaded the csv)\n\n"
                "To set the size of the board do the following: \n"
                "!board_size 5 5\n"
                "This will give you a 5x5 board\n\n"
                "To set who can play the game and which color they will be assigned to do the following: \n"
                "!set_players [(\"user_1\", \"blue\"), (\"user_2\", \"red\")]\n"
                "or\n"
                "!set_players players.csv (where you uploaded the csv)\n\n"
                "To see all colors do !colors\n\n"
                "To start the game enter !start.\n"
                "For any more commands do !commands"
            )


@bot.command(name='commands')
async def bot_commands(ctx):
    if ctx.guild is not None:
        await ctx.send(
            "!info - Sends a summary of how Bingo-Run works\n" 
            "!commands - Send a list of all commands and their descriptions \n"
            "!new_game - Starts a new game and sends a dm for configuration"
            "!help"
        )

    else:
        await ctx.send(
                "!info - Sends a summary of how Bingo-Run works\n" 
                "!start - Starts the game if you have entered players, box size and a list of challenges."
                "!commands - Send a list of all commands and their descriptions \n"
                "!challenges args - gives the bot a list of challenges"
                "!challenges csv - gives the bot a csv with a list lof challenges"
                "!board_size args - sets the size of the board"
                "!players args - gives the bot a list of player_id's(121543210987654321) and their colors. Max three teams"
                "!players csv - gives the bot a csv with a list of players and colors"
                "!colors - red, green, blurple"
                "!save"
                "!load"
                "!all_info"
                "!example - list an example of different commands"
                "!help"
            )


#Dm Commands
@bot.command(name='all_info')
@commands.dm_only()
async def display_info(ctx):
    try:
        user_id = ctx.author.id
        print(USER_CONFIGS[user_id])

    except Exception as e:
        print(f"An error occured: {e}")
        await ctx.send("Before seeing info you have to start a new game")
        return None


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

@bot.command(name='players')
@commands.dm_only()
async def set_players(ctx, data: list[list]):
    try: 
        user_id = ctx.author.id

        # [[id, color ], [id, color]]
        for i, player_info in data, enumerate(len(data)):
            id: int = int(player_info[0])
            color: str = player_info[1]

            is_id = checkId(id)
            is_color = checkColor(color)

            if is_id and is_color:
                USER_CONFIGS[user_id].player_dic.append(i+1,[id, color])
                await ctx.send(f"You set the the players: {USER_CONFIGS[user_id].player_dic}")

            elif is_id == False:
                await ctx.send(f"Player{i+1}'s id is not a real id")

            elif is_color == False:
                await ctx.send(f"Player{i+1}'s color is wrong")

            else:
                await ctx.send(f"Player{i+1}'s color and id are both wrong")





@new_game.error 
async def new_game_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command is only used in servers") 


@set_board_size.error
async def set_board_size_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide both width and height! Usage: `!board_size <width> <height>`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Args must be numbers. Usage `!board_size 5 5`")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
