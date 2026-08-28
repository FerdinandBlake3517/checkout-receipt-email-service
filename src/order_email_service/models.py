from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class OrderEvent(str, Enum):
    CHECKOUT_PAID = "checkout_paid"
    FULFILLED = "fulfilled"


class CustomerOrderUpdate(BaseModel):
    order_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    event: OrderEvent
    customer_email: EmailStr
    customer_name: str = Field(min_length=1)
    total_cents: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    item_title: str = Field(min_length=1)
    download_url: str | None = None


class DeliveryAccepted(BaseModel):
    order_id: str
    event: OrderEvent
    message_id: str

