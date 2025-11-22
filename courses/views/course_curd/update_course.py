from fastapi import HTTPException, Depends, Form, File, UploadFile
from typing import Optional
from bson import ObjectId
from core.database import courses_collection
from helper_function.video_upload import upload_to_tencent_vod, delete_from_tencent_vod
from helper_function.image_upload import upload_image_to_tencent
from helper_function.apis_requests import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def update_course(
    course_id: str,
    token: str = Depends(get_current_user),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),  # Comma-separated IDs
    language_id: Optional[str] = Form(None),  # Comma-separated IDs
    visible: Optional[bool] = Form(None),
    course_image_url: Optional[UploadFile] = File(None),
    course_intro_video: Optional[UploadFile] = File(None),
    rating: Optional[float] = Form(None),
    price: Optional[float] = Form(None),
    instructor_id: Optional[str] = Form(None)  # Comma-separated IDs
):
    """Update course basic info with smart file replacement (no videos)"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        # Get existing course
        existing_course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not existing_course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_files_to_delete = []  # Track old files for cleanup
        
        # Prepare update data - only include fields that are provided
        update_data = {"updated_at": current_time}
        
        # Update only provided fields, keep existing values for others
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if category_id is not None:
            update_data["category_id"] = [ObjectId(id.strip()) for id in category_id.split(',') if id.strip() and id.strip() != "string"]
        if language_id is not None:
            update_data["language_id"] = [ObjectId(id.strip()) for id in language_id.split(',') if id.strip() and id.strip() != "string"]
        if visible is not None:
            update_data["visible"] = visible
        if rating is not None:
            update_data["rating"] = rating
        if price is not None:
            update_data["price"] = price
        if instructor_id is not None:
            update_data["instructor_id"] = [ObjectId(id.strip()) for id in instructor_id.split(',') if id.strip() and id.strip() != "string"]
        
        # Handle course image update
        if course_image_url and course_image_url.filename:
            # Get old image fileId for deletion
            if "images" in existing_course and existing_course["images"]:
                old_image = existing_course["images"]
                if "fileId" in old_image and old_image["fileId"]:
                    old_files_to_delete.append(old_image["fileId"])
            
            # Upload new image
            course_image_content = await course_image_url.read()
            course_image_result = await upload_image_to_tencent(course_image_content, course_image_url.filename)
            
            new_image_obj = {
                "fileId": course_image_result["file_id"],
                "course_image_url": course_image_result["image_url"],
                "type": "course_image",
                "uploaded_at": current_time
            }
            update_data["images"] = new_image_obj
            logger.info(f"New course image uploaded: {course_image_result['file_id']}")
        
        # Handle intro video update
        if course_intro_video and course_intro_video.filename:
            # Get old intro video fileId for deletion
            if "intro_videos" in existing_course and existing_course["intro_videos"]:
                old_intro_video = existing_course["intro_videos"]
                if "fileId" in old_intro_video and old_intro_video["fileId"]:
                    old_files_to_delete.append(old_intro_video["fileId"])
            
            # Upload new intro video
            course_intro_video_content = await course_intro_video.read()
            course_intro_video_result = await upload_to_tencent_vod(course_intro_video_content, course_intro_video.filename)
            
            new_intro_video_obj = {
                "fileId": course_intro_video_result["file_id"],
                "videoUrl": course_intro_video_result["video_url"],
                "type": "intro_video",
                "uploaded_at": current_time
            }
            update_data["intro_videos"] = new_intro_video_obj
            logger.info(f"New intro video uploaded: {course_intro_video_result['file_id']}")
        
        # Update course in database
        result = await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to course")
        
        # Background cleanup: Delete old files from Tencent
        deleted_files = []
        failed_deletions = []
        
        for old_file_id in old_files_to_delete:
            try:
                success = await delete_from_tencent_vod(old_file_id)
                if success:
                    deleted_files.append(old_file_id)
                    logger.info(f"Successfully deleted old file from Tencent: {old_file_id}")
                else:
                    failed_deletions.append(old_file_id)
                    logger.warning(f"Failed to delete old file from Tencent: {old_file_id}")
            except Exception as e:
                failed_deletions.append(old_file_id)
                logger.error(f"Error deleting old file {old_file_id}: {str(e)}")
        
        # Get updated course for response
        updated_course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        
        # Format response
        response_data = {
            "_id": course_id,
            "title": updated_course["title"],
            "description": updated_course["description"],
            "category_id": [str(id) for id in updated_course.get("category_id", [])],
            "language_id": [str(id) for id in updated_course.get("language_id", [])],
            "visible": updated_course["visible"],
            "rating": updated_course.get("rating", 0.0),
            "price": updated_course.get("price", 0.0),
            "instructor_id": [str(id) for id in updated_course.get("instructor_id", [])],
            "images": updated_course.get("images"),
            "intro_videos": updated_course.get("intro_videos"),
            "image_url": updated_course["images"]["course_image_url"] if updated_course.get("images") else None,
            "intro_video": updated_course["intro_videos"]["videoUrl"] if updated_course.get("intro_videos") else None,
            "updated_at": current_time,
            "cleanup_info": {
                "old_files_deleted": deleted_files,
                "failed_deletions": failed_deletions
            }
        }
        
        return {
            "success": True,
            "message": "Course updated successfully",
            "data": response_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update course: {str(e)}")