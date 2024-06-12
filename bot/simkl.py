import json
import os

import aiohttp
import pydantic
from log import get_logger
from dotenv import load_dotenv
from cachetools import TTLCache
from validation import Movie, Show

load_dotenv()

API_URL = "https://api.simkl.com"
CLIENT_ID = os.getenv("SIMKL_CLIENT_ID")
cache = TTLCache(maxsize=100, ttl=300)
logger = get_logger("Simkl")


def log_media(media: Movie | Show):
    json_data = json.dumps(media.model_dump(), indent=4, default=str)
    logger.info(f"Getting {media.title}\n{json_data}")


async def fetch(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error occurred: {e}")
        return {}


async def api_request(endpoint: str):
    url = API_URL + endpoint
    async with aiohttp.ClientSession() as session:
        return await fetch(session, url)


async def search(media_type: str, search_string: str) -> list[dict[str, str]]:
    _media_type = media_type.replace("s", "") if media_type in ["movies", "tv"] else "movie"
    search_id = f'{search_string.replace(" ", "_")}_{_media_type}'

    if search_id in cache:
        logger.info(f"Cache hit for: {search_id}")
        return cache[search_id]

    logger.info(f"Searching Simkl for: {search_string}")
    results = await api_request(f'/search/{_media_type}?&q={search_string}&client_id={CLIENT_ID}')
    autocomplete = [
        {
            "name": f'{result["title"] if len(result["title"]) <= 75 else (result["title"][:72] + "...")} '
                    f'({result.get("year", 0)})',
            "value": result["ids"]["simkl_id"]
        }
        for result in results
        if result.get("year", 0)
    ]

    cache[search_id] = autocomplete
    return autocomplete


async def id_to_object(media_type: str, simkl_id: int) -> Movie | Show | None:
    data = await api_request(f'/{media_type}/{simkl_id}?extended=full&client_id={CLIENT_ID}')

    try:
        if media_type == "tv":
            media = Show.model_validate(data)
        else:
            media = Movie.model_validate(data)

        log_media(media)
        return media

    except pydantic.ValidationError as e:
        logger.error(f"{type(e)=}\n{e=}")
        return


if __name__ == '__main__':
    pass
