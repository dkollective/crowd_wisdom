# -*- coding: utf-8 -*-
import json
from threading import Thread

from model import create_group_prediction, action_handler, submission_handler
from interface import oauth, auth_team
from flask import Flask, request, make_response, render_template, send_from_directory

app = Flask(__name__, static_url_path='')

gds = {}


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


@app.route("/install", methods=["GET"])
def pre_install():
    """This route renders the installation page with 'Add to Slack' button."""
    # Since we've set the client ID and scope on our Bot object, we can change
    # them more easily while we're developing our app.
    client_id = oauth["client_id"]
    scope = oauth["scope"]
    # Our template is using the Jinja templating language to dynamically pass
    # our client id and scope
    return render_template("install.html", client_id=client_id, scope=scope)


@app.route("/thanks", methods=["GET", "POST"])
def thanks():
    """
    This route is called by Slack after the user installs our app. It will
    exchange the temporary authorization code Slack sends for an OAuth token
    which we'll save on the bot object to use later.
    To let the user know what's happened it will also render a thank you page.
    """
    # Let's grab that temporary authorization code Slack's sent us from
    # the request's parameters.
    code_arg = request.args.get('code')
    # The bot's auth method to handles exchanging the code for an OAuth token
    auth_team(code_arg)
    return render_template("thanks.html")


@app.route("/health", methods=["GET"])
def health():
    """
    This route is called by Slack after the user installs our app. It will
    exchange the temporary authorization code Slack sends for an OAuth token
    which we'll save on the bot object to use later.
    To let the user know what's happened it will also render a thank you page.
    """
    return render_template("health.html")


def handle_block_action(payload):
    team_id = payload['team']['id']
    user_id = payload['user']['id']
    channel_id = payload['channel']['id']
    response_url = payload['response_url']

    message_ts = payload['container']['message_ts']
    trigger_id = payload['trigger_id']
    actions = payload['actions']

    for action in actions:
        action_id = action['action_id']
        block_id = action['block_id']

        thread = Thread(
            target=action_handler, args=(
                team_id, channel_id, user_id, message_ts, block_id,
                action_id, action, response_url, trigger_id))
        thread.start()


def handle_dialog_submission(payload):
    team_id = payload['team']['id']
    channel_id = payload['channel']['id']
    user_id = payload['user']['id']
    response_url = payload['response_url']

    callback_id = payload['callback_id']
    submission = payload['submission']

    thread = Thread(
        target=submission_handler,
        args=(team_id, channel_id, user_id, callback_id, submission, response_url))
    thread.start()


@app.route("/action", methods=["POST", "GET"])
def handle_action():
    payload = json.loads(request.form['payload'])
    action_type = payload['type']
    if action_type == 'block_actions':
        handle_block_action(payload)
    elif action_type == 'dialog_submission':
        handle_dialog_submission(payload)

    return make_response('', 200)


@app.route("/decide", methods=["POST", "GET"])
def decide():
    team_id = request.form.get('team_id')
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user_id')
    text = request.form.get('text')
    text_str = text[1:-1].split('" "')

    print(text_str)
    question = text_str[0]
    options = text_str[1:]
    thread = Thread(
        target=create_group_prediction, args=(team_id, channel_id, user_id, question, options))
    thread.start()
    return ('', 200)


if __name__ == '__main__':
    app.run(debug=True)
