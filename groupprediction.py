import numpy as np
import uuid
from time import sleep


def create_callback_id(function_name, function_id, action_name, action_id):
    return '#'.join(
        [str(function_name), str(function_id), str(action_name), str(action_id)])


class Conversation:
    def __init__(self, function, user_id, team, channel, profile):
        self.function = function
        self.user_id = user_id
        self.team = team
        self.channel = channel
        self.join_prediction = None
        self.first_round = None
        self.second_round = None
        self.peers = None
        self.profile = profile

    def action(self, action_name, action_id, action):
        if action_name == 'FIRST_ROUND_START':
            self.join_prediction = (action["actions"][0]['value'] == 'yes')
            self.reply_join(self.join_prediction)
            sleep(0)
            if self.join_prediction:
                trigger_id = action['trigger_id']
                self.prediction_dialog(trigger_id)
        elif action_name == 'FIRST_ROUND_RESULT':
            value = float(action['submission']['value'])
            self.first_round = value
        elif action_name == 'SECOND_ROUND_RESULT':
            value = float(action['submission']['value'])
            self.second_round = value
        elif action_name == 'PEERS_START':
            trigger_id = action['trigger_id']
            self.select_members_dialog(trigger_id)
        elif action_name == 'PEERS_SELECTED':
            self.peers = list(action['submission'].values())
        elif action_name == 'SECOND_ROUND_START':
            if (action["actions"][0]['value'] == 'yes'):
                trigger_id = action['trigger_id']
                self.prediction_dialog(trigger_id, prediction_name='SECOND_ROUND_RESULT')
            else:
                self.second_round = self.first_round

    def listing():
        pass

    def reply_join(self, join_prediction):
        if join_prediction:
            text = "Great. Let's start."
        else:
            text = "Ok, maybe next time."
        self.team.api_call(
            "chat.postEphemeral",
            user=self.user_id,
            channel=self.channel,
            text=text,
        )

    def wait_for_other_user(self):
        self.team.api_call(
            "chat.postEphemeral",
            user=self.user_id,
            channel=self.channel,
            text="Great, let's wait for the others.",
        )

    def prediction_dialog(self, trigger_id, prediction_name='FIRST_ROUND_RESULT'):
        dialog = {
            "callback_id": create_callback_id(
                self.function.name, self.function.id, prediction_name, self.user_id),
            "title": "Make a prediction",
            "submit_label": "Submit",
            "notify_on_cancel": True,
            "elements": [
                {
                    "type": "text",
                    "label": "Your value",
                    "name": "value"
                }
            ]
        }
        self.team.api_call(
            "dialog.open",
            trigger_id=trigger_id,
            dialog=dialog,
        )

    def decided_join(self):
        return (self.join_prediction is not None)

    def first_round_ready(self):
        return (
            (self.join_prediction is not None) and
            (not self.join_prediction or self.first_round)
        )

    def second_round_ready(self):
        return (
            (self.join_prediction is not None) and
            (not self.join_prediction or self.second_round)
        )

    def select_peers_ready(self):
        return (
            (self.join_prediction is not None) and
            (not self.join_prediction or self.peers)
        )

    def select_members_dialog(self, trigger_id):
        members = self.function.active_members
        member_profiles = self.function.member_profiles
        n_select = self.function.n_peers
        options = [
            {
                'label': member_profiles[m]['real_name'],
                'value': m
            }
            for m in members
            # if (m != self.user_id)
        ]

        # options = [
        #     {'label': 'A', 'value': 'a'},
        #     {'label': 'B', 'value': 'b'},
        #     {'label': 'C', 'value': 'c'},
        # ]

        elements = [
            {
                'label': f'Member {(i + 1)}',
                'name': f'member_{i}',
                'type': 'select',
                'options': options
            }
            for i in range(0, n_select)
        ]

        # elements = [
        #     {
        #         'label': 'Test',
        #         'name': 'test',
        #         'type': 'select',
        #         'options': options
        #     }
        # ]
        # elements = [
        # {
        #     "type": "text",
        #     "label": "Your value",
        #     "name": "value"
        # }
        # ]

        dialog = {
            "callback_id": create_callback_id(
                self.function.name, self.function.id, "PEERS_SELECTED", self.user_id),
            "title": "Select your peers",
            "submit_label": "Submit",
            "notify_on_cancel": True,
            "elements": elements
        }
        test = self.team.api_call(
            "dialog.open",
            trigger_id=trigger_id,
            dialog=dialog,
        )
        print(test)

    def communicate_private_results_first_round(self):
        if self.join_prediction:
            print(self.function.first_round_all)
            peer_prediction = np.mean([
                self.function.first_round_all[p] for p in self.peers])
            text = \
                f"Your prediciton {self.first_round}\n" \
                f"Your peers average prediction {peer_prediction}"
            self.team.api_call(
                "chat.postEphemeral",
                text=text,
                channel=self.channel,
                user=self.user_id
            )


