from fastapi import HTTPException, Depends
from core.database import courses_videos_collection
from helper_function.video_upload import delete_from_tencent_vod
from helper_function.apis_requests import get_current_user
import logging

logger = logging.getLogger(__name__)

async def delete_all_course_videos_from_tencent(
    token: str = Depends(get_current_user)
):
    """Delete all course videos from courses_videos collection and Tencent Cloud"""
    try:
        # Get all video containers from collection
        video_containers = await courses_videos_collection.find({}).to_list(None)
        
        if not video_containers:
            return {
                "success": True,
                "message": "No course videos found to delete",
                "data": {
                    "total_containers": 0,
                    "total_videos": 0,
                    "deleted_from_tencent": 0,
                    "deleted_from_database": 0,
                    "failed_deletions": []
                }
            }
        
        deleted_from_tencent = []
        failed_deletions = []
        total_videos = 0
        
        # Process each video container
        for container in video_containers:
            # Check if container has videos array
            if "videos" in container and isinstance(container["videos"], list):
                for video in container["videos"]:
                    total_videos += 1
                    file_id = None
                    
                    # Try to get fileId from different possible fields
                    if "fileId" in video and video["fileId"]:
                        file_id = video["fileId"]
                    elif "file_id" in video and video["file_id"]:
                        file_id = video["file_id"]
                    elif "FileId" in video and video["FileId"]:
                        file_id = video["FileId"]
                    
                    if file_id:
                        success = await delete_from_tencent_vod(file_id)
                        if success:
                            deleted_from_tencent.append(file_id)
                            logger.info(f"Successfully deleted course video from Tencent: {file_id}")
                        else:
                            failed_deletions.append(file_id)
                            logger.error(f"Failed to delete course video from Tencent: {file_id}")
                    else:
                        logger.warning(f"No fileId found for video in container: {container.get('_id', 'Unknown')}")
        
        # Delete all video containers from database collection
        delete_result = await courses_videos_collection.delete_many({})
        deleted_from_database = delete_result.deleted_count
        
        response = {
            "success": True,
            "message": f"Processed {len(video_containers)} video containers with {total_videos} videos",
            "data": {
                "total_containers": len(video_containers),
                "total_videos": total_videos,
                "deleted_from_tencent": len(deleted_from_tencent),
                "deleted_from_database": deleted_from_database,
                "failed_deletions": failed_deletions,
                "tencent_deleted_files": deleted_from_tencent
            }
        }
        
        if failed_deletions:
            response["message"] += f" (Warning: {len(failed_deletions)} files could not be deleted from Tencent Cloud)"
        
        return response
        
    except Exception as e:
        logger.error(f"Error deleting all course videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete course videos: {str(e)}")