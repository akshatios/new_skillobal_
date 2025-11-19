from fastapi import HTTPException, Request, Depends
from core.database import languages_collection
from helper_function.apis_requests import get_current_user

async def get_all_languages(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get all languages with id and name"""
    try:
        docs = await languages_collection.find({}).to_list(length=10000)
        
        languages = [
            {
                "id": str(doc.get("_id")),
                "name": doc.get("name")
            }
            for doc in docs
        ]
        
        return {
            "success": True,
            "message": "Languages retrieved successfully",
            "data": {
                "total_languages": len(languages),
                "languages": languages
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))