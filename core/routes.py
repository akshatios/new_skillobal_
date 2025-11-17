from fastapi import APIRouter
from user.userRoutes import user_router
# from middleware.auth_router import auth_router
# from sliders.slider_router import slider_router
from courses.coursesRoutes import courses_router
# from dashboard.dashboard_router import dashboard_router
from ai_features.aiFeatureRoutes import aiFeatureRoutes

api_router = APIRouter()

# Include all module routers
# api_router.include_router(auth_router)
# api_router.include_router(dashboard_router)
api_router.include_router(user_router)
api_router.include_router(courses_router)
# api_router.include_router(slider_router)
api_router.include_router(aiFeatureRoutes)