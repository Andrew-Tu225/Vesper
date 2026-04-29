"""Billing API — Stripe Checkout, portal, and webhook endpoints.

GET  /api/billing/status                  → subscription state + publishable key
POST /api/billing/create-checkout-session → { checkout_url }
POST /api/billing/create-portal-session   → { portal_url }
POST /api/billing/webhook                 → Stripe event handler (no session auth)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_workspace_for_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace

stripe.api_key = settings.stripe_secret_key

router = APIRouter(tags=["billing"])

# Stripe subscription status → Vesper subscription_status
_STRIPE_STATUS_MAP: dict[str, str] = {
    "active": "active",
    "trialing": "active",
    "past_due": "suspended",
    "unpaid": "suspended",
    "canceled": "cancelled",
    "incomplete_expired": "cancelled",
    "incomplete": "suspended",
    "paused": "suspended",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _load_workspace(workspace_id: UUID, db: AsyncSession) -> Workspace:
    """Load the full Workspace row by ID. Raises 404 if missing."""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


async def _workspace_by_customer(customer_id: str, db: AsyncSession) -> Workspace | None:
    """Look up a workspace by its Stripe customer ID. Returns None if not found."""
    result = await db.execute(
        select(Workspace).where(Workspace.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status")
async def billing_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Return the workspace's current subscription state.

    Response shape:
    ```json
    {
      "subscription_status": "trialing",
      "trial_ends_at": "2026-05-28T00:00:00Z",
      "days_remaining": 29,
      "stripe_customer_id": null,
      "stripe_publishable_key": "pk_test_..."
    }
    ```
    `days_remaining` is null when the workspace is not on a trial or
    `trial_ends_at` is unset. `stripe_publishable_key` is always returned so
    the frontend can initialise Stripe.js without a build-time env var.
    """
    workspace_id = await get_workspace_for_user(user, db)
    workspace = await _load_workspace(workspace_id, db)

    days_remaining: int | None = None
    if workspace.subscription_status == "trialing" and workspace.trial_ends_at:
        delta = workspace.trial_ends_at - datetime.now(tz=timezone.utc)
        days_remaining = max(0, delta.days)

    return {
        "subscription_status": workspace.subscription_status,
        "trial_ends_at": workspace.trial_ends_at,
        "days_remaining": days_remaining,
        "stripe_customer_id": workspace.stripe_customer_id,
        "stripe_publishable_key": settings.stripe_publishable_key,
    }


@router.post("/create-checkout-session", status_code=status.HTTP_200_OK)
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a Stripe Checkout session and return the redirect URL.

    If the workspace has no Stripe Customer yet, one is created and
    `stripe_customer_id` is persisted before the session is opened — this
    prevents duplicate customer records if the user clicks Upgrade twice.

    Returns:
        `{ "checkout_url": "https://checkout.stripe.com/..." }`
    """
    workspace_id = await get_workspace_for_user(user, db)
    workspace = await _load_workspace(workspace_id, db)

    customer_id = workspace.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=workspace.name,
            metadata={"workspace_id": str(workspace.id)},
        )
        customer_id = customer.id
        workspace.stripe_customer_id = customer_id
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=f"{settings.app_frontend_url}/settings?billing=success",
        cancel_url=f"{settings.app_frontend_url}/settings?billing=cancel",
        metadata={"workspace_id": str(workspace.id)},
    )

    return {"checkout_url": session.url}


@router.post("/create-portal-session", status_code=status.HTTP_200_OK)
async def create_portal_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a Stripe Billing Portal session and return the redirect URL.

    Requires the workspace to already have a `stripe_customer_id`, meaning
    the user must have previously started or completed a Checkout session.

    Returns:
        `{ "portal_url": "https://billing.stripe.com/..." }`

    Raises:
        400 if no Stripe customer has been created for this workspace yet.
    """
    workspace_id = await get_workspace_for_user(user, db)
    workspace = await _load_workspace(workspace_id, db)

    if not workspace.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found — complete checkout first",
        )

    session = stripe.billing_portal.Session.create(
        customer=workspace.stripe_customer_id,
        return_url=f"{settings.app_frontend_url}/settings",
    )

    return {"portal_url": session.url}


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process inbound Stripe webhook events.

    The raw request body is read directly via `request.body()` so Stripe's
    HMAC signature can be verified before any parsing. FastAPI must not
    consume the body (no Pydantic model parameter) or signature verification
    will always fail.

    Handled events:

    | Event                             | Effect                                          |
    |-----------------------------------|-------------------------------------------------|
    | customer.subscription.created    | status → active, store stripe_subscription_id  |
    | customer.subscription.updated    | sync Stripe status → Vesper status              |
    | customer.subscription.deleted    | status → cancelled, clear stripe_subscription_id|
    | invoice.payment_succeeded        | ensure status → active                          |
    | invoice.payment_failed           | status → suspended                              |

    Status mapping (Stripe → Vesper):
    - active / trialing          → active
    - past_due / unpaid / incomplete / paused → suspended
    - canceled / incomplete_expired           → cancelled
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload"
        )

    event_type: str = event["type"]
    obj = event["data"]["object"]

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await _handle_subscription_event(event_type, obj, db)
    elif event_type == "invoice.payment_succeeded":
        await _handle_invoice_event(obj, "active", db)
    elif event_type == "invoice.payment_failed":
        await _handle_invoice_event(obj, "suspended", db)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Webhook sub-handlers
# ---------------------------------------------------------------------------


async def _handle_subscription_event(
    event_type: str,
    subscription: dict,
    db: AsyncSession,
) -> None:
    """Sync workspace billing state from a subscription lifecycle event."""
    customer_id: str = subscription["customer"]
    workspace = await _workspace_by_customer(customer_id, db)
    if workspace is None:
        return  # customer not in our system — skip

    if event_type == "customer.subscription.created":
        workspace.subscription_status = "active"
        workspace.stripe_subscription_id = subscription["id"]
    elif event_type == "customer.subscription.updated":
        stripe_status: str = subscription.get("status", "")
        workspace.subscription_status = _STRIPE_STATUS_MAP.get(stripe_status, "suspended")
        workspace.stripe_subscription_id = subscription["id"]
    elif event_type == "customer.subscription.deleted":
        workspace.subscription_status = "cancelled"
        workspace.stripe_subscription_id = None

    await db.commit()


async def _handle_invoice_event(
    invoice: dict,
    new_status: str,
    db: AsyncSession,
) -> None:
    """Update workspace subscription_status from a payment invoice event."""
    customer_id: str = invoice["customer"]
    workspace = await _workspace_by_customer(customer_id, db)
    if workspace is None:
        return

    workspace.subscription_status = new_status
    await db.commit()