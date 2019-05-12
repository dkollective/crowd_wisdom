import os

import uuid
import requests
from toolz import get_in
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


def auth_team(code):
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


class SlackSession:
    def __init__(
            self, team_id, channel_id, user_id, creator_id,
            thread_ts, _id, store, participants):
        self.team_id = team_id
        self.channel_id = channel_id
        self.user_id = user_id
        self.thread_ts = thread_ts
        self.creator_id = creator_id
        self.session_id = _id
        self.participants = participants
        # self.store = store
        self.si = SlackInteract(team_id, channel_id, thread_ts)

    @classmethod
    def create(cls, team_id, channel_id, user_id, blocks):
        si = SlackInteract(team_id, channel_id, None)
        thread_ts = si.post_message(blocks)
        channel_user = si.get_channel_members()
        gp_dict = {
            'team_id': team_id,
            'channel_id': channel_id,
            'creator_id': user_id,
            # 'user_id': user_id,
            '_id': str(uuid.uuid4()),
            'thread_ts': thread_ts,
            'participants': channel_user,
            'store': None
        }
        db["group_predictions"].insert_one(gp_dict)
        return cls(**gp_dict, user_id=user_id)

    @classmethod
    def get(cls, team_id, channel_id, user_id, message_ts):
        ms_search = {
            'team_id': team_id,
            'channel_id': channel_id,
            'message_ts': message_ts
        }
        ms_dict = db["messages"].find_one(ms_search)
        gp_dict = db["group_predictions"].find_one({'_id': ms_dict['session_id']})
        return cls(**gp_dict, user_id=user_id)

    # def add_thread_ts(self, thread_ts):
    #     db["group_predictions"].find_one_and_update(
    #         {'session_id': self.session_id}, {"$set": {'thread_ts': thread_ts}})
    #     self.thread_ts = thread_ts
    #     self.slack_interact = SlackInteract(
    #         self.team_id, self.channel_id, self.user_id, self.thread_ts)

    @property
    def store(self):
        return db["group_predictions"].find_one({'_id': self.session_id})['store']

    @store.setter
    def store(self, store):
        db["group_predictions"].find_one_and_update(
            {'_id': self.session_id}, {'$set': {'store': store}})

    def set_store_value(self, path, value, append=False):
        method = '$push' if append else '$set'
        path_str = '.'.join(['store'] + path)
        db["group_predictions"].find_one_and_update(
            {'_id': self.session_id}, {method: {path_str: value}})

    def get_store_value(self, path):
        path = ['store'] + path
        path_str = '.'.join(path)
        res = db["group_predictions"].find_one(
            {'_id': self.session_id}, projection={path_str: True, '_id': False})
        return get_in(path, res)

    def update_participants(self, participants):
        self.participants = participants
        db["group_predictions"].find_one_and_update(
            {'_id': self.session_id}, {'$set': {'participants': participants}})

    def register_ms(self, message_ts, message_name, user_id, blocks, mtype):
        ms_dict = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'user_id': user_id,
            'session_id': self.session_id,
            'thread_ts': self.thread_ts,
            'message_ts': message_ts,
            'message_name': message_name,
            'blocks': blocks,
            'mtype': mtype
        }
        db["messages"].insert_one(ms_dict)

    def post_message(self, message_name, blocks, in_thread=True):
        assert self.user_id == self.creator_id, 'Only the creator can post messages general messages.'
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        message_ts = self.si.post_message(blocks, in_thread)
        self.register_ms(message_ts, message_name, self.user_id, blocks, mtype='normal')

    def post_emessage(self, message_name, blocks, in_thread=True, user_id=None):
        if not user_id:
            user_id = self.user_id
        else:
            assert self.user_id == self.creator_id, 'Only the creator can post messages to other user.'
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        message_ts = self.si.post_emessage(user_id, blocks, in_thread)
        self.register_ms(message_ts, message_name, user_id, blocks, mtype='ephemeral')

    def post_emessage_all(self, message_name, blocks, in_thread=True):
        assert self.user_id == self.creator_id, 'Only the creator can post messages to other user.'
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        for user_id in self.participants:
            message_ts = self.si.post_emessage(user_id, blocks, in_thread)
            self.register_ms(message_ts, message_name, user_id, blocks, mtype='ephemeral')

    def update_message(self, message_ts, message_name, blocks):
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        db["messages"].find_one_and_update(
            {'message_ts': message_ts}, {'$set': {'blocks': blocks}})
        self.si.update_message(message_ts, blocks)

    def reopen(self):
        ms_dict = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'mtype': 'ephemeral'
        }
        messages = db["messages"].find(ms_dict)
        for m in messages:
            # TODO: bookkeeping of in_thread
            message_ts = self.si.post_emessage(m['user_id'], m['blocks'], in_thread=True)
            # TODO: bookkeeping of reopened messages

    # def delete_messages(self, message_name):
    #     ms_search = {
    #         'team_id': self.team_id,
    #         'channel_id': self.channel_id,
    #         'session_id': self.session_id,
    #         'user_id': self.user_id,
    #         'message_name': message_name
    #     }
    #     ms_list = db["messages"].find(ms_search)
    #     for m in ms_list:
    #         print(m['message_ts'])
    #         self.si.delete_message(m['message_ts'], m['user_id'])

    # def delete_messages_all(self, message_name):
    #     assert self.user_id == self.creator_id, 'Only the creator can delete messages of other user.'
    #     ms_search = {
    #         'team_id': self.team_id,
    #         'channel_id': self.channel_id,
    #         'session_id': self.session_id,
    #         'message_name': message_name
    #     }
    #     ms_list = db["messages"].find(ms_search)
    #     for m in ms_list:
    #         self.si.delete_message(m['message_ts'])

    def update_emassage(self, message_name, message_ts, response_url, blocks):
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        db["messages"].find_one_and_update(
            {'message_ts': message_ts}, {'$set': {'blocks': blocks}})
        self.si.update_emassage(blocks, response_url)

    def delete_emassage(self, message_ts, response_url):
        ms_search = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'session_id': self.session_id,
            'message_ts': message_ts
        }
        db["messages"].find_one_and_update(ms_search, {'$set': {'deleted': True}})
        self.si.delete_emassage(response_url)

    def get_channel_members(self):
        return self.si.get_channel_members()


