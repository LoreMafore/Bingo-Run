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
# [CHANGED] Added io and Pillow imports for board image generation
import io
from PIL import Image, ImageDraw, ImageFont

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
    # [CHANGED] Stores the randomised board order after !start so redraws are consistent
    randomised_challenges: list = field(default_factory=list)
    # [CHANGED] Tracks which cells have been marked and by which color {cell_index: color}
    clicked: dict[int, str] = field(default_factory=dict)


USER_CONFIGS : dict[int, BingoRunConfig_c] = {} #user_id, game_info
USER_IDS : dict[int, Ids] = {} #user_id, (server_id, channel_id)


# [CHANGED] Expanded color map to support all chosen player colors.
# Maps color name -> RGB tuple used when drawing the Pillow board.
COLOR_MAP = {
    "red":     (237, 66,  69),
    "green":   (59,  165, 93),
    "orange":  (242, 140, 40),
    "yellow":  (254, 231, 92),
    "purple":  (149, 55,  255),
    "pink":    (255, 105, 180),
    "cyan":    (0,   210, 211),
}

# [CHANGED] checkColor now validates against COLOR_MAP keys instead of a hardcoded list
def checkColor(color: str) -> bool:
    return color.lower() in COLOR_MAP


def randomise(challenges: list, total: int):
    try:
        # [CHANGED] Use .copy() so the original challenge_list is not mutated
        temp_list = challenges.copy()
        random_challenges: list = []

        for i in range(total):
            # [CHANGED] Fixed randint upper bound (was inclusive and caused index out of range)
            index = random.randint(0, len(temp_list) - 1)
            challenge = temp_list.pop(index)
            random_challenges.append(challenge)

        # [CHANGED] Added missing return statement
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


# [CHANGED] New function — generates the bingo board as a Pillow image.
# Each cell shows the challenge text and is colored based on who marked it.
# Cell numbers are shown in the top-left corner matching the buttons below.
def generate_bingo_board(config: BingoRunConfig_c) -> discord.File:
    COLS = config.size[0]
    ROWS = config.size[1]

    CELL_W, CELL_H = 220, 80
    PADDING = 12
    HEADER_H = 60
    IMG_W = COLS * CELL_W + (COLS + 1) * PADDING
    IMG_H = ROWS * CELL_H + (ROWS + 1) * PADDING + HEADER_H

    BG_COLOR     = (32,  34,  37)   # Discord dark background
    CELL_DEFAULT = (47,  49,  54)   # Unclicked cell color
    TEXT_COLOR   = (255, 255, 255)

    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except:
        font = ImageFont.load_default()
        header_font = font

    draw.text((IMG_W // 2, HEADER_H // 2), "BINGO BOARD", font=header_font,
              fill=TEXT_COLOR, anchor="mm")

    def wrap_text(text, max_width):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if draw.textlength(test, font=font) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    for idx, challenge in enumerate(config.randomised_challenges):
        col = idx % COLS
        row = idx // COLS

        x = PADDING + col * (CELL_W + PADDING)
        y = HEADER_H + PADDING + row * (CELL_H + PADDING)

        # Use the marked color if clicked, otherwise default gray
        cell_color = COLOR_MAP.get(config.clicked.get(idx), CELL_DEFAULT)

        draw.rounded_rectangle([x, y, x + CELL_W, y + CELL_H], radius=8, fill=cell_color)
        draw.rounded_rectangle([x, y, x + CELL_W, y + CELL_H], radius=8,
                                outline=(255, 255, 255), width=1)

        # Cell number in top-left corner matching the button below
        draw.text((x + 6, y + 4), str(idx + 1), font=font, fill=(200, 200, 200))

        lines = wrap_text(challenge, CELL_W - 20)
        line_h = 20
        total_text_h = len(lines) * line_h
        text_y = y + (CELL_H - total_text_h) // 2

        for line in lines:
            draw.text((x + CELL_W // 2, text_y), line, font=font,
                      fill=TEXT_COLOR, anchor="mt")
            text_y += line_h

    # Send as in-memory buffer — no file saved to disk
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="bingo.png")


# [CHANGED] Replaced old BingoButton with MarkButton.
# Buttons are numbered to match the cell numbers shown on the board image.
# Clicking marks that cell with the player's color and redraws the board image.
class MarkButton(ui.Button):
    def __init__(self, cell_index: int, row: int, game_owner_id: int):
        super().__init__(
            label=str(cell_index + 1),
            style=discord.ButtonStyle.secondary,
            row=row
        )
        self.cell_index = cell_index
        self.game_owner_id = game_owner_id

    async def callback(self, interaction: discord.Interaction):
        config = USER_CONFIGS.get(self.game_owner_id)

        if config is None:
            await interaction.response.send_message("Game not found.", ephemeral=True)
            return

        # Find the player's color from their Discord ID
        player_color = None
        for player_id, color in config.player_dic.values():
            if player_id == interaction.user.id:
                player_color = color
                break

        if player_color is None:
            # ephemeral = only visible to the user who clicked, no chat spam
            await interaction.response.send_message("You are not a player in this game!", ephemeral=True)
            return

        # Mark the cell and redraw the board
        config.clicked[self.cell_index] = player_color
        file = generate_bingo_board(config)
        await interaction.response.edit_message(attachments=[file], view=self.view)


# [CHANGED] Replaced old BingoView with new version using MarkButtons (numbered 1-N).
# The view sits below the Pillow image — buttons are just numbers matching the board cells.
class BingoView(ui.View):
    def __init__(self, config: BingoRunConfig_c, game_owner_id: int):
        super().__init__(timeout=43200)  # 12hr timeout
        total = config.size[0] * config.size[1]
        for i in range(total):
            row = i // config.size[0]
            self.add_item(MarkButton(cell_index=i, row=row, game_owner_id=game_owner_id))


@bot.event 
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")


# Server Commands
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
                "!set_players 123456789 red, 987654321 green\n"
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
            "!commands - Send a list of all commands and their descriptions\n"
            "!new_game - Starts a new game and sends a dm for configuration\n"
            "!help"
        )

    else:
        await ctx.send(
                "!info - Sends a summary of how Bingo-Run works\n"
                "!start - Starts the game if you have entered players, box size and a list of challenges.\n"
                "!commands - Send a list of all commands and their descriptions\n"
                "!challenges args - gives the bot a list of challenges\n"
                "!board_size args - sets the size of the board\n"
                "!players args - gives the bot a list of player_id's and their colors.\n"
                # [CHANGED] Updated colors list to reflect new supported colors
                "!colors - red, green, orange, yellow, purple, pink, cyan\n"
                "!all_info\n"
                "!help"
            )


