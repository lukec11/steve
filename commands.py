import json
import os
import sys
from uuid import UUID

import slack
from flask import Flask, abort, jsonify, request
from mcstatus import MinecraftServer
from mcuuid.api import GetPlayerData


def getPlayerUUID(username):
    data = GetPlayerData(username)
    return UUID(data.uuid)

def getNickname(username):
    uuid = getPlayerUUID(username)
    try:
        with open (f"HCCore/players/{uuid}.json") as f:
            nick = json.load(f)['nickname']
            if nick == None: #if the Nick doesn't exist, return just the username
                nick = username
    except FileNotFoundError:
        nick = username

    return nick

def buildStatusMessage(config):
    try:
        server = MinecraftServer.lookup(config['address'])
        status = server.status()
    except ConnectionRefusedError:
        return f"*{config['name']}:* Server is down! :scream:"

    if status.players.online == 0:
        return f"*{config['name']}:* No players online :disappointed:"

    message = (f"*{config['name']}:* " + str(status.players.online) + " out of " + str(status.players.max) + ":bust_in_silhouette: online:\n")

    for player in status.players.sample:
        nickname = getNickname(player.name)
        message += f"- {nickname}" + (f" ({player.name})" if nickname != player.name else "") + "\n"

    return message

def buildFullMessage():
    message = []

    with open('servers.json') as f:
        servers = json.load(f)
        for server in servers:
            message.extend([
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': buildStatusMessage(server)
                    }
                },
                {
                    'type': 'divider'
                }
            ])

    # Remove the divider after the last section
    if len(message) > 1:
        del message[-1]

    return message

app = Flask(__name__)

def request_valid(request): #checks for valid slack token / ID
    token_valid = request.form['token'] == os.environ['TOKEN']
    team_id_valid = request.form['team_id'] == os.environ['TEAM_ID']
    return token_valid and team_id_valid


@app.route('/players', methods=['POST']) #checking for POST from slack
def players():
    if not request_valid(request):
        abort(400)

    return jsonify(
        response_type='in_channel', #response in chann  el, visible to everyone
        blocks=buildFullMessage()
    )
