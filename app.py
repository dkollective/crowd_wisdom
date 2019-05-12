# -*- coding: utf-8 -*-
import json
from threading import Thread
from time import sleep

from model import create_group_prediction, action_handler
# from dialogs import create_question, create_guess_info_message
# import team as s
# from groupprediction import GroupPrediction
# from test import test_create_and_delete, action_handler
from interface import oauth, auth_team
from flask import Flask, request, make_response, render_template, jsonify

app = Flask(__name__)

gds = {}


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


@app.route("/action", methods=["POST", "GET"])
def handle_action():
    # todo: authorize

    payload = json.loads(request.form['payload'])

    # resp = action_handler(payload)
    # print(resp)
    # return jsonify(resp)

    team_id = payload['team']['id']
    user_id = payload['user']['id']
    message_ts = payload['container']['message_ts']
    channel_id = payload['channel']['id']
    response_url = payload['response_url']
    # trigger_id = payload['trigger_id']

    actions = payload['actions']

    for action in actions:
        action_id = action['action_id']
        block_id = action['block_id']
        action_handler(team_id, channel_id, user_id, message_ts, block_id, action_id, action, response_url)

    # if function_name == 'GD':
    #     thread = Thread(
    #         target=gds[function_id].action, args=(action_name, action_id, action))
    #     thread.start()
    return make_response('', 200)


# def start_prediction(team, channel):
#     sleep(0)
#     global gds
#     # gd = GroupPrediction(team=team, channel=channel)
#     gds[gd.id] = gd


@app.route("/decide", methods=["POST", "GET"])
def decide():
    team_id = request.form.get('team_id')
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user_id')
    # team = Team(team_id)
    # thread = Thread(target=start_prediction, args=(team, channel_id))
    # thread.start()
    question = 'Which pill is he going to take?'
    options = ['Blue', 'Red']

    # test_create_and_delete(team_id, channel_id, user_id)

    create_group_prediction(team_id, channel_id, user_id, question, options)

    # steps = {
    #     'INITIAL_GUESS': {'status': 'ACTIVE', 'user': []},
    #     'SELECT_PEARS': {'status': 'INACTIVE', 'user': []},
    #     'VIEW_INTERMEDIATE': {'status': 'INACTIVE', 'user': []},
    #     'REVIESE_GUESS': {'status': 'INACTIVE', 'user': []},
    # }

    # outcomes = [
    #     {
    #         'id': o,
    #         'name': o,
    #         'options': [{
    #             'value': f"{i*5}", 'text': f"{i*5} %", 'inital_user': [], 'revised_user': []
    #         } for i in range(21)]
    #     }
    #     for o in options
    # ]

    # blocks = create_question('Which pill is he going to take?', ['Blue', 'Red'], steps)

    # data = {
    #     # "response_type": "in_channel",
    #     # "text": f"You started a group prediction.",
    #     # "blocks": blocks
    # }
    # print(data)

    return ('', 200)


if __name__ == '__main__':
    app.run(debug=True)
