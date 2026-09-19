import unittest
from datetime import date
from unittest.mock import patch

from fastmcp import Client
from fastmcp.server.auth import AccessToken
from mysql.connector import Error
from starlette.requests import Request

import booking_api
import mcp_server


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return self.test_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def is_connected(self):
        return True

    def close(self):
        pass


class SearchCursor:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.executed = None

    def execute(self, statement, params):
        if self.error:
            raise self.error
        self.executed = (statement, params)

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class BookingCursor:
    def __init__(self, attraction_exists=True, insert_error=None):
        self.attraction_exists = attraction_exists
        self.insert_error = insert_error
        self.statements = []

    def execute(self, statement, params):
        self.statements.append((statement, params))
        if statement.startswith("INSERT INTO booking") and self.insert_error:
            raise self.insert_error

    def fetchone(self):
        return (10,) if self.attraction_exists else None

    def close(self):
        pass


class TokenCursor:
    def __init__(self, member_id):
        self.member_id = member_id
        self.executed = None

    def execute(self, statement, params):
        self.executed = (statement, params)

    def fetchone(self):
        return (self.member_id,) if self.member_id else None

    def close(self):
        pass


class McpToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_metadata_and_tool_schemas(self):
        async with Client(mcp_server.mcp) as client:
            self.assertEqual(client.server_info.name, "台北一日遊")
            tools = {tool.name: tool for tool in await client.list_tools()}

        self.assertEqual(set(tools), {"search", "add_to_cart"})
        self.assertEqual(tools["search"].title, "搜尋台北市景點")
        self.assertEqual(tools["add_to_cart"].title, "預定景點導覽行程")
        self.assertEqual(
            set(tools["add_to_cart"].input_schema["properties"]),
            {"attractionId", "date", "time", "price"},
        )
        properties = tools["add_to_cart"].input_schema["properties"]
        self.assertEqual(properties["attractionId"]["type"], "integer")
        self.assertEqual(properties["attractionId"]["exclusiveMinimum"], 0)
        self.assertEqual(properties["date"]["type"], "string")
        self.assertEqual(properties["date"]["format"], "date")
        self.assertEqual(properties["time"]["enum"], ["morning", "afternoon"])
        self.assertEqual(properties["price"]["type"], "integer")
        self.assertEqual(properties["price"]["enum"], [2000, 2500])

    async def test_search_returns_compact_attraction_list(self):
        cursor = SearchCursor([
            {"id": 2, "name": "北投溫泉博物館", "description": "景點簡介"}
        ])
        connection = FakeConnection(cursor)
        with patch.object(mcp_server, "get_database_connection", return_value=connection):
            result = mcp_server.search_attractions("北投")

        self.assertEqual(
            result,
            {"data": [{"id": 2, "name": "北投溫泉博物館", "description": "景點簡介"}]},
        )
        self.assertIn("INSTR(name, %s)", cursor.executed[0])
        self.assertEqual(cursor.executed[1], ("北投", "北投"))

    async def test_search_treats_like_characters_as_plain_text(self):
        cursor = SearchCursor()
        connection = FakeConnection(cursor)
        with patch.object(mcp_server, "get_database_connection", return_value=connection):
            result = mcp_server.search_attractions("%_")

        self.assertEqual(result, {"data": []})
        self.assertEqual(cursor.executed[1], ("%_", "%_"))

    async def test_search_invalid_input_and_database_error(self):
        self.assertEqual(mcp_server.search_attractions("   "), {"error": True})
        cursor = SearchCursor(error=Error("failed"))
        with patch.object(
            mcp_server,
            "get_database_connection",
            return_value=FakeConnection(cursor),
        ):
            self.assertEqual(mcp_server.search_attractions("北投"), {"error": True})

    async def test_database_token_verifier_returns_member_claim(self):
        token = "a" * 64
        cursor = TokenCursor(member_id=7)
        with patch.object(
            mcp_server,
            "get_database_connection",
            return_value=FakeConnection(cursor),
        ):
            access_token = await mcp_server.DatabaseTokenVerifier().verify_token(token)

        self.assertEqual(access_token.claims["member_id"], 7)
        self.assertEqual(access_token.subject, "7")
        self.assertIn("BINARY api_token", cursor.executed[0])
        self.assertEqual(cursor.executed[1], (token,))

    async def test_database_token_verifier_rejects_invalid_or_missing_token(self):
        with patch.object(mcp_server, "get_database_connection") as get_connection:
            self.assertIsNone(await mcp_server.DatabaseTokenVerifier().verify_token("invalid"))
        get_connection.assert_not_called()

        with patch.object(
            mcp_server,
            "get_database_connection",
            return_value=FakeConnection(TokenCursor(member_id=None)),
        ):
            self.assertIsNone(
                await mcp_server.DatabaseTokenVerifier().verify_token("b" * 64)
            )

    async def test_database_token_verifier_checks_rotation_on_every_request(self):
        verifier = mcp_server.DatabaseTokenVerifier()
        with patch.object(
            mcp_server,
            "find_member_id_by_api_token",
            side_effect=[7, None],
        ) as find_member:
            self.assertIsNotNone(await verifier.verify_token("a" * 64))
            self.assertIsNone(await verifier.verify_token("a" * 64))

        self.assertEqual(find_member.call_count, 2)


