"""
MongoDB helper functions for fetching course videos and saving results.
Updated to handle new video storage format and batch processing.
"""

import aiohttp
from pathlib import Path
from bson import ObjectId
from typing import List, Dict, Any, Tuple

async def download_video_from_url(video_url: str, save_path: Path) -> None:
    """
    Download video from URL and save to local path.
    
    Args:
        video_url: URL of the video to download
        save_path: Local path where video will be saved
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download video. Status: {response.status}")
                
                # Download in chunks to handle large files
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(save_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        
    except Exception as err:
        raise Exception(f"Video download failed: {err}")


async def fetch_course_videos(
    course_id: str,
    courses_collection,
    courses_videos_collection
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Fetch all videos for a course from MongoDB, filtering only ObjectId entries.
    
    Args:
        course_id: String ID of the course
        courses_collection: MongoDB courses collection
        courses_videos_collection: MongoDB courses_videos collection
        
    Returns:
        Tuple of (list of video objects, list of skipped non-ObjectId entries)
    """
    try:
        # Step 1: Find course document
        course_doc = await courses_collection.find_one({"_id": ObjectId(course_id)})
        
        if not course_doc:
            raise Exception(f"Course not found with ID: {course_id}")
        
        # Step 2: Get videos array from course document
        videos_array = course_doc.get("videos", [])
        
        if not videos_array:
            raise Exception(f"No videos array found for course ID: {course_id}")
        
        # Step 3: Filter only ObjectId entries and track skipped items
        valid_video_ids = []
        skipped_items = []
        
        for item in videos_array:
            if isinstance(item, ObjectId):
                valid_video_ids.append(item)
            else:
                skipped_items.append(str(item))
        
        if not valid_video_ids:
            raise Exception(f"No valid video ObjectIds found for course ID: {course_id}")
        
        # Step 4: Fetch all video documents
        cursor = courses_videos_collection.find({"_id": {"$in": valid_video_ids}})
        video_docs = await cursor.to_list(length=None)
        
        if not video_docs:
            raise Exception(f"No video documents found for course ID: {course_id}")
        
        # Step 5: Sort videos by order field
        sorted_videos = sorted(video_docs, key=lambda x: int(x.get("order", 0)))
        
        return sorted_videos, skipped_items
        
    except Exception as err:
        raise Exception(f"Failed to fetch course videos: {err}")


async def save_video_results(
    video_id: str,
    video_data: Dict[str, Any],
    courses_videos_collection
) -> bool:
    """
    Save question and summary results directly to video document.
    
    Args:
        video_id: String ObjectId of the video
        video_data: Dictionary containing questions and summaries
        courses_videos_collection: MongoDB courses_videos collection
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare update document
        update_doc = {
            "$set": {
                "ai_generated_content": {
                    "individual_questions": video_data.get("individual_questions"),
                    "cumulative_questions": video_data.get("cumulative_questions"),
                    "concise_summary": video_data.get("concise_summary"),
                    "detailed_summary": video_data.get("detailed_summary"),
                    "cumulative_summary_up_to_here": video_data.get("cumulative_summary_up_to_here"),
                    "processed_at": video_data.get("processed_at")
                }
            }
        }
        
        # Update video document
        result = await courses_videos_collection.update_one(
            {"_id": ObjectId(video_id)},
            update_doc
        )
        
        return result.modified_count > 0
        
    except Exception as err:
        raise Exception(f"Failed to save video results: {err}")


def chunk_videos(videos: List[Dict], batch_size: int = 5) -> List[List[Dict]]:
    """
    Split videos list into batches of specified size for RAM management.
    
    Args:
        videos: List of video objects
        batch_size: Number of videos per batch (default: 5)
        
    Returns:
        List of video batches
    """
    batches = []
    for i in range(0, len(videos), batch_size):
        batches.append(videos[i:i + batch_size])
    return batches


async def cleanup_batch_files(batch_paths: List[Path]) -> None:
    """
    Clean up files from a processed batch to free RAM.
    
    Args:
        batch_paths: List of paths to delete
    """
    import os
    import shutil
    
    for path in batch_paths:
        try:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        except Exception:
            pass  # Ignore cleanup errors