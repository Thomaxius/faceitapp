import requests
from config import config
import asyncio
from retrying import retry

faceit_config = config(section="faceit")['faceit']
API_KEY = faceit_config['api_key']
DEFAULT_HEADERS = {"accept": "application/json", "Authorization": "Bearer {0}".format(API_KEY)}
MATCH_SEARCH_RANGE = int(faceit_config['match_search_range_s'])


class NotFound(Exception):
    pass


class Unauthorized(Exception):
    pass


class Forbidden(Exception):
    pass


class TooManyRequests(Exception):
    pass


class UnknownError(Exception):
    pass


@retry(stop_max_attempt_number=7)
async def call_api(url):
    result = requests.get(url, headers=DEFAULT_HEADERS)
    if result.status_code not in [200, 401, 403, 429, 404]:
        raise UnknownError(result)
    elif result.status_code == 401:
        raise Unauthorized(result.json().get("error_description", "Unauthorized"))
    elif result.status_code == 403:
        raise Forbidden(result.json().get("error_description", "Forbidden request"))
    elif result.status_code == 429:
        raise Forbidden(result.json().get("error_description", "Too many requests"))
    else:
        return result



async def get_matches(player_id, from_timestamp=0, to_timestamp=None):
    if to_timestamp:
        to_timestamp_param = "&to={0}".format(to_timestamp)
    else:
        to_timestamp_param = ""
    url = """https://open.faceit.com/data/v4/players/{0}/history?game=csgo&from={1}{2}&offset=0&limit=999""".format(player_id, from_timestamp, to_timestamp_param)
    result = await call_api(url)
    if result.status_code == 200:
        return result.json()
    if result.status_code == 404:
        raise NotFound("Error: Couldn't find match.")


async def get_player_guid_by_faceit_nick(nickname):
    url = """https://open.faceit.com/data/v4/players?nickname={0}""".format(nickname)
    result = await call_api(url)
    if result.status_code == 200:
        result = result.json()
        return result
    if result.status_code == 404:
        raise NotFound("User not found")


async def get_match_stats(match_id):
    url = "https://open.faceit.com/data/v4/matches/{0}/stats".format(match_id)
    result = await call_api(url)
    if result.status_code == 200:
        return result.json()
    if result.status_code == 404:
        raise NotFound("Match not found")


async def get_ranking(player_guid, region="EU", game_id="csgo"):
    url = "https://open.faceit.com/data/v4/rankings/games/{0}/regions/{1}/players/{2}".format(game_id, region, player_guid)
    result = await call_api(url)
    if result.status_code == 200:
        return result.json().get('position', None)
    if result.status_code == 404:
        raise NotFound("Couldn't get ranking for some reason")


async def user_by_guid(player_id):
    url = "https://open.faceit.com/data/v4/players/{0}".format(player_id)
    result = await call_api(url)
    if result.status_code == 200:
        return result.json()
    if result.status_code == 404:
        raise NotFound("Couldn't find user %s" % player_id)


async def get_player_stats(player_guid):
    url = "https://open.faceit.com/data/v4/players/{0}".format(player_guid)
    result = await call_api(url)
    if result.status_code == 200:
        return result.json()
    if result.status_code == 404:
        raise NotFound("Couldn't find stats for player %s" % player_guid)


async def get_player_stats_and_ranking(player_guid):
    player_stats = await get_player_stats(player_guid)
    eu_ranking = await get_ranking(player_guid)
    try:
        elo = int(player_stats.get("games").get("csgo").get("faceit_elo"))
        skill_level = int(player_stats.get("games").get("csgo").get("skill_level"))
    except (AttributeError, TypeError):
        elo = None
        skill_level = None
    nickname = player_stats.get("nickname")
    return Player(elo, nickname, skill_level, player_guid, eu_ranking)


class Player:
    def __init__(self, elo, nickname, skill_level, guid, eu_ranking):
        self.elo = elo
        self.nickname = nickname
        self.skill_level = skill_level
        self.eu_ranking = eu_ranking
        self.guid = guid
