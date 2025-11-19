from fastapi import APIRouter
from courses.views.course_curd.create_courses import create_course
from courses.views.course_curd.all_courses_details import get_all_courses_details
from courses.views.course_curd.categories import get_all_categories
from courses.views.course_curd.instructor import get_all_instructors
from languages.views.get_languages import get_all_languages
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
from courses.views.lessons.create_lesson import create_lesson
from courses.views.lessons.get_lessons import get_lessons, get_lesson_details
from courses.views.lessons.update_lesson import update_lesson
from courses.views.lessons.delete_lesson import delete_lesson
from courses.views.lessons.lesson_video_ops import add_video_to_lesson, delete_video_from_lesson, update_video_in_lesson
from helper_function.video_upload import upload_course_video, get_course_videos
from courses.views.lessons.update_lesson_video import update_video_by_file_id
from helper_function.delete_video import delete_video_by_file_id
from helper_function.layoutdata_update import update_layout_by_rating, get_layout_courses
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

# Categories, Languages and Instructors
courses_router.add_api_route("/categories/all", get_all_categories, methods=["GET"], description="Get all categories")
courses_router.add_api_route("/languages/all", get_all_languages, methods=["GET"], description="Get all languages")
courses_router.add_api_route("/instructors/all", get_all_instructors, methods=["GET"], description="Get all instructors")

# Lessons
courses_router.add_api_route("/courses/{course_id}/lessons/add", create_lesson, methods=["POST"], description="Create lesson")
courses_router.add_api_route("/courses/{course_id}/lessons", get_lessons, methods=["GET"], description="Get all lessons")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}", get_lesson_details, methods=["GET"], description="Get lesson details")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/update", update_lesson, methods=["PUT"], description="Update lesson")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/delete", delete_lesson, methods=["DELETE"], description="Delete lesson")

# Lesson Videos
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/add", add_video_to_lesson, methods=["POST"], description="Add video to lesson")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{video_id}/update", update_video_in_lesson, methods=["PUT"], description="Update video in lesson")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{video_id}/delete", delete_video_from_lesson, methods=["DELETE"], description="Delete video from lesson")

# Course Videos
courses_router.add_api_route("/courses/{course_id}/videos/upload", upload_course_video, methods=["POST"], description="Upload course video")
courses_router.add_api_route("/courses/{course_id}/videos", get_course_videos, methods=["GET"], description="Get course videos")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{fileId}/update", update_video_by_file_id, methods=["PUT"], description="Update video by file ID")
courses_router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{fileId}/delete", delete_video_by_file_id, methods=["DELETE"], description="Delete video by file ID")

# Layout Management
courses_router.add_api_route("/layout/update-by-rating", update_layout_by_rating, methods=["PUT"], description="Update layout based on course ratings")
courses_router.add_api_route("/layout/{layout_id}/courses", get_layout_courses, methods=["GET"], description="Get courses for specific layout")

