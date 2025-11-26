from fastapi import HTTPException, Request, Depends
from core.database import instructors_collection
from helper_function.apis_requests import get_current_user

async def get_all_instructors(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get all instructors with id and instructor_name"""
    try:
        docs = await instructors_collection.find({}).to_list(length=10000)  
        instructors = [
            {
                "id": str(doc.get("_id")),
                "instructor_name": doc.get("name")
            }
            for doc in docs
        ]
        
        return {
            "success": True,
            "message": "Instructors retrieved successfully",
            "data": {
                "total_instructors": len(instructors),
                "instructors": instructors
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))