import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src import models

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def get_current_user(
        x_api_key: str = Header(...),
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user
