

def _create_text_input(name, label, value, number, optional):
    return {
        "label": label,
        "name": name,
        "type": "text",
        **({"subtype": 'number'} if number else {}),
        "value": value,
        "optional": optional
    }


settings_info = [
    {'id': 'n_rounds', 'display': 'Number of rounds', 'default': 3, 'dtype': 'int'},
    {'id': 'min_val', 'display': 'Smallest selectable value', 'default': 0, 'dtype': 'int'},
    {'id': 'max_val', 'display': 'Largest selectable value', 'default': 100, 'dtype': 'int'},
    {'id': 'step', 'display': 'Interval between values', 'default': 25, 'dtype': 'int'},
    {'id': 'unit', 'display': 'Unit', 'default': '%', 'dtype': 'int'},
    {
        'id': 'constrained_sum', 'display': 'Constrain the sum (empty: no constrain)',
        'default': 100, 'dtype': 'int', 'optional': True
    },
]


def create_settings_dialog(**defaults):
    elements = [
        _create_text_input(
            s['id'], s['display'], defaults[s['id']], s['dtype'] == 'int',
            s.get('optional', False))
        for s in settings_info
    ]

    return {
        "title": "Settings",
        "submit_label": 'Update',
        "notify_on_cancel": True,
        "elements": elements
    }
