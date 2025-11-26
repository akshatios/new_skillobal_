from bson import ObjectId
from core.database import categories_collection, languages_collection, instructors_collection, courses_collection
import logging

logger = logging.getLogger(__name__)

async def validate_course_references(course):
    """Validate and filter invalid references in course data and update database"""
    
    course_updated = False
    original_categories = course.get("category_id", [])
    original_languages = course.get("language_id", [])
    original_instructors = course.get("instructor_id", [])
    
    # Validate category_id (handle both array and single value)
    if "category_id" in course and course["category_id"]:
        if isinstance(course["category_id"], list):
            valid_categories = []
            for cat_id in course["category_id"]:
                if isinstance(cat_id, str):
                    cat_id = ObjectId(cat_id)
                exists = await categories_collection.find_one({"_id": cat_id, "status": True})
                logger.info(f"Checking category {cat_id}: exists={bool(exists)}")
                if exists:
                    valid_categories.append(cat_id)
            if len(valid_categories) != len(course["category_id"]):
                course_updated = True
            course["category_id"] = valid_categories
        else:
            # Single value - validate and keep or remove
            cat_id = course["category_id"]
            if isinstance(cat_id, str):
                cat_id = ObjectId(cat_id)
            exists = await categories_collection.find_one({"_id": cat_id, "status": True})
            if not exists:
                course["category_id"] = None
                course_updated = True
    
    # Validate language_id (handle both array and single value)
    if "language_id" in course and course["language_id"]:
        if isinstance(course["language_id"], list):
            valid_languages = []
            for lang_id in course["language_id"]:
                if isinstance(lang_id, str):
                    lang_id = ObjectId(lang_id)
                exists = await languages_collection.find_one({"_id": lang_id, "status": True})
                if exists:
                    valid_languages.append(lang_id)
            if len(valid_languages) != len(course["language_id"]):
                course_updated = True
            course["language_id"] = valid_languages
        else:
            # Single value - validate and keep or remove
            lang_id = course["language_id"]
            if isinstance(lang_id, str):
                lang_id = ObjectId(lang_id)
            exists = await languages_collection.find_one({"_id": lang_id, "status": True})
            if not exists:
                course["language_id"] = None
                course_updated = True
    
    # Validate instructor_id (handle both array and single value)
    if "instructor_id" in course and course["instructor_id"]:
        if isinstance(course["instructor_id"], list):
            valid_instructors = []
            for inst_id in course["instructor_id"]:
                if isinstance(inst_id, str):
                    inst_id = ObjectId(inst_id)
                exists = await instructors_collection.find_one({"_id": inst_id, "status": True})
                if exists:
                    valid_instructors.append(inst_id)
            if len(valid_instructors) != len(course["instructor_id"]):
                course_updated = True
            course["instructor_id"] = valid_instructors
        else:
            # Single value - validate and keep or remove
            inst_id = course["instructor_id"]
            if isinstance(inst_id, str):
                inst_id = ObjectId(inst_id)
            exists = await instructors_collection.find_one({"_id": inst_id, "status": True})
            if not exists:
                course["instructor_id"] = None
                course_updated = True
    
    # Update database if references were cleaned
    if course_updated:
        update_data = {}
        if "category_id" in course:
            update_data["category_id"] = course["category_id"]
        if "language_id" in course:
            update_data["language_id"] = course["language_id"]
        if "instructor_id" in course:
            update_data["instructor_id"] = course["instructor_id"]
        
        await courses_collection.update_one(
            {"_id": course["_id"]},
            {"$set": update_data}
        )
    
    return course