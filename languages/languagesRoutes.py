from fastapi import APIRouter
from languages.views.get_languages import get_all_languages
from languages.views.create_language import create_language
from languages.views.update_language import update_language
from languages.views.delete_language import delete_language

router = APIRouter()

# Language CRUD operations
router.add_api_route("/create", create_language, methods=["POST"], description="Create new language")
router.add_api_route("/all", get_all_languages, methods=["GET"], description="Get all languages")
router.add_api_route("/{language_id}/update", update_language, methods=["PUT"], description="Update language")
router.add_api_route("/{language_id}/delete", delete_language, methods=["DELETE"], description="Delete language")