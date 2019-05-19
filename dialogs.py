from plots import pie_lots, bar_plots
from settings import settings_info


# ========== general ===========

def _create_select(placeholder, action_id, options, value=None):
    print('value', value)
    option_objs = []
    initial_option = {}
    for o in options:
        option = {
            "text": {
                "type": "plain_text",
                "text": o['text'],
                "emoji": True
            },
            "value": o['value'],
        }
        option_objs.append(option)
        if value == o['value']:
            initial_option = {"initial_option": option}

    return {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": placeholder,
                "emoji": True
            },
            "action_id": action_id,
            "options": option_objs,
            **initial_option
    }


def _join_comma_andor(strings, andor='and'):
    return ', '.join(strings[:-1]) + f' {andor} ' + strings[-1]


_divider = {
    "type": "divider"
}


def _create_button(button_text, button_value, action_id=None):
    return {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": button_text,
            "emoji": True
        },
        "value": button_value,
        **({"action_id": action_id} if action_id else {})
    }


_close_button = _create_button('Ok', 'CLOSE', 'CLOSE')


_close_button_block = {
    "type": 'actions',
    "elements": [_close_button]
}


def _create_text_block(text, accessory=None):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        },
        **({"accessory": accessory} if accessory else {})
    }


def _create_context_block(text):
    return {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": text
            }
        ]
    }


def _create_actions_block(*actions):
    return {
        "type": "actions",
        "elements": actions
    }


def _create_fig(filename):
    path = f'http://coltechtive.com/app/{filename}'
    return {
        "type": "image",
        "title": {
            "type": "plain_text",
            "text": "results",
            "emoji": True
        },
        "image_url": path,
        "alt_text": "results"
    }


def _create_fields_block(texts):
    fields = [
        {
            "type": "mrkdwn",
            "text": text
        }
        for text in texts
    ]
    return {
        "type": "section",
        "fields": fields
    }


# ==== main message =============

def _create_round_section(status, name, user, **kwargs):
    if len(user) == 0:
        p_str = 'Noone responded yet'
    elif len(user) == 1:
        p_str = f'<@{user[0]}>'
    elif len(user) <= 3:
        p_str = _join_comma_andor([f'<@{p}>' for p in user])
    else:
        p_str = f'<@{user[0]}>, <@{user[1]}> and {len(user) - 2} others'

    if status == 'ACTIVE':
        text = f'*{name}* ({p_str})'
    elif status == 'INACTIVE':
        text = f'{name}'
    elif status == 'FINISHED':
        text = f'{name} ({p_str})'
    return text


def create_question(question, entities, rounds, final_results=None):
    question_str = f"*TeamWisdom: {question}*"

    entities_str = _join_comma_andor([f"*{o['entity_name']}*" for o in entities], 'or')

    info_str = "Follow the thread to join this group prediction."
    fooder_str = "Report a bug: <mailto:datakollective@gmail.com|DataKollective>"
    rounds_strs = [_create_round_section(**r) for r in rounds]

    if final_results is not None:
        filename = bar_plots(final_results, question)
        info_block = _create_fig(filename)
    else:
        info_block = _create_text_block(info_str)

    return [
        _create_text_block(question_str),
        _create_text_block(entities_str),
        _divider,
        _create_fields_block(rounds_strs),
        _divider,
        info_block,
        _create_context_block(fooder_str)
    ]


# ------------------ guess message

def create_estimate_message(question, entities, estimate_sum, constrained_sum, unit, round_idx):
    header_text = f'*Round {round_idx}: {question}* Make estimates'

    if constrained_sum is None:
        info_text = f'Sum: {estimate_sum} {unit}'
    else:
        if estimate_sum == constrained_sum:
            info_text = f'Great. Values are adding up to {constrained_sum} {unit}'
        else:
            info_text = f'Values need to sum up to {constrained_sum} {unit}.' + \
                f' Current sum: {estimate_sum} {unit}'

    outcome_block = [
        _create_text_block(
            e['entity_name'],
            accessory=_create_select(
                "Select outcome probability", e['entity_id'], e['options'], e.get('value')))
        for e in entities
    ]

    return [
        _create_text_block(header_text),
        _divider,
        *outcome_block,
        _divider,
        _create_text_block(info_text),
        _divider,
        _create_actions_block(_create_button('Submit', "SUBMIT", 'SUBMIT'))
    ]


# ------------------ select peer members message

def _create_select_selected_block(n_selected, participants):
    text = 'Select selected.'
    options = [{'value': p, 'text': f'<@{p}>'} for p in participants]
    return {
        "type": "actions",
        "elements": [_create_select(text, f'USER_{i}', options) for i in range(n_selected)]
    }


def create_peer_select_message(n_selected, participants):
    return [
        _create_text_block(f"*Select {n_selected} members you trust most.*"),
        _divider,
        _create_select_selected_block(n_selected, participants),
        _divider,
        _create_actions_block(_create_button('Submit', "SUBMIT", 'SUBMIT'))
    ]


# ------------------ outcome message

def create_view(round_idx, data):
    filename = bar_plots(data)
    return [
        _create_text_block(f"*Estimate of round {round_idx}.*"),
        _divider,
        _create_fig(filename),
        _divider,
        _close_button_block
    ]


def create_final_view(question, guess_all):
    data = [
        {'title': question, 'data': guess_all},
    ]
    filename = pie_lots(data)
    return [
        _create_text_block("*Predictions from the revised guess.*"),
        _divider,
        _create_fig(filename),
        _divider,
        _close_button_block
    ]


# ------------------ open thread

open_thread = [
    _create_text_block(
        "We encourage you to discuss the question, but not to reviel" +
        " your guesses to other user."),
    _divider,
    _create_text_block(
        "We are making intensive use of so call" +
        " private messages within the thread. These are only delivered when being" +
        " online and are lost on reloads. Use the button to resend them."),
    _create_actions_block(_create_button('Resend interactive messages', 'REOPEN', 'REOPEN'))
]


# ------ admin

def create_admin_section(round_idx):
    return [_create_text_block(
        "Finish the round.",
        accessory=_create_button(f'Finish round {round_idx}', 'FINISH', 'FINISH')
    )]


# ------------------ wait

wait_first = [
    _create_text_block(
        "Wait for the creator to finish the first round.",
        accessory=_close_button)
    ]

wait_second = [_create_text_block("Wait for the creator to finish the second round.")]


# ------------------ error

min_two_user = [
    _create_text_block(
        "In the first round a minimum of two participants is needed.",
        accessory=_close_button)
    ]


# ------------------------ settings

def create_settings_message(question, entities, settings):
    question_str = f"*Question:* {question}"
    entities_str = "*Options:* " + _join_comma_andor([f'*{o}*'for o in entities], 'or')

    settings_strs = [f"{s['display']}: {settings[s['id']]}" for s in settings_info]
    return [
        _create_text_block('*TeamWisdom*'),
        _divider,
        _create_text_block(question_str),
        _create_text_block(entities_str),
        _divider,
        _create_fields_block(settings_strs),
        _create_actions_block(
            _create_button('Edit Settings', 'UPDATE', 'UPDATE'),
            _create_button('Start', 'START', 'START'),
        )
    ]
