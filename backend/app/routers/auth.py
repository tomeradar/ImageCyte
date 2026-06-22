from fastapi import APIRouter, HTTPException, status
import httpx
import logging
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def proxy_login(payload: LoginRequest):
    """
    Proxies login request directly to the upstream server and returns the tokens.
    """
    logger.info(f"Auth Router: Received proxy login request for username '{payload.username}'...")
    async with httpx.AsyncClient(verify=False) as client:
        try:
            res = await client.post(
                f"{settings.UPSTREAM_URL.rstrip('/')}/api/auth/login",
                json=payload.model_dump()
            )
            if res.status_code == 200:
                logger.info(f"Auth Router: Upstream login succeeded for user '{payload.username}'. Returning token credentials.")
                return res.json()
            else:
                logger.warning(f"Auth Router: Upstream login failed for user '{payload.username}' with status code {res.status_code}.")
                raise HTTPException(
                    status_code=res.status_code,
                    detail=res.json().get("detail", "Authentication failed")
                )
        except httpx.HTTPError as e:
            logger.error(f"Auth Router: Network error proxying login request to upstream: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to upstream server: {e}"
            )

@router.post("/refresh", response_model=TokenResponse)
async def proxy_refresh(payload: RefreshRequest):
    """
    Proxies token refresh request directly to the upstream server.
    """
    logger.info("Auth Router: Received proxy token refresh request.")
    async with httpx.AsyncClient(verify=False) as client:
        try:
            res = await client.post(
                f"{settings.UPSTREAM_URL.rstrip('/')}/api/auth/refresh",
                json=payload.model_dump()
            )
            if res.status_code == 200:
                logger.info("Auth Router: Upstream token refresh succeeded. Returning new credentials.")
                return res.json()
            else:
                logger.warning(f"Auth Router: Upstream token refresh failed with status code {res.status_code}.")
                raise HTTPException(
                    status_code=res.status_code,
                    detail=res.json().get("detail", "Token refresh failed")
                )
        except httpx.HTTPError as e:
            logger.error(f"Auth Router: Network error proxying token refresh request to upstream: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to upstream server: {e}"
            )
