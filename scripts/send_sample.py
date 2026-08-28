import asyncio
import os

from order_email_service.infrai_client import InfraiEmailClient
from order_email_service.models import CustomerOrderUpdate, OrderEvent
from order_email_service.receipt_sender import send_customer_update


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    recipient = os.environ.get("RECEIPT_TO")
    if not api_key or not recipient:
        raise SystemExit("Set INFRAI_API_KEY and RECEIPT_TO")

    update = CustomerOrderUpdate(
        order_id="ORD-1042",
        event_id="payment-1042",
        event=OrderEvent.CHECKOUT_PAID,
        customer_email=recipient,
        customer_name="Maya",
        total_cents=2400,
        currency="USD",
        item_title="Creator Lighting Presets",
    )
    accepted = await send_customer_update(update, InfraiEmailClient(api_key))
    print(accepted.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