class GroupPrediction:
    def __init__(self, team, channel):
        self.members = team.get_channel_member(channel)
        self.member_profiles = {
            m: team.get_user_profile(m, fields=['real_name'])
            for m in self.members
        }
        self.active_members = None
        self.name = "GD"
        self.id = str(uuid.uuid4())
        self.team = team
        self.channel = channel
        self.conversations = {
            m: Conversation(
                function=self, user_id=m, team=team, channel=channel,
                profile=self.member_profiles[m])
            for m in self.members
        }
        self.start_first_round()

    def action(self, action_name, action_id, action):
        if action_name in [
                'FIRST_ROUND_START', 'FIRST_ROUND_RESULT',
                'SECOND_ROUND_RESULT', 'SECOND_ROUND_START',
                'PEERS_SELECTED', 'PEERS_START']:
            user_id = action['user']['id']
            self.conversations[user_id].action(action_name, action_id, action)
        if action_name == 'FIRST_ROUND_START':
            if all(m.decided_join() for m in self.conversations.values()):
                self.active_members = [
                    m.user_id for m in self.conversations.values()
                    if m.join_prediction is True
                ]
        if action_name == 'FIRST_ROUND_RESULT':
            sleep(0)
            if all(m.first_round_ready() for m in self.conversations.values()):
                self.collect_first_round()
                # self.communicate_first_round()
                # put some logic here
                self.n_peers = 1
                self.start_select_members()
            else:
                self.conversations[user_id].wait_for_other_user()
        if action_name == 'SECOND_ROUND_RESULT':
            sleep(0)
            if all(m.second_round_ready() for m in self.conversations.values()):
                self.collect_second_round()
                self.communicate_second_round()
            else:
                self.conversations[user_id].wait_for_other_user()
        if action_name == 'PEERS_SELECTED':
            sleep(0)
            if all(m.select_peers_ready() for m in self.conversations.values()):
                for m in self.conversations.values():
                    m.communicate_private_results_first_round()
                self.start_second_round()
            else:
                self.conversations[user_id].wait_for_other_user()

    def listing(self):
        pass

    def start_first_round(self):
        text = "Let's start a group prediction."
        attachments = [
            {
                "text": "Would you like to join?",
                "fallback": "You are unable to join",
                "callback_id": create_callback_id(
                    self.name, self.id, "FIRST_ROUND_START", 0),
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "join_prediction",
                        "text": "Yes",
                        "type": "button",
                        "value": "yes"
                    },
                    {
                        "name": "join_prediction",
                        "text": "No",
                        "type": "button",
                        "value": "no"
                    }
                ]
            }
        ]
        self.team.api_call(
            "chat.postMessage",
            attachments=attachments,
            text=text,
            channel=self.channel,
        )

    def start_second_round(self):
        text = "Let's make a second round."
        attachments = [
            {
                "text": "Would you like to revise your prediction?",
                "fallback": "You are unable to join",
                "callback_id": create_callback_id(
                    self.name, self.id, "SECOND_ROUND_START", 0),
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "revise_prediction",
                        "text": "Yes",
                        "type": "button",
                        "value": "yes"
                    },
                    {
                        "name": "revise_prediction",
                        "text": "No",
                        "type": "button",
                        "value": "no"
                    }
                ]
            }
        ]
        self.team.api_call(
            "chat.postMessage",
            attachments=attachments,
            text=text,
            channel=self.channel,
        )

    def start_select_members(self):
        # text = "Now it's time to select some members you trust most for this prediction."
        callback_id = create_callback_id(
                self.name, self.id, "PEERS_START", 0)
        attachments = [
            {
                "text": "Now it's time to select some members you trust most for this prediction.",
                "fallback": "Failed to select trusted members.",
                "callback_id": callback_id,
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "open_member_select",
                        "text": "Let's do it.",
                        "type": "button",
                        "value": "yes"
                    }
                ]
            }
        ]
        self.team.api_call(
            "chat.postMessage",
            attachments=attachments,
            # text='',
            channel=self.channel
        )

    def collect_first_round(self):
        self.first_round_all = {
            m_id: m.first_round
            for m_id, m in self.conversations.items()
            if m.join_prediction
        }
        self.first_round_mean = np.mean(list(self.first_round_all.values()))

    def collect_second_round(self):
        self.second_round_all = {
            m_id: m.second_round
            for m_id, m in self.conversations.items()
            if m.join_prediction
        }
        self.second_round_mean = np.mean(list(self.second_round_all.values()))

    def communicate_first_round(self):
        self.team.api_call(
            "chat.postMessage",
            channel=self.channel,
            text=f"The average value is: {self.first_round_mean}",
        )

    def communicate_second_round(self):
        self.team.api_call(
            "chat.postMessage",
            channel=self.channel,
            text=f"The average value is: {self.second_round_mean}",
        )
