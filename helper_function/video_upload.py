# Tencent Cloud VOD Integration - Working Implementation
from fastapi import HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional
from core.database import courses_collection
import os
import uuid
import json
import asyncio
import logging
from core.config import settings
from tencentcloud.vod.v20180717 import vod_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import io

logger = logging.getLogger(__name__)



# Initialize client outside function for reuse
try:
    cred = credential.Credential(settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY)
    client_profile = ClientProfile(httpProfile=HttpProfile(endpoint="vod.tencentcloudapi.com"))
    vod_client_instance = vod_client.VodClient(cred, settings.TENCENT_REGION, client_profile)
except Exception as e:
    logger.error(f"Tencent client initialization failed: {e}")
    vod_client_instance = None

def upload_progress(consumed_bytes, total_bytes):
    """Progress callback for monitoring upload"""
    if total_bytes:
        rate = int(100 * consumed_bytes / total_bytes)
        if rate % 10 == 0: # Log every 10%
            logger.info(f"Upload progress: {rate}% ({consumed_bytes}/{total_bytes} bytes)")

def uploadVideo(videoFile):
    """Upload video with multipart upload for large files"""
    if not vod_client_instance:
        raise Exception("Tencent client not initialized")
    
    for attempt in range(3):
        try:
            # Step 1: Apply for upload
            params = models.ApplyUploadRequest()
            params.MediaType = "MP4"
            params.SubAppId = int(settings.TENCENT_SUB_APP_ID)
            response = vod_client_instance.ApplyUpload(params)
            
            logger.info(f"Upload approved. Region: {response.StorageRegion}")

            # Step 2: Configure COS client with extended timeouts
            cos_config = CosConfig(
                Region=response.StorageRegion,
                SecretId=response.TempCertificate.SecretId,
                SecretKey=response.TempCertificate.SecretKey,
                Token=response.TempCertificate.Token,
                Timeout=1800, # 30 minutes timeout
                Scheme='https'
            )
            cos = CosS3Client(cos_config)
            
            # Configure retry policy on the session
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=5,
                backoff_factor=2,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            cos._session.mount("https://", adapter)
            cos._session.mount("http://", adapter)

            # Step 3: Get file size and ensure proper format
            if isinstance(videoFile, bytes):
                # If it's raw bytes, convert to BytesIO
                file_size = len(videoFile)
                videoFile = io.BytesIO(videoFile)
                logger.info(f"Converted bytes to BytesIO")
            elif isinstance(videoFile, io.BytesIO):
                videoFile.seek(0, 2)
                file_size = videoFile.tell()
                videoFile.seek(0)
            elif hasattr(videoFile, 'size'):
                file_size = videoFile.size
                if hasattr(videoFile, 'seek'):
                    videoFile.seek(0)
            elif hasattr(videoFile, 'tell') and hasattr(videoFile, 'seek'):
                # Try to get size from file object
                current_pos = videoFile.tell()
                videoFile.seek(0, 2)
                file_size = videoFile.tell()
                videoFile.seek(current_pos)
            else:
                raise ValueError("Unable to determine file size from provided video object")
            
            # Step 4: Upload based on file size
            # Use multipart for files > 5MB
            if file_size > 5 * 1024 * 1024:
                logger.info("Using multipart upload for large file")
                
                # Calculate optimal part size (between 1MB and 100MB)
                part_size_mb = min(max(1, file_size // (100 * 1024 * 1024)), 100)
                
                response_upload = cos.upload_file_from_buffer(
                    Bucket=response.StorageBucket,
                    Key=response.MediaStoragePath,
                    Body=videoFile,
                    PartSize=part_size_mb, # Part size in MB
                    MAXThread=10 # Parallel upload threads
                )
            else:
                response_upload = cos.put_object(
                    Bucket=response.StorageBucket,
                    Key=response.MediaStoragePath,
                    Body=videoFile
                )

            # Step 5: Commit upload
            commitParams = models.CommitUploadRequest()
            commitParams.VodSessionKey = response.VodSessionKey
            commitParams.SubAppId = int(settings.TENCENT_SUB_APP_ID)
            commitResponse = vod_client_instance.CommitUpload(commitParams)
            logger.info(f"Video uploaded successfully: {commitResponse.FileId}")
            
            return {
                "MediaUrl": commitResponse.MediaUrl,
                "FileId": commitResponse.FileId
            }
            
        except TencentCloudSDKException as err:
            if attempt == 2:
                raise
            import time
            time.sleep(2 ** attempt) # Exponential backoff
        except Exception as err:
            logger.error(f"Upload error (attempt {attempt+1}): {err}", exc_info=True)
            if attempt == 2:
                raise
            import time
            time.sleep(2 ** attempt)

async def uploadVideoToTencent(video):
    """Main async function for video upload"""
    try:
        if not vod_client_instance:
            return None
        
        # Ensure video file is at the beginning
        if hasattr(video, 'seek'):
            video.seek(0)
            
        loop = asyncio.get_running_loop()
        
        # Upload video with extended timeout
        videoData = await asyncio.wait_for(
            loop.run_in_executor(None, uploadVideo, video),
            timeout=3600 # 1 hour timeout for very large files
        )
        
        if not videoData:
            logger.error("UploadVideo returned None")
            return None
            
        fileId = videoData["FileId"]
        mediaUrl = videoData["MediaUrl"]
        
        logger.info("Upload completed successfully")
        return {
            "file_id": fileId,
            "video_url": mediaUrl
        }
        
    except asyncio.TimeoutError:
        logger.error("Upload timed out after 1 hour")
        return None
    except Exception as err:
        logger.error(f"Video upload failed: {str(err)}", exc_info=True)
        return None

async def delete_from_tencent_vod(file_id: str):
    """Delete file from Tencent VOD"""
    try:
        if not vod_client_instance or not file_id:
            return False
        
        params = models.DeleteMediaRequest()
        params.FileId = file_id
        params.SubAppId = int(settings.TENCENT_SUB_APP_ID)
        
        response = vod_client_instance.DeleteMedia(params)
        logger.info(f"File deleted from Tencent: {file_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {str(e)}")
        return False

def extract_file_id_from_url(url: str) -> str:
    """Extract FileId from Tencent VOD URL"""
    try:
        if not url:
            return None
        
        # Tencent VOD URLs format: https://domain/subappid/fileId/transcodeId/filename.mp4
        # Extract fileId which is typically between subappid and transcodeId
        import re
        
        # Pattern 1: Standard Tencent URL with fileId in path
        match = re.search(r'/vodsgp\d+/([a-zA-Z0-9]+)/', url)
        if match:
            return match.group(1)
        
        # Pattern 2: Alternative format
        match = re.search(r'/([a-zA-Z0-9]{12,})/', url)
        if match:
            return match.group(1)
        
        # Pattern 3: Fallback - filename without extension
        match = re.search(r'/([a-zA-Z0-9]+)\.[a-zA-Z0-9]+$', url)
        if match:
            return match.group(1)
            
        logger.warning(f"Could not extract fileId from URL: {url}")
        return None
    except Exception as e:
        logger.error(f"Error extracting fileId from URL {url}: {e}")
        return None

async def upload_to_tencent_vod(file_content: bytes, filename: str):
    """Async upload function"""
    try:
        result = await uploadVideoToTencent(file_content)
        if result:
            return result
        else:
            raise Exception("Upload returned None")
    except Exception as e:
        raise Exception(f"Video upload failed: {str(e)}")

async def upload_course_video(
    course_id: str = Form(...),
    video_file: UploadFile = File(...),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None),
    order: Optional[int] = Form(None)
):
    """Upload video file to Tencent Cloud VOD"""
    try:
        # Check course exists
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Read video file content
        file_content = await video_file.read()
        
        # Upload to Tencent Cloud VOD
        tencent_result = await upload_to_tencent_vod(file_content, video_file.filename)

        # Add video to course with Tencent URLs
        video_data = {
            "fileId": tencent_result["file_id"],
            "videoUrl": tencent_result["video_url"],
            "video_title": video_title or video_file.filename,
            "video_description": video_description or "",
            "order": order or 1
        }

        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$push": {"videos": video_data}}
        )

        return {
            "success": True,
            "message": "Video uploaded to Tencent Cloud VOD successfully",
            "data": video_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_course_videos(course_id: str):
    """Get all videos for a course"""
    try:
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return {
            "success": True,
            "data": course.get("videos", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))