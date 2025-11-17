from core.database import users_collection, courses_collection

from fastapi import Request, Depends
from bson import ObjectId
from fastapi.responses import JSONResponse
from helper_function.apis_requests import get_current_user
from core.database import users_collection
async def list_users(request:Request, token: str = Depends(get_current_user)):

    try:
        docs = await users_collection.find().to_list(length=10000)
        users = [
            {   
                "name": doc.get("name"),
                "id": str(doc.get("_id")),
                "email": doc.get("email"),
                "created_at": doc.get("created_at"),
            }
            for doc in docs
        ]

        # Count active (visible) courses
        active_courses = await courses_collection.count_documents({"visible": True})

        return {"total": len(users), "activeCourses": active_courses, "users": users}

    except Exception as err:
        return JSONResponse(
            {"msg": "something went wrong", "err": str(err)}, status_code=500
        )
