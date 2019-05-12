import asyncio
import datetime
import db_endpoints as db
import faceit_api
import logger
import traceback
from config import config

log = logger.get("MAIN")


faceit_config = config(section="faceit")['faceit']
API_KEY = faceit_config['api_key']
DEFAULT_HEADERS = {"accept": "application/json", "Authorization": "Bearer {0}".format(API_KEY)}
MATCH_SEARCH_RANGE = int(faceit_config['match_search_range_s'])


async def get_winner_and_loser_score(score_string): # Faceit api has score listed as "16 / 7"
    score1, score2 = score_string.replace(" ", "").split("/")
    score_list = [int(score1), int(score2)]
    return max(score_list), min(score_list)


async def get_player_rank_in_team(players_list, player_dict):
    return sorted(players_list, reverse=True, key=lambda x: int(x.get("player_stats").get("Kills"))).index(player_dict) + 1


async def get_team_data(teams_list):
    for team in teams_list:
        if team.get("team_stats").get("Team Win") == "1":
            winner_team_id = team.get("team_id")
            winner_team_first_half_score = int(team.get("team_stats").get("First Half Score"))
            winner_team_second_half_score = int(team.get("team_stats").get("Second Half Score"))
            winner_team_overtime_score = int(team.get("team_stats").get("Overtime score"))
        else:
            loser_team_id = team.get("team_id")
            loser_team_first_half_score = int(team.get("team_stats").get("First Half Score"))
            loser_team_second_half_score = int(team.get("team_stats").get("Second Half Score"))
            loser_team_overtime_score = int(team.get("team_stats").get("Overtime score"))
    return {
        "winner" : {"team_id": winner_team_id,
                    "scores":
                        {
                            "first_half": winner_team_first_half_score,
                            "second_half": winner_team_second_half_score,
                            "overtime": winner_team_overtime_score,
                            "total": winner_team_first_half_score + winner_team_second_half_score + winner_team_overtime_score,
                         },
                    },
        "loser" : {"team_id": loser_team_id,
                    "scores":
                        {
                            "first_half": loser_team_first_half_score,
                            "second_half": loser_team_second_half_score,
                            "overtime": loser_team_overtime_score,
                            "total": loser_team_first_half_score + loser_team_second_half_score + loser_team_overtime_score
                         }
                   },
            }

async def get_player_skill_level(match_id, player_guid):
    match = await faceit_api.get_match_details(match_id)
    api_version = match.get("version")
    player_skill_level = 0
    if api_version == 1:
        for faction in match.get("teams"):  # For some reason, faceit sticks player's skill level in here, and other stats in the other matches endpoint..
            for player in match.get("teams").get(faction).get("roster_v1"):
                if player.get("guid") == player_guid:
                    player_skill_level = int(player.get("csgo_skill_level", 0))
    elif api_version == 2:
        for team in [match.get("teams").get("faction1").get("roster"), match.get("teams").get("faction2").get("roster")]:  # For some reason, faceit sticks player's skill level in here, and other stats in the other matches endpoint..
            for player in team:
                if player.get("player_id") == player_guid:
                    player_skill_level = int(player.get("game_skill_level", 0))
    return player_skill_level


async def get_player_match_stats(match, player_guid): # Fetch player's stats from a specific match
    log.debug("Handling match %s" % match.get("match_id"))
    game_id = match.get("game_id")
    log.info(game_id)
    if game_id != 'csgo':
        log.info("This match is not csgo, skipping. game: %s" % game_id)
        log.debug("This match is not csgo, skipping. game id %s, match id: %s" % (game_id, match))
        return None
    match_id = match.get("match_id")
    started_at = match.get("started_at")
    finished_at = match.get("finished_at")
    status = match.get("status")
    player_skill_level = await get_player_skill_level(match_id, player_guid)
    try:
        result = await faceit_api.get_match_stats(match_id)
    except Exception as e:
        log.error('error: %s\nTraceback: %s' % (e, traceback.format_exc()))
        return None
        pass
    if result:
        best_of = int(result.get("rounds")[0].get("best_of"))
        competition_id = result.get("rounds")[0].get("competition_id")
        game_id = result.get("rounds")[0].get("game_id")
        game_mode = result.get("rounds")[0].get("game_mode")
        match_id = result.get("rounds")[0].get("match_id")
        match_round = int(result.get("rounds")[0].get("match_round"))
        played = int(result.get("rounds")[0].get("played"))
        map = result.get("rounds")[0].get("round_stats").get("Map")
        match_teams_info = await get_team_data(result.get("rounds")[0].get("teams"))
        teams = result.get("rounds")[0].get("teams") # Get the two teams that played in the game
        await db.insert_match(match_teams_info.get("winner").get("team_id"), best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, match_teams_info.get("winner").get("scores").get("total"),
                              match_teams_info.get("winner").get("scores").get("first_half"), match_teams_info.get("winner").get("scores").get("second_half"), match_teams_info.get("winner").get("scores").get("overtime"),
                              match_teams_info.get("loser").get("scores").get("total"), match_teams_info.get("loser").get("scores").get("first_half"), match_teams_info.get("loser").get("scores").get("second_half"), match_teams_info.get("loser").get("scores").get("overtime"), started_at, finished_at, status) # Add match stats
        for team in teams: # Loop through each team
            players = team.get("players")
            for player in players:
                if player.get("player_id") == player_guid: # If player is in this team
                    player_team = team.get('team_id')
                    player_team_kills_rank = await get_player_rank_in_team(players, player)
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
                    await db.insert_match_player_stats(player_guid, player_team, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, player_skill_level, win)


