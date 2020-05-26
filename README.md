# slack-commands


Uses the [mcstatus](https://github.com/Dinnerbone/mcstatus) API to get online Minecrafters, 
as well as the [HCCore](https://github.com/hackclub/hccore) plugin to get their real names.

This app is in use on [Hack Club](https://hackclub.com/community)'s [Minecraft Server](https://mc.hackclub.com).

## Slack

### Slash Commands

`/players` will point to `https://your-app/players`

### Interactivity

The interactive "Request URL" should point to `https://your-app/delete`

### OAuth Scopes

The bot will also require either the older "bot" oauth scope, or the following new permissions:

* chat:write
* chat:write.customize
* commands
* channels:join

## Environment

The app will require several modifications to get running. 

### Setting Servers

The `servers.json` file can be used to set which servers the bot will show activity for.
There is a usage example in `servers.json.template`.

### Environment Variables

`TOKEN` is your Slack App's verification token - this is how it knows the requests are actually coming from slack.

`TEAM_ID` is the ID of your slack workspace, starting with `T`. 

`BOT_OAUTH_TOKEN` is your app's Bot Token, beginning with `xoxb-`. 

`FLASK_ENV` is the environment flask is serving in - probably set to `production`.

`PLAYER_DATA_API` is where the app is polling for nicknames.

`CENSORED_WORDS` contains a regex string of things that you might want censored from appearing in slack - for example, this could help if someone set their nickname to something unsavory.

 ### Defaults

 The app defaults to running on port `8080`, on the IP `0.0.0.0`. 