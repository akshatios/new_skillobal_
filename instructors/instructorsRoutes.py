from fastapi import APIRouter
from instructors.views.get_instructors import get_all_instructors

router = APIRouter()

# Instructor operations
router.add_api_route("/all", get_all_instructors, methods=["GET"], description="Get all instructors")