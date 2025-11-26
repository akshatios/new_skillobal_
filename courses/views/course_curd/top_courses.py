from fastapi import HTTPException, Request, Depends
from core.database import layout_collection, courses_collection
from bson import ObjectId
from helper_function.apis_requests import get_current_user

async def get_top_courses(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get top courses based on layout linked_courses"""
    try:
        # Get the specific layout document with ID 68d0d3643deb5b22c6613b61
        layout_id = "68d0d3643deb5b22c6613b61"
        layout_doc = await layout_collection.find_one({"_id": ObjectId(layout_id)})
        
        if not layout_doc:
            return {
                "success": False,
                "message": "Layout document not found",
                "data": {
                    "top_courses": [],
                    "total": 0
                }
            }
        
        # Get linked_courses from layout document
        linked_courses = layout_doc.get("linked_courses", [])
        
        if not linked_courses:
            return {
                "success": True,
                "message": "No linked courses found in layout",
                "data": {
                    "top_courses": [],
                    "total": 0
                }
            }
        
        # Convert string IDs to ObjectIds for query
        course_object_ids = []
        for course_id in linked_courses:
            try:
                course_object_ids.append(ObjectId(course_id))
            except:
                # Skip invalid ObjectId strings
                continue
        
        if not course_object_ids:
            return {
                "success": True,
                "message": "No valid course IDs found in linked_courses",
                "data": {
                    "top_courses": [],
                    "total": 0
                }
            }
        
        # Fetch matching courses from courses collection
        courses_docs = await courses_collection.find(
            {"_id": {"$in": course_object_ids}}
        ).to_list(length=1000)
        
        # Format course data
        top_courses = [
            {
                "id": str(doc.get("_id")),
                "title": doc.get("title"),
                "description": doc.get("description"),
                "image_url": doc.get("images", [{}])[0].get("course_image_url") if doc.get("images") else None,
                "rating": doc.get("rating"),
                "price": doc.get("price"),
                "visible": doc.get("visible"),
                "instructor_id": str(doc.get("instructor_id")) if doc.get("instructor_id") else None,
                "category_id": str(doc.get("category_id")) if doc.get("category_id") else None,
            }
            for doc in courses_docs
        ]
        
        return {
            "success": True,
            "message": "Top courses retrieved successfully",
            "data": {
                "layout_id": layout_id,
                "linked_courses_count": len(linked_courses),
                "matched_courses_count": len(top_courses),
                "top_courses": top_courses,
                "total": len(top_courses)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
