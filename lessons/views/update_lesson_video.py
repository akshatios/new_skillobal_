from fastapi import HTTPException, UploadFile, File, Form, Request, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.video_upload import upload_to_tencent_vod
from helper_function.apis_requests import get_current_user
from typing import Optional

async def update_video_by_file_id(
    request: Request,
    course_id: str,
    lesson_id: str, 
    fileId: str,
    video_file: UploadFile = File(...),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None),
    order: Optional[int] = Form(None),
    token: str = Depends(get_current_user)
):
    """Update lesson video by fileId - replaces old video with new one"""
    try:
        # Check course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Read new video file content
        file_content = await video_file.read()
        
        # Upload new video to Tencent Cloud VOD
        tencent_result = await upload_to_tencent_vod(file_content, video_file.filename)

        # Prepare updated video data
        updated_video = {
            "fileId": tencent_result["file_id"],
            "videoUrl": tencent_result["video_url"],
            "video_title": video_title or video_file.filename,
            "video_description": video_description or "",
            "order": order or 1
        }

        # Update video in course lessons by fileId
        update_result = await courses_collection.update_one(
            {
                "_id": ObjectId(course_id),
                "lessons.lesson_id": lesson_id,
                "lessons.videos.fileId": fileId
            },
            {
                "$set": {
                    "lessons.$.videos.$[video].fileId": updated_video["fileId"],
                    "lessons.$.videos.$[video].videoUrl": updated_video["videoUrl"],
                    "lessons.$.videos.$[video].video_title": updated_video["video_title"],
                    "lessons.$.videos.$[video].video_description": updated_video["video_description"],
                    "lessons.$.videos.$[video].order": updated_video["order"]
                }
            },
            array_filters=[{"video.fileId": fileId}]
        )

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lesson or video not found")

        return {
            "success": True,
            "message": "Lesson video updated successfully",
            "data": updated_video
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))