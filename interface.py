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
            thread_ts, _id, store):
        self.team_id = team_id
        self.channel_id = channel_id
        self.user_id = user_id
        self.thread_ts = thread_ts
        self.creator_id = creator_id
        self.session_id = _id
        self.si = SlackInteract(team_id, channel_id, thread_ts)

    @classmethod
    def create(cls, team_id, channel_id, user_id, store):
        # si = SlackInteract(team_id, channel_id, None)
        # channel_user = si.get_channel_members()
        gp_dict = {
            'team_id': team_id,
            'channel_id': channel_id,
            'creator_id': user_id,
            '_id': str(uuid.uuid4()),
            'store': store,
            'thread_ts': None
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

    @classmethod
    def get_dialog(cls, team_id, channel_id, user_id, callback_id):
        d_search = {
            'team_id': team_id,
            'channel_id': channel_id,
            'callback_id': callback_id
        }
        d_dict = db["dialogs"].find_one(d_search)
        gp_dict = db["group_predictions"].find_one({'_id': d_dict['session_id']})
        return cls(**gp_dict, user_id=user_id)

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

    def set_store_values(self, values, append=False):
        method = '$push' if append else '$set'
        values = {f'store.{k}': v for k, v in values.items()}
        db["group_predictions"].find_one_and_update(
            {'_id': self.session_id}, {method: values})

    def get_store_value(self, path):
        path = ['store'] + path
        path_str = '.'.join(path)
        res = db["group_predictions"].find_one(
            {'_id': self.session_id}, projection={path_str: True, '_id': False})
        return get_in(path, res)

    def register_ms(self, message_ts, message_name, user_id, blocks, mtype):
        ms_dict = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'user_id': user_id,
            'session_id': self.session_id,
            'message_ts': message_ts,
            'message_name': message_name,
            'blocks': blocks,
            'mtype': mtype,
            'active': True,
            'id': uuid.uuid4()
        }
        db["messages"].insert_one(ms_dict)

    def register_dialog(self, callback_id):
        ms_dict = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'callback_id': callback_id
        }
        db["dialogs"].insert_one(ms_dict)

    def post_message(self, message_name, blocks, in_thread=True, new_thread=False):
        assert self.user_id == self.creator_id, 'Only the creator can post messages general messages.'
        assert new_thread != in_thread

        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        message_ts = self.si.post_message(blocks, in_thread)
        self.register_ms(message_ts, message_name, self.user_id, blocks, mtype='normal')
        if new_thread:
            self.thread_ts = message_ts
            db["group_predictions"].find_one_and_update(
                {'_id': self.session_id}, {'$set': {'thread_ts': message_ts}})
            self.si = SlackInteract(self.team_id, self.channel_id, self.thread_ts)

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
            'mtype': 'ephemeral',
            'active': True
        }
        messages = db["messages"].find(ms_dict)
        for m in messages:
            db["messages"].update_many({"id": m['id']}, {'$set': {'active': False}})
            message_ts = self.si.post_emessage(m['user_id'], m['blocks'], in_thread=True)
            self.register_ms(
                message_ts, m['message_name'], m['user_id'], m['blocks'], mtype='ephemeral')

    def update_emassage(self, message_name, message_ts, response_url, blocks):
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        db["messages"].find_one_and_update(
            {'message_ts': message_ts}, {'$set': {'blocks': blocks}})
        self.si.update_emassage(blocks, response_url)

    def update_emassage_by_name(self, message_name, response_url, blocks):
        blocks = [
            {'block_id': f'{message_name}#{i}', **b} for i, b in enumerate(blocks)
        ]
        ms_search = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'session_id': self.session_id,
            'message_name': message_name
        }
        db["messages"].find_one_and_update(
            ms_search, {'$set': {'blocks': blocks}})
        self.si.update_emassage(blocks, response_url)

    def delete_emassage(self, message_ts, response_url):
        ms_search = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'session_id': self.session_id,
            'message_ts': message_ts
        }
        db["messages"].find_one_and_update(ms_search, {'$set': {'active': False}})
        self.si.delete_emassage(response_url)

    def delete_emassage_by_name(self, message_name, response_url):
        ms_search = {
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'session_id': self.session_id,
            'message_name': message_name
        }
        db["messages"].find_one_and_update(ms_search, {'$set': {'active': False}})
        self.si.delete_emassage(response_url)

    def get_channel_members(self):
        return self.si.get_channel_members()

    def open_dialog(self, trigger_id, dialog):
        callback_id = str(uuid.uuid4())
        dialog = {'callback_id': callback_id, **dialog}
        self.si.open_dialog(trigger_id, dialog)
        self.register_dialog(callback_id)


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
        print(blocks, resp)
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
            "replace_original": True,
            # "delete_original": True
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

    def get_channel_members(self):
        channel_info = self.client.api_call(
            "channels.info",
            channel=self.channel_id
        )
        print(channel_info)
        return channel_info['channel']['members']

    def open_dialog(self, trigger_id, dialog):
        resp = self.client.api_call(
            "dialog.open",
            dialog=dialog,
            trigger_id=trigger_id
        )
        print(resp)
