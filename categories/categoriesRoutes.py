from fastapi import APIRouter
from categories.views.get_categories import get_all_categories
from categories.views.create_category import create_category
from categories.views.update_category import update_category
from categories.views.delete_category import delete_category

router = APIRouter()

# Category CRUD operations
router.add_api_route("/create", create_category, methods=["POST"], description="Create new category")
router.add_api_route("/all", get_all_categories, methods=["GET"], description="Get all categories")
router.add_api_route("/{category_id}/update", update_category, methods=["PUT"], description="Update category")
router.add_api_route("/{category_id}/delete", delete_category, methods=["DELETE"], description="Delete category")