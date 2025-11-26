# Tencent Cloud VOD Image Upload (same as video upload approach)
import os
import asyncio
import time
import logging
from core.config import settings
from tencentcloud.vod.v20180717 import vod_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

logger = logging.getLogger(__name__)

# Initialize VOD client (same as video upload)
try:
    cred = credential.Credential(settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY)
    client_profile = ClientProfile(httpProfile=HttpProfile(endpoint="vod.tencentcloudapi.com"))
    vod_client_instance = vod_client.VodClient(cred, settings.TENCENT_REGION, client_profile)
except Exception as e:
    logger.error(f"Tencent VOD client initialization failed: {e}")
    vod_client_instance = None

def uploadImageAsMedia(image_bytes: bytes, filename: str):
    """Upload image as a media file using VOD service"""
    if not vod_client_instance:
        raise Exception("Tencent VOD client not initialized")

    # Determine image type and set MediaType
    ext = os.path.splitext(filename)[1].lower() if filename else ".jpg"
    if ext in (".jpg", ".jpeg"):
        media_type = "jpg"
    elif ext == ".png":
        media_type = "png"
    else:
        raise Exception(f"Unsupported format: {ext}")

    # ApplyUpload - Upload image as media file
    apply_req = models.ApplyUploadRequest()
    apply_req.MediaType = media_type  # Use image format as MediaType
    apply_req.MediaName = filename or f"image.{media_type}"
    apply_req.SubAppId = int(settings.TENCENT_SUB_APP_ID)

    apply_resp = vod_client_instance.ApplyUpload(apply_req)

    bucket = apply_resp.StorageBucket
    region = apply_resp.StorageRegion

    # Use MediaStoragePath for media files
    media_path = apply_resp.MediaStoragePath
    if media_path.startswith("/"):
        media_path = media_path[1:]  # Remove leading slash

    cos_url = f"https://{bucket}.cos.{region}.myqcloud.com/{media_path}"
    logger.info(f"ApplyUpload -> bucket={bucket}, media_path={media_path}")

    # Upload to COS as media file
    cos = CosS3Client(CosConfig(
        Region=region,
        SecretId=apply_resp.TempCertificate.SecretId,
        SecretKey=apply_resp.TempCertificate.SecretKey,
        Token=apply_resp.TempCertificate.Token,
    ))

    # Upload without ACL (use default permissions)
    cos.put_object(
        Bucket=bucket,
        Body=image_bytes,
        Key=media_path,
        StorageClass="STANDARD",
        ContentType=f"image/{media_type}",
    )
    logger.info(f"Uploaded to COS at ({cos_url})")

    # Create a presigned URL for reliable access
    presigned_url = cos_url
    try:
        presigned_url = cos.get_presigned_download_url(
            Bucket=bucket,
            Key=media_path,
            Expired=315360000  # 10 years
        )
        logger.info("Generated presigned URL for media file")
    except Exception as e:
        logger.warning(f"Failed to generate presigned URL: {e}")
        presigned_url = cos_url

    # Wait for COS processing
    time.sleep(2)

    # CommitUpload for media file
    commit_req = models.CommitUploadRequest()
    commit_req.VodSessionKey = apply_resp.VodSessionKey
    commit_req.SubAppId = int(settings.TENCENT_SUB_APP_ID)

    commit_resp = vod_client_instance.CommitUpload(commit_req)
    logger.info(f"✅ Media upload succeeded: FileId={commit_resp.FileId}")

    # Return the best available URL: MediaUrl > presigned > direct COS
    final_url = commit_resp.MediaUrl or presigned_url or cos_url
    return {"imageUrl": final_url, "FileId": commit_resp.FileId}

def uploadImage(image_bytes: bytes, filename: str):
    """Original cover upload method with fallbacks"""
    if not vod_client_instance:
        raise Exception("Tencent VOD client not initialized")

    # Try uploading as media file first (better for public access)
    try:
        return uploadImageAsMedia(image_bytes, filename)
    except Exception as media_error:
        logger.warning(f"Media upload failed, trying cover upload: {media_error}")

    # Fallback to cover upload
    ext = os.path.splitext(filename)[1].lower() if filename else ".jpg"
    if ext in (".jpg", ".jpeg"):
        cover_type = "jpg"
    elif ext == ".png":
        cover_type = "png"
    else:
        raise Exception(f"Unsupported format: {ext}")

    # ApplyUpload for cover
    apply_req = models.ApplyUploadRequest()
    apply_req.CoverType = cover_type
    apply_req.SubAppId = int(settings.TENCENT_SUB_APP_ID)

    apply_resp = vod_client_instance.ApplyUpload(apply_req)

    bucket = apply_resp.StorageBucket
    region = apply_resp.StorageRegion
    cover_path = apply_resp.CoverStoragePath.lstrip("/")

    # Upload to COS
    cos = CosS3Client(CosConfig(
        Region=region,
        SecretId=apply_resp.TempCertificate.SecretId,
        SecretKey=apply_resp.TempCertificate.SecretKey,
        Token=apply_resp.TempCertificate.Token,
    ))

    cos.put_object(
        Bucket=bucket,
        Body=image_bytes,
        Key=cover_path,
        StorageClass="STANDARD",
        ContentType=f"image/{cover_type}",
    )

    # Generate a presigned URL for reliable access
    signed_url = cos.get_presigned_download_url(
        Bucket=bucket,
        Key=cover_path,
        Expired=315360000  # 10 years
    )

    logger.info(f"Cover uploaded, using signed URL: {signed_url}")
    return {"imageUrl": signed_url, "FileId": None}

async def uploadImageToTencent(image: bytes, filename: str):
    """Async wrapper for image upload"""
    logger.info("🚀 Starting Tencent image upload")
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, uploadImage, image, filename)
        return result
    except TencentCloudSDKException as e:
        logger.error(f"VOD error: {e}", exc_info=True)
        raise Exception(f"Image upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise Exception(f"Image upload failed: {str(e)}")

# Legacy function name for compatibility
async def upload_image_to_tencent(image_content: bytes, filename: str):
    """Legacy function name - redirects to new implementation"""
    result = await uploadImageToTencent(image_content, filename)
    return {
        "file_id": result["FileId"],
        "image_url": result["imageUrl"]
    }