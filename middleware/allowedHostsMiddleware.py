from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class AllowedHostsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_hosts: list[str]):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        host = request.headers.get("host", "").split(":")[0]  # Extract the host
        if host not in self.allowed_hosts and "*" not in self.allowed_hosts:
            return JSONResponse({"detail": "Host not allowed"}, status_code=400)
        return await call_next(request)