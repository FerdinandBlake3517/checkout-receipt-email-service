import asyncio
import json

import httpx

from order_email_service.infrai_client import InfraiEmailClient
from order_email_service.models import CustomerOrderUpdate, OrderEvent
from order_email_service.receipt_sender import compose_order_email, send_customer_update


def test_checkout_payment_becomes_receipt_with_stable_event_identity() -> None:
    update = CustomerOrderUpdate(
        order_id="ORD-1042",
        event_id="payment-77",
        event=OrderEvent.CHECKOUT_PAID,
        customer_email="creator@example.com",
        customer_name="Maya",
        total_cents=2400,
        currency="USD",
        item_title="Creator Lighting Presets",
    )

    first = compose_order_email(update)
    replay = compose_order_email(update)

    assert first.subject == "Receipt for order ORD-1042"
    assert "24.00 USD" in first.html
    assert first.idempotency_key == "order-email:ORD-1042:checkout_paid:payment-77"
    assert replay.idempotency_key == first.idempotency_key


def test_fulfillment_is_an_access_update_instead_of_a_second_receipt() -> None:
    update = CustomerOrderUpdate(
        order_id="ORD-1042",
        event_id="fulfillment-19",
        event=OrderEvent.FULFILLED,
        customer_email="creator@example.com",
        customer_name="Maya",
        total_cents=2400,
        currency="USD",
        item_title="Creator Lighting Presets",
        download_url="https://media.example.com/orders/ORD-1042",
    )

    email = compose_order_email(update)

    assert email.subject == "Order ORD-1042 is ready"
    assert "Receipt" not in email.subject
    assert "Open your purchase" in email.html


def test_idempotency_key_is_sent_in_email_request_body() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Idempotency-Key") is None
        assert request.content
        payload = json.loads(request.content)
        assert payload == {
            "to": "creator@example.com",
            "subject": "Receipt for order ORD-1042",
            "html": (
                "<h1>Thanks, Maya</h1>"
                "<p>Your payment for Creator Lighting Presets is complete.</p>"
                "<p>Order <strong>ORD-1042</strong>: 24.00 USD</p>"
            ),
            "idempotency_key": "order-email:ORD-1042:checkout_paid:payment-77",
        }
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg_1"}})

    update = CustomerOrderUpdate(
        order_id="ORD-1042",
        event_id="payment-77",
        event=OrderEvent.CHECKOUT_PAID,
        customer_email="creator@example.com",
        customer_name="Maya",
        total_cents=2400,
        currency="USD",
        item_title="Creator Lighting Presets",
    )

    accepted = asyncio.run(
        send_customer_update(
            update,
            InfraiEmailClient("test-key", transport=httpx.MockTransport(handler)),
        )
    )

    assert accepted.message_id == "msg_1"
