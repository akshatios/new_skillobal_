from fastapi import APIRouter
from user.views.list_users import list_users
from user.views.adminLogin import login
from user.views.slider_home import slider_home

from documentation.userRoutesAPIDocumentation import *

user_router = APIRouter(prefix="/admin", tags=["Users"])
user_router.add_api_route("/users", list_users, methods=["GET"],description=registerAndSignInDocumentation)
user_router.add_api_route("/login", login, methods=["POST"],description=registerAndSignInDocumentation)
user_router.add_api_route("/slider", slider_home, methods=["GET"], description="Get all slider data")