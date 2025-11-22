from fastapi import HTTPException, Request, Form, File, UploadFile, Depends
from bson import ObjectId
from core.database import categories_collection
from helper_function.image_upload import upload_image_to_tencent
from helper_function.video_upload import delete_from_tencent_vod
from helper_function.apis_requests import get_current_user
from datetime import datetime
from typing import Optional

async def update_category(
    category_id: str,
    request: Request,
    token: str = Depends(get_current_user),
    name: Optional[str] = Form(None),
    category_image: Optional[UploadFile] = File(None),
    status: Optional[bool] = Form(None)
):
    """Update category with optional name and image change"""
    try:
        if not ObjectId.is_valid(category_id):
            raise HTTPException(status_code=400, detail={"message": "Invalid category ID format. Please provide a valid category identifier."})
        
        # Check if category exists
        existing_category = await categories_collection.find_one({"_id": ObjectId(category_id)})
        if not existing_category:
            raise HTTPException(status_code=404, detail={"message": "Category not found. Please verify the category ID and try again."})
        
        # Check if at least one field is provided for update
        if not name and not category_image and status is None:
            raise HTTPException(status_code=400, detail={"message": "No data provided for update. Please provide at least name, image, or status to update."})
        
        # Prepare update data
        update_data = {"updatedAt": datetime.now()}
        old_image_file_id = None
        
        # Update name if provided
        if name:
            # Check if new name already exists (excluding current category)
            name_exists = await categories_collection.find_one({
                "name": name,
                "_id": {"$ne": ObjectId(category_id)}
            })
            if name_exists:
                raise HTTPException(status_code=400, detail={"message": f"A category with the name '{name}' already exists. Please choose a different name."})
            update_data["name"] = name
        
        # Update status if provided
        if status is not None:
            update_data["status"] = status
        
        # Update image if provided
        if category_image:
            # Store old image fileId for deletion
            if "image" in existing_category and existing_category["image"]:
                old_image_file_id = existing_category["image"].get("fileId")
            elif "image_url" in existing_category and existing_category["image_url"]:
                old_image_file_id = existing_category["image_url"].get("fileId")
            
            # Upload new image to Tencent Cloud
            image_content = await category_image.read()
            image_result = await upload_image_to_tencent(image_content, category_image.filename)
            
            # Create new image object
            update_data["image"] = {
                "fileId": image_result["file_id"],
                "image_url": image_result["image_url"]
            }
        
        # Update category in database
        result = await categories_collection.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail={"message": "Category not found. Please verify the category ID and try again."})
        
        # Delete old image from Tencent Cloud if new image was uploaded
        deleted_from_tencent = False
        if old_image_file_id and category_image:
            deleted_from_tencent = await delete_from_tencent_vod(old_image_file_id)
        
        # Get updated category
        updated_category = await categories_collection.find_one({"_id": ObjectId(category_id)})
        
        # Format response
        updated_category["_id"] = str(updated_category["_id"])
        updated_category["createdAt"] = updated_category["createdAt"].isoformat()
        updated_category["updatedAt"] = updated_category["updatedAt"].isoformat()
        
        return {
            "success": True,
            "message": "Category updated successfully",
            "data": {
                "category": updated_category,
                "old_image_deleted": deleted_from_tencent,
                "old_image_fileId": old_image_file_id if old_image_file_id else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update category error: {str(e)}")
        raise HTTPException(status_code=500, detail={"message": "Failed to update category. Please verify the data and try again."})