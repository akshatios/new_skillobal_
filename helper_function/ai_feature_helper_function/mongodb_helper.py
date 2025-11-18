"""
MongoDB helper functions for fetching course videos and saving results.
Add this to your helper_function folder.
"""

import aiohttp
from pathlib import Path
from bson import ObjectId
from typing import List, Dict, Any

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
) -> List[Dict[str, Any]]:
    """
    Fetch all videos for a course from MongoDB.
    
    Args:
        course_id: String ID of the course
        courses_collection: MongoDB courses collection
        courses_videos_collection: MongoDB courses_videos collection
        
    Returns:
        List of video objects with order, title, description, and videoUrl
    """
    try:
        # Step 1: Find course document
        course_doc = await courses_collection.find_one({"_id": ObjectId(course_id)})
        
        if not course_doc:
            raise Exception(f"Course not found with ID: {course_id}")
        
        # Step 2: Get videos ObjectId from course document
        videos_id = course_doc.get("videos")
        
        if not videos_id:
            raise Exception(f"No videos found for course ID: {course_id}")
        
        # Step 3: Find videos document
        videos_doc = await courses_videos_collection.find_one({"_id": videos_id})
        
        if not videos_doc:
            raise Exception(f"Videos document not found with ID: {videos_id}")
        
        # Step 4: Extract videos array
        videos = videos_doc.get("videos", [])
        
        if not videos:
            raise Exception(f"No videos in videos document for course ID: {course_id}")
        
        # Step 5: Sort videos by order
        sorted_videos = sorted(videos, key=lambda x: int(x.get("order", 0)))
        
        return sorted_videos
        
    except Exception as err:
        raise Exception(f"Failed to fetch course videos: {err}")


async def save_results_to_mongodb(
    course_id: str,
    results_data: Dict[str, Any],
    courses_collection,
    course_question_and_answers_collection
) -> str:
    """
    Save question generation results to MongoDB and update course document.
    
    Args:
        course_id: String ID of the course
        results_data: Dictionary containing all questions and summaries
        courses_collection: MongoDB courses collection
        course_question_and_answers_collection: MongoDB Q&A collection
        
    Returns:
        String ObjectId of the saved Q&A document
    """
    try:
        # Step 1: Create document for Q&A collection
        qa_document = {
            "course_id": ObjectId(course_id),
            "lecture_questions": results_data.get("lecture_questions", {}),
            "cumulative_questions": results_data.get("cumulative_questions", {}),
            "lecture_summaries": results_data.get("lecture_summaries", {}),
            "all_previous_lecture_summary": results_data.get("all_previous_lecture_summary", ""),
            "total_lectures_processed": results_data.get("total_lectures_processed", 0),
            "created_at": results_data.get("created_at"),
            "updated_at": results_data.get("updated_at")
        }
        
        # Step 2: Insert into Q&A collection
        insert_result = await course_question_and_answers_collection.insert_one(qa_document)
        qa_document_id = insert_result.inserted_id
        
        # Step 3: Update course document with Q&A reference
        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "question_answers_id": qa_document_id,
                    "updated_at": results_data.get("updated_at")
                }
            }
        )
        
        return str(qa_document_id)
        
    except Exception as err:
        raise Exception(f"Failed to save results to MongoDB: {err}")


def chunk_videos(videos: List[Dict], batch_size: int = 5) -> List[List[Dict]]:
    """
    Split videos list into batches of specified size.
    
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