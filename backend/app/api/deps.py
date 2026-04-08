import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request, status

from app.config import settings

_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


async def verify_slack_signature(
    request: Request,
    x_slack_request_timestamp: str = Header(...),
    x_slack_signature: str = Header(...),
) -> None:
    """
    FastAPI dependency that verifies Slack's request signature.

    Apply per-route (not globally) on every endpoint that receives Slack events
    or interactivity payloads.

    Raises HTTP 401 if the signature is missing, stale, or invalid.
    """
    now = int(time.time())
    try:
        timestamp = int(x_slack_request_timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp")

    if abs(now - timestamp) > _TIMESTAMP_TOLERANCE_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request timestamp too old")

    body = await request.body()
    basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

    expected = (
        "v0="
        + hmac.new(
            settings.slack_signing_secret.encode(),
            basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected, x_slack_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature")
