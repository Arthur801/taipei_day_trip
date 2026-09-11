import unittest
from datetime import date
from unittest.mock import Mock, patch

import order_api


ORDER_REQUEST = {
    "prime": "test-prime",
    "order": {
        "price": 2000,
        "trip": {
            "attraction": {
                "id": 10,
                "name": "前端景點",
                "address": "台北市",
                "image": None,
            },
            "date": "2026-12-01",
            "time": "morning",
        },
        "contact": {
            "name": "王小明",
            "email": "test@example.com",
            "phone": "0912345678",
        },
    },
}


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.current_result = None
        self.lastrowid = None
        self.rowcount = 0

    def execute(self, sql, params):
        self.rowcount = 0
        if sql.startswith("SELECT b.attraction_id"):
            self.current_result = self.state["booking"]
        elif sql.startswith("SELECT id, number FROM orders"):
            self.current_result = next(
                (order for order in reversed(self.state["orders"]) if order["status"] == "UNPAID"),
                None,
            )
        elif sql.startswith("INSERT INTO orders"):
            order = {
                "id": len(self.state["orders"]) + 1,
                "number": params[0],
                "status": "UNPAID",
            }
            self.state["orders"].append(order)
            self.lastrowid = order["id"]
        elif sql.startswith("UPDATE orders SET status = 'PAID'"):
            order_id = params[-1]
            for order in self.state["orders"]:
                if order["id"] == order_id and order["status"] == "UNPAID":
                    order["status"] = "PAID"
                    self.rowcount = 1
                    break

    def fetchone(self):
        return self.current_result

    def close(self):
        pass


class FakeConnection:
    def __init__(self, state):
        self.state = state

    def cursor(self, dictionary=False):
        return FakeCursor(self.state)

    def commit(self):
        pass

    def rollback(self):
        pass

    def is_connected(self):
        return True

    def close(self):
        pass


class OrderPaymentTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "booking": {
                "attraction_id": 10,
                "attraction_name": "資料庫景點",
                "date": date(2026, 12, 1),
                "time": "morning",
                "price": 2000,
            },
            "orders": [],
        }

    def test_failed_payment_retry_reuses_unpaid_order(self):
        with (
            patch.object(order_api, "get_authenticated_user_id", return_value=7),
            patch.object(
                order_api,
                "get_database_connection",
                side_effect=lambda: FakeConnection(self.state),
            ),
            patch.object(
                order_api,
                "generate_order_number",
                side_effect=["20260912000001", "20260912000002"],
            ),
            patch.object(
                order_api,
                "pay_by_prime",
                side_effect=[(7, "declined"), (0, "success")],
            ),
        ):
            first = order_api.create_order(ORDER_REQUEST, "Bearer token")
            second = order_api.create_order(ORDER_REQUEST, "Bearer token")

        self.assertEqual(first["data"]["payment"]["status"], 1)
        self.assertEqual(second["data"]["payment"]["status"], 0)
        self.assertEqual(len(self.state["orders"]), 1)
        self.assertEqual(self.state["orders"][0]["number"], "20260912000001")
        self.assertEqual(self.state["orders"][0]["status"], "PAID")

    def test_pay_by_prime_does_not_reuse_bank_transaction_id(self):
        response = Mock()
        response.json.return_value = {"status": 0, "msg": "Success"}

        with (
            patch.object(order_api, "TAPPAY_PARTNER_KEY", "partner-secret"),
            patch.object(order_api, "TAPPAY_MERCHANT_ID", "merchant-id"),
            patch.object(order_api.requests, "post", return_value=response) as post,
        ):
            result = order_api.pay_by_prime(
                "test-prime",
                "20260912000001",
                2000,
                "資料庫景點",
                "王小明",
                "test@example.com",
                "0912345678",
            )

        self.assertEqual(result, (0, "Success"))
        self.assertEqual(post.call_args.kwargs["json"]["order_number"], "20260912000001")
        self.assertNotIn("bank_transaction_id", post.call_args.kwargs["json"])


if __name__ == "__main__":
    unittest.main()
