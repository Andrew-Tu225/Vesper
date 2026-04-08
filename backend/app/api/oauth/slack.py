from fastapi import APIRouter

router = APIRouter(prefix="/slack", tags=["oauth-slack"])


@router.get("/install")
async def slack_install() -> dict:
    """Redirect user to Slack OAuth consent screen. (Phase 1.5)"""
    raise NotImplementedError


@router.get("/callback")
async def slack_callback() -> dict:
    """Handle Slack OAuth callback, upsert workspace, store token. (Phase 1.5)"""
    raise NotImplementedError
