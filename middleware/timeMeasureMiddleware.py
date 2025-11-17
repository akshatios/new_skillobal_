import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class ExecutionTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()  # Record the start time
        response = await call_next(request)  # Process the request
        end_time = time.time()  # Record the end time
        execution_time = end_time - start_time  # Calculate execution time

        # Add the execution time to the response headers
        response.headers["X-Execution-Time"] = f"{execution_time:.4f} seconds"

        # Optionally, log the execution time
        print(f"API {request.url.path} took {execution_time:.4f} seconds")

        return response