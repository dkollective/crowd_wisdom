

# ========== general ===========


def _create_select(text, options):
    option_objs = [
        {
            "text": {
                "type": "plain_text",
                "text": o['text'],
                "emoji": True
            },
            "value": o['value'],
        }
        for o in options
    ]
    return {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": text,
                "emoji": True
            },
            "options": option_objs
    }


def _join_comma_andor(strings, andor='and'):
    return ', '.join(strings[:-1]) + f' {andor} ' + strings[-1]


_divider = {
    "type": "divider"
}


def _create_button(button_text, button_value):
    return {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": button_text,
            "emoji": True
        },
        "value": button_value
    }


def _create_submit_fooder(step_id):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ""
        },
        'accessory': _create_button('Submit', step_id + "_SUBMIT")
    }


# ==== main message =============

def _create_step_status_section(step_id, status, user):
    if len(user) == 0:
        p_str = 'Noone responded yet'
    elif len(user) < 5:
        p_str = _join_comma_andor([f'<@{p}>' for p in user]) + " responded"
    else:
        p_str = f'<@{user[0]}>, <@{user[1]}> and {len(user) - 2} others responded'

    text_templates = {
        'INITIAL_GUESS': {
            'ACTIVE': f'*1. Give a first guess.* _({p_str})_',
            'FINISHED': f'_1. Give a first guess._ _({p_str})_',
        },
        'SELECT_PEARS': {
            'INACTIVE': '2. Select peers.',
            'ACTIVE': '*2. Select peers.*',
            'FINISHED': '_2. Select peers._',
        },
        'VIEW_INTERMEDIATE': {
            'INACTIVE': '3. View intermediate results.',
            'ACTIVE': '*3. View intermediate results.*',
            'FINISHED': '_3. View intermediate results._',
        },
        'REVIESE_GUESS': {
            'INACTIVE': '4. Give a second guess.',
            'ACTIVE': f'*4. Give a second guess.* _({p_str})_',
            'FINISHED': f'_4. Give a second guess._ _({p_str})_',
        },
    }
    text = text_templates[step_id][status]

    return {
            "type": "mrkdwn",
            "text": text
    }


def _create_status_block(steps):
    order = ['INITIAL_GUESS', 'SELECT_PEARS', 'VIEW_INTERMEDIATE', 'REVIESE_GUESS']
    return [
        {
            "type": "section",
            "fields": [_create_step_status_section(so, **steps[so]) for so in order]
        }
    ]


def _create_menu_section(steps):
    actions = [_create_button('Resend menu to thread', 'REOPEN')]
    if steps["INITIAL_GUESS"]["status"] == 'ACTIVE':
        actions.append(_create_button('Creator: Finish round', 'FINISH_INITAL_GUESS'))
    elif steps["REVIESE_GUESS"]["status"] == 'ACTIVE':
        actions.append(_create_button('Creator: Finish round', 'FINISH_REVIESE_GUESS'))
    return {
        "type": "actions",
        "elements": actions,
    }


def _create_question_header(question, outcomes):
    outcomes_str = _join_comma_andor([f'*{o}*'for o in outcomes], 'or')
    return [
        # _divider,
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{question}*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{outcomes_str}? Follow the thread to take part."
            }
        },
    ]


_question_fooder = {
    "type": "context",
    "elements": [
        {
            "type": "mrkdwn",
            "text": "Report a bug: <mailto:bob@example.com|Email Bob Roberts>"
        }
    ]
}


def create_question(question, outcomes, steps):
    return [
        *_create_question_header(question, outcomes),
        _divider,
        *_create_status_block(steps),
        _divider,
        _create_menu_section(steps),
        # _divider,
        _question_fooder
    ]

# ------------------ guess message


def _create_guess_header(step_id):
    if step_id == 'INITIAL_GUESS':
        text = "* Make a first guess for the likelihood of the following outcomes *"
    elif step_id == 'REVISE_GUESS':
        text = "* Revise your guess for likelihood of the following outcomes *"
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


def _create_guess_section(outcome):
    choices = [{'value': f"{i*5}", 'text': f"{i*5} %"} for i in range(21)]

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": outcome
        },
        "accessory": _create_select("Select outcome probability", choices)
    }


def _create_guess_block(outcomes):
    return [_create_guess_section(o) for o in outcomes]


def create_guess_message(outcomes, step_id):
    return [
        _create_guess_header(step_id),
        _divider,
        *_create_guess_block(outcomes),
        _divider,
        _create_submit_fooder(step_id)
    ]


# ------------------ guess info message

def create_guess_info_message(sum_guess):
    if sum_guess != 1:
        text = 'Procentages need to sum up to 100%. Current total: "{0.0%}"'.format(sum_guess)
    else:
        text = 'Great. Procentages are adding up to 100%.'
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            },
            "accessory": _create_button('Ok', 'GUESS_INFO_CLOSE')
        }
    ]


# ------------------ info creator button

error_creator_only = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Only the creator can finish a round."
        },
        "accessory": _create_button('Ok', 'ERROR_CREATOR_ONLY_CLOSE')
    }
]


# ------------------ select peer members message

def _create_select_peers_header(n_peers):
    text = f"* Select {n_peers} members you trust most. *"
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


def _create_select_peers_block(n_peers, participants):
    text = 'Select trusted members.'
    return {
        "type": "actions",
        "elements": [create_select(text, participants) for i in range(n_peers)]
    }


def create_peer_select_message(n_peers, participants):
    return [
        _create_select_peers_header(n_peers),
        _divider,
        _create_select_peers_block(n_peers, participants),
        _divider,
        _create_submit_fooder("SELECT_PEARS")
    ]


# ------------------ outcome message


def _create_outcome_header(step_id):
    if step_id == 'INITIAL_GUESS':
        text = "* Prediction from the initial guess. *"
    elif step_id == 'REVISE_GUESS':
        text = "* Prediction from the revised guess. *"
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


def _create_debug_outcome_string(d):
    return ','.join(["{}: {:0%}".format(k, v) for k, v in d])


# intermediate solution
def _create_outcome_info(guess_all, guess_peers=None, guess_you=None):
    text = 'all: ' + _create_debug_outcome_string(guess_all)
    if guess_peers:
        text += '\npeers: ' + _create_debug_outcome_string(guess_peers)
    if guess_you:
        text += '\nyou: ' + _create_debug_outcome_string(guess_you)
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


def create_outcome_message(step_id, guess_all, guess_peers=None, guess_you=None):
    return [
        _create_outcome_header(step_id),
        _divider,
        _create_outcome_info(guess_all, guess_peers, guess_you)
    ]


# ------------------ info revise

info_revise_now = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "You can now revise your guess."
        },
        "accessory": _create_button('Ok', 'REVISE_NOW_CLOSE')
    }
]


# ------------------ error same peer member selection

def create_error_peers_selection(n_peers):
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"You have to select {n_peers} members."
            },
            "accessory": _create_button('Ok', 'ERROR_PEERS_CLOSE')
        }
    ]
