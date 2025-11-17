from fastapi import Header
async def get_current_user(token: str = Header(..., description="User authentication token")):
    return token