class AddToCartTests(unittest.TestCase):
    def make_request(self, scheme="https", host="travel.example"):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": scheme,
                "server": (host, 443 if scheme == "https" else 80),
                "path": "/mcp/",
                "raw_path": b"/mcp/",
                "query_string": b"",
                "headers": [(b"host", host.encode())],
            }
        )

    def access_token(self, member_id=7):
        return AccessToken(
            token="a" * 64,
            client_id=f"member-{member_id}",
            subject=str(member_id),
            scopes=[mcp_server.MCP_SCOPE],
            claims={"member_id": member_id},
        )

    def test_success_uses_authenticated_member_and_live_booking_url(self):
        with patch.object(mcp_server, "replace_booking") as replace_booking:
            result = mcp_server.add_to_cart(
                10,
                date(2026, 12, 1),
                "morning",
                2000,
                self.access_token(),
                self.make_request(),
            )

        self.assertEqual(result["ok"], True)
        self.assertIn("https://travel.example/booking", result["message"])
        member_id, booking = replace_booking.call_args.args
        self.assertEqual(member_id, 7)
        self.assertEqual(booking.attraction_id, 10)
        self.assertEqual(booking.date, date(2026, 12, 1))

    def test_success_uses_http_booking_url(self):
        with patch.object(mcp_server, "replace_booking"):
            result = mcp_server.add_to_cart(
                10,
                date(2026, 12, 1),
                "afternoon",
                2500,
                self.access_token(),
                self.make_request(scheme="http", host="localhost:8000"),
            )

        self.assertIn("http://localhost:8000/booking", result["message"])

    def test_invalid_inputs_return_error_without_writing(self):
        invalid_cases = [
            (10, date(2026, 12, 1), "morning", 2500),
            (10, date(2026, 12, 1), "afternoon", 2000),
        ]
        for values in invalid_cases:
            with self.subTest(values=values), patch.object(
                mcp_server, "replace_booking"
            ) as replace_booking:
                replace_booking.side_effect = booking_api.BookingValidationError()
                result = mcp_server.add_to_cart(
                    *values,
                    self.access_token(),
                    self.make_request(),
                )
                self.assertEqual(result, {"error": True})


class BookingTransactionTests(unittest.TestCase):
    def booking(self):
        return booking_api.BookingRequest.model_validate(
            {
                "attractionId": 10,
                "date": "2026-12-01",
                "time": "morning",
                "price": 2000,
            }
        )

    def test_replace_booking_commits_delete_and_insert(self):
        cursor = BookingCursor()
        connection = FakeConnection(cursor)
        with patch.object(
            booking_api, "get_database_connection", return_value=connection
        ):
            booking_api.replace_booking(7, self.booking())

        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(any(sql.startswith("DELETE FROM booking") for sql, _ in cursor.statements))
        self.assertTrue(any(sql.startswith("INSERT INTO booking") for sql, _ in cursor.statements))

    def test_missing_attraction_keeps_existing_booking(self):
        cursor = BookingCursor(attraction_exists=False)
        connection = FakeConnection(cursor)
        with patch.object(
            booking_api, "get_database_connection", return_value=connection
        ):
            with self.assertRaises(booking_api.BookingValidationError):
                booking_api.replace_booking(7, self.booking())

        self.assertEqual(connection.rollbacks, 1)
        self.assertFalse(any(sql.startswith("DELETE FROM booking") for sql, _ in cursor.statements))

    def test_insert_failure_rolls_back_delete(self):
        cursor = BookingCursor(insert_error=Error("insert failed"))
        connection = FakeConnection(cursor)
        with patch.object(
            booking_api, "get_database_connection", return_value=connection
        ):
            with self.assertRaises(booking_api.BookingStorageError):
                booking_api.replace_booking(7, self.booking())

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
