import os

from fastapi import Depends, FastAPI

from .infrai_client import InfraiEmailClient
from .models import CustomerOrderUpdate, DeliveryAccepted
from .receipt_sender import send_customer_update

receipt_service = FastAPI(title="Checkout receipt email service")


def email_client() -> InfraiEmailClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiEmailClient(api_key)


@receipt_service.post("/order-events", response_model=DeliveryAccepted)
async def accept_order_event(
    update: CustomerOrderUpdate,
    client: InfraiEmailClient = Depends(email_client),
) -> DeliveryAccepted:
    return await send_customer_update(update, client)

