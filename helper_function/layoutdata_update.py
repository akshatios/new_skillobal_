from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import courses_collection, layout_collection
from helper_function.apis_requests import get_current_user

async def update_layout_by_rating():
    """Update layout collection based on course ratings"""
    try:
        # Get all courses directly from database
        courses_cursor = courses_collection.find({})
        courses = await courses_cursor.to_list(length=None)
        
        # Separate courses by rating
        high_rating_courses = []  # Rating >= 4
        low_rating_courses = []   # Rating < 4
        
        for course in courses:
            course_id = course["_id"]  # Already ObjectId from database
            if course.get("rating", 0) >= 4:
                high_rating_courses.append(course_id)
            else:
                low_rating_courses.append(course_id)
        
        # Update high rating layout (68d0d3643deb5b22c6613b61)
        await layout_collection.update_one(
            {"_id": ObjectId("68d0d3643deb5b22c6613b61")},
            {"$set": {"linked_courses": high_rating_courses}},
            upsert=True
        )
        
        # Update low rating layout (68d104bd896833b9498ad494)
        await layout_collection.update_one(
            {"_id": ObjectId("68d104bd896833b9498ad494")},
            {"$set": {"linked_courses": low_rating_courses}},
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Layout updated successfully",
            "data": {
                "high_rating_courses": len(high_rating_courses),
                "low_rating_courses": len(low_rating_courses),
                "total_courses": len(courses)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_layout_courses(
    layout_id: str,
    request: Request = None,
    token: str = Depends(get_current_user)
):
    """Get courses for specific layout"""
    try:
        layout = await layout_collection.find_one({"_id": ObjectId(layout_id)})
        if not layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        linked_course_ids = layout.get("linked_courses", [])
        courses = []
        
        for course_id in linked_course_ids:
            course = await courses_collection.find_one({"_id": course_id})
            if course:
                course["_id"] = str(course["_id"])
                if course.get("cat_id"):
                    course["cat_id"] = str(course["cat_id"])
                courses.append(course)
        
        return {
            "success": True,
            "layout_id": layout_id,
            "courses_count": len(courses),
            "data": courses
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_layout_endpoint(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Endpoint to manually update layout"""
    return await update_layout_by_rating()