from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection
from helper_function.apis_requests import get_current_user
from helper_function.validate_references import validate_course_references

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

async def get_all_courses_details(
    request: Request,
    token: str = Depends(get_current_user),
    page: int = 1, 
    limit: int = 10
):
    """Get all courses with pagination"""
    try:
        skip = (page - 1) * limit
        
        # Get total count
        total_courses = await courses_collection.count_documents({})
        
        # Get paginated courses
        courses_cursor = courses_collection.find({}).skip(skip).limit(limit)
        courses = await courses_cursor.to_list(length=None)
        
        # Validate references and fetch video details for each course
        for course in courses:
            # Validate and clean invalid references
            course = await validate_course_references(course)
            if "videos" in course and course["videos"]:
                try:
                    # Get individual video documents sorted by order
                    videos_cursor = courses_videos_collection.find({"_id": {"$in": course["videos"]}}).sort("order", 1)
                    videos_details = []
                    async for video in videos_cursor:
                        video["_id"] = str(video["_id"])
                        # Remove unwanted fields
                        video.pop("type", None)
                        video.pop("created_at", None)
                        videos_details.append(video)
                    course["videos_details"] = videos_details
                    course["total_videos"] = len(videos_details)
                except Exception as e:
                    course["videos_details"] = []
                    course["total_videos"] = 0
            else:
                course["videos_details"] = []
                course["total_videos"] = 0
            
            # Remove videos array (keep only videos_details)
            if "videos" in course:
                del course["videos"]
            
            # Clean intro_videos and images - remove type and uploaded_at
            if "intro_videos" in course and course["intro_videos"]:
                course["intro_videos"].pop("type", None)
                course["intro_videos"].pop("uploaded_at", None)
            
            if "images" in course and course["images"]:
                course["images"].pop("type", None)
                course["images"].pop("uploaded_at", None)
        
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