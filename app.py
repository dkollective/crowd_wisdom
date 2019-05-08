# -*- coding: utf-8 -*-
import json
from threading import Thread
from time import sleep

from dialogs import create_question
# from groupprediction import GroupPrediction
from team import Team, oauth
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
    Team.auth(code_arg)
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
    action = json.loads(request.form['payload'])
    print(action)
    # callback_id = action['callback_id']
    # function_name, function_id, action_name, action_id = callback_id.split('#')
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
    team = Team(team_id)
    # thread = Thread(target=start_prediction, args=(team, channel_id))
    # thread.start()

    blocks = create_question('Which pill is he going to take', ['Blue', 'Red'])

    data = {
        "response_type": "in_channel",
        # "text": f"You started a group prediction.",
        "blocks": blocks
    }
    # print(data)

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
