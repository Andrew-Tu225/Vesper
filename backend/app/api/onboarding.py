"""Onboarding API routes.

Handles the channels_setup step: listing available Slack channels and saving
the user's selection to workspace.settings.enrichment_channels.

Flow
----
1. User completes LinkedIn OAuth → redirected to ?step=channels_setup.
2. Frontend calls GET /api/onboarding/channels to render the picker.
3. User selects channels and submits.
4. Frontend calls POST /api/onboarding/channels with {channel_ids: [...]}.
5. API saves selection, sets onboarding_complete = True.
6. Frontend navigates to the main app.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.slack_client import SlackClientError, get_workspace_client, list_channels

router = APIRouter(tags=["onboarding"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChannelItem(BaseModel):
    id: str
    name: str
    member_count: int


class ChannelListResponse(BaseModel):
    channels: list[ChannelItem]


class SetChannelsRequest(BaseModel):
    channel_ids: list[str] = Field(..., description="Slack channel IDs to monitor")

    @field_validator("channel_ids")
    @classmethod
    def must_be_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("channel_ids must contain at least one channel")
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for cid in v:
            if cid not in seen:
                seen.add(cid)
                deduped.append(cid)
        return deduped


class SetChannelsResponse(BaseModel):
    status: str
    enrichment_channels: list[str]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _get_workspace(db: AsyncSession, user: User) -> Workspace:
    """Load the first workspace the user belongs to.

    Raises HTTP 400 if the user has no workspace (Slack OAuth not yet done).
    """
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workspace found — complete Slack OAuth first",
        )
    return workspace


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/channels", response_model=ChannelListResponse)
async def get_channels(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChannelListResponse:
    """List Slack channels available for monitoring.

    Calls conversations.list via the workspace's bot token and returns all
    non-archived public and private channels the bot can see. Used to populate
    the channel picker in the onboarding UI.

    Returns HTTP 503 if the bot token is missing or Slack is unreachable.
    """
    workspace = await _get_workspace(db, user)

    try:
        client = await asyncio.to_thread(get_workspace_client, str(workspace.id))
        raw_channels = await asyncio.to_thread(list_channels, client)
    except SlackClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Slack: {exc}",
        )

    channels = [
        ChannelItem(
            id=ch["id"],
            name=ch["name"],
            member_count=ch["num_members"],
        )
        for ch in raw_channels
    ]

    return ChannelListResponse(channels=channels)


@router.post("/channels", response_model=SetChannelsResponse)
async def set_channels(
    body: SetChannelsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SetChannelsResponse:
    """Save the selected channels and complete onboarding.

    Writes channel_ids to workspace.settings.enrichment_channels, sets
    onboarding_step = "done" and onboarding_complete = True, and writes an
    AuditLog entry. After this call the intake scanner can run for the workspace.
    """
    workspace = await _get_workspace(db, user)

    # Write settings as a new dict — SQLAlchemy does not track in-place JSONB mutations
    workspace.settings = {
        **workspace.settings,
        "enrichment_channels": body.channel_ids,
    }
    workspace.onboarding_step = "done"
    workspace.onboarding_complete = True

    audit = AuditLog(
        workspace_id=workspace.id,
        entity_type="workspace",
        entity_id=workspace.id,
        action="channels_setup",
        old_value=None,
        new_value={"enrichment_channels": body.channel_ids},
        actor=user.email,
    )
    db.add(audit)
    await db.commit()

    return SetChannelsResponse(
        status="ok",
        enrichment_channels=body.channel_ids,
    )
