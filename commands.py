import json
import os
import sys
from uuid import UUID
import random
import re
import slack
from flask import Flask, abort, jsonify, request
from mcstatus import MinecraftServer
import requests

# get configs
slackVerifyToken = os.environ['TOKEN']
slackTeamId = os.environ['TEAM_ID']
slackBotToken = os.environ['BOT_OAUTH_TOKEN']
playerDataApi = os.environ['PLAYER_DATA_API']
censoredWords = os.environ['CENSORED_WORDS']
# This is required because slack doesn't allow deleting messages with webhooks.
# The app can be otherwise modified to use postMessage, but it can't talk in
#  DMs or private channels without being invited.
slackAdminToken = os.environ['ADMIN_TOKEN']


slack_client = slack.WebClient(
    token=slackBotToken
)


def getPlayerUUID(username):
    """Return as a "long" UUID"""
    data = json.loads(
        requests.get(
            f'https://api.mojang.com/users/profiles/minecraft/{username}'
        ).text
    )
    return UUID(data['id'])


def getNick(uuid):
    try:
        res = requests.get(f'{playerDataApi}/{uuid}.json')
        nick = re.sub(censoredWords, 'null', res.json()['nickname'])
        return nick
    except:
        return None


def getFormattedOutput(reName, realName):
    """Gets the formatted output of the username, complete with nickname support
    - Places a "\u200c" character after nickname
      -  prevent slack from tagging someone by name
      - still show name without visible modification"""
    output = ""
    uuid = getPlayerUUID(realName)
    ign = '\u200c'.join(reName[i:i+1]
                        for i in range(0, len(reName), 1))
    ign = re.sub(r'[_~*]', '', ign)  # Same as above, but for usernames

    try:
        nick = getNick(uuid)
        if nick == None:  # if the Nick doesn't exist, immediately return just the username
            return f'- {ign}\n'

        # Removes _ from nicknames, which can cause potential formatting issues in slack
        nick = re.sub(r'[_~*]', '', nick)

        output = '- ' + \
            '\u200c'.join(
                nick[i:i+1] for i in range(0, len(nick), 1)) + f' ({ign})'

        if '[BOT]' in nick:
            output = f'~{output}~'

    except TypeError as e:
        output = f'- {ign}'
        print(f'ERROR: {e}')

    output += '\n'

    return output


def buildStatusMessage(config):
    """Builds the final message to send to slack
    - Header (# Players online)
    - Nicknames + IGNs of online players"""
    try:
        server = MinecraftServer.lookup(config['address'])
        status = server.status()
    except ConnectionRefusedError:
        return f"*{config['name']}:* Server is down! :scream:"

    if status.players.online == 0:
        return f"*{config['name']}:* No players online :disappointed:"

    """Fun addition - if there are 4 players online,
    there is a 20% chance that the appearing emoji will
    be :weed:. Can be disabled in config."""
    emote = ':bust_in_silhouette:'
    try:
        if status.players.online == 4 and config['weedEasterEgg'] != False:
            randomNum = random.randint(0, 4)
            if randomNum == 4:
                emote = ':weed:'
    except KeyError:
        pass

    message = (f"*{config['name']}:* " + str(status.players.online) +
               ' out of ' + str(status.players.max) + f' {emote} online:\n')

    playersList = []
    botsList = []

    for player in status.players.sample:
        name = re.sub(censoredWords, 'null', player.name)
        player = getFormattedOutput(reName=name, realName=player.name)
        if '[BOT]' in player:
            botsList.append(player)
        else:
            playersList.append(player)

    playersList = playersList.sort()
    botsList = botsList.sort()

    message = playersList + botsList

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
                    'type': 'context',
                    'elements': [
                        {
                            'type': 'mrkdwn',
                            'text': f'Requested by <@{user}>'
                        }
                    ]
                }

            ])

    # Remove divider after last section
    if len(message) > 1:
        del message[-2]

    return message


app = Flask(__name__)


