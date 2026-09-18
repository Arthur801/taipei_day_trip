import hashlib
import json
import unittest
from unittest.mock import patch

from mysql.connector import Error

import user_api


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.rowcount = 0

    def execute(self, statement, params):
        if self.database.fail:
            raise Error("database failure")
        self.database.statements.append((statement, params))
        token, user_id = params
        self.rowcount = int(user_id in self.database.users)
        if self.rowcount:
            self.database.pending = (user_id, token)

    def close(self):
        pass


class FakeDatabase:
    def __init__(self, users=(1,), fail=False):
        self.users = {user_id: None for user_id in users}
        self.fail = fail
        self.pending = None
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        user_id, token = self.pending
        self.users[user_id] = token
        self.pending = None
        self.commits += 1

    def rollback(self):
        self.pending = None
        self.rollbacks += 1

    def is_connected(self):
        return True

    def close(self):
        pass


class ApiTokenTests(unittest.TestCase):
    def authorization(self, user_id=1):
        user = {"id": user_id, "name": "Tester", "email": "test@example.com"}
        return f"Bearer {user_api.create_access_token(user)}"

    def test_generates_and_rotates_only_own_token_after_commit(self):
        database = FakeDatabase(users=(1, 2))
        with patch.object(user_api, "get_database_connection", return_value=database), \
             patch.object(user_api.secrets, "token_hex", side_effect=["a" * 64, "b" * 64]):
            first = user_api.update_api_token(self.authorization())
            second = user_api.update_api_token(self.authorization())

        first_body = json.loads(first.body)
        second_body = json.loads(second.body)
        self.assertEqual(first_body, {
            "ok": True,
            "token": hashlib.sha256(f"1:{'a' * 64}".encode()).hexdigest(),
        })
        self.assertNotEqual(first_body["token"], second_body["token"])
        self.assertEqual(database.users[1], second_body["token"])
        self.assertIsNone(database.users[2])
        self.assertEqual(database.commits, 2)
        self.assertEqual(first.headers["cache-control"], "no-store")

    def test_missing_and_invalid_login_token_return_403(self):
        for authorization in (None, "Bearer invalid", "Basic abc"):
            with self.subTest(authorization=authorization):
                response = user_api.update_api_token(authorization)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(json.loads(response.body), {"error": True})

    def test_deleted_user_returns_403_without_commit(self):
        database = FakeDatabase(users=())
        with patch.object(user_api, "get_database_connection", return_value=database):
            response = user_api.update_api_token(self.authorization())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.body), {"error": True})
        self.assertEqual(database.commits, 0)

    def test_database_error_returns_500_without_commit(self):
        database = FakeDatabase(fail=True)
        with patch.object(user_api, "get_database_connection", return_value=database):
            response = user_api.update_api_token(self.authorization())

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {"error": True})
        self.assertEqual(database.commits, 0)
        self.assertEqual(database.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
