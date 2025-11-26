from fastapi import APIRouter
from dashboard.views.dashboard_home import get_dashboard_home

dashboard_router = APIRouter(prefix="/admin", tags=["Dashboard"])

# Dashboard routes
dashboard_router.add_api_route("/dashboard", get_dashboard_home, methods=["GET"], description="Get dashboard home data with statistics")