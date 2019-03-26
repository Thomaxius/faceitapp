import main
import asyncio
import db_endpoints as db
from config import config
import logger

log = logger.get("TASKER")

faceit_config = config(section="faceit")['faceit']
CHECK_INTERVAL = int(faceit_config['check_interval_s'])

async def tasker():
    log.info("Starting tasker..")
    while True:
        log.info("Doing tasks..")
        try:
            records = await db.get_all_player_guids()
            for record in records:
                await main.check_for_elo_change(record['player_guid'])
                await main.check_and_handle_nickname_change(record['player_guid'])
                await main.check_for_new_matches(record['player_guid'])
            log.info("Tasks done.")
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            log.error(e)
            pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tasker())