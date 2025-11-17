import jwt
from bson import ObjectId
from fastapi import Request
from core.config import jwt_settings
from core.database import admins_collection
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class CheckUserExistsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            if request.method == "OPTIONS":
                return await call_next(request)
            excluded_paths = [
                "/admin/login",
                "/docs",
                "/redoc",
                "/openapi.json",
            ]
            # Skip the check for excluded paths
            if request.url.path in excluded_paths:
                return await call_next(request)
            
            token = request.headers.get("token")
            if not token:
                return JSONResponse({"msg": "token not present"}, status_code=400)
            
            decoded_token = jwt.decode(
                token, jwt_settings.SUGAR_VALUE, algorithms=["HS256"]
            )
            userId = decoded_token.get("id") 

            # Check if the user exists in the database
            user = await admins_collection.find_one({"_id": ObjectId(userId)})
            if not user:
                return JSONResponse({"msg": "no user found"}, status_code=404)

            # Proceed to the next middleware or endpoint
            return await call_next(request)
        except Exception as e:
            return JSONResponse({"msg": str(e)}, status_code=400)