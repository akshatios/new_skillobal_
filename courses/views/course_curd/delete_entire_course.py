from fastapi import HTTPException, Depends
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection
from helper_function.video_upload import delete_from_tencent_vod
from helper_function.apis_requests import get_current_user
import logging

logger = logging.getLogger(__name__)

async def delete_from_tencent_vod_image(file_id: str):
    """Delete image from Tencent VOD (same function as video delete)"""
    try:
        return await delete_from_tencent_vod(file_id)
    except Exception as e:
        logger.error(f"Failed to delete image {file_id}: {str(e)}")
        return False

async def delete_entire_course(
    course_id: str,
    token: str = Depends(get_current_user)
):
    """Delete entire course and all associated media from Tencent Cloud and database"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Find the course
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        deleted_files = []
        failed_deletions = []
        
        # Delete course images from Tencent VOD
        if "images" in course and course["images"]:
            for image in course["images"]:
                if "fileId" in image and image["fileId"]:
                    success = await delete_from_tencent_vod_image(image["fileId"])
                    if success:
                        deleted_files.append(f"Image: {image['fileId']}")
                    else:
                        failed_deletions.append(f"Image: {image['fileId']}")
        
        # Delete intro videos from Tencent VOD
        if "intro_videos" in course and course["intro_videos"]:
            for intro_video in course["intro_videos"]:
                if "fileId" in intro_video and intro_video["fileId"]:
                    success = await delete_from_tencent_vod(intro_video["fileId"])
                    if success:
                        deleted_files.append(f"Intro Video: {intro_video['fileId']}")
                    else:
                        failed_deletions.append(f"Intro Video: {intro_video['fileId']}")
        
        # Delete course videos from Tencent VOD and video container
        if "videos" in course and course["videos"]:
            video_container = await courses_videos_collection.find_one({"_id": course["videos"]})
            if video_container and "videos" in video_container:
                for video in video_container["videos"]:
                    if "fileId" in video and video["fileId"]:
                        success = await delete_from_tencent_vod(video["fileId"])
                        if success:
                            deleted_files.append(f"Video: {video['fileId']}")
                        else:
                            failed_deletions.append(f"Video: {video['fileId']}")
                
                # Delete video container from database
                await courses_videos_collection.delete_one({"_id": course["videos"]})
        
        # Delete course from database
        await courses_collection.delete_one({"_id": ObjectId(course_id)})
        
        # Prepare response
        response = {
            "success": True,
            "message": "Course deleted successfully",
            "data": {
                "course_id": course_id,
                "course_title": course.get("title", "Unknown"),
                "deleted_files": deleted_files,
                "failed_deletions": failed_deletions,
                "total_deleted": len(deleted_files),
                "total_failed": len(failed_deletions)
            }
        }
        
        if failed_deletions:
            response["message"] += f" (Warning: {len(failed_deletions)} files could not be deleted from Tencent Cloud)"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete course: {str(e)}")