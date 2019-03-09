import db
import asyncio

async def create_initial_tables():
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS player 
        (
	        id serial PRIMARY KEY,
	        player_guid VARCHAR UNIQUE,
	        removed boolean default FALSE
	    );
  
        CREATE TABLE IF NOT EXISTS player_nickname
        (
	        id serial PRIMARY KEY,
	        player_guid VARCHAR REFERENCES player(player_guid) NOT NULL,
	        nickname VARCHAR,
	        added TIMESTAMPTZ default CURRENT_TIMESTAMP 
	    );	  
        CREATE TABLE IF NOT EXISTS match
        (
          id serial PRIMARY KEY,
          winner_team_id VARCHAR,
          best_of SMALLINT,
          competition_id VARCHAR,
          game_id VARCHAR,
          game_mode VARCHAR,
          match_id VARCHAR UNIQUE,
          match_round smallint,
          played smallint,
          match_type VARCHAR,
          map VARCHAR,
          winner_team_score SMALLINT,
          loser_team_score SMALLINT,
          started_at timestamptz,
          finished_at timestamptz,
          status VARCHAR
        );
        
        CREATE TABLE IF NOT EXISTS match_player_stats
        (
            id serial PRIMARY KEY,
            player_guid VARCHAR REFERENCES player(player_guid) NOT NULL,
            assists SMALLINT ,
            deaths SMALLINT,
            headshots SMALLINT,
            headshots_percentage SMALLINT,
            kd_ratio NUMERIC,
            kr_ratio NUMERIC,
            kills SMALLINT, 
            mvps SMALLINT,
            penta_kills SMALLINT,
            quadro_kills SMALLINT,
            triple_kills SMALLINT,
            win boolean,
            match_id VARCHAR not null REFERENCES match(match_id)
        );
        
        CREATE TABLE IF NOT EXISTS player_elo
        (
            id serial PRIMARY KEY,
            player_guid VARCHAR REFERENCES player(player_guid) NOT NULL,
            elo SMALLINT,
            eu_ranking INTEGER,
            date TIMESTAMPTZ default CURRENT_TIMESTAMP 
        );
        """

    )


loop = asyncio.get_event_loop()
loop.run_until_complete(
create_initial_tables())