async def parse_matches(matches, player_guid): # Parse list of matches that is fetched from the API, get some general match info that is not in the match stats
    matches = matches.get("items")
    for match in matches:
        await get_player_match_stats(match, player_guid) # Get player's match stats
        await asyncio.sleep(0.01)



async def add_latest_matches(player_guid, timestamp): # Check and add matches since last played match, if there are any
    from_timestamp = await db.get_latest_match_timestamp(player_guid)
    from_timestamp = int(from_timestamp)
    matches = await faceit_api.get_matches(player_guid, from_timestamp=from_timestamp)
    if len(matches.get("items", [])) > 0:
        log.info("Found %s matches " % len(matches))
        await parse_matches(matches, player_guid)
    else:
        log.info("No new matches to add.")


async def add_all_matches(player_guid, timestamp):
    from_timestamp = await db.get_earliest_match_timestamp(player_guid)
    from_timestamp = int(from_timestamp)
    matches = await faceit_api.get_matches(player_guid, from_timestamp)
    if len(matches.get("items", [])) > 0:
        log.info("Found %s matches " % len(matches))
        await parse_matches(matches, player_guid)
    else:
        log.info("No new matches to add.")


async def add_past_matches(player_guid):
    last_searched_from_timestamp = None
    last_searched_to_timestamp = None
    finished = False
    while not finished:
        log.info('Searching for matches for player %s' % player_guid)
        total_found_matches = 0
        tries = 0
        to_timestamp = await db.get_earliest_match_timestamp(player_guid)
        while total_found_matches < 100: # We will start working only when we have found 100 matches
            log.info('Trying to find more matches.. (attempt %s of %s)' % (tries, 50))
            if to_timestamp:
                to_timestamp = int(to_timestamp)
            else:
                to_timestamp = int(datetime.datetime.now().timestamp()) # If player has no matches added, we will find all matches until now

            if last_searched_from_timestamp:
                from_timestamp = max((last_searched_from_timestamp - MATCH_SEARCH_RANGE), 0) # Go back the amount of time specified in the config. By default, It's two weeks
            else:
                from_timestamp = to_timestamp - MATCH_SEARCH_RANGE # Go back the amount of time specified in the config. By default, It's two weeks

            last_searched_to_timestamp = to_timestamp
            last_searched_from_timestamp = from_timestamp

            matches = await faceit_api.get_matches(player_guid, from_timestamp=from_timestamp,
                                            to_timestamp=to_timestamp) # Find matches from faceit api
            found_matches = len(matches.get("items", []))
            if found_matches > 0:
                if found_matches == total_found_matches:
                    tries += 1
                total_found_matches = found_matches
            if tries >= 50: # We will go back 2 weeks a total number of 50 times, after which we will break and add found matches
                tries = 0
                log.info("No more matches found")
                finished = True
                break
            if found_matches == 0:
                tries += 1
        await parse_matches(matches, player_guid)


async def check_and_handle_nickname_change(player_guid, api_nickname=None, db_nickname=None):
    log.info('Checking nickname changes for player %s' % player_guid)
    if not db_nickname:
        result = await db.get_player_info(player_guid)
        db_nickname = result['nickname']
    if not api_nickname:
        player = await faceit_api.get_player_stats_and_ranking(player_guid)
        api_nickname = player.nickname
    if db_nickname != api_nickname:
        log.info("Player nickname has changed, adding new nickname to db..")
        await db.add_new_nickname(player_guid, api_nickname)


async def check_for_elo_change(player_guid):
    log.info('Checking elo change for player %s' % player_guid)
    player_db_elo = await db.get_player_last_elo(player_guid)
    player = await faceit_api.get_player_stats_and_ranking(player_guid)
    if player_db_elo != player.elo:
        log.info('Player elo has changed, adding new elo..')
        await db.add_elo(player_guid, player.elo, player.eu_ranking)


async def add_player(player):
    await db.add_player_to_db(player.guid)
    await check_and_handle_nickname_change(player.guid, api_nickname=player.nickname)
    await check_for_elo_change(player.guid)


async def new_player(player_nickname="", player_guid=""):
    if not player_nickname and not player_guid:
        log.info("Error: You must specify either player nickname or player id (guid)")
        return
    if player_nickname:
        result = await faceit_api.get_player_guid_by_faceit_nick(player_nickname)  #
        player_guid = result.get('player_id')
    if not player_guid:
        log.info('Player guid could not be retrieved, check nickname.')
        return
    await faceit_api.user_by_guid(player_guid) # Check that the user exists
    player = await faceit_api.get_player_stats_and_ranking(player_guid)
    await add_player(player)


async def check_for_new_matches(player_guid):
    log.info('Checking for new matches for player %s' % player_guid)
    last_match_timestamp = await db.get_latest_match_timestamp(player_guid)
    result = await db.get_player_info(player_guid)
    log.info(result)
    if not result['match_history_parsed']:
        log.info('No matches added for player %s, checking and adding past matches..' % player_guid)
        await add_past_matches(player_guid)
        await db.add_history_parsed_flag(player_guid)
    await add_latest_matches(player_guid, last_match_timestamp)


