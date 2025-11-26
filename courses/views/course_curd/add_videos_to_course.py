from fastapi import HTTPException, Depends, Form, File, UploadFile
from typing import Optional, List
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection
from helper_function.video_upload import upload_to_tencent_vod
from helper_function.apis_requests import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def add_videos_to_course(
    course_id: str,
    token: str = Depends(get_current_user),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None),
    order: Optional[str] = Form(None),
    video_file: List[UploadFile] = File(...)
):
    """Add new videos to existing course"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Check course exists
        existing_course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not existing_course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Validate video files
        if not video_file or len(video_file) == 0 or not video_file[0].filename:
            raise HTTPException(status_code=400, detail="At least one video file is required")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Parse comma-separated metadata
        titles = video_title.split(',') if video_title else []
        descriptions = video_description.split(',') if video_description else []
        orders = order.split(',') if order else []
        
        # Upload videos and prepare data
        new_videos_list = []
        for i, vid_file in enumerate(video_file):
            if vid_file.filename:
                # Upload video to Tencent
                video_content = await vid_file.read()
                video_result = await upload_to_tencent_vod(video_content, vid_file.filename)
                
                # Simple order - use provided order or increment
                order_value = int(orders[i].strip()) if i < len(orders) and orders[i].strip().isdigit() else i + 1
                
                video_obj = {
                    "order": order_value,
                    "video_title": titles[i].strip() if i < len(titles) else f"Video {i+1}",
                    "video_description": descriptions[i].strip() if i < len(descriptions) else "",
                    "fileId": video_result["file_id"],
                    "videoUrl": video_result["video_url"],
                    "type": "video",
                    "uploaded_at": current_time
                }
                new_videos_list.append(video_obj)
                logger.info(f"Video uploaded: {video_result['file_id']}")
        
        if not new_videos_list:
            raise HTTPException(status_code=400, detail="No valid videos were uploaded")
        
        # Insert individual video documents
        new_video_ids = []
        for video_obj in new_videos_list:
            video_obj["course_id"] = course_id
            video_result = await courses_videos_collection.insert_one(video_obj)
            new_video_ids.append(video_result.inserted_id)
        
        # Update course with new video IDs
        existing_video_ids = existing_course.get("videos", [])
        updated_video_ids = existing_video_ids + new_video_ids
        
        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": {"videos": updated_video_ids, "updated_at": current_time}}
        )
        
        # Get all videos for response sorted by order
        all_videos_cursor = courses_videos_collection.find({"_id": {"$in": updated_video_ids}}).sort("order", 1)
        all_videos = []
        async for video in all_videos_cursor:
            video["_id"] = str(video["_id"])
            all_videos.append(video)
        
        return {
            "success": True,
            "message": f"Successfully added {len(new_videos_list)} videos to course",
            "data": {
                "course_id": course_id,
                "videos_added": len(new_videos_list),
                "total_videos": len(all_videos),
                "new_video_ids": [str(vid_id) for vid_id in new_video_ids],
                "all_videos": all_videos
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding videos to course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add videos: {str(e)}")