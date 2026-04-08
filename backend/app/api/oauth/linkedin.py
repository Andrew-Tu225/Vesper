from fastapi import APIRouter

router = APIRouter(prefix="/linkedin", tags=["oauth-linkedin"])


@router.get("/install")
async def linkedin_install() -> dict:
    """Redirect user to LinkedIn OAuth consent screen. (Phase 1.6)"""
    raise NotImplementedError


@router.get("/callback")
async def linkedin_callback() -> dict:
    """Handle LinkedIn OAuth callback, encrypt + store tokens. (Phase 1.6)"""
    raise NotImplementedError
