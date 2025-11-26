from fastapi import HTTPException, Request, Depends
from bson import ObjectId
from core.database import languages_collection, courses_collection
from helper_function.apis_requests import get_current_user

async def delete_language(
    language_id: str,
    request: Request,
    token: str = Depends(get_current_user)
):
    """Delete language"""
    try:
        if not ObjectId.is_valid(language_id):
            raise HTTPException(status_code=400, detail={"message": "Invalid language ID format. Please provide a valid language identifier."})
        
        # Check if language exists
        language = await languages_collection.find_one({"_id": ObjectId(language_id)})
        if not language:
            raise HTTPException(status_code=404, detail={"message": "Language not found. Please verify the language ID and try again."})
        
        # Check if language is being used in courses
        courses_using_language = await courses_collection.count_documents({"language_id": ObjectId(language_id)})
        if courses_using_language > 0:
            raise HTTPException(status_code=400, detail={"message": f"Cannot delete language as it is currently being used in {courses_using_language} active course(s)."})
        
        # Delete language from database
        await languages_collection.delete_one({"_id": ObjectId(language_id)})
        
        return {
            "success": True,
            "message": "Language deleted successfully",
            "data": {
                "language_id": language_id,
                "language_name": language.get("name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to delete language. Please try again later."})