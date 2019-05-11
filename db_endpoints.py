import db
import logger

log = logger.get("db")

async def insert_match(winner_team_id, best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, winner_team_score, winner_team_first_half_score, winner_team_second_half_score, winner_team_overtime_score, loser_team_score, loser_team_first_half_score, loser_team_second_half_score, loser_team_overtime_score, started_at, finished_at, status):
    await db.execute("INSERT INTO match (winner_team_id, best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, winner_team_score, winner_team_first_half_score, winner_team_second_half_score, winner_team_overtime_score, loser_team_score, loser_team_first_half_score, loser_team_second_half_score, loser_team_overtime_score, started_at, finished_at, status) "
               "SELECT $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,to_timestamp($18),to_timestamp($19), $20 WHERE NOT EXISTS (SELECT match_id FROM match WHERE match_id = $21)", winner_team_id, best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, winner_team_score, winner_team_first_half_score, winner_team_second_half_score, winner_team_overtime_score, loser_team_score, loser_team_first_half_score, loser_team_second_half_score, loser_team_overtime_score, started_at, finished_at, status, match_id)
    log.info("Inserted match  %s %s  %s  %s  %s  %s %s  %s %s  %s %s  %s %s  %s %s  %s %s %s %s %s" % (winner_team_id, best_of, competition_id, game_id, game_mode, match_id, match_round, played, map, winner_team_score, winner_team_first_half_score, winner_team_second_half_score, winner_team_overtime_score, loser_team_score, loser_team_first_half_score, loser_team_second_half_score, loser_team_overtime_score, started_at, finished_at, status))


async def insert_match_player_stats(player_guid, player_team, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, player_skill_level, win):
    await db.execute("INSERT INTO match_player_stats (player_guid, player_team, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, player_skill_level, win) "
               "SELECT $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17 WHERE NOT EXISTS (SELECT match_id FROM match_player_stats WHERE match_id = $18 AND player_guid = $19)", player_guid, player_team, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, player_skill_level, win, match_id, player_guid)
    log.info("Inserted stats %s %s  %s  %s  %s  %s %s  %s %s  %s %s  %s %s  %s %s  %s %s %s %s" % (player_guid, player_team, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, mvps, penta_kills, quadro_kills, triple_kills, match_id, win, player_skill_level,  match_id, player_guid))


async def add_history_parsed_flag(player_guid):
    await db.execute("UPDATE player SET match_history_parsed = TRUE WHERE player_guid = $1", player_guid)


async def get_player_info(player_guid):
    return await db.fetchrow("SELECT * FROM player p LEFT JOIN player_nickname pn ON (pn.player_guid = p.player_guid) WHERE p.player_guid = $1", player_guid)


async def get_all_player_guids():
    return await db.fetch("SELECT player_guid from player WHERE NOT removed")


async def get_all_available_players():
    return await db.fetch("SELECT p.id, p.player_guid, nickname, extract(epoch from added) as nickname_added FROM player p JOIN player_nickname pn ON p.player_guid = pn.player_guid WHERE NOT removed")


async def add_player_to_db(player_guid):
    await db.execute("INSERT INTO player (player_guid) VALUES ($1) ON CONFLICT (player_guid) DO UPDATE SET removed = FALSE WHERE player.player_guid = $1", player_guid)
    log.info("Player %s added" % player_guid)


async def delete_player_from_db(player_guid):
    await db.execute("UPDATE player SET removed = FALSE WHERE player_guid = $1", player_guid)
    log.info("Player %s set as removed" % player_guid)


async def get_elo_history_of_player(player_guid, limit):
    limit_string = "LIMIT {0}".format(limit) if limit else ''
    return await db.fetch("SELECT elo, eu_ranking, extract (epoch from date) as date FROM player_elo WHERE player_guid = '{0}' ORDER BY date DESC {1}".format(player_guid, limit_string))


async def get_matches_by_guid(player_guid, limit):
    limit_string = "LIMIT {0}".format(limit) if limit else ''
    return await db.fetch("SELECT mps.match_id, map, player_team_kills_rank, assists, deaths, headshots, headshots_percentage, kd_ratio, kr_ratio, kills, "
                     "mvps, penta_kills, quadro_kills, triple_kills, win, winner_team_score, loser_team_score, "
                     "extract(epoch from started_at) as started_at, extract(epoch from finished_at) as finished_at "
                     "from match_player_stats mps JOIN match m ON (m.match_id = mps.match_id) "
                     "WHERE mps.player_guid = '{0}' ORDER BY finished_at DESC {1}".format(player_guid, limit_string))


async def get_latest_match_timestamp(guid):
    return await db.fetchval("select extract(epoch from finished_at) as finished_at from match_player_stats JOIN match ON match.match_id = match_player_stats.match_id WHERE player_guid = $1 order by finished_at desc limit 1;", guid)


async def get_earliest_match_timestamp(guid):
    return await db.fetchval("select extract(epoch from started_at) as started_at from match_player_stats JOIN match ON match.match_id = match_player_stats.match_id WHERE player_guid = $1 order by started_at asc limit 1;", guid)


async def add_new_nickname(player_guid, new_nickname):
    await db.execute("INSERT INTO player_nickname (player_guid, nickname) VALUES ($1, $2)", player_guid, new_nickname)
    log.info("Added new nickname %s for player %s" % (new_nickname, player_guid))


async def get_player_last_elo(player_guid):
    return await db.fetchval("SELECT elo from player_elo WHERE player_guid = $1 ORDER BY date DESC", player_guid)


async def add_elo(player_guid, player_elo, eu_ranking):
    await db.execute("INSERT INTO player_elo (player_guid, elo, eu_ranking) VALUES ($1, $2, $3)", player_guid, player_elo, eu_ranking)
    log.info("New elo %s and ranking %s added for player %s" % (player_elo, eu_ranking, player_guid))