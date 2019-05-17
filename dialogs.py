from plots import pie_lots, bar_plots

# ========== general ===========


def _create_select(placeholder, action_id, options):
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
        if o.get('selected'):
            assert not initial_option, 'Only one option can be selected.'
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


def _create_submit_fooder(step_id):
    return {
        "type": "actions",
        "elements": [_create_button('Submit', step_id + "_SUBMIT", 'SUBMIT')]
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

# ==== main message =============

def _create_step_status_section(step_id, status, user):
    if len(user) == 0:
        p_str = 'Noone responded yet'
    elif len(user) == 1:
        p_str = f'<@{user[0]}>'
    elif len(user) <= 3:
        p_str = _join_comma_andor([f'<@{p}>' for p in user])
    else:
        p_str = f'<@{user[0]}>, <@{user[1]}> and {len(user) - 2} others'

    text_templates = {
        'INITIAL_GUESS': {
            'ACTIVE': f'*1. Give a first guess.* _({p_str})_',
            'FINISHED': f'_1. Give a first guess._ _({p_str})_',
        },
        'SELECT_USER': {
            'INACTIVE': '2. Select selected.',
            'ACTIVE': '*2. Select selected.*',
            'FINISHED': '_2. Select selected._',
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
    order = ['INITIAL_GUESS', 'SELECT_USER', 'VIEW_INTERMEDIATE', 'REVIESE_GUESS']
    return [
        {
            "type": "section",
            "fields": [_create_step_status_section(so, **steps[so]) for so in order]
        }
    ]


def _create_menu_section(steps):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Follow the thread to join this group prediction."
        }
    }


def _create_question_header(question, outcomes):
    outcomes_str = _join_comma_andor([f'*{o}*'for o in outcomes], 'or')
    return [
        # _divider,
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*TeamWisdom: {question}*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{outcomes_str}? Guess the likelihood of these outcomes."
            }
        },
    ]


_question_fooder = {
    "type": "context",
    "elements": [
        {
            "type": "mrkdwn",
            "text": "Report a bug: <mailto:datakollective@gmail.com|DataKollective>"
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


def _create_guess_header(message_name):
    if message_name == 'INITIAL_GUESS':
        text = "*Make a first guess for the likelihood of the following outcomes*"
    elif message_name == 'REVISED_GUESS':
        text = "*Revise your guess for likelihood of the following outcomes*"
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


def _create_guess_section(outcome_id, outcome_name, options):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": outcome_name
        },
        "accessory": _create_select("Select outcome probability", outcome_id, options)
    }


def _create_guess_block(outcomes):
    return [_create_guess_section(**o) for o in outcomes]


def create_guess_message(message_name, outcomes, total_sum=0):
    return [
        _create_guess_header(message_name),
        _divider,
        *_create_guess_block(outcomes),
        _divider,
        *create_guess_info_message(total_sum),
        _divider,
        _create_submit_fooder(message_name)
    ]


# ------------------ guess info message

def create_guess_info_message(sum_guess):
    if sum_guess != 100:
        text = f'Procentages need to sum up to 100%. Current total: {sum_guess}%'
    else:
        text = 'Great. Procentages are adding up to 100%.'
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            },
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

def _create_select_selected_header(n_selected):
    text = f"* Select {n_selected} members you trust most. *"
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }


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
        _create_submit_fooder("SELECT_USER")
    ]


# ------------------ outcome message


def create_fig(filename):
    path = f'http://coltechtive.com/app/{filename}'
    # path = "https://api.slack.com/img/blocks/bkb_template_images/beagle.png"
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


def create_int_view(guess_all, guess_selected, guess_user):
    data = [
        {'title': 'All', 'data': guess_all},
        {'title': 'Selected', 'data': guess_selected},
        {'title': 'You', 'data': guess_user}
    ]
    filename = bar_plots(data)
    return [
        _create_text_block("*Predictions from the initial guess.*"),
        _divider,
        create_fig(filename),
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
        create_fig(filename),
        _divider,
        _close_button_block
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

def create_error_selected_selection(n_selected):
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"You have to select {n_selected} members."
            },
            "accessory": _create_button('Ok', 'ERROR_USER_CLOSE')
        }
    ]


# ------------------ open thread

open_thread = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "We encourage you to discuss the question, but not to reviel" +
            " your guesses to other user."
        }
    },
    _divider,
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "We are making intensive use of so call" +
            " private messages within the thread. These are only delivered when being" +
            " online and are lost on reloads. Use the button to resend them."
        }
    },
    {
        "type": "actions",
        "elements": [_create_button('Resend interactive messages', 'REOPEN', 'REOPEN')]
    }
]


# ------ admin

def create_admin_section(guess):
    if guess == 'INITIAL':
        button = _create_button('Finish first guess', 'FINISH_INITAL_GUESS', 'FINISH_INITAL_GUESS')
    elif guess == 'REVIESED':
        button = _create_button('Finish second guess', 'FINISH_REVISED_GUESS', 'FINISH_REVISED_GUESS')
    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Only you as the creator can finish a guessing round."
        },
        'accessory': button
    }]


# ------------------ wait

wait_first = [
    _create_text_block(
        "Wait for the creator to finish the first round.",
        accessory=_close_button
    )]

wait_second = [_create_text_block("Wait for the creator to finish the second round.")]


# ------------------ error

min_two_user = [
    _create_text_block(
        "In the first round a minimum of two participants is needed.",
        accessory=_close_button
)]
