import unittest

from msbot.msdb import MSDatabase
from msbot.settings import TEST_DB_LOCATION


class TestMSDatabase(unittest.TestCase):
    def setUp(self):
        def cleanup_test_db():
            self.test_db.drop_table('spoilers')
            self.test_db.drop_table('users')

        def setup_test_db():
            self.test_db.create_spoilers_table()
            self.test_db.create_users_table()

        self.test_db = MSDatabase(TEST_DB_LOCATION)
        setup_test_db()
        self.addCleanup(cleanup_test_db)

    def test_get_all_user_ids(self):
        mock_user_ids = {
            'Alice',
            'Bob',
            'Carol',
        }

        for mock_id in mock_user_ids:
            self.test_db.write(
                "INSERT INTO users VALUES('{mock_id}', 0)".format(mock_id=mock_id)
            )

        self.assertEqual(
            mock_user_ids,
            { e for e in self.test_db.get_all_user_ids() }
        )

    def test_spoiler_exists(self):
        test_spoiler = 'test_spoiler_img'
        self.assertFalse(self.test_db.spoiler_exists(test_spoiler))
        self.test_db.write(
            "INSERT INTO spoilers VALUES('{img}', 0, NULL)".format(img=test_spoiler)
        )
        self.assertTrue(self.test_db.spoiler_exists(test_spoiler))

    def test_user_exists(self):
        test_user = 'test_user_id'
        self.assertFalse(self.test_db.user_exists(test_user))
        self.test_db.write(
            "INSERT INTO users VALUES('{test_user}', 0)".format(test_user=test_user)
        )
        self.assertTrue(self.test_db.user_exists(test_user))

    def test_add_user(self):
        test_user = 'test_user_id'
        self.test_db.query(
            "SELECT id FROM users where id = '{test_user}'".format(test_user=test_user)
        )
        self.assertFalse(self.test_db.fetchall())

        self.test_db.add_user(test_user)

        self.test_db.query(
            "SELECT id FROM users where id = '{test_user}'".format(test_user=test_user)
        )
        self.assertTrue(self.test_db.fetchall())

    def test_delete_user(self):
        test_user = 'test_user_id'
        self.test_db.write(
            "INSERT INTO users VALUES('{test_user}', 0)".format(test_user=test_user)
        )
        self.test_db.query(
            "SELECT id FROM users where id = '{test_user}'".format(test_user=test_user)
        )
        self.assertTrue(self.test_db.fetchall())

        self.test_db.delete_user(test_user)

        self.test_db.query(
            "SELECT id FROM users where id = '{test_user}'".format(test_user=test_user)
        )
        self.assertFalse(self.test_db.fetchall())

    def test_add_spoiler(self):
        test_spoiler = 'test_spoiler_img'
        test_attach_id = '12345'
        self.test_db.query(
            "SELECT img FROM spoilers where img = '{test_spoiler}'"
            .format(test_spoiler=test_spoiler)
        )
        self.assertFalse(self.test_db.fetchall())

        self.test_db.add_spoiler(test_spoiler, test_attach_id)

        self.test_db.query(
            '''
            SELECT img FROM spoilers where img = '{test_spoiler}' AND
            attach_id = '{test_attach_id}'
            '''
            .format(
                test_spoiler=test_spoiler,
                test_attach_id=test_attach_id
            )
        )
        self.assertTrue(self.test_db.fetchall())

    def test_get_latest_spoiler_id(self):
        self.test_db.add_spoiler('1', 0)
        self.test_db.add_spoiler('2', 0)
        self.test_db.add_spoiler('3', 0)
        self.test_db.add_spoiler('4', 0)

        self.assertEqual(self.test_db.get_latest_spoiler_id(), 4)


    def test_create_spoilers_table(self):
        self.test_db.write(
            'DROP TABLE IF EXISTS spoilers'
        )

        self.test_db.create_spoilers_table()

        self.test_db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='spoilers'"
        )
        self.assertTrue(self.test_db.fetchall())

    def test_create_users_table(self):
        self.test_db.write(
            'DROP TABLE IF EXISTS users'
        )

        self.test_db.create_users_table()

        self.test_db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        self.assertTrue(self.test_db.fetchall())
