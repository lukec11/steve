import json
import os
import sys
from uuid import UUID
import random

import slack
from flask import Flask, abort, jsonify, request
from mcstatus import MinecraftServer
from mcuuid.api import GetPlayerData

# get configs
slackVerifyToken = os.environ['TOKEN']
slackTeamId = os.environ['TEAM_ID']
slackBotToken = os.environ['BOT_OAUTH_TOKEN']

# This only serves to raise an exception when user isn't authorized to delete


class NotAuthorized(Exception):
    pass


slack_client = slack.WebClient(
    token=slackBotToken
)


def getPlayerUUID(username):
    data = GetPlayerData(username)
    return UUID(data.uuid)


def getNickname(username):
    uuid = getPlayerUUID(username)
    try:
        with open(f'HCCore/players/{uuid}.json') as f:
            nick = json.load(f)['nickname']
            if nick == None:  # if the Nick doesn't exist, return just the username
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

    emote = ':bust_in_silhouette:'
    if status.players.online == 4:
        randomNum = random.randint(0, 4)
        if randomNum == 4:
            emote = ':weed:'

    message = (f"*{config['name']}:* " + str(status.players.online) +
               ' out of ' + str(status.players.max) + f' {emote} online:\n')

    for player in status.players.sample:
        nickname = getNickname(player.name)
        message += f"- {nickname}" + \
            (f" ({player.name})" if nickname != player.name else '') + '\n'

    return message


def buildFullMessage(channel, user):
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
                },
                {
                    "type": "actions",
                    "elements": [
                            {
                                "type": "button",
                                "text": {
                                        "type": "plain_text",
                                        "text": "Delete",
                                        "emoji": True
                                },
                                "style": "danger"
                            }
                    ]
                },
                {
                    'type': 'context',
                    'elements': [
                        {
                            'type': 'mrkdwn',
                            'text': f'Requested by <@{user}>'
                        }
                    ]
                }

            ])

    # Remove the divider after the last section
    if len(message) > 1:
        del message[-3]

    return message


app = Flask(__name__)


def request_valid(request):  # checks for valid slack token / ID
    token_valid = request.form['token'] == slackVerifyToken
    team_id_valid = request.form['team_id'] == slackTeamId
    # return token_valid and team_id_valid
    return True


def postChatMessage(channel, blocks):
    slack_client.chat_postMessage(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        blocks=blocks
    )


def postEphemeralMessage(channel, text, uid):
    slack_client.chat_postEphemeral(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        text=text,
        user=uid
    )


def delChatMessage(channel, ts):
    slack_client.chat_delete(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        ts=ts
    )


@app.route('/players', methods=['POST'])  # checking for POST from slack
def players():

    if not request_valid(request):
        print('Request invalid!')
        abort(400)

    channel = request.form['channel_id']
    user = request.form['user_id']

    msg = buildFullMessage(channel, user)
    postChatMessage(channel, msg)

    return ('', 200)


@app.route('/delete', methods=['POST'])
def delete():
    # if not request_valid(request):
    #     print('Request invalid!')
    #     abort(400)
    payload = json.loads(request.form.to_dict()['payload'])

    origMessageSender = payload['message']['user']
    deleteReqSender = payload['user']['id']

    channel = payload['channel']['id']
    ts = payload['message']['ts']

    # i know this is hacky, maybe i will fix it later
    if deleteReqSender == origMessageSender or deleteReqSender == 'UE8DH0UHM':
        delChatMessage(
            channel=channel,
            ts=ts
        )
    else:
        print(
            'Delete sender is {deleteReqSender}, orig is {origMessagesender}.')
        postEphemeralMessage(
            channel=channel,
            uid=deleteReqSender,
            text='Sorry, you can\'t do that!'
        )
        raise NotAuthorized

    return jsonify(
        delete_original=True
    )
