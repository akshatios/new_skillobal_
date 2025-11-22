from fastapi import HTTPException, Request, Form, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.apis_requests import get_current_user
from typing import Optional
from datetime import datetime

async def update_lesson(
    request: Request,
    course_id: str,
    lesson_id: str,
    token: str = Depends(get_current_user),
    lesson_title: Optional[str] = Form(None),
    lesson_description: Optional[str] = Form(None),
    order: Optional[int] = Form(None)
):
    """Update an existing lesson"""
    try:
        # Check if course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Find lesson in course
        lesson_found = False
        for lesson in course.get("lessons", []):
            if lesson.get("lesson_id") == lesson_id:
                lesson_found = True
                break

        if not lesson_found:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Prepare update data
        update_data = {"lessons.$.updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        if lesson_title is not None:
            update_data["lessons.$.lesson_title"] = lesson_title
        if lesson_description is not None:
            update_data["lessons.$.lesson_description"] = lesson_description
        if order is not None:
            update_data["lessons.$.order"] = order

        # Update lesson
        result = await courses_collection.update_one(
            {"_id": ObjectId(course_id), "lessons.lesson_id": lesson_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update lesson")

        return {
            "success": True,
            "message": "Lesson updated successfully",
            "data": {
                "lesson_id": lesson_id,
                "course_id": course_id,
                "updated_fields": list(update_data.keys())
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))