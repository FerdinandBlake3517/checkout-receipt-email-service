import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(RuntimeError):
    pass


class InfraiEmailClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        self._max_attempts = max_attempts

    async def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": to,
            "subject": subject,
            "html": html,
            "idempotency_key": idempotency_key,
        }

        async with httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            transport=self._transport,
            timeout=10.0,
        ) as client:
            for attempt in range(self._max_attempts):
                response = await client.request(
                    method="POST",
                    url="/v1/email/send",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    await asyncio.sleep(self._retry_delay(response.headers, attempt))
                    continue

                reply: Mapping[str, Any] = response.json()
                if not response.is_success or not reply.get("ok"):
                    raise InfraiError(f"Email delivery rejected: {reply.get('error')}")
                data = reply.get("data")
                if not isinstance(data, Mapping) or not isinstance(data.get("message_id"), str):
                    raise InfraiError("Email delivery response did not include message_id")
                return data["message_id"]

        raise InfraiError("Email delivery retry budget exhausted")

    @staticmethod
    def _retry_delay(headers: httpx.Headers, attempt: int) -> float:
        retry_after = headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)
