from fastapi import APIRouter, HTTPException, status
import httpx
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def proxy_login(payload: LoginRequest):
    """
    Proxies login request directly to the upstream server and returns the tokens.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            res = await client.post(
                f"{settings.UPSTREAM_URL.rstrip('/')}/api/auth/login",
                json=payload.model_dump()
            )
            if res.status_code == 200:
                return res.json()
            else:
                raise HTTPException(
                    status_code=res.status_code,
                    detail=res.json().get("detail", "Authentication failed")
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to upstream server: {e}"
            )

@router.post("/refresh", response_model=TokenResponse)
async def proxy_refresh(payload: RefreshRequest):
    """
    Proxies token refresh request directly to the upstream server.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            res = await client.post(
                f"{settings.UPSTREAM_URL.rstrip('/')}/api/auth/refresh",
                json=payload.model_dump()
            )
            if res.status_code == 200:
                return res.json()
            else:
                raise HTTPException(
                    status_code=res.status_code,
                    detail=res.json().get("detail", "Token refresh failed")
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to upstream server: {e}"
            )
