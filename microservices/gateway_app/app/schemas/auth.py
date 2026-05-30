from pydantic import BaseModel

from datetime import datetime


class JWTTokenResponse(BaseModel):
    jwt_token: str


class JWTDataResponse(BaseModel):
    username: str
    exp: datetime
    iat: datetime
