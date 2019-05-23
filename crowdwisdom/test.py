from time import sleep
from slackclient import SlackClient
import requests

from . interface import get_bot_token


def test_create_and_delete(team_id, channel_id, user_id):
    bot_token = get_bot_token(team_id)
    return _test_create_and_delete2(bot_token, channel_id, user_id)


def _test_create_and_delete(bot_token, channel_id, user_id):
    client = SlackClient(bot_token)
    resp = client.api_call(
        "chat.postEphemeral",
        user=user_id,
        text='Hello World.',
        channel=channel_id)
    message_ts = resp['message_ts']
    sleep(1)
    resp = client.api_call(
        "chat.delete",
        channel=channel_id,
        ts=message_ts
    )
    print(resp)


def _test_create_and_delete3(bot_token, channel_id, user_id):
    client = SlackClient(bot_token)
    resp = client.api_call(
        "chat.postMessage",
        user=user_id,
        text='Hello World.',
        channel=channel_id)
    print(resp)
    message_ts = resp['ts']
    sleep(2)
    resp = client.api_call(
        "chat.delete",
        channel=channel_id,
        ts=message_ts
    )
    print(resp)



def _test_create_and_delete2(bot_token, channel_id, user_id):
    client = SlackClient(bot_token)

    message = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": 'Hello World'
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": 'Delete me',
                "emoji": True
            },
            "value": 'DELETE'
        }
    }

    resp = client.api_call(
        "chat.postEphemeral",
        user=user_id,
        blocks=[message],
        channel=channel_id)
    message_ts = resp['message_ts']
    sleep(2)
    resp = client.api_call(
        "chat.delete",
        channel=channel_id,
        ts=message_ts
    )
    print(resp)


def action_handler(action):
    response_url = action['response_url']
    print(response_url)
    data = {
        "text": "",
        "response_type": "ephemeral",
        "replace_original": True,
        "delete_original": True
    }
    print(data)
    resp = requests.post(response_url, json=data)
    # print(resp.text)
    return data
