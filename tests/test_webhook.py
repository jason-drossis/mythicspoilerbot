import json
import unittest

import unittest.mock as mock

from boddle import boddle

import webhook

import msbot.constants
from msbot.spoiler import Spoiler
from msbot.user import User

TEST_ACCESS_TOKEN = 'TEST_ACCESS_TOKEN'
TEST_VERIFY_TOKEN = 'TEST_VERIFY_TOKEN'
TEST_API_KEY = 'TEST_API_KEY'


class TestWebhook(unittest.TestCase):
    def setUp(self):
        settings_patch = mock.patch('webhook.msbot.settings')
        self.addCleanup(settings_patch.stop)
        self.settings_mock = settings_patch.start()
        self.settings_mock.configure_mock(
            **{
                'PAGE_ACCESS_TOKEN': TEST_ACCESS_TOKEN,
                'VERIFY_TOKEN': TEST_VERIFY_TOKEN,
                'API_KEY': TEST_API_KEY,
            }
        )

        requests_patch = mock.patch('webhook.requests')
        self.addCleanup(requests_patch.stop)
        self.requests_mock = requests_patch.start()

    def test_send_message(self):
        mock_send_psid = 123456
        mock_message = 'Hello'
        mock_request_body = {
            'json': {
                msbot.constants.RECIPIENT: {
                    msbot.constants.ID: mock_send_psid
                },
                msbot.constants.MESSAGE: mock_message
            },
            'params': {
                msbot.constants.ACCESS_TOKEN: TEST_ACCESS_TOKEN,
                msbot.constants.RECIPIENT: mock_send_psid
            }
        }

        webhook.send_message(mock_send_psid, mock_message)

        self.assertEqual(self.requests_mock.post.call_count, 1)

        _, request_body = self.requests_mock.post.call_args

        self.assertDictEqual(request_body, mock_request_body)

    def test_get_attach_id_for(self):
        test_url = 'www.fake.com'
        attach_id = 123456
        response_mock = mock.Mock()
        response_mock.text = json.dumps({'attachment_id': attach_id})

        self.requests_mock.post.return_value = response_mock
        self.assertEqual(webhook.get_attach_id_for(test_url), attach_id)

    @mock.patch('webhook.send_message')
    def test_send_spoiler_to(self, send_mock):
        test_user = User((1234, 0))
        test_spoiler = Spoiler(('test', 123456, None))

        test_response = {
            'attachment': {
                'type': 'image',
                'payload': {
                    'attachment_id': test_spoiler.attach_id
                }
            }
        }

        webhook.send_spoiler_to(test_user, test_spoiler)

        send_mock.assert_called_once_with(test_user.user_id, test_response)


    @mock.patch('webhook.get_attach_id_for')
    @mock.patch('msbot.mslib.getLatestSpoilers')
    @mock.patch('msbot.msdb.MSDatabase')
    def test_update_spoilers(self, db_mock, spoils_mock, attach_mock):
        test_spoilers = {
            '1': {'exists': False, 'attach_id': '123'},
            '2': {'exists': False, 'attach_id': '456'},
            '3': {'exists': True, 'attach_id': '789'},
        }

        def spoiler_exists_return_values(spoiler):
            return test_spoilers[spoiler]['exists']

        def get_attach_id_for_return_values(spoiler):
            return test_spoilers[spoiler]['attach_id']

        db = db_mock.return_value
        db.spoiler_exists.side_effect = spoiler_exists_return_values

        spoils_mock.return_value = [k for k in test_spoilers.keys()]

        attach_mock.side_effect = get_attach_id_for_return_values

        webhook.update_spoilers()

        calls = [
            mock.call('2', '456'),
            mock.call('1', '123'),
        ]

        db.add_spoiler.assert_has_calls(calls, any_order=True)
        self.assertEqual(db.add_spoiler.call_count, len(calls))

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_spoiler_to')
    def test_update_users(self, send_mock, db_mock):
        db = db_mock.return_value

        alice = User(('Alice', 0))
        bob = User(('Bob', 1))
        dan = User(('Dan', 3))
        db.get_all_unnotified_users.return_value = [alice, bob, dan]

        spoil1 = Spoiler(('test1', '123', 1))
        spoil2 = Spoiler(('test2', '456', 2))
        spoil3 = Spoiler(('test3', '789', 3))
        db.get_spoilers_later_than.return_value = [spoil1, spoil2, spoil3]
        db.get_latest_spoiler_id.return_value = 5

        calls = [
            mock.call(alice, spoil1),
            mock.call(alice, spoil2),
            mock.call(alice, spoil3),
            mock.call(bob, spoil2),
            mock.call(bob, spoil3),
        ]

        webhook.update_users()

        send_mock.assert_has_calls(calls, any_order=True)
        self.assertEqual(send_mock.call_count, len(calls))

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_sub_when_unsubbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = False
        sender_psid = 1234

        webhook.handle_message(sender_psid, msbot.constants.HELLO)
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_SUBBED })

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_sub_when_subbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = True
        sender_psid = 1234

        webhook.handle_message(sender_psid, msbot.constants.HELLO)
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_ALREADY_SUBBED })

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_unsub_when_unsubbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = False
        sender_psid = 1234

        webhook.handle_message(sender_psid, msbot.constants.GOODBYE)
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_ALREADY_UNSUBBED })

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_unsub_when_subbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = True
        sender_psid = 1234

        webhook.handle_message(sender_psid, msbot.constants.GOODBYE)
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_UNSUBBED })

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_invalid_when_subbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = True
        sender_psid = 1234

        webhook.handle_message(sender_psid, 'unsupported_message')
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_INVALID_SUBBED })

    @mock.patch('msbot.msdb.MSDatabase')
    @mock.patch('webhook.send_message')
    def test_handle_message_invalid_when_unsubbed(self, send_mock, db_mock):
        db = db_mock.return_value
        db.user_exists.return_value = False
        sender_psid = 1234

        webhook.handle_message(sender_psid, 'unsupported_message')
        send_mock.assert_called_once_with(
            sender_psid,
            { msbot.constants.TEXT: msbot.constants.RESP_INVALID_UNSUBBED })

    def test_webhook_event_text_message_received(self):
        with boddle(
            body=json.dumps(
                {
                    msbot.constants.OBJECT: msbot.constants.PAGE_OBJECT,
                    msbot.constants.ENTRY: [
                        {
                            msbot.constants.MESSAGING: [
                                {
                                    msbot.constants.MESSAGE: {
                                        msbot.constants.TEXT: 'Hello!'
                                    },
                                    msbot.constants.SENDER: {
                                        msbot.constants.ID: 123456
                                    }
                                }
                            ],
                        }
                    ]
                }
            )
        ):
            webhook.webhook_event()
            self.assertEqual(webhook.response.status_code, 200)

    def test_webhook_event_non_text_message_received(self):
        with boddle(
            body=json.dumps(
                {
                    msbot.constants.OBJECT: msbot.constants.PAGE_OBJECT,
                    msbot.constants.ENTRY: [
                        {
                            msbot.constants.MESSAGING: [
                                {
                                    msbot.constants.MESSAGE: {
                                        'foo': None
                                    },
                                    msbot.constants.SENDER: {
                                        msbot.constants.ID: 123456
                                    }
                                }
                            ],
                        }
                    ]
                }
            )
        ):
            webhook.webhook_event()
            self.assertEqual(webhook.response.status_code, 200)

    def test_webhook_event_no_page_object(self):
        with boddle(
            body=json.dumps(
                {
                    msbot.constants.OBJECT: None,
                }
            )
        ):
            webhook.webhook_event()
            self.assertEqual(webhook.response.status_code, 404)

    def test_webhook_verify_success(self):
        with boddle(
            query={
                msbot.constants.MODE: msbot.constants.SUBSCRIBE,
                msbot.constants.TOKEN: TEST_VERIFY_TOKEN,
                msbot.constants.CHALLENGE: 'TEST_CHALLENGE'
            }
        ):
            self.assertEqual(webhook.webhook_verify(), 'TEST_CHALLENGE')
            self.assertEqual(webhook.response.status_code, 200)

    def test_webhook_verify_bad_token(self):
        with boddle(
            query={
                msbot.constants.MODE: msbot.constants.SUBSCRIBE,
                msbot.constants.TOKEN: 'BAD_TOKEN',
                msbot.constants.CHALLENGE: 'TEST_CHALLENGE'
            }
        ):
            webhook.webhook_verify()
            self.assertEqual(webhook.response.status_code, 403)

    def test_webhook_verify_bad_mode(self):
        with boddle(
            query={
                msbot.constants.MODE: 'BAD_MODE',
                msbot.constants.TOKEN: TEST_VERIFY_TOKEN,
                msbot.constants.CHALLENGE: 'TEST_CHALLENGE'
            }
        ):
            webhook.webhook_verify()
            self.assertEqual(webhook.response.status_code, 403)

    def test_webhook_verify_no_mode(self):
        with boddle(
            query={
                msbot.constants.MODE: None,
                msbot.constants.TOKEN: TEST_VERIFY_TOKEN,
                msbot.constants.CHALLENGE: 'TEST_CHALLENGE'
            }
        ):
            self.assertEqual(webhook.webhook_verify(), None)

    def test_webhook_verify_no_token(self):
        with boddle(
            query={
                msbot.constants.MODE: msbot.constants.SUBSCRIBE,
                msbot.constants.TOKEN: None,
                msbot.constants.CHALLENGE: 'TEST_CHALLENGE'
            }
        ):
            self.assertEqual(webhook.webhook_verify(), None)
