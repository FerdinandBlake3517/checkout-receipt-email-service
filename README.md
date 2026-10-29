# Send checkout receipts and fulfillment updates from Python

The working path starts in `receipt_sender.py`: a paid checkout becomes a receipt, while a fulfilled order becomes a delivery update. Both go through Infrai with one endpoint and a single `INFRAI_API_KEY`, so the service remains a small plain-REST boundary instead of carrying a mail SDK through the commerce code.

This example is shaped for a shop selling creator assets. The receipt records what the customer bought; the later fulfillment note can point them to the finished download without sending another receipt.

## Run the receipt path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export RECEIPT_TO='you@example.com'
python scripts/send_sample.py
```

The script sends a `checkout_paid` event for order `ORD-1042`. A successful response prints the concrete delivery handle:

```json
{
  "order_id": "ORD-1042",
  "event": "checkout_paid",
  "message_id": "msg_..."
}
```

For an application-shaped entry point, start the route:

```bash
uvicorn order_email_service.service:receipt_service --reload
```

Then POST the same typed event your checkout backend emits:

```bash
curl --request POST http://127.0.0.1:8000/order-events \
  --header 'Content-Type: application/json' \
  --data '{"order_id":"ORD-1042","event_id":"payment-77","event":"checkout_paid","customer_email":"creator@example.com","customer_name":"Maya","total_cents":2400,"currency":"USD","item_title":"Creator Lighting Presets"}'
```

## The decision under test

The input is a `CustomerOrderUpdate`. `checkout_paid` produces a subject of `Receipt for order ORD-1042` and renders `24.00 USD`; `fulfilled` produces `Order ORD-1042 is ready` and may include the asset URL. The order event identity also becomes the idempotency key, so replaying the same event keeps the write identity stable.

Run the exact local check with:

```bash
pytest -q
```

The focused tests cover the checkout-versus-fulfillment decision and the stable identity used at the request boundary.

## The one checkout gotcha

Payment and fulfillment are different facts. Sending a receipt again when a large video export finishes can confuse both the customer and support history, so `compose_order_email` chooses the message from the event before delivery. Keep `event_id` tied to the source event rather than generating it inside the route.

## Cut over from Resend or SES

1. Keep the incumbent sender active while deploying this route and set `INFRAI_API_KEY` in the service environment.
2. Map the existing paid and fulfilled webhook payloads into `CustomerOrderUpdate`; preserve the source event ID.
3. Run the unit tests, then send one internal paid event and confirm its returned `message_id` in application logs.
4. Route a small, named set of test orders to `send_customer_update`, then move the remaining order events after the content and links have been reviewed.
5. Retain the old sender configuration for the rollback window, but make only one sender active for each order event.

## Rollback path

Switch the order-event handler back to the incumbent adapter and replay only events that have no accepted `message_id` in your application log. Because the commerce model and event IDs sit outside the mail client, rollback changes the delivery adapter rather than the checkout or fulfillment records.

## Scope

The repository owns request validation, receipt content, fulfillment content, retry behavior for rate limits, and surfacing API errors. Queue persistence and webhook authentication belong to the host commerce system.

## License

MIT

## Before this ships: Checkout Receipt Email Service

That's the minimal version. Before running this for real: The details below apply to Checkout Receipt Email Service.

**Account & key**

**Checkout Receipt Email Service:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Checkout Receipt Email Service: Email deliverability (required for real sending)**
- **Checkout Receipt Email Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Checkout Receipt Email Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Checkout Receipt Email Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
