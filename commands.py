import os
from flask import abort, Flask, jsonify, request
from mcstatus import MinecraftServer
import slack
import json

#imports the projects json file
with open("projects.json") as f:
    projectsFile = json.load(f)
    projectsList = projectsFile["projects"]

def online():
    server = MinecraftServer.lookup("--SERVER IP HERE--")
    server = server.status()
    if server.players.online == 0:
        return "No players online!"
    
    slackMessage = ""
    slackMessage += (str(server.players.online) + " out of " + str(server.players.max) + ":bust_in_silhouette: online:\n")
    
    for player in server.players.sample:
        slackMessage += ("- " + player.name + "\n")
        
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

@app.route('/projects', methods=['POST', 'GET'])
def projects():
    if not request_valid(request):
        print('NOTVALID')
        abort(400)
    
    text = request.args.get("text")

    if not text:
        return jsonify(
            response_type = 'in_channel',
            text = projectsList
        )
    elif "add" in text:
        projectsList.append(text[3:])
        with open("projects.json", "w") as f2:
            json.dump({"projects":projectsList}, f2)

        return jsonify(
            response_type = "in_channel",
            text = "Added!"
        )
