from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import courses_collection
from helper_function.apis_requests import get_current_user
from helper_function.video_upload import delete_from_tencent_vod

async def delete_video_by_file_id(
    request: Request,
    course_id: str,
    lesson_id: str, 
    fileId: str,
    token: str = Depends(get_current_user)
):
    """Delete video by fileId from lesson"""
    try:
        # Check course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Delete video from course lessons by fileId
        delete_result = await courses_collection.update_one(
            {
                "_id": ObjectId(course_id),
                "lessons.lesson_id": lesson_id
            },
            {
                "$pull": {
                    "lessons.$.videos": {"fileId": fileId}
                }
            }
        )

        if delete_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Also delete from Tencent VOD
        await delete_from_tencent_vod(fileId)

        return {
            "success": True,
            "message": "Video deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))