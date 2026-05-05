"""
publishing queue — LinkedIn post delivery.

publish_post
    Delivers an approved DraftPost to LinkedIn via the UGC Posts API.
    Uses the psycopg2 sync pool (same pattern as intake.py and draft_pipeline.py).
    Retries on transient failures (network errors, 401, 429).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.db_sync import get_sync_pool
from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)

_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_LINKEDIN_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"

# Fallback expiry values when LinkedIn omits them in the refresh response
_DEFAULT_ACCESS_EXPIRES_SECONDS = 5_183_944   # ~60 days
_DEFAULT_REFRESH_EXPIRES_SECONDS = 31_536_000  # ~365 days


# ---------------------------------------------------------------------------
# Sync token refresh helper
# ---------------------------------------------------------------------------

def _refresh_linkedin_token_sync(user_id: UUID) -> bool:
    """Refresh the LinkedIn access token for user_id using psycopg2 + requests.

    Reads the refresh token from oauth_token, calls LinkedIn's token endpoint,
    and writes the new access + refresh tokens back.

    Returns True on success, False on any failure (token missing, HTTP error,
    decrypt error, DB write error).
    """
    import requests as req_lib

    from app.config import settings
    from app.crypto import EncryptedToken, TokenDecryptionError, decrypt, encrypt

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT encrypted_token, nonce, tag
                FROM oauth_token
                WHERE user_id = %s::uuid
                  AND provider = 'linkedin_personal'
                  AND token_type = 'refresh'
                LIMIT 1
                """,
                (str(user_id),),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        logger.warning("_refresh_linkedin_token_sync: no refresh token for user %s", user_id)
        return False

    try:
        refresh_token = decrypt(
            EncryptedToken(
                ciphertext=bytes(row[0]),
                nonce=bytes(row[1]),
                tag=bytes(row[2]),
            )
        )
    except TokenDecryptionError:
        logger.exception("_refresh_linkedin_token_sync: decrypt failed for user %s", user_id)
        return False

    try:
        resp = req_lib.post(
            _LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except req_lib.RequestException:
        logger.exception(
            "_refresh_linkedin_token_sync: HTTP request failed for user %s", user_id
        )
        return False

    try:
        body = resp.json()
    except ValueError:
        logger.error(
            "_refresh_linkedin_token_sync: invalid JSON in response for user %s", user_id
        )
        return False

    if "access_token" not in body:
        logger.error(
            "_refresh_linkedin_token_sync: no access_token in response for user %s", user_id
        )
        return False

    now = datetime.now(tz=timezone.utc)
    access_expires_in: int = body.get("expires_in", _DEFAULT_ACCESS_EXPIRES_SECONDS)
    refresh_expires_in: int = body.get(
        "refresh_token_expires_in", _DEFAULT_REFRESH_EXPIRES_SECONDS
    )
    new_refresh_token: str = body.get("refresh_token", refresh_token)

    new_access = encrypt(body["access_token"])
    new_refresh_enc = encrypt(new_refresh_token)

    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE oauth_token
                SET encrypted_token = %s, nonce = %s, tag = %s, expires_at = %s
                WHERE user_id = %s::uuid
                  AND provider = 'linkedin_personal'
                  AND token_type = 'access'
                """,
                (
                    new_access.ciphertext,
                    new_access.nonce,
                    new_access.tag,
                    now + timedelta(seconds=access_expires_in),
                    str(user_id),
                ),
            )
            cur.execute(
                """
                UPDATE oauth_token
                SET encrypted_token = %s, nonce = %s, tag = %s, expires_at = %s
                WHERE user_id = %s::uuid
                  AND provider = 'linkedin_personal'
                  AND token_type = 'refresh'
                """,
                (
                    new_refresh_enc.ciphertext,
                    new_refresh_enc.nonce,
                    new_refresh_enc.tag,
                    now + timedelta(seconds=refresh_expires_in),
                    str(user_id),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception(
            "_refresh_linkedin_token_sync: DB write failed for user %s", user_id
        )
        return False
    finally:
        pool.putconn(conn)

    logger.info("_refresh_linkedin_token_sync: refreshed token for user %s", user_id)
    return True


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.publishing.publish_post",
    queue=Queue.PUBLISHING,
    bind=True,
    max_retries=5,
    default_retry_delay=120,
)
def publish_post(self, draft_post_id: str) -> None:
    """Deliver an approved DraftPost to LinkedIn.

    1. Load DraftPost row (psycopg2 sync).
    2. Guard: already published → return early.
    3. Load OAuthToken for publisher_user_id, provider='linkedin_personal'.
    4. If token is near expiry (<5 min), refresh inline.
    5. Decrypt access token.
    6. POST https://api.linkedin.com/v2/ugcPosts.
    7. On success: write published_at, linkedin_post_id; set ContentSignal.status='posted'.
    8. Update Slack card via _posted_blocks() (non-fatal).
    9. On transient errors: self.retry(). 400 bad payload: log and return.
    """
    import requests as req_lib

    from app.crypto import EncryptedToken, TokenDecryptionError, decrypt

    pool = get_sync_pool()

    # ------------------------------------------------------------------
    # Step 1: Load DraftPost
    # ------------------------------------------------------------------
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content_signal_id, workspace_id, body,
                       published_at, publisher_user_id,
                       slack_message_ts, slack_channel_id
                FROM draft_post
                WHERE id = %s::uuid
                """,
                (draft_post_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        logger.warning("publish_post: draft_post_id=%s not found", draft_post_id)
        return

    (
        post_id,
        signal_id,
        workspace_id,
        body,
        published_at,
        publisher_user_id,
        slack_ts,
        slack_channel,
    ) = row

    # ------------------------------------------------------------------
    # Step 2: Guard — no publisher means we can't deliver
    # ------------------------------------------------------------------
    if publisher_user_id is None:
        logger.error(
            "publish_post: %s has no publisher_user_id — cannot publish", draft_post_id
        )
        return

    publisher_user_id = UUID(str(publisher_user_id))

    # ------------------------------------------------------------------
    # Step 3: Load access token + person URN
    # ------------------------------------------------------------------
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT encrypted_token, nonce, tag, expires_at, provider_user_id
                FROM oauth_token
                WHERE user_id = %s::uuid
                  AND provider = 'linkedin_personal'
                  AND token_type = 'access'
                LIMIT 1
                """,
                (str(publisher_user_id),),
            )
            access_row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if access_row is None:
        logger.error(
            "publish_post: no LinkedIn access token for user %s", publisher_user_id
        )
        return

    enc_token, nonce, tag, expires_at, person_id = access_row

    # ------------------------------------------------------------------
    # Step 4: Check expiry — refresh inline if within 5 minutes
    # ------------------------------------------------------------------
    now = datetime.now(tz=timezone.utc)
    # Normalise to aware datetime in case psycopg2 returns a naive object
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or (expires_at - now).total_seconds() < 300:
        logger.info(
            "publish_post: access token near/past expiry for user %s — refreshing",
            publisher_user_id,
        )
        if not _refresh_linkedin_token_sync(publisher_user_id):
            logger.error(
                "publish_post: token refresh failed for user %s", publisher_user_id
            )
            raise self.retry(exc=RuntimeError("LinkedIn token refresh failed"))

        # Reload the freshly written token
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT encrypted_token, nonce, tag, provider_user_id
                    FROM oauth_token
                    WHERE user_id = %s::uuid
                      AND provider = 'linkedin_personal'
                      AND token_type = 'access'
                    LIMIT 1
                    """,
                    (str(publisher_user_id),),
                )
                refreshed_row = cur.fetchone()
        finally:
            pool.putconn(conn)

        if refreshed_row is None:
            raise self.retry(exc=RuntimeError("LinkedIn access token missing after refresh"))

        enc_token, nonce, tag, person_id = refreshed_row

    # ------------------------------------------------------------------
    # Step 5: Decrypt access token
    # ------------------------------------------------------------------
    try:
        access_token = decrypt(
            EncryptedToken(
                ciphertext=bytes(enc_token),
                nonce=bytes(nonce),
                tag=bytes(tag),
            )
        )
    except TokenDecryptionError:
        logger.exception(
            "publish_post: failed to decrypt access token for user %s", publisher_user_id
        )
        raise self.retry(exc=RuntimeError("LinkedIn token decryption failed"))

    if not person_id:
        logger.error(
            "publish_post: no provider_user_id (LinkedIn person sub) for user %s",
            publisher_user_id,
        )
        return

    # ------------------------------------------------------------------
    # Step 6: POST to LinkedIn UGC Posts API
    # ------------------------------------------------------------------
    ugc_payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": body},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    try:
        resp = req_lib.post(
            _LINKEDIN_UGC_URL,
            json=ugc_payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            timeout=30,
        )
    except req_lib.RequestException as exc:
        logger.warning(
            "publish_post: network error for %s — retrying: %s", draft_post_id, exc
        )
        raise self.retry(exc=exc)

    if resp.status_code == 400:
        logger.error(
            "publish_post: LinkedIn 400 bad payload for %s — %s",
            draft_post_id,
            resp.text,
        )
        return  # bad payload will not succeed on retry

    if resp.status_code == 401:
        logger.warning(
            "publish_post: LinkedIn 401 for %s — refreshing token and retrying",
            draft_post_id,
        )
        if not _refresh_linkedin_token_sync(publisher_user_id):
            logger.error(
                "publish_post: 401 and token refresh failed for user %s — giving up",
                publisher_user_id,
            )
            return
        raise self.retry(exc=RuntimeError("LinkedIn 401 unauthorized"), countdown=10)

    if resp.status_code == 429:
        logger.warning(
            "publish_post: LinkedIn 429 rate-limited for %s — retrying with backoff",
            draft_post_id,
        )
        raise self.retry(exc=RuntimeError("LinkedIn 429 rate-limited"), countdown=300)

    if not resp.ok:
        logger.error(
            "publish_post: LinkedIn %s for %s — %s",
            resp.status_code,
            draft_post_id,
            resp.text,
        )
        raise self.retry(exc=RuntimeError(f"LinkedIn HTTP {resp.status_code}"))

    # ------------------------------------------------------------------
    # Step 7: Parse X-RestLi-Id header for post URN
    # ------------------------------------------------------------------
    linkedin_post_id: str = resp.headers.get("X-RestLi-Id", "")
    now = datetime.now(tz=timezone.utc)

    logger.info(
        "publish_post: posted %s → linkedin_post_id=%s", draft_post_id, linkedin_post_id
    )

    # ------------------------------------------------------------------
    # Step 8: Atomic write-back — guard against concurrent workers
    # ------------------------------------------------------------------
    # Use WHERE published_at IS NULL so only one worker wins if two tasks
    # race. If RETURNING returns no rows, another worker already published.
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_post
                SET published_at = %s, linkedin_post_id = %s
                WHERE id = %s::uuid
                  AND published_at IS NULL
                RETURNING id
                """,
                (now, linkedin_post_id, draft_post_id),
            )
            if cur.fetchone() is None:
                logger.info(
                    "publish_post: %s already written by concurrent worker — skip",
                    draft_post_id,
                )
                return
            cur.execute(
                """
                UPDATE content_signal
                SET status = 'posted'
                WHERE id = %s::uuid
                """,
                (str(signal_id),),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("publish_post: DB write-back failed for %s", draft_post_id)
        raise
    finally:
        pool.putconn(conn)

    # ------------------------------------------------------------------
    # Step 9: Update Slack card (non-fatal)
    # ------------------------------------------------------------------
    if slack_ts and slack_channel:
        try:
            from app.services.approval import _posted_blocks
            from app.services.slack_client import get_workspace_client, update_message

            client = get_workspace_client(str(workspace_id))
            update_message(client, slack_channel, slack_ts, _posted_blocks(linkedin_post_id))
        except Exception:
            logger.warning(
                "publish_post: failed to update Slack card for %s",
                draft_post_id,
                exc_info=True,
            )