# [CHANGED] Added !colors command so players can easily see all available colors
@bot.command(name='colors')
async def colors(ctx):
    color_list = ", ".join(COLOR_MAP.keys())
    await ctx.send(f"Available colors: {color_list}")


# DM Commands
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

        if int_w > 5 or int_w < 0:
            await ctx.send("Width must be between 0 and 5. Usage `!board_size 5 5`")

        elif int_h > 5 or int_h < 0:
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

        challenge_list: list = [p.strip() for p in data.split(',')]
        board_size: int = USER_CONFIGS[user_id].size[0] * USER_CONFIGS[user_id].size[1]

        if len(challenge_list) < board_size:
            await ctx.send(f'Your challenge list has {len(challenge_list)} challenges. It needs at least {board_size}.')
            return 

        USER_CONFIGS[user_id].challenge_list = challenge_list
        await ctx.send(f"All challenges set: {USER_CONFIGS[user_id].challenge_list}")

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

        for i, player_info in enumerate(players):
            if len(player_info) != 2:
                await ctx.send(f"Player {i+1}'s info is wrong. Format: `player1_id player1_color, player2_id player2_color`")
                return

            player_id: int = int(player_info[0])
            color: str = player_info[1].lower()

            # [CHANGED] Added await to checkId (was missing before, caused RuntimeWarning)
            is_id = await checkId(player_id)
            is_color = checkColor(color)

            if is_id and is_color:
                USER_CONFIGS[user_id].player_dic[i+1] = [player_id, color]
            elif not is_id:
                await ctx.send(f"Player {i+1}'s id is not a real id")
            elif not is_color:
                # [CHANGED] Show valid colors in the error message
                await ctx.send(f"Player {i+1}'s color is wrong. Valid colors: {', '.join(COLOR_MAP.keys())}")
            else:
                await ctx.send(f"Player {i+1}'s color and id are both wrong")

        await ctx.send(f"All players set: {USER_CONFIGS[user_id].player_dic}")

    except ValueError:
        await ctx.send("Player IDs must be numbers. Format: `!players 123456789 red, 987654321 green`")
    except Exception as e:
        print(f"An error occured: {e}")


@bot.command(name='start')
@commands.dm_only()
async def start_game(ctx):
    user_id = ctx.author.id
    try:
        if len(USER_CONFIGS[user_id].size) == 0:
            await ctx.send("Board size is 0. Please set board size with !board_size")
            return

        elif len(USER_CONFIGS[user_id].player_dic) == 0:
            await ctx.send("There are no players. Please set players with !players")
            return

        elif len(USER_CONFIGS[user_id].challenge_list) == 0:
            await ctx.send("There are no challenges. Please set challenges with !challenges")
            return

        config = USER_CONFIGS[user_id]

        # [CHANGED] Randomise and store board order on start
        total_cells = config.size[0] * config.size[1]
        config.randomised_challenges = randomise(config.challenge_list, total_cells)

        if config.randomised_challenges is None:
            await ctx.send("Failed to randomise challenges. Please try again.")
            return

        # Fetch saved channel
        channel_id = USER_IDS[user_id].channel_id
        channel = bot.get_channel(channel_id)
        if channel is None:
            channel = await bot.fetch_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            await ctx.send("The saved channel is not a text channel!")
            return

        # [CHANGED] Send Pillow image with BingoView number buttons attached below it
        file = generate_bingo_board(config)
        view = BingoView(config, user_id)
        await channel.send("Bingo board is ready! Click a number to mark that cell.", file=file, view=view)
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
