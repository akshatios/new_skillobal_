from fastapi import APIRouter
from courses.views.course_curd.create_courses import create_course
from courses.views.course_curd.all_courses_details import get_all_courses_details
from courses.views.course_curd.top_courses import get_top_courses
from courses.views.course_curd.visible_courses import get_visible_courses
from courses.views.course_curd.visible_T_F import toggle_course_visibility
from courses.views.course_curd.delete_entire_course import delete_entire_course
from courses.views.course_curd.delete_all_intro_videos import delete_all_intro_videos_from_tencent
from courses.views.course_curd.delete_all_course_videos import delete_all_course_videos_from_tencent
from courses.views.course_curd.update_course import update_course
from courses.views.course_curd.add_videos_to_course import add_videos_to_course
from courses.views.course_curd.update_course_video import update_course_video_by_fileid, delete_course_video_by_fileid
from courses.views.course_curd.specific_course_details import get_specific_course_details
from helper_function.video_upload import upload_course_video, get_course_videos
from helper_function.layoutdata_update import update_layout_endpoint, get_layout_courses
from documentation.userRoutesAPIDocumentation import *

courses_router = APIRouter(prefix="/admin", tags=["Courses"])

# Course CRUD
courses_router.add_api_route("/courses/add", create_course, methods=["POST"], description="Create new course")
courses_router.add_api_route("/courses/all", get_all_courses_details, methods=["GET"], description="Get all courses with pagination")
courses_router.add_api_route("/courses/{course_id}/details", get_specific_course_details, methods=["GET"], description="Get specific course full details")
courses_router.add_api_route("/courses/visible", get_visible_courses, methods=["GET"], description="Get visible courses")
courses_router.add_api_route("/courses/top", get_top_courses, methods=["GET"], description="Get top courses")
courses_router.add_api_route("/courses/{course_id}/update", update_course, methods=["PUT"], description="Update course with smart file replacement")
courses_router.add_api_route("/courses/{course_id}/videos/add", add_videos_to_course, methods=["POST"], description="Add videos to existing course")
courses_router.add_api_route("/courses/{course_id}/videos/{file_id}/update", update_course_video_by_fileid, methods=["PUT"], description="Update specific course video by fileId")
courses_router.add_api_route("/courses/{course_id}/videos/{file_id}/delete", delete_course_video_by_fileid, methods=["DELETE"], description="Delete specific course video by fileId")
courses_router.add_api_route("/courses/{course_id}/visibility/toggle", toggle_course_visibility, methods=["PUT"], description="Toggle course visibility")
courses_router.add_api_route("/courses/{course_id}/delete", delete_entire_course, methods=["DELETE"], description="Delete entire course and all media")
courses_router.add_api_route("/intro-videos/delete-all", delete_all_intro_videos_from_tencent, methods=["DELETE"], description="Delete all intro videos from collection and Tencent Cloud")
courses_router.add_api_route("/course-videos/delete-all", delete_all_course_videos_from_tencent, methods=["DELETE"], description="Delete all course videos from collection and Tencent Cloud")

# Course Videos
courses_router.add_api_route("/courses/{course_id}/videos/upload", upload_course_video, methods=["POST"], description="Upload course video")
courses_router.add_api_route("/courses/{course_id}/videos", get_course_videos, methods=["GET"], description="Get course videos")

# Layout Management
courses_router.add_api_route("/layout/update-by-rating", update_layout_endpoint, methods=["PUT"], description="Update layout based on course ratings")
# courses_router.add_api_route("/layout/{layout_id}/courses", get_layout_courses, methods=["GET"], description="Get courses for specific layout")

