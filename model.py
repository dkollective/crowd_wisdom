from time import sleep
import dialogs as d
from interface import SlackSession
import requests
from toolz import merge_with


def create_group_prediction(team, channel, creator, question, options):
    steps = {
        'INITIAL_GUESS': {'status': 'ACTIVE', 'user': []},
        'SELECT_PEERS': {'status': 'INACTIVE', 'user': []},
        'VIEW_INTERMEDIATE': {'status': 'INACTIVE', 'user': []},
        'REVIESE_GUESS': {'status': 'INACTIVE', 'user': []},
    }

    outcomes = [
        {
            'outcome_id': f"outcome_{i}",
            'outcome_name': o,
            'options': [{
                'value': f"{i*5}", 'text': f"{i*5} %",
            } for i in range(21)]
        }
        for i, o in enumerate(options)
    ]

    blocks = d.create_question(question, options, steps)
    sess = SlackSession.create(team, channel, creator, blocks)
    sess.store = {
        'steps': steps, 'outcomes': outcomes, 'revised_guess': {}, 'initial_guess': {}, 'peers': {},
        'question': question}

    sleep(2)
    sess.post_message('OPEN_THREAD', d.open_thread)

    sleep(1)
    blocks = d.create_admin_section('INITIAL')
    sess.post_emessage('ADMIN_MENU', blocks)

    sleep(1)
    blocks = d.create_guess_message('INITIAL_GUESS', outcomes)
    sess.post_emessage_all('INITIAL_GUESS', blocks)

    # debug


def update_question(sess):
    store = sess.store
    print(store)
    steps = store['steps']
    question = store['question']
    options = [o['outcome_name'] for o in store['outcomes']]
    blocks = d.create_question(question, options, steps)
    sess.update_message(sess.thread_ts, 'QUESTION', blocks)


def close(sess, message_ts, response_url):
    sess.delete_emassage(message_ts, response_url)

def reopen(sess):
    sess.reopen()

def action_handler(team_id, channel_id, user_id, message_ts, block_id, action_id, action, response_url=None):
    print(block_id, action_id, action)
    sess = SlackSession.get(team_id, channel_id, user_id, message_ts)
    message_name, block_name = block_id.split('#')
    if message_name == 'OPEN_THREAD':
        if action_id == 'REOPEN':
            reopen(sess)
    elif message_name == 'INITIAL_GUESS':
        if action_id == 'SUBMIT':
            initial_guess_submit_handler(sess, message_ts, response_url)
        else:
            value = int(action['selected_option']['value'])
            initial_guess_select_handler(sess, action_id, value, message_ts, response_url)
    elif message_name == 'ADMIN_MENU':
        if action_id == 'FINISH_INITAL_GUESS':
            finish_initial_guess(sess, message_ts, response_url)
        elif action_id == 'FINISH_REVISED_GUESS':
            finish_revised_guess(sess, message_ts, response_url)
    elif message_name == 'REVISED_GUESS':
        if block_name == 'SUBMIT':
            revised_guess_submit_handler(sess)
        else:
            revised_guess_select_handler(sess, action_id, value)
    elif message_name == 'PEER_SELECT':
        if block_name == 'SUBMIT':
            peer_select_submit_handler(sess, message_ts, response_url)
        else:
            value = int(action['selected_option']['value'])
            peer_select_select_handler(sess, action_id, value, message_ts, response_url)
    else:
        if action_id == 'CLOSE':
            close(sess, message_ts, response_url)


def initial_guess_submit_handler(sess, message_ts, response_url):
    user_guess = sess.get_store_value(['initial_guess', sess.user_id])
    total = sum(user_guess.values())

    if total == 100:
        sess.set_store_value(['steps', 'INITIAL_GUESS', 'user'], sess.user_id, append=True)
        sess.delete_emassage(message_ts, response_url)
        sess.post_emessage('WAIT_FIRST', d.wait_first)
        update_question(sess)
    else:
        # TODO: create some additional warning.
        pass

