import main
import asyncio
import db_endpoints as db
from config import config

faceit_config = config(section="faceit")['faceit']
CHECK_INTERVAL = int(faceit_config['check_interval_s'])

async def tasker():
    print("Starting tasker..")
    while True:
        print("Doing tasks..")
        try:
            records = await db.get_all_player_guids()
            for record in records:
                await main.check_for_elo_change(record['player_guid'])
                await main.check_and_handle_nickname_change(record['player_guid'])
                await main.check_for_new_matches(record['player_guid'])
            print("Tasks done.")
            await asyncio.sleep(CHECK_INTERVAL)
        except:
            continue


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tasker())