from fastapi import HTTPException, Request, Form, Depends
from bson import ObjectId
from core.database import languages_collection
from helper_function.apis_requests import get_current_user
from datetime import datetime
from typing import Optional

async def update_language(
    language_id: str,
    request: Request,
    token: str = Depends(get_current_user),
    name: Optional[str] = Form(None),
    status: Optional[bool] = Form(None)
):
    """Update language with optional name and status change"""
    try:
        if not ObjectId.is_valid(language_id):
            raise HTTPException(status_code=400, detail={"message": "Invalid language ID format. Please provide a valid language identifier."})
        
        # Check if language exists
        existing_language = await languages_collection.find_one({"_id": ObjectId(language_id)})
        if not existing_language:
            raise HTTPException(status_code=404, detail={"message": "Language not found. Please verify the language ID and try again."})
        
        # Check if at least one field is provided for update
        if not name and status is None:
            raise HTTPException(status_code=400, detail={"message": "No data provided for update. Please provide at least name or status to update."})
        
        # Prepare update data
        update_data = {"updatedAt": datetime.now()}
        
        # Update name if provided
        if name:
            # Check if new name already exists (excluding current language)
            name_exists = await languages_collection.find_one({
                "name": name,
                "_id": {"$ne": ObjectId(language_id)}
            })
            if name_exists:
                raise HTTPException(status_code=400, detail={"message": f"A language with the name '{name}' already exists. Please choose a different name."})
            update_data["name"] = name
        
        # Update status if provided
        if status is not None:
            update_data["status"] = status
        
        # Update language in database
        result = await languages_collection.update_one(
            {"_id": ObjectId(language_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail={"message": "Language not found. Please verify the language ID and try again."})
        
        # Get updated language
        updated_language = await languages_collection.find_one({"_id": ObjectId(language_id)})
        
        # Format response
        updated_language["_id"] = str(updated_language["_id"])
        updated_language["createdAt"] = updated_language["createdAt"].isoformat()
        updated_language["updatedAt"] = updated_language["updatedAt"].isoformat()
        
        return {
            "success": True,
            "message": "Language updated successfully",
            "data": updated_language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to update language. Please verify the data and try again."})