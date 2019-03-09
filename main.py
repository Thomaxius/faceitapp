import asyncio
import datetime
import db_endpoints as db
import faceit_api
from config import config

faceit_config = config(section="faceit")['faceit']
API_KEY = faceit_config['api_key']
DEFAULT_HEADERS = {"accept": "application/json", "Authorization": "Bearer {0}".format(API_KEY)}
MATCH_SEARCH_RANGE = int(faceit_config['match_search_range_s'])
CHECK_INTERVAL = int(faceit_config['check_interval_s'])

async def get_winner_and_loser_score(score_string):
    score1, score2 = score_string.replace(" ", "").split("/")
    score_list = [int(score1), int(score2)]
    return max(score_list), min(score_list)


async def get_player_match_stats(match_id, player_guid, started_at, finished_at, status):
    result = await faceit_api.get_match_stats(match_id)
    if result:
        best_of = int(result.get("rounds")[0].get("best_of"))
        competition_id = result.get("rounds")[0].get("competition_id")
        game_id = result.get("rounds")[0].get("game_id")
        game_mode = result.get("rounds")[0].get("game_mode")
        match_id = result.get("rounds")[0].get("match_id")
        match_round = int(result.get("rounds")[0].get("match_round"))
        played = int(result.get("rounds")[0].get("played"))
        map = result.get("rounds")[0].get("round_stats").get("Map")
        winner_team_score, loser_team_score = await get_winner_and_loser_score(result.get("rounds")[0].get("round_stats").get("Score"))
        winner_team_id = result.get("rounds")[0].get("round_stats").get("Winner")
        teams = result.get("rounds")[0].get("teams")
        await db.insert_match(winner_team_id, best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, winner_team_score, loser_team_score, started_at, finished_at, status)
        for team in teams:
            players = team.get("players")
            for player in players:
                if player.get("player_id") == player_guid:
                    assists = int(player.get("player_stats").get("Assists"))
                    deaths = int(player.get("player_stats").get("Deaths"))
                    headshots = int(player.get("player_stats").get("Headshot"))
                    headshots_percentage = int(player.get("player_stats").get("Headshots %"))
                    kd_ratio = format(float(player.get("player_stats").get("K/D Ratio")),'.2f')
                    kr_ratio = format(float(player.get("player_stats").get("K/R Ratio")),'.2f')
                    kills = int(player.get("player_stats").get("Kills"))
                    mvps = int(player.get("player_stats").get("MVPs"))
                    penta_kills = int(player.get("player_stats").get("Penta Kills"))
                    quadro_kills = int(player.get("player_stats").get("Quadro Kills"))
                    triple_kills = int(player.get("player_stats").get("Triple Kills"))
                    win = True if int(player.get("player_stats").get("Result")) == 1 else False
                    await db.insert_match_player_stats(player_guid, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, win)


async def parse_matches(matches, player_guid):
    matches = matches.get("items")
    for match in matches:
        match_id = match.get("match_id")
        started_at = match.get("started_at")
        finished_at = match.get("finished_at")
        status = match.get("status")
        teams = match.get("teams")
        for faction in teams:
            players = teams.get(faction).get("players")
            for x in players:
                if x.get("player_id") == player_guid:
                    await get_player_match_stats(match_id, player_guid, started_at, finished_at, status)
                    await asyncio.sleep(0.1)


async def add_latest_matches(player_guid, timestamp):
    from_timestamp = await db.get_latest_match_timestamp(player_guid)
    from_timestamp = int(from_timestamp)
    matches = await faceit_api.get_matches(player_guid, from_timestamp=from_timestamp)
    if len(matches.get("items", [])) > 0:
        print("Found %s matches " % len(matches))
        await parse_matches(matches, player_guid)
    else:
        print("No new matches to add.")


async def add_all_matches(player_guid, timestamp):
    from_timestamp = await db.get_earliest_match_timestamp(player_guid)
    from_timestamp = str(from_timestamp).replace('.0', '')
    matches = await faceit_api.get_matches(player_guid, int(from_timestamp))
    if len(matches.get("items", [])) > 0:
        print("Found %s matches " % len(matches))
        await parse_matches(matches, player_guid)
    else:
        print("No new matches to add.")


