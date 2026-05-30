import jwt

from fastapi import (
    HTTPException,
    status
)

from datetime import (
    datetime,
    timedelta,
    timezone
)

from core.config import get_settings
from schemas.auth import (
    JWTTokenResponse,
    JWTDataResponse
)


settings = get_settings()


class JWTAuthService:

    def generate_token(self, username: str) -> JWTTokenResponse:
        expire = (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.jwt_expire_minutes)
        )

        payload = {
            'username': username,
            'exp': expire,
            'iat': datetime.now(timezone.utc)
        }

        token = jwt.encode(
            payload=payload,
            key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        return JWTTokenResponse(jwt_token=token)
    
    def verify_token(self, token: str) -> JWTDataResponse:
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=(settings.jwt_algorithm,)
            )

            return JWTDataResponse(**payload)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expired'
            )
        
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token'
            )
