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
        
        # Check if course has videos
        if "videos" not in existing_course or not existing_course["videos"]:
            raise HTTPException(status_code=404, detail="Course has no videos")
        
        # Handle both old and new video formats
        video_ids = existing_course["videos"]
        if not isinstance(video_ids, list):
            video_ids = [video_ids] if video_ids else []
        
        # Find video document by fileId
        target_video = await courses_videos_collection.find_one({
            "_id": {"$in": video_ids},
            "fileId": file_id
        })
        
        if not target_video:
            raise HTTPException(status_code=404, detail=f"Video with fileId {file_id} not found")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_file_to_delete = None
        
        # Prepare update data
        update_data = {"updated_at": current_time}
        
        # Update metadata fields if provided
        if video_title is not None:
            update_data["video_title"] = video_title
        if video_description is not None:
            update_data["video_description"] = video_description
        if video_order is not None:
            update_data["order"] = video_order
        
        # Handle video file replacement
        if video_file and video_file.filename:
            # Store old fileId for deletion
            old_file_to_delete = target_video.get("fileId")
            
            # Upload new video to Tencent
            video_content = await video_file.read()
            video_result = await upload_to_tencent_vod(video_content, video_file.filename)
            
            # Update video with new file data
            update_data["fileId"] = video_result["file_id"]
            update_data["videoUrl"] = video_result["video_url"]
            
            logger.info(f"New video uploaded: {video_result['file_id']}")
        
        # Update video document in database
        await courses_videos_collection.update_one(
            {"_id": target_video["_id"]},
            {"$set": update_data}
        )
        
        # Get updated video for response
        updated_video = await courses_videos_collection.find_one({"_id": target_video["_id"]})
        updated_video["_id"] = str(updated_video["_id"])
        
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
                "old_file_deleted": old_file_to_delete if old_file_to_delete else None
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
        
        # Check if course has videos
        if "videos" not in existing_course or not existing_course["videos"]:
            raise HTTPException(status_code=404, detail="Course has no videos")
        
        # Handle both old and new video formats
        video_ids = existing_course["videos"]
        if not isinstance(video_ids, list):
            video_ids = [video_ids] if video_ids else []
        
        # Find video document by fileId
        video_to_delete = await courses_videos_collection.find_one({
            "_id": {"$in": video_ids},
            "fileId": file_id
        })
        
        if not video_to_delete:
            raise HTTPException(status_code=404, detail=f"Video with fileId {file_id} not found")
        
        # Remove video from course videos array
        updated_video_ids = [vid_id for vid_id in video_ids if vid_id != video_to_delete["_id"]]
        
        # Update course with new video IDs array
        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": {"videos": updated_video_ids}}
        )
        
        # Delete video document
        await courses_videos_collection.delete_one({"_id": video_to_delete["_id"]})
        
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
                "deleted_video": {
                    "_id": str(video_to_delete["_id"]),
                    "fileId": video_to_delete["fileId"],
                    "video_title": video_to_delete.get("video_title")
                },
                "deleted_from_tencent": deleted_from_tencent,
                "remaining_videos": len(updated_video_ids)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course video {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")