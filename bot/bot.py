import os
import re
import simkl
import asyncio
import sqlite3
import interactions
import database as db
from log import get_logger
from dotenv import load_dotenv
from validation import Movie, Show, get_current_timestamp
from embeds import WatchedEmbed, ToWatchEmbed, MoviePreviewEmbed, TVPreviewEmbed
from interactions import slash_command, Intents, SlashContext, AutocompleteContext, Client, listen, slash_option, \
    OptionType, SlashCommandChoice

load_dotenv()

WATCHED_MESSAGE_ID = 1245925656592908299
MAIN_MESSAGE_ID = 1245925657628905472
BOT_ID = os.getenv("DISCORD_BOT_ID")
logger = get_logger("DiscordBot")
bot = Client(
    intents=Intents.DEFAULT,
    send_command_tracebacks=False,
    sync_interactions=True,
    asyncio_debug=True,
    logger=logger
)


###########################################
# -------------) General (----------------#
###########################################

@listen()
async def on_ready():
    logger.info(f"MovieNights bot is ready.")
    
    
def media_type_option():
    def wrapper(func):
        return slash_option(
            name="media_type",
            description="Type",
            required=True,
            opt_type=OptionType.STRING,
            choices=[
                SlashCommandChoice(name="Movie", value='movies'),
                SlashCommandChoice(name="TV", value='tv')
            ]
        )(func)

    return wrapper


def title_option():
    def wrapper(func):
        return slash_option(
            name="title",
            description="Title",
            required=True,
            opt_type=OptionType.STRING,
            autocomplete=True
        )(func)

    return wrapper


async def update_to_watch_message(channel):
    to_watch_message = await channel.fetch_message(message_id=MAIN_MESSAGE_ID)
    await to_watch_message.edit(embed=create_to_watch_embed())


async def update_watched_message(channel):
    watched_message = await channel.fetch_message(message_id=WATCHED_MESSAGE_ID)
    await watched_message.edit(embed=create_watched_embed())


async def update_unreleased_media(media_type: str):
    unreleased_ids = db.get_unreleased_ids(media_type)

    for _id, in unreleased_ids:
        media: Movie | Show = await simkl.id_to_object(media_type, _id)
        db.update_entry(media_type, media)


###########################################
# -----------) Main Embeds (--------------#
###########################################

def create_to_watch_embed() -> interactions.Embed:
    movie_data = db.get_to_watch_data("movies")
    tv_data = db.get_to_watch_data("tv")

    e = ToWatchEmbed(movie_data, tv_data)
    embed = e.build_embed()
    return embed


def create_watched_embed() -> interactions.Embed:
    movie_data = db.get_watched_data("movies")
    tv_data = db.get_watched_data("tv")

    e = WatchedEmbed(movie_data, tv_data)
    embed = e.build_embed()
    return embed


###########################################
# -----------) Preview Embed (------------#
###########################################

def create_preview_embed(media: Movie | Show, color) -> interactions.Embed:
    if isinstance(media, Show):
        e = TVPreviewEmbed(media, color)
    else:
        e = MoviePreviewEmbed(media, color)

    embed = e.build_embed()
    return embed


###########################################
# ---------------) /add (-----------------#
###########################################

@slash_command(
    name="add",
    description="Add to the list"
)
@media_type_option()
@title_option()
async def add_function(ctx: SlashContext, media_type: str, title: int):
    await ctx.defer(ephemeral=True)

    if db.entry_exists(media_type, title):
        await ctx.send(f"# 🗍 Already on the list.", ephemeral=True)
        return

    media = await simkl.id_to_object(media_type, title)
    if not media:
        pretty_map = {
            "movies": "Movie",
            "tv": "Show"
        }

        await ctx.send(f"# 🛇 {pretty_map[media_type]} cannot be found.", ephemeral=True)
        return

    user_name: str = str(ctx.author.username)
    user_id: int = int(ctx.author_id)

    try:
        db.insert(media, user_name, user_id)
    except sqlite3.DatabaseError as e:
        logger.error(f"{type(e)=}\n{e=}")
        return

    await asyncio.gather(
        update_to_watch_message(ctx.channel),
        ctx.send(embed=create_preview_embed(media, 0x87ff00), ephemeral=True)
    )


@add_function.autocomplete("title")
async def add_autocomplete(ctx: AutocompleteContext):
    search_string = ctx.input_text
    media_type = ctx.kwargs.get("media_type", "movie")
    sanitized_search_string = re.sub('[^A-z0-9?! ]', '', search_string) if len(search_string) >= 2 else "avatar"

    if sanitized_search_string and len(sanitized_search_string) < 75:
        results = await simkl.search(media_type, sanitized_search_string.lower())
        await ctx.send(choices=results)
    else:
        await ctx.send(choices=[])


