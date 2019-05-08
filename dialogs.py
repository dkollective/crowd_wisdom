def create_choices():
    return [
        {
            "text": {
                "type": "plain_text",
                "text": f"{i*5} %",
                "emoji": True
            },
            "value": f"{i*5}"
        }
        for i in range(20)
    ]


def create_outcome_section(outcome):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": outcome
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Select event probability",
                "emoji": True
            },
            "options": create_choices()
        }
    }


delete_button = {
    "type": "actions",
    "elements": [
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Lock Guess",
                "emoji": True
            },
            "value": "lock"
        },
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Delete Question",
                "emoji": True
            },
            "value": "delete"
        }
    ]

}


divider = {
    "type": "divider"
}


def create_question_header(question):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{question}*"
        }
    }


def create_question(question, poss_outcomes):
    return [
        create_question_header(question),
        divider,
        *[create_outcome_section(po) for po in poss_outcomes],
        divider,
        delete_button
    ]

# ------------------
