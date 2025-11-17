from fastapi import HTTPException
from fastapi import Request, Body, HTTPException, Depends, Form, File, UploadFile
from typing import Optional, List
from bson import ObjectId
from core.database import courses_collection, courses_videos_collection, course_intro_video_collection
from helper_function.video_upload import upload_to_tencent_vod
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
    language: str = Form(...),
    visible: bool = Form(...),
    course_image_url: str = Form(...),
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
        print(1)
        # Create video container for this course
        videos_container_id = None
        if video_file and len(video_file) > 0 and video_file[0].filename:
            titles = video_title.split(',') if video_title else []
            descriptions = video_description.split(',') if video_description else []
            orders = video_order.split(',') if video_order else []
            
            videos_list = []
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
                        "type": "video"
                    }
                    videos_list.append(video_obj)
            
            # Create video container with all videos
            if videos_list:
                video_container = {
                    "videos": videos_list,
                    "created_at": current_time
                }
                container_result = await courses_videos_collection.insert_one(video_container)
                videos_container_id = container_result.inserted_id
        
        # Handle course intro video upload to separate collection
        course_intro_video_id = None
        intro_video_url = None
        
        if course_intro_video and course_intro_video.filename:
            course_intro_video_content = await course_intro_video.read()
            course_intro_video_result = await upload_to_tencent_vod(course_intro_video_content, course_intro_video.filename)
            
            intro_video_obj = {
                "fileId": course_intro_video_result["file_id"],
                "videoUrl": course_intro_video_result["video_url"],
                "created_at": current_time
            }
            
            # Insert into course_intro_video collection
            intro_video_result = await course_intro_video_collection.insert_one(intro_video_obj)
            course_intro_video_id = intro_video_result.inserted_id
            intro_video_url = course_intro_video_result["video_url"]
            


        new_course = {
            "title": title,
            "description": description,
            "category_id": ObjectId(category_id) if category_id and category_id != "string" else None,
            "language": language,
            "visible": visible,
            "course_image_url": course_image_url,
            "course_intro_video_id": course_intro_video_id,
            "videos": videos_container_id,
            "rating": rating,
            "price": price,
            "instructor_id": ObjectId(instructor_id) if instructor_id and instructor_id != "string" else None,
            "created_at": current_time,
            "updated_at": current_time
        }

        result = await courses_collection.insert_one(new_course)
        course_id = str(result.inserted_id)
        
        # Update video container with course_id
        if videos_container_id:
            await courses_videos_collection.update_one(
                {"_id": videos_container_id},
                {"$set": {"course_id": course_id}}
            )
        
        # Update course intro video with course_id
        if course_intro_video_id:
            await course_intro_video_collection.update_one(
                {"_id": course_intro_video_id},
                {"$set": {"course_id": course_id}}
            )

        new_course["_id"] = course_id
        if new_course["instructor_id"]:
            new_course["instructor_id"] = str(new_course["instructor_id"])
        if new_course["category_id"]:
            new_course["category_id"] = str(new_course["category_id"])
        if new_course["course_intro_video_id"]:
            new_course["course_intro_video_id"] = str(new_course["course_intro_video_id"])
        if new_course["videos"]:
            new_course["videos"] = str(new_course["videos"])

        # Auto-update layout based on rating
        try:
            await update_layout_by_rating()
        except Exception:
            pass  # Don't fail course creation if layout update fails

        # Format response for frontend compatibility
        response_data = {
            "_id": course_id,
            "title": title,
            "description": description,
            "image_url": course_image_url,  # Frontend expects image_url
            "rating": rating or 0.0,
            "price": price or 0.0,
            "visible": visible,
            "instructor_id": str(new_course["instructor_id"]) if new_course["instructor_id"] else None,
            "category_id": str(new_course["category_id"]) if new_course["category_id"] else None,
            "content_language": language,
            "videos": [],  # Frontend expects empty array for course videos
            "intro_video": intro_video_url,  # Frontend expects intro_video
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

