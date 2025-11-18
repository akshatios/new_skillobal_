from fastapi import HTTPException, Depends, Form, File, UploadFile
from typing import Optional
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection
from helper_function.video_upload import upload_to_tencent_vod, delete_from_tencent_vod
from helper_function.apis_requests import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def update_course_video_by_fileid(
    course_id: str,
    file_id: str,
    token: str = Depends(get_current_user),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None),
    video_order: Optional[int] = Form(None),
    video_file: Optional[UploadFile] = File(None)
):
    """Update specific course video by fileId - can update title, description, order, or replace video file"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Check course exists
        existing_course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not existing_course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if course has videos container
        if "videos" not in existing_course or not existing_course["videos"]:
            raise HTTPException(status_code=404, detail="Course has no videos")
        
        # Get video container
        video_container = await courses_videos_collection.find_one({"_id": existing_course["videos"]})
        if not video_container or "videos" not in video_container:
            raise HTTPException(status_code=404, detail="Video container not found")
        
        # Find video by fileId
        videos_list = video_container["videos"]
        video_index = -1
        target_video = None
        
        for i, video in enumerate(videos_list):
            if video.get("fileId") == file_id:
                video_index = i
                target_video = video
                break
        
        if video_index == -1:
            raise HTTPException(status_code=404, detail=f"Video with fileId {file_id} not found")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_file_to_delete = None
        
        # Prepare updated video data
        updated_video = target_video.copy()
        
        # Update metadata fields if provided
        if video_title is not None:
            updated_video["video_title"] = video_title
        if video_description is not None:
            updated_video["video_description"] = video_description
        if video_order is not None:
            updated_video["order"] = video_order
        
        # Handle video file replacement
        if video_file and video_file.filename:
            # Store old fileId for deletion
            old_file_to_delete = target_video.get("fileId")
            
            # Upload new video to Tencent
            video_content = await video_file.read()
            video_result = await upload_to_tencent_vod(video_content, video_file.filename)
            
            # Update video with new file data
            updated_video["fileId"] = video_result["file_id"]
            updated_video["videoUrl"] = video_result["video_url"]
            updated_video["updated_at"] = current_time
            
            logger.info(f"New video uploaded: {video_result['file_id']}")
        
        # Update video in the list
        videos_list[video_index] = updated_video
        
        # Update video container in database
        await courses_videos_collection.update_one(
            {"_id": existing_course["videos"]},
            {"$set": {"videos": videos_list, "updated_at": current_time}}
        )
        
        # Background cleanup: Delete old video file from Tencent
        if old_file_to_delete:
            try:
                success = await delete_from_tencent_vod(old_file_to_delete)
                if success:
                    logger.info(f"Successfully deleted old video from Tencent: {old_file_to_delete}")
                else:
                    logger.warning(f"Failed to delete old video from Tencent: {old_file_to_delete}")
            except Exception as e:
                logger.error(f"Error deleting old video {old_file_to_delete}: {str(e)}")
        
        return {
            "success": True,
            "message": "Course video updated successfully",
            "data": {
                "course_id": course_id,
                "updated_video": updated_video,
                "video_index": video_index,
                "old_file_deleted": old_file_to_delete if old_file_to_delete else None,
                "total_videos": len(videos_list)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating course video {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update video: {str(e)}")

async def delete_course_video_by_fileid(
    course_id: str,
    file_id: str,
    token: str = Depends(get_current_user)
):
    """Delete specific course video by fileId"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Check course exists
        existing_course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not existing_course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if course has videos container
        if "videos" not in existing_course or not existing_course["videos"]:
            raise HTTPException(status_code=404, detail="Course has no videos")
        
        # Get video container
        video_container = await courses_videos_collection.find_one({"_id": existing_course["videos"]})
        if not video_container or "videos" not in video_container:
            raise HTTPException(status_code=404, detail="Video container not found")
        
        # Find and remove video by fileId
        videos_list = video_container["videos"]
        video_to_delete = None
        updated_videos = []
        
        for video in videos_list:
            if video.get("fileId") == file_id:
                video_to_delete = video
            else:
                updated_videos.append(video)
        
        if not video_to_delete:
            raise HTTPException(status_code=404, detail=f"Video with fileId {file_id} not found")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update video container in database
        await courses_videos_collection.update_one(
            {"_id": existing_course["videos"]},
            {"$set": {"videos": updated_videos, "updated_at": current_time}}
        )
        
        # Delete video from Tencent
        deleted_from_tencent = False
        try:
            success = await delete_from_tencent_vod(file_id)
            if success:
                deleted_from_tencent = True
                logger.info(f"Successfully deleted video from Tencent: {file_id}")
            else:
                logger.warning(f"Failed to delete video from Tencent: {file_id}")
        except Exception as e:
            logger.error(f"Error deleting video {file_id}: {str(e)}")
        
        return {
            "success": True,
            "message": "Course video deleted successfully",
            "data": {
                "course_id": course_id,
                "deleted_video": video_to_delete,
                "deleted_from_tencent": deleted_from_tencent,
                "remaining_videos": len(updated_videos)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course video {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")