import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from dataclasses import dataclass

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

print("Hello world")
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event 
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")


@dataclass
class BingoRunConfig_c:
    size: list
    challenge_list: list
    member_list: dict


#Server Commands
@bot.command(name='new_game')
@commands.guild_only()
async def new_game(ctx):
    await ctx.author.send(f"Are you ready to start a new game?")

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
                "!commands - Send a list of all commands and their descriptions \n"
                "!set_list args - gives the bot a list of challenges"
                "!set_list csv - gives the bot a csv with a list lof challenges"
                "!board_size args - sets the size of the board"
                "!set_members args - gives the bot a list of players and their colors"
                "!set_list csv - gives the bot a csv with a list of players and colors"
                "!example - list an example of different commands"
                "!help"
            )

#Dm Commands 
@bot.command()
@commands.dm_only()
async def csv(ctx):
    await ctx.send(f"Upload your csv")


@new_game.error 
async def new_game_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command is only used in servers") 


@csv.error 
async def csv_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command is only used in dms") 


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
