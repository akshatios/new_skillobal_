from datetime import datetime
from fastapi.responses import JSONResponse
from core.database import admins_collection
from fastapi import Request,Body,HTTPException
from helper_function.tokenCreator import tokenCreator
from helper_function.apis_requests import get_current_user
from helper_function.Creating_and_Verifing_Password import verify_password
async def login(request:Request, body: dict = Body(
        example={
            "email": "a6PZg@example.com",
            "password": "123456"
        },
    )):

    try:
        email = body.get("email")
        password = body.get("password")
        print(email,password)
        if not email or not password:
            return JSONResponse(
                {"msg": "email and password are required"}, status_code=400
            )
        user = await admins_collection.find_one({"email": email})
        if not user or not verify_password(password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await admins_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": now}}
        )
        token = await tokenCreator({"id": str(user["_id"])})
        return {"access_token": token, "token_type": "bearer"}
    except Exception as err:
        return JSONResponse(
            {"msg": "something went wrong", "err": str(err)}, status_code=500
        )