def request_valid(request):  # checks for valid slack token / ID
    """Checks whether or not the request from slack is valid"""
    token_valid = request.form['token'] == slackVerifyToken
    team_id_valid = request.form['team_id'] == slackTeamId
    return token_valid and team_id_valid


def postRichChatMessage(channel, blocks, **kwargs):
    # Posts public JSON-formatted slack message
    slack_client.chat_postMessage(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        blocks=blocks,
        # Include str as fallback
        text=kwargs.get('text') or 'Message from @Steve!'
    )


def postPlainChatMessage(channel, text):
    # Posts public plaintext slack message
    slack_client.chat_postMessage(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        text=text
    )


def postEphemeralMessage(channel, text, user):
    # Posts ephemeral plaintext slack message
    slack_client.chat_postEphemeral(
        token=slackBotToken,
        channel=channel,
        as_user=True,
        text=text,
        user=user
    )


def delChatMessage(token, channel, ts):
    # Delete chat message based on ts
    slack_client.chat_delete(
        token=token,
        channel=channel,
        ts=ts
    )


def joinChannel(channel):
    # Method to add the bot to a public channel
    slack_client.conversations_join(
        token=slackBotToken,
        channel=channel
    )


@app.route('/players', methods=['POST'])  # checking for POST from slack
def players():

    # If verification fails, return 400
    if not request_valid(request):
        print('Request invalid!')
        abort(400)

    channel = request.form['channel_id']
    user = request.form['user_id']
    response_url = request.form['response_url']

    msg = buildFullMessage(channel, user)
    fallbackText = f'Message from @Steve, requested by <@{user}>'

    try:  # Attempts to post message in channel
        postRichChatMessage(
            channel=channel,
            blocks=msg,
            text=fallbackText
        )
    except:
        try:  # If it cannot post in the channel, it will attempt to join the channel
            joinChannel(
                channel=channel)
            postRichChatMessage(
                channel=channel,
                blocks=msg,
                text=fallbackText
            )
        except:  # If it cannot join the channel, it will post as a wehbook
            requests.post(
                response_url,
                headers={
                    'Content-Type': 'application/json',
                },
                json={
                    'channel': channel,
                    'blocks': msg,
                    'text': fallbackText,
                    'response_type': 'in_channel'
                }
            )
    # Returns 200 to make slack happy and avoid operation_timeout
    return ('', 200)


@app.route('/delete', methods=['POST'])
def delete():
    """Deletes messages posted by the bot"""

    # Grabs and parses payload from button
    payload = json.loads(request.form.to_dict()['payload'])

    # gets the specific text block that the UID is in
    origMessageSignature = payload['message']['blocks'][-1]['elements'][0]['text']
    # gathers the UID from there using regex
    origMessageSender = re.search(r'\<\@(.+)\>', origMessageSignature).group(1)
    # gathers the UID of the person who asked for the reload
    deleteReqSender = payload['user']['id']

    channel = payload['channel']['id']
    ts = payload['message']['ts']
    response_url = payload['response_url']

    # Only allows original message sender or me to delete message
    if deleteReqSender == origMessageSender or deleteReqSender == os.environ['DELETE_ADMIN']:
        try:
            delChatMessage(
                token=slackBotToken,
                channel=channel,
                ts=ts
            )
        except:
            requests.post(
                response_url,
                headers={
                    'Content-Type': 'application/json',
                },
                json={
                    'channel': channel,
                    'text': "Sorry, slack won't let me delete this message due to arbitrary restrictions on webhooks.\n\nTo delete messages like this in the future, invite <@UKD6P483E> to the channel.",
                    'response_type': 'ephemeral'
                }
            )
    else:
        print(
            f'Delete sender is {deleteReqSender}, orig is {origMessageSender}.')
        postEphemeralMessage(
            channel=channel,
            user=deleteReqSender,
            text=f'Sorry, you can\'t do that!'
        )

    return jsonify({
        "delete_original": True
    })


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        debug=False,
        port=8000
    )
