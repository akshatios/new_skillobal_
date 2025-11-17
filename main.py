from core.routes import api_router
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from middleware.allowedHostsMiddleware import AllowedHostsMiddleware
from middleware.timeMeasureMiddleware import ExecutionTimeMiddleware
from middleware.checkUserExistsMiddleware import CheckUserExistsMiddleware
from middleware.tokenAuthentication import AccessTokenAuthenticatorMiddleware

app = FastAPI(title="Skillobal API")

# Updated CORS origins to include HTTPS domain
origins = [
    "*"                       # For development only, allows all origins
]

allowed_hosts = ["*"]  # In production, consider: ["a.com", "www.a.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # If we convert it to allow_origins=["*"] it will allow all origins -> so we implemented CORS_ALLOW_ALL_ORIGINS = True from django to fastapi
    allow_credentials=False, # For development only, when origins is "*", credentials cannot be true
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

    # uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    # gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000
    # Remove-Item -Path "prom-metrics\*" -Recurse -Force