def get_bot_token(team_id):
    return db["authed_teams"].find_one({'team_id': team_id})['bot_token']


class SlackInteract:
    def __init__(self, team_id, channel_id, thread_ts):
        self.client = SlackClient(get_bot_token(team_id))
        self.channel_id = channel_id
        self.thread_ts = thread_ts

    def post_message(self, blocks, in_thread=False):
        resp = self.client.api_call(
            "chat.postMessage",
            blocks=blocks,
            channel=self.channel_id,
            **({'thread_ts': self.thread_ts} if in_thread else {})
        )
        return resp['ts']

    def post_emessage(self, user, blocks, in_thread=False):
        resp = self.client.api_call(
            "chat.postEphemeral",
            user=user,
            blocks=blocks,
            channel=self.channel_id,
            **({'thread_ts': self.thread_ts} if in_thread else {})
        )
        print(resp)
        return resp['message_ts']

    def update_message(self, message_ts, blocks):
        self.client.api_call(
            "chat.update",
            blocks=blocks,
            channel=self.channel_id,
            ts=message_ts
        )

    def update_emassage(self, blocks, response_url):
        data = {
            "blocks": blocks,
            "thread_ts": self.thread_ts,
            "response_type": "ephemeral",
            "replace_original": True
        }
        resp = requests.post(response_url, json=data)

    def delete_emassage(self, response_url):
        data = {
            "response_type": "ephemeral",
            "replace_original": True,
            "delete_original": True
        }
        resp = requests.post(response_url, json=data)

    def delete_message(self, message_ts, user_id):
        resp = self.client.api_call(
            "chat.delete",
            channel=self.channel_id,
            ts=message_ts,
            user=user_id
        )
        print(resp)

    def get_channel_members(self):
        channel_info = self.client.api_call(
            "channels.info",
            channel=self.channel_id
        )
        return channel_info['channel']['members']

    # def get_user_profile(self, user_id, fields=None):
    #     user_info = self.client.api_call(
    #         "users.info",
    #         user=user_id
    #     )
    #     profile = user_info['user']['profile']
    #     if fields:
    #         profile = {f: profile[f] for f in fields}
    #     return profile