def add_selected(outcome_id, user_guess, option):
    if int(option['value']) == user_guess.get(outcome_id):
        return {**option, 'selected': True}
    else:
        return option


def initial_guess_select_handler(sess, action_id, value, message_ts, response_url):
    sess.set_store_value(['initial_guess', sess.user_id, action_id], value)
    user_guess = sess.get_store_value(['initial_guess', sess.user_id])
    outcomes = sess.get_store_value(['outcomes'])
    outcomes = [
        {
            **o,
            'options': [add_selected(o['outcome_id'], user_guess, oo) for oo in o['options']]
        }
        for o in outcomes
    ]
    total_guess = sum(user_guess.values())
    blocks = d.create_guess_message('INITIAL_GUESS', outcomes, total_guess)
    sess.update_emassage('INITIAL_GUESS', message_ts, response_url, blocks)


def finish_initial_guess(sess, message_ts, response_url):
    sess.delete_emassage(message_ts, response_url)

    sess.set_store_value(['steps', 'INITIAL_GUESS', 'status'], 'FINISHED')
    sess.set_store_value(['steps', 'SELECT_PEERS', 'status'], 'ACTIVE')
    sess.set_store_value(['steps', 'VIEW_INTERMEDIATE', 'status'], 'ACTIVE')
    sess.set_store_value(['steps', 'REVIESE_GUESS', 'status'], 'ACTIVE')

    participants = sess.get_store_value(['steps', 'INITIAL_GUESS', 'user'])
    sess.update_participants(participants)

    update_question(sess)
    # temporary solution
    n_peers = len(participants) // 2
    sess.set_store_value(['n_peers'], n_peers)

    for p in participants:
        blocks = d.create_peer_select_message(n_peers, [pp for pp in participants if pp != p])
        sess.post_emessage('SELECT_PEERS', blocks, user_id=p)

    blocks = d.create_admin_section('REVIESED')
    sess.post_emessage('ADMIN_MENU', blocks)


def peer_select_select_handler(sess, action_id, value, message_ts, response_url):
    sess.set_store_value(['peers', sess.user_id, action_id], value)
    # TODO: Add some kind of reaction

def peer_select_submit_handler(sess, message_ts, response_url):
    n_peers = sess.get_store_value(['n_peers'])
    selected_peers = sess.get_store_value(['peers', sess.user_id])
    if len(selected_peers) == n_peers:
        sess.set_store_value(['steps', 'SELECT_PEERS', 'user'], sess.user_id, append=True)
        sess.delete_emassage(message_ts, response_url)
        update_question(sess)

        guesses = sess.get_store_value(['initial_guess'])
        peers = sess.get_store_value(['peers', sess.user_id]).values()

        guesses_all = list(guesses.values())
        guesses_peers = [guesses[p] for p in peers]
        guesses_self = guesses[sess.user_id]

        agg_all = merge_with(lambda x: sum(x)/len(x), guesses_all)
        agg_peers = merge_with(lambda x: sum(x)/len(x), guesses_peers)

        blocks = d.create_outcome_message(
            'INITIAL_GUESS', agg_all, guess_peers=agg_peers, guess_you=guesses_self)

        sess.post_emessage('VIEW_INTERMEDIATE', blocks)

        # outcomes = sess.get_store_value(['outcomes'])
        # outcomes = [
        #     {
        #         **o,
        #         'options': [add_selected(o['outcome_id'], user_guess, oo) for oo in o['options']]
        #     }
        #     for o in outcomes
        # ]


        # blocks = d.create_guess_message('REVISED_GUESS', outcomes)
        # sess.post_emessage('REVISED_GUESS', blocks)

    else:
        # TODO: create some additional warning.
        pass






def finish_revised_guess(sess):
    pass

def update_guess_info(team, channel, gp_id, user, guess):
    pass

