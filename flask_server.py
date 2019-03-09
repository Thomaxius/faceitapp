from flask import Flask, request
from config import config
from flask_cors import CORS
import db_endpoints as db
import asyncio
import simplejson
import re
import main

flask_config = config(section="flask")['flask']
FLASK_PORT = flask_config['port']
FLASK_HOSTNAME = flask_config['server_host']
MAIN_ENDPOINT = flask_config['main_endpoint']
AVAILABLE_PLAYERS_ENDPOINT = flask_config['available_players_endpoint']
MATCHES_ENDPOINT = flask_config['matches_endpoint']
GET_ELO_ENDPOINT = flask_config['get_elo_endpoint']
ADD_PLAYER_ENDPOINT = flask_config['add_player_endpoint']

app = Flask(__name__)
CORS(app)
loop = asyncio.get_event_loop()


def build_json(records_list):
    json = []
    for record in records_list:
        json.append(dict(record))
    return json


def is_valid_guid(guid):
    return re.match('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',guid)


def is_valid_limit(limit_param):
    try:
        return int(limit_param) > 0
    except ValueError:
        return False


@app.route(MAIN_ENDPOINT + AVAILABLE_PLAYERS_ENDPOINT)
def get_available_players():
    jsonList = build_json(loop.run_until_complete(db.get_all_available_players()))
    return simplejson.dumps(jsonList)


@app.route(MAIN_ENDPOINT + MATCHES_ENDPOINT)
def get_all_matches_by_guid():
    guid = request.args.get('guid')
    limit = request.args.get('limit')
    if is_valid_guid(guid):
        if limit and is_valid_limit(limit):
            limit = int(limit)
        else:
            limit = None
        records = loop.run_until_complete(db.get_matches_by_guid(guid, limit))
        records_as_json = build_json(records)
        return simplejson.dumps(records_as_json)
    else:
        return "Error: GUID is not in a valid format."


@app.route(MAIN_ENDPOINT + GET_ELO_ENDPOINT)
def get_elo_of_player():
    guid = request.args.get('guid')
    limit = request.args.get('limit')
    if is_valid_guid(guid):
        if limit and is_valid_limit(limit):
            limit = int(limit)
        else:
            limit = None
        records = loop.run_until_complete(db.get_elo_history_of_player(guid, limit))
        records_as_json = build_json(records)
        return simplejson.dumps(records_as_json)
    else:
        return "Error: GUID is not in a valid format."


@app.route(MAIN_ENDPOINT + ADD_PLAYER_ENDPOINT)
def add_player():
    guid = request.args.get('guid')
    nickname = request.args.get('nickname')
    if not guid and not nickname:
        return "You must supply either a nickname or a faceit guid."
    if guid:
        if is_valid_guid(guid):
            try:
                loop.run_until_complete(main.new_player(player_guid=guid))
                return "User %s added succesfully." % guid
            except Exception as e:
                return "Error: %s" % e
        else:
            return "Error: GUID is not in a valid format."
    if nickname:
        try:
            loop.run_until_complete(main.new_player(player_nickname=nickname))
            return "User %s added succesfully." % nickname
        except Exception as e:
            return "Error: %s" % e


if __name__ == "__main__":
    app.run(host=FLASK_HOSTNAME,port=FLASK_PORT)