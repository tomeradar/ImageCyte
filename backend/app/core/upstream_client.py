import time
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class UpstreamClient:
    def __init__(self):
        self.base_url = settings.UPSTREAM_URL
        # Using a client with verification disabled to avoid local SSL trust issues
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0, verify=False)
        self.access_token = None
        self.refresh_token = None
        self.expires_at = 0  # Epoch timestamp when the access token expires
        
        # Token verification cache to protect the upstream server: token -> (user_info, cache_expiry)
        self.token_validation_cache = {}

    async def close(self):
        await self.client.aclose()

    async def login(self) -> bool:
        logger.info("Logging into upstream server...")
        try:
            res = await self.client.post(
                "/api/auth/login",
                json={
                    "username": settings.UPSTREAM_USERNAME,
                    "password": settings.UPSTREAM_PASSWORD
                }
            )
            if res.status_code == 200:
                data = res.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                # Store expires_at as current time + expires_in
                self.expires_at = time.time() + data.get("expires_in", 60)
                logger.info("Successfully logged into upstream server.")
                return True
            else:
                logger.error(f"Upstream login failed with status {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Upstream login exception: {e}")
            return False

    async def refresh_upstream_token(self) -> bool:
        if not self.refresh_token:
            return await self.login()
        
        logger.info("Refreshing upstream token...")
        try:
            res = await self.client.post(
                "/api/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            if res.status_code == 200:
                data = res.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self.expires_at = time.time() + data.get("expires_in", 60)
                logger.info("Successfully refreshed upstream token.")
                return True
            else:
                logger.warning(f"Upstream token refresh failed with status {res.status_code}. Re-authenticating...")
                return await self.login()
        except Exception as e:
            logger.error(f"Upstream token refresh exception: {e}. Re-authenticating...")
            return await self.login()

    async def get_valid_token(self) -> str:
        # If no token, or token expires in less than 5 seconds, refresh it
        if not self.access_token or time.time() > self.expires_at - 5:
            success = await self.refresh_upstream_token()
            if not success:
                raise Exception("Unable to get valid token from upstream server")
        return self.access_token

    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        # Get valid access token
        token = await self.get_valid_token()
        
        # Prepare headers
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        res = await self.client.request(method, endpoint, **kwargs)
        
        # Handle transparent retry if we get a 401
        if res.status_code == 401:
            logger.warning(f"Received 401 on {endpoint} from upstream. Retrying with refreshed token...")
            success = await self.refresh_upstream_token()
            if success:
                token = self.access_token
                headers["Authorization"] = f"Bearer {token}"
                kwargs["headers"] = headers
                res = await self.client.request(method, endpoint, **kwargs)
                
        return res

    async def validate_client_token(self, token: str) -> dict | None:
        """
        Validates the client's token by hitting the upstream /api/auth/me endpoint.
        Uses in-memory cache to prevent redundant HTTP requests for concurrent operations.
        """
        now = time.time()
        
        # Check cache
        if token in self.token_validation_cache:
            user_info, cache_expiry = self.token_validation_cache[token]
            if now < cache_expiry:
                return user_info
            else:
                del self.token_validation_cache[token]

        # Call upstream server to validate
        try:
            res = await self.client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                user_info = res.json()
                # Cache the validation for 15 seconds
                self.token_validation_cache[token] = (user_info, now + 15)
                return user_info
            else:
                logger.warning(f"Client token validation failed on upstream with status {res.status_code}")
                return None
        except Exception as e:
            logger.error(f"Client token validation exception: {e}")
            return None

upstream_client = UpstreamClient()
