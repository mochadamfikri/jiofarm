from __future__ import annotations

import os
import time
import uuid


class SMSCodeMockError(Exception):
    pass


class SMSCodeMock:
    def __init__(self, api_key: str = "mock"):
        self.api_key = api_key
        self.orders = {}
        self._balance = float(os.getenv("SMSCODE_MOCK_BALANCE", "1000"))
        self._price = float(os.getenv("SMSCODE_MOCK_PRICE", "0.20"))
        self._otp_delay = float(os.getenv("SMSCODE_MOCK_OTP_DELAY", "30"))
        self._cancel_delay = float(os.getenv("SMSCODE_MOCK_CANCEL_DELAY", "120"))
        self._otp = os.getenv("SMSCODE_MOCK_OTP", "123456")

    def balance(self) -> float:
        return self._balance

    def rent(self, max_price: float | None = None) -> tuple[str, str]:
        if max_price is not None and self._price > max_price:
            raise SMSCodeMockError(
                f"price {self._price} exceeds max_price {max_price}"
            )

        if self._balance < self._price:
            raise SMSCodeMockError("insufficient balance")

        act_id = str(uuid.uuid4())
        phone = "+919" + str(uuid.uuid4().int % 1_000_000_000).zfill(9)

        self._balance -= self._price

        self.orders[act_id] = {
            "phone": phone,
            "created_at": time.time(),
            "status": "WAIT",
            "price": self._price,
            "refunded": False,
        }

        return act_id, phone

    def ready(self, act_id: str) -> None:
        self._get(act_id)

    def status(self, act_id: str) -> tuple[str, str | None]:
        order = self._get(act_id)

        if order["status"] == "CANCEL":
            return "CANCEL", None

        if order["status"] == "OK":
            return "OK", self._otp

        age = time.time() - order["created_at"]

        if age >= self._otp_delay:
            order["status"] = "OK"
            return "OK", self._otp

        return "WAIT", None

    def complete(self, act_id: str) -> None:
        order = self._get(act_id)

        if order["status"] == "CANCEL":
            raise SMSCodeMockError("order already cancelled")

        order["status"] = "OK"

    def cancel(self, act_id: str) -> None:
        order = self._get(act_id)

        if order["status"] == "CANCEL":
            return

        age = time.time() - order["created_at"]

        if age < self._cancel_delay:
            remaining = int(self._cancel_delay - age)
            raise SMSCodeMockError(
                f"CANCEL_TOO_EARLY: wait {remaining}s"
            )

        if order["status"] == "OK":
            raise SMSCodeMockError(
                "order already received SMS; refund unavailable"
            )

        order["status"] = "CANCEL"

        if not order["refunded"]:
            self._balance += order["price"]
            order["refunded"] = True

    def _get(self, act_id: str):
        try:
            return self.orders[act_id]
        except KeyError:
            raise SMSCodeMockError(f"unknown order: {act_id}")
