from time import sleep
import dialogs as d
from interface import SlackSession
from settings import create_settings_dialog, settings_info
from toolz import merge_with

# actions


def action_handler(
        team_id, channel_id, user_id, message_ts, block_id, action_id, action, response_url=None,
        trigger_id=None):
    sess = SlackSession.get(team_id, channel_id, user_id, message_ts)
    block_ids = block_id.split('#')

    if block_ids[1] == 'SETTINGS':
        if action_id == 'UPDATE':
            settings_dialog_handler(sess, trigger_id, response_url)
        elif action_id == 'START':
            start_predictions_handler(sess, response_url)
    elif block_ids[1] == 'ESTIMATE':
        round_idx = int(block_ids[0])
        if action_id == 'SUBMIT':
            estimate_submit_handler(sess, round_idx, message_ts, response_url)
        else:
            entity = action_id
            value = int(action['selected_option']['value'])
            estimate_select_handler(sess, round_idx, entity, value, message_ts, response_url)
    elif block_ids[1] == 'ADMIN':
        round_idx = int(block_ids[0])
        finish_round(sess, round_idx, message_ts, response_url)
    elif block_ids[1] == 'START':
        if action_id == 'REOPEN':
            reopen(sess)
    else:
        if action_id == 'CLOSE':
            close(sess, message_ts, response_url)


# start / init

def create_group_prediction(team, channel, creator, question, entity_str):
    settings = {s['id']: s['default'] for s in settings_info}
    store = {'question': question, 'entity_str': entity_str, 'settings': settings}
    sess = SlackSession.create(team, channel, creator, store)
    blocks = d.create_settings_message(question, entity_str, settings)
    sess.post_emessage('0#SETTINGS', blocks, in_thread=False)


def settings_dialog_handler(sess, trigger_id, response_url):
    sess.set_store_value(['settings_response_url'], response_url)
    store = sess.store
    dialog = create_settings_dialog(**store['settings'])
    sess.open_dialog(trigger_id, dialog)


def init_prediction(entity_str, settings, participants, **kwargs):
    n_rounds = settings['n_rounds']
    min_val = settings['min_val']
    max_val = settings['max_val']
    step = settings['step']
    unit = settings['unit']

    rounds = [
        {
            'status': ('ACTIVE' if i == 1 else 'INACTIVE'),
            'user': [],
            'name': f'Round {i}',
            'estimates': {}
        }
        for i in range(1, n_rounds + 1)
    ]

    options = [
        {
            'value': f"{i}", 'text': f"{i} {unit}",
        }
        for i in range(min_val, max_val+step, step)
    ]

    entities = [
        {
            'entity_id': f"entity_{i}",
            'entity_name': o,
            'options': options
        }
        for i, o in enumerate(entity_str)
    ]

    store = {'entities': entities, 'rounds': rounds, 'participants': participants}
    return store


def start_predictions_handler(sess, response_url):
    participants = sess.get_channel_members()
    new_to_store = init_prediction(**{**sess.store, 'participants': participants})
    sess.set_store_values(new_to_store, append=False)
    store = sess.store
    blocks = d.create_question(store['question'], store['entities'], store['rounds'])

    sess.delete_emassage_by_name('0#SETTINGS', response_url)

    sess.post_message('0#QUESTION', blocks, in_thread=False, new_thread=True)
    sleep(2)
    sess.post_message('0#START', d.open_thread)
    sleep(2)
    start_round(sess, 1)


# round

def start_round(sess, round_idx, prev_estimates={}):
    store = sess.store
    question = store['question']
    entities = store['entities']
    participants = store['participants']
    constrained_sum = store['settings']['constrained_sum']
    unit = store['settings']['unit']

    for p in participants:
        blocks = create_estimate_message(
            question, entities, prev_estimates.get(p, {}), constrained_sum, unit, round_idx)
        sess.post_emessage(f'{round_idx}#ESTIMATE', blocks, user_id=p)


def estimate_select_handler(sess, round_idx, entity, value, message_ts, response_url):
    sess.set_store_value(['rounds', str(round_idx - 1), 'estimates', sess.user_id, entity], value)
    store = sess.store
    user_estimates = store['rounds'][round_idx - 1]['estimates'].get(sess.user_id)
    question = store['question']
    entities = store['entities']
    constrained_sum = store['settings']['constrained_sum']
    unit = store['settings']['unit']

    blocks = create_estimate_message(
        question, entities, user_estimates, constrained_sum, unit, round_idx)

    sess.update_emassage(f'{round_idx}#ESTIMATE', message_ts, response_url, blocks)


