from fastapi import HTTPException, Request, Form, File, UploadFile, Depends
from bson import ObjectId
from core.database import categories_collection
from helper_function.image_upload import upload_image_to_tencent
from helper_function.apis_requests import get_current_user
from datetime import datetime

async def create_category(
    request: Request,
    token: str = Depends(get_current_user),
    name: str = Form(...),
    category_image: UploadFile = File(...),
    status: bool = Form(True)
):
    """Create new category with image upload to Tencent Cloud"""
    try:
        # Check if category already exists
        existing_category = await categories_collection.find_one({"name": name})
        if existing_category:
            raise HTTPException(status_code=400, detail={"message": f"A category with the name '{name}' already exists. Please choose a different name."})
        
        current_time = datetime.now()
        
        # Upload image to Tencent Cloud
        image_content = await category_image.read()
        image_result = await upload_image_to_tencent(image_content, category_image.filename)
        
        # Create image object
        image_obj = {
            "fileId": image_result["file_id"],
            "image_url": image_result["image_url"]
        }
        
        # Create new category  
        new_category = {
            "name": name,
            "image": image_obj,
            "status": status,
            "createdAt": current_time,
            "updatedAt": current_time
        }
        
        result = await categories_collection.insert_one(new_category)
        category_id = str(result.inserted_id)
        
        # Format response
        new_category["_id"] = category_id
        new_category["createdAt"] = new_category["createdAt"].isoformat()
        new_category["updatedAt"] = new_category["updatedAt"].isoformat()
        
        return {
            "success": True,
            "message": "Category created successfully",
            "data": new_category
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to create category. Please try again with valid data."})