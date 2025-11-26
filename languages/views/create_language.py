from fastapi import HTTPException, Request, Form, Depends
from bson import ObjectId
from core.database import languages_collection
from helper_function.apis_requests import get_current_user
from datetime import datetime

async def create_language(
    request: Request,
    token: str = Depends(get_current_user),
    name: str = Form(...),
    status: bool = Form(True)
):
    """Create new language"""
    try:
        # Check if language already exists
        existing_language = await languages_collection.find_one({"name": name})
        if existing_language:
            raise HTTPException(status_code=400, detail={"message": f"A language with the name '{name}' already exists. Please choose a different name."})
        
        current_time = datetime.now()
        
        # Create new language
        new_language = {
            "name": name,
            "status": status,
            "createdAt": current_time,
            "updatedAt": current_time
        }
        
        result = await languages_collection.insert_one(new_language)
        language_id = str(result.inserted_id)
        
        # Format response
        new_language["_id"] = language_id
        new_language["createdAt"] = new_language["createdAt"].isoformat()
        new_language["updatedAt"] = new_language["updatedAt"].isoformat()
        
        return {
            "success": True,
            "message": "Language created successfully",
            "data": new_language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to create language. Please try again with valid data."})