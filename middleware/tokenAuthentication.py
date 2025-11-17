import jwt
from fastapi import Request
from core.config import jwt_settings
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class AccessTokenAuthenticatorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS requests first (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Define excluded paths
        excluded_paths = [
            "/admin/login",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        # Check if the request path is in the excluded list
        if request.url.path in excluded_paths:
            return await call_next(request)

        # Get the token from headers
        token = request.headers.get("token")
        if not token:
            return JSONResponse({"msg": "token not present"}, status_code=400)

        try:
            # Decode the token using the secret key
            decoded_token = jwt.decode(
                token, jwt_settings.SUGAR_VALUE, algorithms=["HS256"]
            )
            # Attach userId and otpId to the request state
            request.state.userId = decoded_token.get("id")
            request.state.otpId = decoded_token.get("otpId")
        except jwt.ExpiredSignatureError:
            return JSONResponse({"msg": "Token has expired"}, status_code=400)
        except jwt.InvalidTokenError:
            return JSONResponse({"msg": "Invalid token"}, status_code=400)
        except Exception as e:
            return JSONResponse(
                {"msg": "Something went wrong", "error": str(e)}, status_code=500
            )

        # Proceed to the next middleware or endpoint
        response = await call_next(request)
        return response