from fastapi import APIRouter
from documentation.aiFetureDocumentation import LactureQuestionAnswerGenerationModel
from ai_features.views.QuestionAnswerGenerationModel import QuestionAnswerGenerationModel

aiFeatureRoutes = APIRouter(prefix="/Ai_Features", tags=["AI"])


aiFeatureRoutes.add_api_route("/LactureQuestionAnswerGenerationModel", QuestionAnswerGenerationModel, methods=["POST"], description=LactureQuestionAnswerGenerationModel)
