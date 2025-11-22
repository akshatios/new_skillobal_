from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import categories_collection, courses_collection
from helper_function.video_upload import delete_from_tencent_vod
from helper_function.apis_requests import get_current_user

async def delete_category(
    category_id: str,
    request: Request,
    token: str = Depends(get_current_user)
):
    """Delete category and its image from Tencent Cloud"""
    try:
        if not ObjectId.is_valid(category_id):
            raise HTTPException(status_code=400, detail={"message": "Invalid category ID format. Please provide a valid category identifier."})
        
        # Check if category exists
        category = await categories_collection.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise HTTPException(status_code=404, detail={"message": "Category not found. Please verify the category ID and try again."})
        
        # Check if category is being used in courses
        courses_using_category = await courses_collection.count_documents({"category_id": ObjectId(category_id)})
        if courses_using_category > 0:
            raise HTTPException(status_code=400, detail={"message": f"Cannot delete category as it is currently being used in {courses_using_category} active course(s)."})
        
        # Delete image from Tencent Cloud
        deleted_from_tencent = False
        if "image" in category and category["image"]:
            image_obj = category["image"]
            if "fileId" in image_obj and image_obj["fileId"]:
                success = await delete_from_tencent_vod(image_obj["fileId"])
                deleted_from_tencent = success
        elif "image_url" in category and category["image_url"]:
            image_obj = category["image_url"]
            if "fileId" in image_obj and image_obj["fileId"]:
                success = await delete_from_tencent_vod(image_obj["fileId"])
                deleted_from_tencent = success
        
        # Delete category from database
        await categories_collection.delete_one({"_id": ObjectId(category_id)})
        
        return {
            "success": True,
            "message": "Category deleted successfully",
            "data": {
                "category_id": category_id,
                "category_name": category.get("name"),
                "deleted_from_tencent": deleted_from_tencent,
                "image_fileId": category["image"]["fileId"] if category.get("image") else (category["image_url"]["fileId"] if category.get("image_url") else None)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to delete category. Please try again later."})