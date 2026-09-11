import importlib
import sys
import unittest
from unittest.mock import patch


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.current_result = None

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if "information_schema.COLUMNS" in statement:
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
    def __init__(self):
        self.test_cursor = FakeCursor()

    def cursor(self):
        return self.test_cursor


class DatabaseSchemaTests(unittest.TestCase):
    def test_foreign_key_types_match_existing_primary_keys(self):
        database = FakeDatabase()
        sys.modules.pop("load_data", None)

        with patch("mysql.connector.connect", return_value=database):
            load_data = importlib.import_module("load_data")
            load_data.create_database()

        ddl = "\n".join(
            statement
            for statement, _ in database.test_cursor.statements
            if "CREATE TABLE IF NOT EXISTS booking" in statement
            or "CREATE TABLE IF NOT EXISTS orders" in statement
        )
        self.assertIn("user_id INT UNSIGNED NOT NULL", ddl)
        self.assertIn("attraction_id BIGINT UNSIGNED NOT NULL", ddl)


if __name__ == "__main__":
    unittest.main()
