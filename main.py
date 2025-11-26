from core.routes import api_router
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from middleware.allowedHostsMiddleware import AllowedHostsMiddleware
from middleware.timeMeasureMiddleware import ExecutionTimeMiddleware
from middleware.checkUserExistsMiddleware import CheckUserExistsMiddleware
from middleware.tokenAuthentication import AccessTokenAuthenticatorMiddleware

app = FastAPI(title="Skillobal API")

# Custom exception handler for consistent response format
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "massage": exc.detail
        }
    )

# Updated CORS origins to include HTTPS domain
origins = ["*"]

allowed_hosts = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep all existing middleware in same order
app.add_middleware(AllowedHostsMiddleware, allowed_hosts)
# Add the custom middleware
app.add_middleware(AccessTokenAuthenticatorMiddleware)
app.add_middleware(CheckUserExistsMiddleware)
#app.add_middleware(ExecutionTimeMiddleware)

# Include all routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 
