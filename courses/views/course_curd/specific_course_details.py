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
                # Get individual video documents
                videos_cursor = courses_videos_collection.find({"_id": {"$in": course["videos"]}})
                videos_details = []
                async for video in videos_cursor:
                    video["_id"] = str(video["_id"])
                    videos_details.append(video)
                
                # Sort videos by order
                videos_details.sort(key=lambda x: x.get("order", 0))
                
                course["videos_details"] = videos_details
                course["total_videos"] = len(videos_details)
            except Exception as e:
                course["videos_details"] = []
                course["total_videos"] = 0
        else:
            course["videos_details"] = []
            course["total_videos"] = 0
        
        # Add summary statistics
        course["summary"] = {
            "total_images": 1 if course.get("images") else 0,
            "total_intro_videos": 1 if course.get("intro_videos") else 0,
            "total_course_videos": course["total_videos"],
            "has_content": (
                course.get("images") is not None or 
                course.get("intro_videos") is not None or 
                course["total_videos"] > 0
            )
        }
        
        # Add backward compatibility fields
        course["image_url"] = course["images"]["course_image_url"] if course.get("images") else None
        course["intro_video"] = course["intro_videos"]["videoUrl"] if course.get("intro_videos") else None
        
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