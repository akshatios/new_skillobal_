from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.apis_requests import get_current_user

async def toggle_course_visibility(
    course_id: str,
    request: Request,
    token: str = Depends(get_current_user)
):
    """Toggle course visibility between true and false"""
    try:
        try:
            object_id = ObjectId(course_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid course ID format")
        
        # Get current course
        course = await courses_collection.find_one({"_id": object_id})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Toggle visibility
        current_visible = course.get("visible", False)
        new_visible = not current_visible
        
        # Update course
        await courses_collection.update_one(
            {"_id": object_id},
            {"$set": {"visible": new_visible}}
        )
        
        return {
            "success": True,
            "message": "Course is now visible" if new_visible else "Course is now hidden",
            "data": {
                "course_id": course_id,
                "previous_visible": current_visible,
                "current_visible": new_visible
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))