async def do_initial_match_adding(player_guid):
    from_timestamp = 0
    to_timestamp = int(datetime.datetime.now().timestamp())
    last_searched_from_timestamp = int(from_timestamp)
    last_searched_to_timestamp = int(to_timestamp)
    matches = await faceit_api.get_matches(player_guid, from_timestamp=from_timestamp,
                                to_timestamp=to_timestamp)


async def add_past_matches(player_guid):
    last_searched_from_timestamp = None
    last_searched_to_timestamp = None
    finished = False
    while not finished:
        print('Searching for matches for player %s' % player_guid)
        total_found_matches = 0
        tries = 0
        to_timestamp = await db.get_earliest_match_timestamp(player_guid)
        while total_found_matches < 100:
            print('Trying to find more matches..')
            if to_timestamp:
                to_timestamp = int(to_timestamp)
            else:
                to_timestamp = int(datetime.datetime.now().timestamp())

            if last_searched_from_timestamp:
                from_timestamp = max((last_searched_from_timestamp - MATCH_SEARCH_RANGE), 0)
            else:
                from_timestamp = to_timestamp - MATCH_SEARCH_RANGE

            last_searched_to_timestamp = to_timestamp
            last_searched_from_timestamp = from_timestamp

            matches = await faceit_api.get_matches(player_guid, from_timestamp=from_timestamp,
                                            to_timestamp=to_timestamp)
            found_matches = len(matches.get("items", []))
            if found_matches > 0:
                #print("Found %s matches " % found_matches)
                if found_matches == total_found_matches:
                    tries += 1
                total_found_matches = found_matches
                #print("total found matches: ", total_found_matches)
            if tries >= 50:
                tries = 0
                print("No more matches found")
                finished = True
                break
            if found_matches == 0:
                tries += 1
        await parse_matches(matches, player_guid)


async def check_and_handle_nickname_change(player_guid, api_nickname=None, db_nickname=None):
    print('Checking nickname changes for player %s' % player_guid)
    if not db_nickname:
        result = await db.get_player_info(player_guid)
        db_nickname = result['nickname']
    if not api_nickname:
        player = await faceit_api.get_player_stats_and_ranking(player_guid)
        api_nickname = player.nickname
    if db_nickname != api_nickname:
        print("Player nickname has changed, adding new nickname to db..")
        await db.add_new_nickname(player_guid, api_nickname)


async def check_for_elo_change(player_guid):
    print('Checking elo change for player %s' % player_guid)
    player_db_elo = await db.get_player_last_elo(player_guid)
    player = await faceit_api.get_player_stats_and_ranking(player_guid)
    if player_db_elo != player.elo:
        print('Player elo has changed, adding new elo..')
        await db.add_elo(player_guid, player.elo, player.eu_ranking)


async def add_player(player):
    await db.add_player_to_db(player.guid)
    await check_and_handle_nickname_change(player.guid, api_nickname=player.nickname)
    await check_for_elo_change(player.guid)


async def new_player(player_nickname="", player_guid=""):
    if not player_nickname and not player_guid:
        print("Error: You must specify either player nickname or player id (guid)")
        return
    if player_nickname:
        result = await faceit_api.get_player_guid_by_faceit_nick(player_nickname)  #
        player_guid = result.get('player_id')
    if not player_guid:
        print('Player guid could not be retrieved, check nickname.')
        return
    await faceit_api.user_by_guid(player_guid) # Check that the user exists
    player = await faceit_api.get_player_stats_and_ranking(player_guid)
    await add_player(player)


async def check_for_new_matches(player_guid):
    print('Checking for new matches for player %s' % player_guid)
    last_match_timestamp = await db.get_latest_match_timestamp(player_guid)
    if not last_match_timestamp:
        print('No matches added for player %s, checking and adding past matches..' % player_guid)
        await add_past_matches(player_guid)
    await add_latest_matches(player_guid, last_match_timestamp)


async def tasker():
    print("Starting tasker..")
    while True:
        print("Doing tasks..")
        records = await db.get_all_player_guids()
        for record in records:
            await check_for_elo_change(record['player_guid'])
            await check_and_handle_nickname_change(record['player_guid'])
            await check_for_new_matches(record['player_guid'])
        print("Tasks done.")
        await asyncio.sleep(CHECK_INTERVAL)
