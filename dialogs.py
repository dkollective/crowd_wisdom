

# ========== general ===========


def create_select(text, options):
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


def join_comma_and(strings):
    return ', '.join(strings[:-1]) + ' and ' + strings[-1]


divider = {
    "type": "divider"
}


def create_button(button_text, button_value):
    return {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": button_text,
            "emoji": True
        },
        "value": button_value
    }


def create_submit_fooder(step_id) = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": ""
    },
    'accessory' create_button('Submit', step_id + "_SUBMIT")
}



# ==== main message =============


def create_step_status_section(step_id, status, participants):
    if len(participants) == 0:
        p_str = 'Noone'
    elif len(participants) < 5:
        p_str = join_comma_and([f'<@{p}>' for p in participants])
    else:
        p_str = f'<@{participants[0]}>, <@{participants[1]}> and {len(participants) - 2} others'

    text_templates = {
        'INITIAL_GUESS': {
            'ACTIVE': f'* {p_str} gave a first guess. *',
            'FINISHED': f'_ {p_str} gave a first guess. Round closed. _',
        },
        'SELECT_PEARS': {
            'INACTIVE': 'Select pears.',
            'ACTIVE': '* Select pears. *',
            'FINISHED': '_All pears selected. Round closed._',
        },
        'VIEW_INTERMEDIATE': {
            'INACTIVE': 'View intermediate results.',
            'ACTIVE': '* View intermediate results. *',
            'FINISHED': '_Viewing intermediate results. Round closed._',
        },
        'REVIESE_GUESS': {
            'INACTIVE': 'Give a second guess.',
            'ACTIVE': f'* {p_str} gave a second guess. *',
            'FINISHED': f'{p_str} gave a second guess. Round closed.',
        },
    }
    text = text_templates[step_id][status]

    accessory = (
        {"accessory": create_button('Reopen', step_id + 'reopen')}
        if status == 'ACTIVE' else {}
    )

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        },
        **accessory
    }


def create_status_block(steps):
    order = ['INITIAL_GUESS', 'SELECT_PEARS', 'VIEW_INTERMEDIATE', 'REVIESE_GUESS']
    return [create_step_status_section(**steps[so]) for so in order]


def create_creator_section(steps):
    if steps["INITIAL_GUESS"]["status"] == 'ACTIVE':
        accessory = {'accessory': create_button('Finish first round', 'FINISH_INITAL_GUESS')}
    elif steps["REVIESE_GUESS"]["status"] == 'ACTIVE':
        accessory = {'accessory': create_button('Finish second round', 'FINISH_REVIESE_GUESS')}
    else:
        accessory = {}

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Creator menu"
        },
        **accessory
    }



def create_question_header(question, outcomes):
    outcomes_str = join_comma_and(outcomes)
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{question}*\n{outcomes_str}"
        }
    }


question_fooder = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": "_ Report a bug. _"
    }
}


def create_question(question, outcomes, steps):
    return [
        create_question_header(question, outcomes),
        divider,
        *create_status_block(steps),
        divider,
        create_creator_section(steps),
        divider,
        question_fooder
    ]

# ------------------ guess message


def create_guess_header(step_id):
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


def create_outcome_section(outcome):
    choices = [{'value': f"{i*5}", 'text': f"{i*5} %"} for i in range(21)]

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": outcome
        },
        "accessory": create_select("Select outcome probability", choices)
    }


def create_outcomes_block(outcomes):
    return [create_outcome_section(o) for o in outcomes]


def create_outcome_message(outcomes, step_id):
    return [
        guess_header,
        divider,
        *create_outcomes_block(outcomes),
        divider,
        create_submit_fooder(step_id)
    ]
