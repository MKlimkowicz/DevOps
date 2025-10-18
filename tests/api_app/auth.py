from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is required. Please set it in your .env file.")

security = HTTPBearer(auto_error=False)


async def get_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Please provide Authorization header with Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


def verify_api_key(api_key: str) -> bool:
    return api_key == API_KEY
