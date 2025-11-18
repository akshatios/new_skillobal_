from fastapi import HTTPException, Request, Depends
from core.database import categories_collection
from helper_function.apis_requests import get_current_user

async def get_all_categories(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get all categories with id and category_name"""
    try:
        docs = await categories_collection.find({}).to_list(length=10000)
        
        categories = [
            {
                "id": str(doc.get("_id")),
                "category_name": doc.get("name")
            }
            for doc in docs
        ]
        
        return {
            "success": True,
            "message": "Categories retrieved successfully",
            "data": {
                "total_categories": len(categories),
                "categories": categories
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))