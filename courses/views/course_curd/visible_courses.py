from fastapi import HTTPException, Request, Depends
from core.database import courses_collection
from helper_function.apis_requests import get_current_user

async def get_visible_courses(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get visible courses count and data"""
    try:
        # Fetch only courses where visible is true
        docs = await courses_collection.find({"visible": True}).to_list(length=10000)
        
        courses = [
            {
                "id": str(doc.get("_id")),
                "title": doc.get("title"),
                "description": doc.get("description"),
                "image_url": doc.get("imageUrl") or doc.get("course_image_url"),
                "rating": doc.get("rating"),
                "price": doc.get("price"),
                "visible": doc.get("visible"),
                "instructor_id": str(doc.get("instructor_id")) if doc.get("instructor_id") else None,
                "category_id": str(doc.get("category_id")) if doc.get("category_id") else None,
            }
            for doc in docs
        ]
        
        return {
            "success": True,
            "message": "Visible courses retrieved successfully",
            "data": {
                "total_visible_courses": len(courses),
                "courses": courses
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
