from fastapi import APIRouter
from lessons.views.create_lesson import create_lesson
from lessons.views.get_lessons import get_lessons, get_lesson_details
from lessons.views.update_lesson import update_lesson
from lessons.views.delete_lesson import delete_lesson
from lessons.views.lesson_video_ops import add_video_to_lesson, delete_video_from_lesson, update_video_in_lesson
from lessons.views.update_lesson_video import update_video_by_file_id
from helper_function.delete_video import delete_video_by_file_id

router = APIRouter()

# Lesson CRUD operations
router.add_api_route("/courses/{course_id}/lessons/add", create_lesson, methods=["POST"], description="Create lesson")
router.add_api_route("/courses/{course_id}/lessons", get_lessons, methods=["GET"], description="Get all lessons")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}", get_lesson_details, methods=["GET"], description="Get lesson details")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/update", update_lesson, methods=["PUT"], description="Update lesson")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/delete", delete_lesson, methods=["DELETE"], description="Delete lesson")

# Lesson Video operations
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/add", add_video_to_lesson, methods=["POST"], description="Add video to lesson")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{video_id}/update", update_video_in_lesson, methods=["PUT"], description="Update video in lesson")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{video_id}/delete", delete_video_from_lesson, methods=["DELETE"], description="Delete video from lesson")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{fileId}/update", update_video_by_file_id, methods=["PUT"], description="Update video by file ID")
router.add_api_route("/courses/{course_id}/lessons/{lesson_id}/videos/{fileId}/delete", delete_video_by_file_id, methods=["DELETE"], description="Delete video by file ID")