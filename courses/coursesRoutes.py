from fastapi import APIRouter
from courses.views.course_curd.create_courses import create_course
from documentation.userRoutesAPIDocumentation import *

courses_router = APIRouter(prefix="/admin", tags=["Users"])
courses_router.add_api_route("/courses/add", create_course, methods=["POST"], description="Create new course")

