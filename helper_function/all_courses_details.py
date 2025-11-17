from fastapi import HTTPException, Query
from bson import ObjectId
from core.database import courses_collection

def convert_objectids(obj):
    """Recursively convert ObjectIds to strings"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectids(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectids(item) for item in obj]
    else:
        return obj

async def get_all_courses_details(page: int = 1, limit: int = 10):
    try:
        skip = (page - 1) * limit
        
        # Get total count
        total_courses = await courses_collection.count_documents({})
        
        # Get paginated courses
        courses_cursor = courses_collection.find({}).skip(skip).limit(limit)
        courses = await courses_cursor.to_list(length=None)
        
        courses = convert_objectids(courses)
        
        total_pages = (total_courses + limit - 1) // limit
        
        return {
            "success": True,
            "message": f"Retrieved {len(courses)} courses successfully",
            "data": courses,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_courses": total_courses,
                "limit": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))