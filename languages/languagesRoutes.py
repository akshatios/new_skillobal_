from fastapi import APIRouter
from languages.views.get_languages import get_all_languages

router = APIRouter()

# Get all languages
router.add_api_route("/all", get_all_languages, methods=["GET"])