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
    video_order: Optional[str] = Form(None),
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
        orders = video_order.split(',') if video_order else []
        
        # Upload videos and prepare data
        new_videos_list = []
        for i, vid_file in enumerate(video_file):
            if vid_file.filename:
                # Upload video to Tencent
                video_content = await vid_file.read()
                video_result = await upload_to_tencent_vod(video_content, vid_file.filename)
                
                # Get order value, default to index if not provided
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
        
        # Handle video container logic
        videos_container_id = None
        
        if "videos" in existing_course and existing_course["videos"]:
            # Add to existing video container
            video_container = await courses_videos_collection.find_one({"_id": existing_course["videos"]})
            if video_container:
                existing_videos = video_container.get("videos", [])
                updated_videos = existing_videos + new_videos_list
                
                await courses_videos_collection.update_one(
                    {"_id": existing_course["videos"]},
                    {"$set": {"videos": updated_videos, "updated_at": current_time}}
                )
                videos_container_id = existing_course["videos"]
                logger.info(f"Added {len(new_videos_list)} videos to existing container")
            else:
                # Container not found, create new one
                video_container = {
                    "videos": new_videos_list,
                    "course_id": course_id,
                    "created_at": current_time
                }
                container_result = await courses_videos_collection.insert_one(video_container)
                videos_container_id = container_result.inserted_id
                
                # Update course with new container ID
                await courses_collection.update_one(
                    {"_id": ObjectId(course_id)},
                    {"$set": {"videos": videos_container_id, "updated_at": current_time}}
                )
                logger.info(f"Created new video container with {len(new_videos_list)} videos")
        else:
            # Create new video container
            video_container = {
                "videos": new_videos_list,
                "course_id": course_id,
                "created_at": current_time
            }
            container_result = await courses_videos_collection.insert_one(video_container)
            videos_container_id = container_result.inserted_id
            
            # Update course with new container ID
            await courses_collection.update_one(
                {"_id": ObjectId(course_id)},
                {"$set": {"videos": videos_container_id, "updated_at": current_time}}
            )
            logger.info(f"Created new video container with {len(new_videos_list)} videos")
        
        # Get updated videos for response
        video_container = await courses_videos_collection.find_one({"_id": videos_container_id})
        all_videos = video_container.get("videos", []) if video_container else []
        
        return {
            "success": True,
            "message": f"Successfully added {len(new_videos_list)} videos to course",
            "data": {
                "course_id": course_id,
                "videos_added": len(new_videos_list),
                "total_videos": len(all_videos),
                "new_videos": new_videos_list,
                "all_videos": all_videos
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding videos to course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add videos: {str(e)}")