def create_estimate_message(question, entities, user_estimates, constrained_sum, unit, round_idx):
    entities = [
        {
            **e,
            'value': (
                str(user_estimates[e['entity_id']]) if e['entity_id'] in user_estimates else None
            )
        }
        for e in entities
    ]
    estimate_sum = sum(user_estimates.values())
    blocks = d.create_estimate_message(
        question, entities, estimate_sum, constrained_sum, unit, round_idx)
    return blocks


def estimate_submit_handler(sess, round_idx, message_ts, response_url):
    store = sess.store

    user_estimates = store['rounds'][round_idx - 1]['estimates'].get(sess.user_id)
    constrained_sum = store['settings']['constrained_sum']

    estimate_sum = sum(user_estimates.values())

    if (constrained_sum is None) or (constrained_sum == estimate_sum):
        sess.set_store_value(['rounds', str(round_idx - 1), 'user'], sess.user_id, append=True)
        sess.delete_emassage(message_ts, response_url)

        if (sess.user_id == sess.creator_id):
            blocks = d.create_admin_section(round_idx)
            sess.post_emessage(f'{round_idx}#ADMIN', blocks)
        else:
            sess.post_emessage(f'{round_idx}#WAIT_FIRST', d.wait_first)
        update_question(sess)
    else:
        # TODO: create some additional warning.
        pass


# general

def close(sess, message_ts, response_url):
    sess.delete_emassage(message_ts, response_url)


def reopen(sess):
    sess.reopen()


def update_question(sess, final_results=None):
    store = sess.store
    blocks = d.create_question(
        store['question'], store['entities'], store['rounds'], final_results)
    sess.update_message(sess.thread_ts, '0#QUESTION', blocks)


def show_estimates(sess, round_idx):
    store = sess.store
    estimates = store['rounds'][round_idx - 1]['estimates']
    participants = store['rounds'][round_idx - 1]['user']

    agg_estimates = merge_with(lambda x: sum(x)/len(x), estimates.values())

    name_map = {e['entity_id']: e['entity_name'] for e in store['entities']}

    agg_estimates = {name_map[k]: v for k, v in agg_estimates.items()}

    for p in participants:
        p_estimates = {name_map[k]: v for k, v in estimates[p].items()}
        data = [
            {'title': 'All', 'data': agg_estimates},
            {'title': 'You', 'data': p_estimates}
        ]
        blocks = d.create_view(round_idx, data)
        sess.post_emessage(f'{round_idx}#VIEW', blocks, user_id=p)


# finish round

def finish_round(sess, round_idx, message_ts, response_url):
    store = sess.store
    participants = store['rounds'][round_idx - 1]['user']

    final_results = None

    if len(participants) < 2:
        sess.post_emessage(f'{round_idx}#ERROR', d.min_two_user)
    else:
        sess.delete_emassage(message_ts, response_url)
        prev_estimates = store['rounds'][round_idx - 1]['estimates']
        sess.set_store_value(['rounds', str(round_idx - 1), 'status'], 'FINISHED')

        if round_idx < store['settings']['n_rounds']:
            show_estimates(sess, round_idx)
            round_idx += 1
            sess.set_store_value(['rounds', str(round_idx - 1), 'status'], 'ACTIVE')
            sess.set_store_value(['participants'], participants)

            estimates_copy = {k: {**v} for k, v in prev_estimates.items()}

            sess.set_store_value(['rounds', str(round_idx - 1), 'estimates'], estimates_copy)

            sleep(2)
            start_round(sess, round_idx, prev_estimates=estimates_copy)
        else:
            name_map = {e['entity_id']: e['entity_name'] for e in store['entities']}
            agg_estimates = merge_with(lambda x: sum(x)/len(x), prev_estimates.values())
            agg_estimates = {name_map[k]: v for k, v in agg_estimates.items()}
            final_results = [{'data': agg_estimates}]
        update_question(sess, final_results)


## dialog submission

def submission_handler(team_id, channel_id, user_id, callback_id, submission, response_url):
    sess = SlackSession.get_dialog(team_id, channel_id, user_id, callback_id)

    to_int = ['n_rounds', 'min_val', 'max_val', 'step', 'constrained_sum']
    settings = {
        k: (int(v) if (v is not None) & (k in to_int) else v)
        for k, v in submission.items()
    }
    sess.set_store_value(['settings'], settings)

    store = sess.store
    question = store['question']
    entity_str = store['entity_str']
    settings_response_url = store['settings_response_url']

    blocks = d.create_settings_message(question, entity_str, settings)
    sess.delete_emassage_by_name('0#SETTINGS', settings_response_url)
    sess.post_emessage('0#SETTINGS', blocks, in_thread=False)
