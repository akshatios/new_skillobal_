from fastapi import HTTPException
from fastapi import Request, Body, HTTPException, Depends, Form, File, UploadFile
from typing import Optional, List
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection, course_intro_video_collection
from helper_function.video_upload import upload_to_tencent_vod
from helper_function.image_upload import upload_image_to_tencent
from helper_function.layoutdata_update import update_layout_by_rating
from datetime import datetime

# class CourseModel(BaseModel):
#     title: str
#     description: str
#     course_image_url: str
#     rating: float = Field(ge=0, le=5)
#     price: float
#     visible: bool = True
#     instructor_id: str
#     category_id: str | None = None
#     language: str | None = None

from fastapi import Request,Body,HTTPException, Depends
from helper_function.apis_requests import get_current_user

async def create_course(
    request: Request,
    token: str = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(...),
    category_id: str = Form(...),
    language_id: str = Form(...),
    visible: bool = Form(...),
    course_image_url: Optional[UploadFile] = File(None),
    course_intro_video: Optional[UploadFile] = File(None),
    rating: Optional[float] = Form(None),
    price: Optional[float] = Form(None),
    instructor_id: Optional[str] = Form(None),
    video_title: Optional[str] = Form(None),
    video_description: Optional[str] = Form(None),
    video_order: Optional[str] = Form(None),
    video_file: List[UploadFile] = File([]),
):
    """Create course with optional video upload"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Create individual video documents
        video_ids = []
        if video_file and len(video_file) > 0 and video_file[0].filename:
            titles = video_title.split(',') if video_title else []
            descriptions = video_description.split(',') if video_description else []
            orders = video_order.split(',') if video_order else []
            
            for i, vid_file in enumerate(video_file):
                if vid_file.filename:
                    video_content = await vid_file.read()
                    video_result = await upload_to_tencent_vod(video_content, vid_file.filename)
                    
                    # Get order value, default to index if not provided
                    order_value = int(orders[i].strip()) if i < len(orders) and orders[i].strip().isdigit() else i
                    
                    video_obj = {
                        "order": order_value,
                        "video_title": titles[i].strip() if i < len(titles) else f"Video {i+1}",
                        "video_description": descriptions[i].strip() if i < len(descriptions) else "",
                        "fileId": video_result["file_id"],
                        "videoUrl": video_result["video_url"],
                        "type": "video",
                        "created_at": current_time
                    }
                    
                    # Insert each video as separate document
                    video_doc_result = await courses_videos_collection.insert_one(video_obj)
                    video_ids.append(video_doc_result.inserted_id)
        
        # Handle course image upload to Tencent Cloud
        image_obj = None
        
        if course_image_url and course_image_url.filename:
            course_image_content = await course_image_url.read()
            course_image_result = await upload_image_to_tencent(course_image_content, course_image_url.filename)
            
            image_obj = {
                "fileId": course_image_result["file_id"],
                "course_image_url": course_image_result["image_url"],
                "type": "course_image",
                "uploaded_at": current_time
            }
        
        # Handle course intro video upload
        intro_video_obj = None
        intro_video_url = None
        
        if course_intro_video and course_intro_video.filename:
            course_intro_video_content = await course_intro_video.read()
            course_intro_video_result = await upload_to_tencent_vod(course_intro_video_content, course_intro_video.filename)
            
            intro_video_obj = {
                "fileId": course_intro_video_result["file_id"],
                "videoUrl": course_intro_video_result["video_url"],
                "type": "intro_video",
                "uploaded_at": current_time
            }
            intro_video_url = course_intro_video_result["video_url"]
            


        new_course = {
            "title": title,
            "description": description,
            "category_id": ObjectId(category_id) if category_id and category_id != "string" else None,
            "language_id": ObjectId(language_id) if language_id and language_id != "string" else None,
            "visible": visible,
            "images": image_obj,
            "intro_videos": intro_video_obj,
            "videos": video_ids,
            "rating": rating,
            "price": price,
            "instructor_id": ObjectId(instructor_id) if instructor_id and instructor_id != "string" else None,
            "created_at": current_time,
            "updated_at": current_time
        }

        result = await courses_collection.insert_one(new_course)
        course_id = str(result.inserted_id)
        
        # Update all videos with course_id
        if video_ids:
            await courses_videos_collection.update_many(
                {"_id": {"$in": video_ids}},
                {"$set": {"course_id": course_id}}
            )
        

 
        new_course["_id"] = course_id
        if new_course["instructor_id"]:
            new_course["instructor_id"] = str(new_course["instructor_id"])
        if new_course["category_id"]:
            new_course["category_id"] = str(new_course["category_id"])
        if new_course["language_id"]:
            new_course["language_id"] = str(new_course["language_id"])

        if new_course["videos"]:
            new_course["videos"] = [str(vid_id) for vid_id in new_course["videos"]]

        # Auto-update layout based on rating
        try:
            await update_layout_by_rating()
        except Exception:
            pass  # Don't fail course creation if layout update fails

        # Fetch videos data for response
        videos_data = []
        if video_ids:
            videos_cursor = courses_videos_collection.find({"_id": {"$in": video_ids}})
            async for video in videos_cursor:
                video["_id"] = str(video["_id"])
                videos_data.append(video)
        
        # Format response for frontend compatibility
        response_data = {
            "_id": course_id,
            "title": title,
            "description": description,
            "images": image_obj,
            "intro_videos": intro_video_obj,
            "image_url": image_obj["course_image_url"] if image_obj else None,  # Backward compatibility
            "intro_video": intro_video_url,  # Backward compatibility
            "rating": rating or 0.0,
            "price": price or 0.0,
            "visible": visible,
            "instructor_id": str(new_course["instructor_id"]) if new_course["instructor_id"] else None,
            "category_id": str(new_course["category_id"]) if new_course["category_id"] else None,
            "language_id": str(new_course["language_id"]) if new_course["language_id"] else None,
            "videos": videos_data,  # Actual videos data
            "created_at": current_time,
            "updated_at": current_time
        }
        
        return {
            "success": True,
            "message": "Course created successfully",
            "data": response_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

