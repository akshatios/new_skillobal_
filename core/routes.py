from fastapi import APIRouter
from user.userRoutes import user_router
from courses.coursesRoutes import courses_router

# from dashboard.dashboard_router import dashboard_router
from ai_features.aiFeatureRoutes import aiFeatureRoutes

from dashboard.dashboardRoutes import dashboard_router
from languages.languagesRoutes import router as languages_router
from categories.categoriesRoutes import router as categories_router
from instructors.instructorsRoutes import router as instructors_router


api_router = APIRouter()

# Include all module routers
api_router.include_router(user_router)
api_router.include_router(courses_router)
# api_router.include_router(slider_router)
api_router.include_router(aiFeatureRoutes)

api_router.include_router(dashboard_router)
api_router.include_router(languages_router, prefix="/admin/languages", tags=["Languages"])
api_router.include_router(categories_router, prefix="/admin/categories", tags=["Categories"])
api_router.include_router(instructors_router, prefix="/admin/instructors", tags=["Instructors"])
