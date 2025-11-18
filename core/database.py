from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
from core.config import db_settings

# Create a MongoDB client
client = MongoClient(db_settings.MONGODB_URI)

# Access the default database
db = client.get_database(db_settings.DB_NAME)  # This uses the default database from the URI

# Define collections
users_collection = db.users
testimonials_collection = db.testimonials
sponsors_collection = db.sponsors
mobile_otp_collection = db.mobile_otps
layout_collection = db.layout
instructors_collection = db.instructor
email_otp_collection = db.email_otps
dashboard_collection = db.dashboard
courses_videos_collection = db.courses_videos
courses_collection = db.courses
course_intro_video_collection = db.course_intro_video
contact_collection = db.contact
categories_collection = db.categories
admins_collection = db.admins
question_and_answer_collection = db["Q&A"]
course_question_and_answers_collection = db.course_question_and_answers