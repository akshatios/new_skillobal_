from fastapi import HTTPException, Depends, Request
from user.views.list_users import list_users
from core.database import courses_collection
from courses.views.course_curd.top_courses import get_top_courses
from helper_function.apis_requests import get_current_user

async def get_dashboard_home(
    request: Request,
    token: str = Depends(get_current_user)
):
    """Get dashboard home data with statistics"""
    try:
        # Get user data (reuse existing logic)
        user_data = await list_users(request=request, token=token)
        
        # Get total courses count
        total_courses = await courses_collection.count_documents({})
        
        # Get visible courses count
        visible_courses = await courses_collection.count_documents({"visible": True})
        
        # Get top courses data
        top_courses_data = await get_top_courses(request=request, token=token)
        
        # Prepare dashboard statistics
        dashboard_stats = {
            "total_users": user_data.get("total", 0),
            "total_courses": total_courses,
            "visible_courses": visible_courses,
            "hidden_courses": total_courses - visible_courses,
            "top_courses_count": len(top_courses_data.get("data", {}).get("top_courses", []))
        }
        
        return {
            "success": True,
            "message": "Dashboard data retrieved successfully",
            "data": {
                "statistics": dashboard_stats,
                "recent_users": user_data.get("users", [])[:5],  # Last 5 users
                "top_courses": top_courses_data.get("data", {}).get("top_courses", [])[:5],  # Top 5 courses
                "summary": {
                    "users": {
                        "total": dashboard_stats["total_users"],
                        "recent_count": len(user_data.get("users", [])[:5])
                    },
                    "courses": {
                        "total": dashboard_stats["total_courses"],
                        "visible": dashboard_stats["visible_courses"],
                        "hidden": dashboard_stats["hidden_courses"]
                    },
                    "content": {
                        "top_courses": dashboard_stats["top_courses_count"]
                    }
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")