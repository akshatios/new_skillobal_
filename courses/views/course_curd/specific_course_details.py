from fastapi import HTTPException, Depends
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection
from helper_function.apis_requests import get_current_user

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

async def get_specific_course_details(
    course_id: str,
    token: str = Depends(get_current_user)
):
    """Get complete details of a specific course including all videos"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Get course details
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Fetch complete video details
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
            except Exception as e:
                course["videos_details"] = []
        else:
            course["videos_details"] = []
        

        
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
        
        # Convert ObjectIds to strings
        course = convert_objectids(course)
        
        return {
            "success": True,
            "message": "Course details retrieved successfully",
            "data": course
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get course details: {str(e)}")