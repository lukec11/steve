import os
import sys
from flask import abort, Flask, jsonify, request
from mcstatus import MinecraftServer
import slack
import json
import yaml
from mcuuid.api import GetPlayerData




def getUUID(username):
    username = GetPlayerData(username)
    uuid = username.uuid
    fulluuid = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]

    return fulluuid


def parse(username):
    yamlFile = yaml.load(open("./config.yml"))
    jsondump = json.dumps(yamlFile, indent=4)
    jsonfinal = json.loads(jsondump)
    names = (jsonfinal.get("chat"))
    nickname = (names.get(getUUID(username)))
    
    final = nickname.get('nickname')
    
    return str(final)
            


def online():
    server = MinecraftServer.lookup(os.environ['SERVER'])
    server = server.status()
    if server.players.online == 0:
        return "No players online!"
    
    slackMessage = ""
    slackMessage += (str(server.players.online) + " out of " + str(server.players.max) + ":bust_in_silhouette: online:\n")
    
    for player in server.players.sample:
        slackMessage += ("- " + parse(player.name) + '  (' + player.name + ') '"\n")
        
    return slackMessage

app = Flask(__name__)

def request_valid(request):
    token_valid = request.form['token'] == os.environ['TOKEN']
    team_id_valid = request.form['team_id'] == os.environ['TEAM_ID']

    return token_valid and team_id_valid


@app.route('/players', methods=['POST'])
def players():
    if not request_valid(request):
        print('NOTVALID')
        abort(400)

    return jsonify(
        response_type='in_channel',
        text=online(),
    )

getUUID('NotACreativeName')
parse('harbar20')