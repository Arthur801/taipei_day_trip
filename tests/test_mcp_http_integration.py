import asyncio
import os
import socket
import unittest
from unittest.mock import patch

import httpx2
import uvicorn
from fastmcp import Client

import mcp_server
from app import app


class SearchCursor:
    def execute(self, statement, params):
        if "INSTR(name, %s)" not in statement or params != ("北投", "北投"):
            raise AssertionError("unexpected search query")

    def fetchall(self):
        return [{"id": 2, "name": "北投溫泉博物館", "description": "景點簡介"}]

    def close(self):
        pass


class SearchConnection:
    def cursor(self, dictionary=False):
        if dictionary is not True:
            raise AssertionError("search cursor must return dictionaries")
        return SearchCursor()

    def is_connected(self):
        return True

    def close(self):
        pass


@unittest.skipUnless(
    os.getenv("RUN_MCP_HTTP_INTEGRATION") == "1",
    "set RUN_MCP_HTTP_INTEGRATION=1 to allow a local listening socket",
)
class McpHttpIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_auth_metadata_tools_search_and_token_rotation(self):
        original_token = "a" * 64
        replacement_token = "c" * 64
        active_token = {"value": original_token}

        with socket.socket() as temporary_socket:
            temporary_socket.bind(("127.0.0.1", 0))
            port = temporary_socket.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        )
        server_task = asyncio.create_task(server.serve())
        try:
            for _ in range(500):
                if server.started:
                    break
                if server_task.done():
                    await server_task
                await asyncio.sleep(0.01)
            else:
                self.fail("Uvicorn did not start")

            endpoint = f"http://127.0.0.1:{port}/mcp/"
            token_lookup = lambda token: 7 if token == active_token["value"] else None
            with patch.object(
                mcp_server,
                "find_member_id_by_api_token",
                side_effect=token_lookup,
            ), patch.object(
                mcp_server,
                "get_database_connection",
                side_effect=SearchConnection,
            ):
                async with httpx2.AsyncClient(timeout=5) as raw_client:
                    missing = await raw_client.post(endpoint, json={})
                    invalid = await raw_client.post(
                        endpoint,
                        headers={"Authorization": "Bearer " + "b" * 64},
                        json={},
                    )

                async with Client(endpoint, auth=original_token) as client:
                    self.assertEqual(client.server_info.name, "台北一日遊")
                    self.assertEqual(
                        {tool.name for tool in await client.list_tools()},
                        {"search", "add_to_cart"},
                    )
                    result = await client.call_tool("search", {"keyword": "北投"})
                    invalid_booking = await client.call_tool(
                        "add_to_cart",
                        {
                            "attractionId": 2,
                            "date": "2026-12-01",
                            "time": "morning",
                            "price": 2500,
                        },
                    )

                active_token["value"] = replacement_token
                async with httpx2.AsyncClient(timeout=5) as raw_client:
                    rotated = await raw_client.post(
                        endpoint,
                        headers={"Authorization": f"Bearer {original_token}"},
                        json={},
                    )
                async with Client(endpoint, auth=replacement_token) as client:
                    await client.list_tools()

            self.assertEqual(missing.status_code, 401)
            self.assertEqual(invalid.status_code, 401)
            self.assertEqual(rotated.status_code, 401)
            self.assertEqual(invalid_booking.structured_content, {"error": True})
            self.assertEqual(
                result.structured_content,
                {
                    "data": [
                        {
                            "id": 2,
                            "name": "北投溫泉博物館",
                            "description": "景點簡介",
                        }
                    ]
                },
            )
        finally:
            server.should_exit = True
            await asyncio.wait_for(server_task, timeout=10)


if __name__ == "__main__":
    unittest.main()
