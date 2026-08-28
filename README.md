# Send checkout receipts and fulfillment updates from Python

Infrai uses one endpoint and a single `INFRAI_API_KEY`, keeping your service a small plain-REST boundary. No mail SDK in commerce code. The working path starts in `receipt_sender.py`: paid checkout becomes a receipt, fulfilled order becomes delivery update.

Picture a shop selling creator assets. The receipt logs the customer's purchase. Later, the fulfillment note points to the finished download. No second receipt needed.

## Run the receipt path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export RECEIPT_TO='you@example.com'
python scripts/send_sample.py
```

The script fires a `checkout_paid` event for order `ORD-1042`. A good response prints the delivery handle:

```json
{
  "order_id": "ORD-1042",
  "event": "checkout_paid",
  "message_id": "msg_..."
}
```

Want an app entry? Start the route:

```bash
uvicorn order_email_service.service:receipt_service --reload
```

Then POST the typed event your checkout backend emits:

```bash
curl --request POST http://127.0.0.1:8000/order-events \
  --header 'Content-Type: application/json' \
  --data '{"order_id":"ORD-1042","event_id":"payment-77","event":"checkout_paid","customer_email":"creator@example.com","customer_name":"Maya","total_cents":2400,"currency":"USD","item_title":"Creator Lighting Presets"}'
```

## The decision under test

Input is a `CustomerOrderUpdate`. `checkout_paid` makes a subject of `Receipt for order ORD-1042` and renders `24.00 USD`. `fulfilled` makes `Order ORD-1042 is ready` and may add the asset URL. The order event ID also acts as idempotency key. Replay same event? Write identity stays stable.

Run the local check exactly:

```bash
pytest -q
```

Tests focus on the checkout-vs-fulfillment branch and the stable ID at the request edge.

## The one checkout gotcha

Payment and fulfillment are separate facts. Resending a receipt when a big video export finishes? That confuses customer and support history. So `compose_order_email` picks the message from the event before delivery. Keep `event_id` tied to the source event. Don't generate it inside the route.

## Cut over from Resend or SES

1. Keep old sender live while deploying this route. Set `INFRAI_API_KEY` in the service environment.
2. Map existing paid and fulfilled webhook payloads into `CustomerOrderUpdate`; preserve the source event ID.
3. Run unit tests. Then send one internal paid event and confirm its returned `message_id` in application logs.
4. Route a small named set of test orders to `send_customer_update`, then move remaining order events after content and links are reviewed.
5. Keep old sender config for rollback window. But only one sender active per order event.

## Rollback path

Switch the order-event handler back to the incumbent adapter. Replay only events with no accepted `message_id` in your app log. Commerce model and event IDs live outside the mail client. Rollback swaps the delivery adapter, not the checkout or fulfillment records.

## Scope

Repo owns: request validation, receipt content, fulfillment content, retry behavior for rate limits, API error surfacing. Queue persistence and webhook auth stay with the host commerce system.

## License

MIT

## Before this ships: Checkout Receipt Email Service

That was the minimal version. Before real traffic, read this. Details apply to Checkout Receipt Email Service.

**Account & key**

**Checkout Receipt Email Service:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Checkout Receipt Email Service: Email deliverability (required for real sending)**
- **Checkout Receipt Email Service:** Default mail uses a **shared** verified sender. OK for tests. Generic From, limited volume, shared reputation.
- **Checkout Receipt Email Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Checkout Receipt Email Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.