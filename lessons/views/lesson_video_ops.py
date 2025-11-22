from fastapi import HTTPException, Request, UploadFile, File, Form, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.video_upload import upload_to_tencent_vod
from helper_function.apis_requests import get_current_user
from typing import Optional
from datetime import datetime
import uuid

async def add_video_to_lesson(
    request: Request,
    course_id: str,
    lesson_id: str,
    token: str = Depends(get_current_user),
    video_title: str = Form(...),
    video_description: Optional[str] = Form(None),
    video_file: UploadFile = File(...)
):
    """Add video to a specific lesson"""
    try:
        # Check if course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Check if lesson exists
        lesson_found = False
        for lesson in course.get("lessons", []):
            if lesson.get("lesson_id") == lesson_id:
                lesson_found = True
                break

        if not lesson_found:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Upload video to Tencent VOD
        file_content = await video_file.read()
        tencent_result = await upload_to_tencent_vod(file_content, video_file.filename)

        # Create video object
        video_data = {
            "video_id": str(uuid.uuid4()),
            "fileId": tencent_result["file_id"],
            "videoUrl": tencent_result["video_url"],
            "video_title": video_title,
            "video_description": video_description or "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add video to lesson
        result = await courses_collection.update_one(
            {"_id": ObjectId(course_id), "lessons.lesson_id": lesson_id},
            {"$push": {"lessons.$.videos": video_data}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to add video to lesson")

        return {
            "success": True,
            "message": "Video added to lesson successfully",
            "data": {
                "course_id": course_id,
                "lesson_id": lesson_id,
                "video": video_data
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def delete_video_from_lesson(
    request: Request,
    course_id: str,
    lesson_id: str,
    video_id: str,
    token: str = Depends(get_current_user)
):
    """Delete video from a lesson"""
    try:
        # Check if course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Remove video from lesson
        result = await courses_collection.update_one(
            {"_id": ObjectId(course_id), "lessons.lesson_id": lesson_id},
            {"$pull": {"lessons.$.videos": {"video_id": video_id}}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete video or video not found")

        return {
            "success": True,
            "message": "Video deleted from lesson successfully",
            "data": {
                "course_id": course_id,
                "lesson_id": lesson_id,
                "video_id": video_id
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_video_in_lesson(
    request: Request,
    course_id: str,
    lesson_id: str,
    video_id: str,
    token: str = Depends(get_current_user),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None)
):
    """Update video details in a lesson"""
    try:
        # Check if course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Prepare update data
        update_data = {}
        if video_title is not None:
            update_data["lessons.$[lesson].videos.$[video].video_title"] = video_title
        if video_description is not None:
            update_data["lessons.$[lesson].videos.$[video].video_description"] = video_description

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update video in lesson
        result = await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": update_data},
            array_filters=[
                {"lesson.lesson_id": lesson_id},
                {"video.video_id": video_id}
            ]
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update video or video not found")

        return {
            "success": True,
            "message": "Video updated successfully",
            "data": {
                "course_id": course_id,
                "lesson_id": lesson_id,
                "video_id": video_id,
                "updated_fields": list(update_data.keys())
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))