###########################################
# -------------) /watched (---------------#
###########################################

@slash_command(
    name="watched",
    description="Remove from the to watch list and add to the watch list"
)
@media_type_option()
@title_option()
async def watched_function(ctx: SlashContext, media_type: str, title: int):
    await ctx.defer(ephemeral=True)

    db.set_watched(media_type, title)
    channel = ctx.channel

    await asyncio.gather(
        update_to_watch_message(channel),
        update_watched_message(channel),
        ctx.send("# ⮃ Added to watched list.", ephemeral=True)
    )


@watched_function.autocomplete("title")
async def watched_autocomplete(ctx: AutocompleteContext):
    search_string = ctx.input_text
    media_type = ctx.kwargs.get("media_type", "movies")
    choices = db.search_to_watch_titles(media_type, search_string)

    await ctx.send(choices=choices)


###########################################
# -------------) /random (----------------#
###########################################

@slash_command(
    name="random",
    description="Select randomly from the list"
)
@media_type_option()
async def random_function(ctx: SlashContext, media_type: str):
    await ctx.defer()

    random_id = db.select_random_simkl_id(media_type)
    results = db.get_to_watch_owner_data(media_type, random_id)
    user_id, added_at = results[0]
    media = await simkl.id_to_object(media_type, random_id)
    embed = create_preview_embed(media, 0xfaff00)
    footer = [
        {
            "name": "Added By",
            "value": f"<@{user_id}> <t:{added_at}:R>",
            "inline": False
        },
        {
            "name": "ㅤ",
            "value": f"*Deleting <t:{get_current_timestamp() + 595}:R>*",
            "inline": False
        }
    ]
    embed.fields = embed.fields + footer

    await ctx.send(embed=embed, delete_after=600)


###########################################
# ---------------) /remove (--------------#
###########################################

@slash_command(
    name="remove",
    description="Remove a movie from the list that you added",
)
@media_type_option()
@title_option()
async def remove_function(ctx: SlashContext, media_type: str, title: int):
    await ctx.defer(ephemeral=True)
    channel = ctx.channel
    user_id = ctx.author_id

    db.remove_entry(media_type, title, user_id)

    await asyncio.gather(
        update_watched_message(channel),
        update_to_watch_message(channel),
        ctx.send("# Removed from list.", ephemeral=True)
    )


@remove_function.autocomplete("title")
async def remove_autocomplete(ctx: AutocompleteContext):
    media_type = ctx.kwargs.get("media_type", "movies")
    search_string = ctx.input_text
    user_id = ctx.author_id
    choices = db.get_owned_entries(media_type, search_string, user_id)

    await ctx.send(choices=choices)


###########################################
# ----------------) /info (---------------#
###########################################

@slash_command(
    name="info",
    description="Get more info on an entry in the \"To Watch\" list",
)
@media_type_option()
@title_option()
async def info_function(ctx: SlashContext, media_type: str, title: int):
    await ctx.defer(ephemeral=True)

    results = db.get_to_watch_owner_data(media_type, title)
    if results:
        user_id, added_at = results[0]
        media = await simkl.id_to_object(media_type, title)
        embed = create_preview_embed(media, 0xfaff00)
        embed.fields = (embed.fields +
                        [{"name": "ㅤ", "value": f"*Added by <@{user_id}> <t:{added_at}:R>*", "inline": False}])
        await ctx.send(embed=embed, ephemeral=True)

    else:
        await ctx.send("# Not on the \"To Watch\" list.", ephemeral=True)


@info_function.autocomplete("title")
async def info_autocomplete(ctx: AutocompleteContext):
    search_string = ctx.input_text
    media_type = ctx.kwargs.get("media_type", "movies")
    choices = db.search_to_watch_titles(media_type, search_string)

    await ctx.send(choices=choices)


###########################################
# ------) /send_initial_messages (--------#
###########################################

@slash_command(
    name="send_initial_messages",
    description="Sends initial messages",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR
)
async def send_initial_messages_function(ctx: SlashContext):
    await ctx.channel.send("ㅤ")
    await ctx.channel.send("ㅤ")
    await ctx.send("# Sent initial messages.", ephemeral=True)


###########################################
# ---------) /update_to_watch (-----------#
###########################################

@slash_command(
    name="update_to_watch",
    description="Update \"To Watch\" list",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR
)
async def update_embeds_function(ctx: SlashContext):
    await ctx.defer(ephemeral=True)
    channel = ctx.channel

    await update_unreleased_media("movies")
    await update_unreleased_media("tv")

    await asyncio.gather(
        update_watched_message(channel),
        update_to_watch_message(channel),
        ctx.send("# ↻ Updated \"To Watch\".", ephemeral=True)
    )


if __name__ == '__main__':
    bot.start(BOT_ID)
