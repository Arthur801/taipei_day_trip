import importlib
import sys
import unittest
from unittest.mock import patch


class FakeCursor:
    def __init__(self, api_token_exists=False):
        self.statements = []
        self.current_result = None
        self.api_token_exists = api_token_exists

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if "ALTER TABLE users ADD COLUMN api_token" in statement:
            self.api_token_exists = True
        elif "COLUMN_NAME = 'api_token'" in statement:
            self.current_result = (1,) if self.api_token_exists else None
        elif "information_schema.COLUMNS" in statement:
            column_types = {
                "users": "int unsigned",
                "attractions": "bigint unsigned",
            }
            self.current_result = (column_types[params[0]],)

    def fetchone(self):
        return self.current_result

    def close(self):
        pass


class FakeDatabase:
    def __init__(self, api_token_exists=False):
        self.test_cursor = FakeCursor(api_token_exists)

    def cursor(self):
        return self.test_cursor


class DatabaseSchemaTests(unittest.TestCase):
    def load_module(self, database):
        sys.modules.pop("load_data", None)
        with patch("mysql.connector.connect", return_value=database):
            return importlib.import_module("load_data")

    def test_foreign_key_types_match_existing_primary_keys(self):
        database = FakeDatabase()
        load_data = self.load_module(database)
        load_data.create_database()

        ddl = "\n".join(
            statement
            for statement, _ in database.test_cursor.statements
            if "CREATE TABLE IF NOT EXISTS booking" in statement
            or "CREATE TABLE IF NOT EXISTS orders" in statement
        )
        self.assertIn("user_id INT UNSIGNED NOT NULL", ddl)
        self.assertIn("attraction_id BIGINT UNSIGNED NOT NULL", ddl)

    def test_new_users_table_has_api_token_and_existing_table_migrates_once(self):
        database = FakeDatabase()
        load_data = self.load_module(database)

        load_data.create_database()
        load_data.create_database()

        statements = [statement for statement, _ in database.test_cursor.statements]
        users_ddl = next(s for s in statements if "CREATE TABLE IF NOT EXISTS users" in s)
        self.assertIn("api_token CHAR(64) NULL UNIQUE", users_ddl)
        self.assertEqual(
            sum("ALTER TABLE users ADD COLUMN api_token" in s for s in statements), 1
        )

    def test_existing_api_token_column_is_not_changed(self):
        database = FakeDatabase(api_token_exists=True)
        load_data = self.load_module(database)
        load_data.create_database()

        statements = [statement for statement, _ in database.test_cursor.statements]
        self.assertFalse(any("ALTER TABLE users ADD COLUMN api_token" in s for s in statements))


if __name__ == "__main__":
    unittest.main()
