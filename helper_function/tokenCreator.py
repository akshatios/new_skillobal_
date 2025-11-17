import jwt
from core.config import jwt_settings

async def tokenCreator(data):

    try:
        SUGAR_VALUE = jwt_settings.SUGAR_VALUE
        token = jwt.encode(data, SUGAR_VALUE, algorithm="HS256")
        return token

    except Exception as e:
        raise ValueError(str("error in token generation"))