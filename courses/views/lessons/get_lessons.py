from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.apis_requests import get_current_user

async def get_lessons(
    request: Request,
    course_id: str,
    token: str = Depends(get_current_user)
):
    """Get all lessons for a course"""
    try:
        # Find course with lessons
        course = await courses_collection.find_one(
            {"_id": ObjectId(course_id)},
            {"lessons": 1, "title": 1, "_id": 1}
        )
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        lessons = course.get("lessons", [])
        
        # Sort lessons by order
        lessons.sort(key=lambda x: x.get("order", 0))

        return {
            "success": True,
            "message": "Lessons retrieved successfully",
            "data": {
                "course_id": course_id,
                "course_title": course.get("title"),
                "total_lessons": len(lessons),
                "lessons": lessons
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_lesson_details(
    request: Request,
    course_id: str,
    lesson_id: str,
    token: str = Depends(get_current_user)
):
    """Get specific lesson details"""
    try:
        # Find course
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Find specific lesson
        lesson = None
        for l in course.get("lessons", []):
            if l.get("lesson_id") == lesson_id:
                lesson = l
                break

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        return {
            "success": True,
            "message": "Lesson details retrieved successfully",
            "data": {
                "course_id": course_id,
                "lesson": lesson
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))