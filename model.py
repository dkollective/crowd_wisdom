from time import sleep
import dialogs as d
import groupprediction as gp
import team as s


def create_group_prediction(team, channel, creator, question, options):
    steps = {
        'INITIAL_GUESS': {'status': 'ACTIVE', 'user': []},
        'SELECT_PEARS': {'status': 'INACTIVE', 'user': []},
        'VIEW_INTERMEDIATE': {'status': 'INACTIVE', 'user': []},
        'REVIESE_GUESS': {'status': 'INACTIVE', 'user': []},
    }

    outcomes = [
        {
            'id': o,
            'name': o,
            'options': [{
                'value': f"{i*5}", 'text': f"{i*5} %", 'inital_user': [], 'revised_user': []
            } for i in range(21)]
        }
        for o in options
    ]

    gp_id = gp.create(team, channel, creator, question, outcomes, steps)
    blocks = d.create_question(question, outcomes, steps)
    m_ts = s.post_message(team, channel, blocks)
    gp.register_message(gp_id, creator, 'QUESTION', m_ts)

    channel_member = s.get_channel_member(team, channel)
    sleep(2)
    for user in channel_member:
        blocks = d.create_guess_message(outcomes, 'INITIAL_GUESS')
        m_ts = s.post_emessage(team, channel, user, blocks)
        gp.register_message(team, channel, gp_id, user, 'INITIAL_GUESS', m_ts)


def update_guess_info(team, channel, gp_id, user, guess):
    total = sum([o.get('value', 0) for o in guess])
    qts = gp.get_qts(team, channel, gp_id)
    messages = gp.get_messages(team, channel, gp_id, user, 'GUESS_INFO')
    for m_ts in messages:
        s.delete_message(team, channel, m_ts)
    blocks = d.create_guess_info_message(total)
    m_ts = s.post_emessage(team, channel, user, blocks, qts)
    gp.register_message(team, channel, gp_id, user, 'GUESS_INFO', m_ts)


def submit_initial_guess(team, channel, gp_id, user, guess):
    total = sum([o.get('value', 0) for o in guess])

    if total != 1:
        update_guess_info(team, channel, gp_id, user, guess)
    else:
        gp.add_user_guess(team, channel, gp_id, user, step='INITIAL_GUESS', guess=guess)
        question, outcomes, steps, mq_ts = gp.get(team, channel, gp_id)
        blocks = d.create_question(question, outcomes, steps)
        s.update_message(team, channel, mq_ts, blocks)

        messages = gp.get_messages(team, channel, gp_id, user, 'GUESS_INFO')
        for m_ts in messages:
            s.delete_message(team, channel, m_ts)

        messages = gp.get_messages(team, channel, gp_id, user, 'INITIAL_GUESS')
        for m_ts in messages:
            s.delete_message(team, channel, m_ts)


# def action_handler(gp_id, action_name, ):
    # action_name, action_id, action
