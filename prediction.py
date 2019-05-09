import os
from pymongo import MongoClient
from slackclient import SlackClient

mongo_host = os.environ['MONGO_HOST']
mongo_port = int(os.environ['MONGO_PORT'])
mongo_db = os.environ['MONGO_DB']

client = MongoClient(mongo_host, mongo_port)
db = client[mongo_db]

oauth = {
    "client_id": os.environ.get("CLIENT_ID"),
    "client_secret": os.environ.get("CLIENT_SECRET"),
    "scope": "bot"
}
verification = os.environ.get("VERIFICATION_TOKEN")


class Team:
    def __init__(self, team_id):
        team_data = db["authed_teams"].find_one({'team_id': team_id})
        self.client = SlackClient(team_data['bot_token'])

    def api_call(self, *args, **kwargs):
        return self.client.api_call(*args, **kwargs)

    def get_channel_member(self, channel_id):
        channel_info = self.api_call(
            "channels.info",
            channel=channel_id
        )
        return channel_info['channel']['members']

    def get_user_profile(self, user_id, fields=None):
        user_info = self.api_call(
            "users.info",
            user=user_id
        )
        profile = user_info['user']['profile']
        if fields:
            profile = {f: profile[f] for f in fields}
        return profile

    @staticmethod
    def auth(code):
        """
        Authenticate with OAuth and assign correct scopes.
        Save a dictionary of authed team information in memory on the bot
        object.

        Parameters
        ----------
        code : str
            temporary authorization code sent by Slack to be exchanged for an
            OAuth token

        """
        client = SlackClient("")
        auth_response = client.api_call(
            "oauth.access",
            client_id=oauth["client_id"],
            client_secret=oauth["client_secret"],
            code=code
        )
        team_id = auth_response["team_id"]
        bot_token = auth_response["bot"]["bot_access_token"]
        team = {
            "bot_token": bot_token,
            "team_id": team_id
        }
        db["authed_teams"].insert_one(team)
