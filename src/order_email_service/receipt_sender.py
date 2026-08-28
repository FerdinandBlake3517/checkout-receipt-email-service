from dataclasses import dataclass
from html import escape

from .infrai_client import InfraiEmailClient
from .models import CustomerOrderUpdate, DeliveryAccepted, OrderEvent


@dataclass(frozen=True)
class OrderEmail:
    subject: str
    html: str
    idempotency_key: str


def compose_order_email(update: CustomerOrderUpdate) -> OrderEmail:
    order_id = escape(update.order_id)
    name = escape(update.customer_name)
    title = escape(update.item_title)
    amount = f"{update.total_cents / 100:.2f} {update.currency}"
    key = f"order-email:{update.order_id}:{update.event.value}:{update.event_id}"

    if update.event is OrderEvent.CHECKOUT_PAID:
        return OrderEmail(
            subject=f"Receipt for order {update.order_id}",
            html=(
                f"<h1>Thanks, {name}</h1>"
                f"<p>Your payment for {title} is complete.</p>"
                f"<p>Order <strong>{order_id}</strong>: {amount}</p>"
            ),
            idempotency_key=key,
        )

    access = ""
    if update.download_url:
        safe_url = escape(update.download_url, quote=True)
        access = f'<p><a href="{safe_url}">Open your purchase</a></p>'
    return OrderEmail(
        subject=f"Order {update.order_id} is ready",
        html=f"<h1>Your order is ready, {name}</h1><p>{title} has been fulfilled.</p>{access}",
        idempotency_key=key,
    )


async def send_customer_update(
    update: CustomerOrderUpdate, client: InfraiEmailClient
) -> DeliveryAccepted:
    email = compose_order_email(update)
    message_id = await client.send(
        to=str(update.customer_email),
        subject=email.subject,
        html=email.html,
        idempotency_key=email.idempotency_key,
    )
    return DeliveryAccepted(
        order_id=update.order_id,
        event=update.event,
        message_id=message_id,
    )

