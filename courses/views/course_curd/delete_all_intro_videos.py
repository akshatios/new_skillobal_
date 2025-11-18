from fastapi import HTTPException, Depends
from core.database import course_intro_video_collection
from helper_function.video_upload import delete_from_tencent_vod
from helper_function.apis_requests import get_current_user
import logging

logger = logging.getLogger(__name__)

async def delete_all_intro_videos_from_tencent(
    token: str = Depends(get_current_user)
):
    """Delete all intro videos from course_intro_video collection and Tencent Cloud"""
    try:
        # Get all intro videos from collection
        intro_videos = await course_intro_video_collection.find({}).to_list(None)
        
        if not intro_videos:
            return {
                "success": True,
                "message": "No intro videos found to delete",
                "data": {
                    "total_found": 0,
                    "deleted_from_tencent": 0,
                    "deleted_from_database": 0,
                    "failed_deletions": []
                }
            }
        
        deleted_from_tencent = []
        failed_deletions = []
        
        # Delete each video from Tencent Cloud
        for video in intro_videos:
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
                    logger.info(f"Successfully deleted intro video from Tencent: {file_id}")
                else:
                    failed_deletions.append(file_id)
                    logger.error(f"Failed to delete intro video from Tencent: {file_id}")
            else:
                logger.warning(f"No fileId found for intro video: {video.get('_id', 'Unknown')}")
        
        # Delete all intro videos from database collection
        delete_result = await course_intro_video_collection.delete_many({})
        deleted_from_database = delete_result.deleted_count
        
        response = {
            "success": True,
            "message": f"Processed {len(intro_videos)} intro videos",
            "data": {
                "total_found": len(intro_videos),
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
        logger.error(f"Error deleting all intro videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete intro videos: {str(e)}")